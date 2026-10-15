"""Estimate a recipe's nutrients from its ingredient lines with USDA FoodData Central.

1. Claude reads each ingredient line and writes a USDA-style search term,
   or marks the line as skipped ("salt and pepper to taste", water).
2. FoodData Central search returns candidate foods with nutrients per 100 g.
   SR Legacy is searched first: its nutrient profiles are complete, while many
   Foundation entries lack basics like energy or protein.
3. Claude picks the best candidate per line and estimates the line's weight in grams.
4. Nutrients are summed over all matched lines (whole-recipe totals).
"""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import lru_cache

import anthropic
import httpx
from pydantic import BaseModel, Field

MODEL = "claude-haiku-5-5"
FDC_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
CANDIDATES_PER_LINE = 6

# (key, label, USDA nutrient numbers in order of preference, unit, FDA daily value, group).
# Energy has fallbacks because some entries only list Atwater-factor energy.
NUTRIENTS = [
    ("calories", "Calories", ["208", "958", "957"], "kcal", 2000, "macro"),
    ("protein", "Protein", ["203"], "g", 50, "macro"),
    ("carbs", "Carbohydrates", ["205"], "g", 275, "macro"),
    ("fiber", "Fiber", ["291"], "g", 28, "macro"),
    ("sugars", "Sugars", ["269"], "g", None, "macro"),
    ("fat", "Fat", ["204"], "g", 78, "macro"),
    ("saturated_fat", "Saturated fat", ["606"], "g", 20, "macro"),
    ("cholesterol", "Cholesterol", ["601"], "mg", 300, "macro"),
    ("sodium", "Sodium", ["307"], "mg", 2300, "micro"),
    ("potassium", "Potassium", ["306"], "mg", 4700, "micro"),
    ("calcium", "Calcium", ["301"], "mg", 1300, "micro"),
    ("iron", "Iron", ["303"], "mg", 18, "micro"),
    ("magnesium", "Magnesium", ["304"], "mg", 420, "micro"),
    ("zinc", "Zinc", ["309"], "mg", 11, "micro"),
    ("vitamin_a", "Vitamin A", ["320"], "µg", 900, "micro"),
    ("vitamin_c", "Vitamin C", ["401"], "mg", 90, "micro"),
    ("vitamin_d", "Vitamin D", ["328"], "µg", 20, "micro"),
    ("vitamin_e", "Vitamin E", ["323"], "mg", 15, "micro"),
    ("vitamin_k", "Vitamin K", ["430"], "µg", 120, "micro"),
    ("thiamin", "Thiamin (B1)", ["404"], "mg", 1.2, "micro"),
    ("riboflavin", "Riboflavin (B2)", ["405"], "mg", 1.3, "micro"),
    ("niacin", "Niacin (B3)", ["406"], "mg", 16, "micro"),
    ("vitamin_b6", "Vitamin B6", ["415"], "mg", 1.7, "micro"),
    ("folate", "Folate", ["435"], "µg", 400, "micro"),
    ("vitamin_b12", "Vitamin B12", ["418"], "µg", 2.4, "micro"),
]


class ParsedLine(BaseModel):
    index: int
    food_queries: list[str] = Field(description="One or two USDA-style search terms, best first; empty when skipped")
    skip: bool = Field(description="True for lines that add no meaningful nutrients or have no amount: water, ice, 'salt and pepper to taste', optional garnish")


class ParsedRecipe(BaseModel):
    lines: list[ParsedLine]


class LineMatch(BaseModel):
    index: int
    fdc_id: int = Field(description="fdcId of the best candidate, or 0 if no candidate is a reasonable match")
    grams: float = Field(description="Estimated weight in grams of the whole amount on this line")
    note: str = Field(description="Very short note on any assumption, e.g. '1 cup = 227 g', 'used midpoint of 1-2 tsp'; empty if none")


class RecipeMatches(BaseModel):
    matches: list[LineMatch]


PARSE_PROMPT = """You prepare recipe ingredient lines for a USDA FoodData Central search.

For each line, write one or two short search terms for the food as it is used, best first. Ignore quantities and preparation words like "chopped" or "softened". USDA food names start with the food category, so put it first: "butter salted", "wheat flour all-purpose", "chicken breast raw", "milk condensed sweetened", "sugars powdered" (for confectioners' or icing sugar), "nuts walnuts", "cheese cheddar".
When the ingredient is unspecific ("chopped nuts", "cheese"), use the most typical choice for this recipe, and add a broader second term ("nuts mixed").
For well-known branded products USDA lists (candy bars, cereals, soups), put the brand term first ("candies milky way bar") and a brand-free term second ("candies milk chocolate").
For lines listing alternatives ("butter or margarine"), use the first.
Set skip=true for lines that add no meaningful nutrients or have no measurable amount: water, ice, "salt and pepper to taste", cooking spray, optional garnish. Keep salt with a stated amount (it matters for sodium).
Return one entry per line, using the line's index."""

MATCH_PROMPT = """You match recipe ingredient lines to USDA FoodData Central foods and estimate their weight.

For each line you get the original text and candidate foods. Pick the candidate that best matches the ingredient as used in the recipe (raw vs cooked, salted vs unsalted, fat level). Use fdc_id 0 only if no candidate is a reasonable match.
Estimate the weight in grams of the full amount on the line, using standard kitchen conversions for that food (e.g. 1 cup all-purpose flour = 125 g, 1 tbsp butter = 14 g, 1 large egg = 50 g without shell). Use stated package weights when given ("1 (14 ounce) can" = 397 g). For ranges, use the midpoint. For counts of whole items, use a typical edible weight.
Return one entry per line, using the line's index."""


def anthropic_client():
    return anthropic.Anthropic(max_retries=3)


@lru_cache(maxsize=2048)
def search_fdc(query):
    """Return candidate foods for a search term, each with nutrients per 100 g."""
    def search(data_types):
        response = httpx.post(
            FDC_SEARCH_URL,
            params={"api_key": os.environ["USDA_API_KEY"]},
            json={"query": query, "dataType": data_types, "pageSize": CANDIDATES_PER_LINE},
            timeout=20,
        )
        response.raise_for_status()
        return response.json().get("foods", [])

    foods = search(["SR Legacy"]) or search(["Foundation"])
    return tuple(
        {
            "fdc_id": food["fdcId"],
            "description": food["description"],
            "nutrients": {
                n["nutrientNumber"]: n["value"]
                for n in food.get("foodNutrients", [])
                if n.get("nutrientNumber") and n.get("value") is not None
            },
        }
        for food in foods
    )


def nutrient_amount(per_100g, numbers):
    for number in numbers:
        if number in per_100g:
            return per_100g[number]
    return None


def analyze(recipe):
    """Return the nutrition analysis for a recipe dict with id, name, ingredients_raw, servings."""
    client = anthropic_client()
    lines = recipe["ingredients_raw"]
    numbered = "\n".join(f"{i}: {line}" for i, line in enumerate(lines))

    parsed = client.messages.parse(
        model=MODEL,
        max_tokens=8000,
        system=PARSE_PROMPT,
        output_config={"effort": "medium"},
        messages=[{"role": "user", "content": f"Recipe: {recipe['name']}\nIngredient lines:\n{numbered}"}],
        output_format=ParsedRecipe,
    ).parsed_output
    parsed_by_index = {p.index: p for p in parsed.lines if 0 <= p.index < len(lines)}

    queries = {
        p.index: [q.strip().lower() for q in p.food_queries[:2] if q.strip()]
        for p in parsed_by_index.values() if not p.skip
    }
    unique_queries = sorted({q for qs in queries.values() for q in qs})
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = dict(zip(unique_queries, pool.map(search_fdc, unique_queries)))

    # Candidates from both search terms, best term first, without duplicates
    candidates = {}
    for index, qs in queries.items():
        seen, foods = set(), []
        for food in (food for q in qs for food in results[q]):
            if food["fdc_id"] not in seen:
                seen.add(food["fdc_id"])
                foods.append(food)
        candidates[index] = foods[:2 * CANDIDATES_PER_LINE]

    match_input = "\n\n".join(
        f"Line {index}: {lines[index]}\nCandidates:\n" + "\n".join(
            f"- fdc_id {c['fdc_id']}: {c['description']}" for c in foods
        )
        for index, foods in candidates.items() if foods
    )
    matches_by_index = {}
    if match_input:
        matches = client.messages.parse(
            model=MODEL,
            max_tokens=8000,
            system=MATCH_PROMPT,
            output_config={"effort": "medium"},
            messages=[{"role": "user", "content": f"Recipe: {recipe['name']}\n\n{match_input}"}],
            output_format=RecipeMatches,
        ).parsed_output
        matches_by_index = {m.index: m for m in matches.matches}

    totals = {key: 0.0 for key, *_ in NUTRIENTS}
    ingredients = []
    for index, line in enumerate(lines):
        parsed_line = parsed_by_index.get(index)
        match = matches_by_index.get(index)
        food = next((c for c in candidates.get(index, ()) if match and c["fdc_id"] == match.fdc_id), None)

        if parsed_line is None or parsed_line.skip:
            ingredients.append({"line": line, "status": "skipped"})
            continue
        if food is None or match.grams <= 0:
            ingredients.append({"line": line, "status": "unmatched"})
            continue

        for key, _, numbers, *_ in NUTRIENTS:
            amount = nutrient_amount(food["nutrients"], numbers)
            if amount is not None:
                totals[key] += amount * match.grams / 100
        ingredients.append({
            "line": line,
            "status": "matched",
            "food": food["description"],
            "fdc_id": food["fdc_id"],
            "grams": round(match.grams, 1),
            "note": match.note,
        })

    return {
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "nutrients": [
            {"key": key, "label": label, "unit": unit, "daily_value": dv, "group": group,
             "amount": round(totals[key], 2)}
            for key, label, _, unit, dv, group in NUTRIENTS
        ],
        "ingredients": ingredients,
    }
