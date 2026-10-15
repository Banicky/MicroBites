"""Classify each recipe's dietary fit from its full ingredient list with Claude.

Pilot mode compares models on a sample and writes results to a JSON file;
it does not touch the database. Batch mode classifies every recipe through the
Message Batches API (50% cheaper, asynchronous) and stores the "yes" verdicts in
recipe.diet_tags.

Usage:
    python classify_diet.py pilot --pilot 100 --model claude-haiku-5-5 --out pilot_haiku.json
    python classify_diet.py submit    # send all recipes as one batch
    python classify_diet.py status    # check the submitted batch
    python classify_diet.py collect   # write results to recipe.diet_tags once the batch has ended
"""
import argparse
import json
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Literal

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from db import connect

load_dotenv()

BATCH_MODEL = "claude-haiku-5-5"
CACHE_DIR = Path(__file__).resolve().parent / ".cache"
BATCH_STATE_PATH = CACHE_DIR / "diet_batch.json"
RESULTS_PATH = CACHE_DIR / "diet_results.jsonl"

Verdict = Literal["yes", "no", "unsure"]
DIET_TAGS = ["vegan", "vegetarian", "pescatarian", "gluten_free", "dairy_free", "egg_free", "nut_free", "keto"]


class DietClassification(BaseModel):
    vegan: Verdict
    vegetarian: Verdict
    pescatarian: Verdict
    gluten_free: Verdict
    dairy_free: Verdict
    egg_free: Verdict
    nut_free: Verdict
    keto: Verdict
    notes: str = Field(description="One short sentence naming the ingredients behind any 'no' or 'unsure'")


SYSTEM_PROMPT = """You classify recipes by dietary fit using only their ingredient list.

For each diet, answer:
- "yes": every ingredient, as written, fits the diet.
- "no": at least one ingredient clearly breaks it.
- "unsure": an ingredient might break it depending on brand or variety, and the recipe does not say.

Definitions:
- vegan: no meat, poultry, fish, shellfish, dairy, eggs, honey, gelatin, or other animal products.
- vegetarian: no meat, poultry, fish, shellfish, gelatin, or meat/fish-based stock or sauce. Dairy and eggs are fine.
- pescatarian: vegetarian, but fish and shellfish are also allowed.
- gluten_free: no wheat, barley, rye, spelt, or ingredients made from them (regular flour, bread, pasta, beer, malt). Ingredients often containing hidden gluten (regular soy sauce, bouillon, some spice blends, oats not labeled gluten-free) are "unsure" unless the recipe specifies a gluten-free version.
- dairy_free: no milk, butter, cheese, cream, yogurt, whey, ghee, or other cow/goat/sheep milk products. Plant milks (coconut, almond, soy) are fine.
- egg_free: no eggs or egg-based ingredients (mayonnaise, egg noodles, meringue).
- nut_free: no tree nuts or peanuts, or their butters, oils, flours, or extracts. Nutmeg, coconut, and water chestnuts are not nuts.
- keto: no sugar or sweet syrups (artificial sweeteners are fine), grains, flour, bread, pasta, rice, potatoes, legumes, or sweet fruit beyond small amounts of berries or lemon/lime. Trace amounts for seasoning (a teaspoon of flour to thicken, a pinch of sugar) are "unsure".

Judge only the ingredients as written. Ignore processing details (sugar filtered with bone char, wine or spirits fined with animal products), possible cross-contamination, and "may contain traces" risks. Plain pantry staples (sugar, salt, spices, vinegar, vanilla extract, oils, baking soda/powder) fit every diet except where a definition above names them.
Ingredients listing alternatives ("butter or margarine") break a diet only if every alternative breaks it.
Use "unsure" only when a common version of an ingredient breaks the diet and the recipe does not say which version (e.g. "soy sauce" for gluten_free, "broth" for vegetarian). Never answer "yes" when you are not confident."""


def user_message(recipe):
    ingredients = "\n".join(f"- {line}" for line in recipe["ingredients_raw"])
    return f"Recipe: {recipe['name']}\nIngredients:\n{ingredients}"


def classify(client, model, recipe):
    response = client.messages.parse(
        model=model,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        output_config={"effort": "medium"},
        messages=[{"role": "user", "content": user_message(recipe)}],
        output_format=DietClassification,
    )
    return {
        "id": recipe["id"],
        "name": recipe["name"],
        "ingredients_raw": recipe["ingredients_raw"],
        "result": response.parsed_output.model_dump(),
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }


# Same shape as DietClassification, written out for batch requests, which take a raw JSON schema
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        **{tag: {"type": "string", "enum": ["yes", "no", "unsure"]} for tag in DIET_TAGS},
        "notes": {"type": "string", "description": "One short sentence naming the ingredients behind any 'no' or 'unsure'"},
    },
    "required": [*DIET_TAGS, "notes"],
    "additionalProperties": False,
}


def load_recipes():
    cursor = connect().cursor()
    cursor.execute("select id, name, ingredients_raw from recipe order by id")
    return [dict(zip(["id", "name", "ingredients_raw"], row)) for row in cursor.fetchall()]


def pilot(args):
    sample = random.Random(args.seed).sample(load_recipes(), args.pilot)
    client = anthropic.Anthropic(max_retries=5)
    errors = []

    def run(recipe):
        try:
            return classify(client, args.model, recipe)
        except anthropic.APIError as exc:
            errors.append((recipe["id"], str(exc)))
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = [r for r in pool.map(run, sample) if r]

    with open(args.out, "w") as f:
        json.dump(results, f, indent=1)

    print(f"{len(results)} classified, {len(errors)} errors -> {args.out}")
    for recipe_id, message in errors[:5]:
        print(f"  {recipe_id}: {message}")
    print("input tokens:", sum(r["input_tokens"] for r in results),
          "output tokens:", sum(r["output_tokens"] for r in results))


def submit(args):
    if BATCH_STATE_PATH.exists():
        raise SystemExit(f"A batch was already submitted ({BATCH_STATE_PATH}). Delete that file to submit a new one.")

    recipes = load_recipes()
    requests = [
        Request(
            custom_id=str(recipe["id"]),
            params=MessageCreateParamsNonStreaming(
                model=BATCH_MODEL,
                max_tokens=4000,
                system=SYSTEM_PROMPT,
                output_config={"effort": "medium", "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
                messages=[{"role": "user", "content": user_message(recipe)}],
            ),
        )
        for recipe in recipes
    ]
    batch = anthropic.Anthropic().messages.batches.create(requests=requests)

    CACHE_DIR.mkdir(exist_ok=True)
    BATCH_STATE_PATH.write_text(json.dumps({"batch_id": batch.id, "model": BATCH_MODEL, "count": len(requests)}))
    print(f"Submitted batch {batch.id} with {len(requests)} recipes ({batch.processing_status})")


def batch_id():
    if not BATCH_STATE_PATH.exists():
        raise SystemExit("No batch submitted yet. Run: python classify_diet.py submit")
    return json.loads(BATCH_STATE_PATH.read_text())["batch_id"]


def status(args):
    batch = anthropic.Anthropic().messages.batches.retrieve(batch_id())
    counts = batch.request_counts
    print(f"{batch.id}: {batch.processing_status} | processing {counts.processing}, succeeded {counts.succeeded}, "
          f"errored {counts.errored}, expired {counts.expired}, canceled {counts.canceled}")


def collect(args):
    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(batch_id())
    if batch.processing_status != "ended":
        raise SystemExit(f"Batch {batch.id} is still {batch.processing_status}; try again later.")

    updates, failed = [], []
    input_tokens = output_tokens = 0
    with open(RESULTS_PATH, "w") as log:
        for result in client.messages.batches.results(batch.id):
            if result.result.type != "succeeded":
                failed.append((result.custom_id, result.result.type))
                continue
            message = result.result.message
            input_tokens += message.usage.input_tokens
            output_tokens += message.usage.output_tokens
            text = next((b.text for b in message.content if b.type == "text"), "")
            try:
                verdicts = json.loads(text)
            except json.JSONDecodeError:
                failed.append((result.custom_id, f"bad JSON (stop_reason={message.stop_reason})"))
                continue
            log.write(json.dumps({"id": int(result.custom_id), **verdicts}) + "\n")
            diet_tags = [tag.replace("_", "-") for tag in DIET_TAGS if verdicts.get(tag) == "yes"]
            updates.append((diet_tags, int(result.custom_id)))

    conn = connect()
    cursor = conn.cursor()
    cursor.executemany("update recipe set diet_tags = %s where id = %s", updates)
    conn.commit()
    conn.close()

    print(f"Stored diet_tags for {len(updates)} recipes; {len(failed)} failed")
    for recipe_id, reason in failed[:10]:
        print(f"  {recipe_id}: {reason}")
    print(f"input tokens: {input_tokens}, output tokens: {output_tokens} (billed at batch rates)")


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    pilot_parser = commands.add_parser("pilot", help="classify a sample; results go to a JSON file, not the DB")
    pilot_parser.add_argument("--pilot", type=int, required=True, help="number of recipes to sample")
    pilot_parser.add_argument("--model", required=True)
    pilot_parser.add_argument("--out", required=True)
    pilot_parser.add_argument("--seed", type=int, default=42)
    pilot_parser.set_defaults(run=pilot)

    commands.add_parser("submit", help="submit every recipe as one batch").set_defaults(run=submit)
    commands.add_parser("status", help="check the submitted batch").set_defaults(run=status)
    commands.add_parser("collect", help="store results in recipe.diet_tags").set_defaults(run=collect)

    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
