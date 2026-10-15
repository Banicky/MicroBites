const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000"

async function getJson(path) {
  const response = await fetch(API_URL + path)
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`)
  }
  return response.json()
}

export function searchRecipes(query, diets = []) {
  const params = new URLSearchParams({ q: query })
  diets.forEach((diet) => params.append("diet", diet))
  return getJson(`/search?${params}`)
}

export function getRecipe(id) {
  return getJson(`/recipes/${id}`)
}

// Values of recipe.diet_tags, in display order
export const DIETS = [
  { id: "vegan", label: "Vegan" },
  { id: "vegetarian", label: "Vegetarian" },
  { id: "pescatarian", label: "Pescatarian" },
  { id: "gluten-free", label: "Gluten-free" },
  { id: "dairy-free", label: "Dairy-free" },
  { id: "egg-free", label: "Egg-free" },
  { id: "nut-free", label: "Nut-free" },
  { id: "keto", label: "Keto" },
]

// Allergy-related tags, shown with a note to check product labels
export const ALLERGY_DIETS = new Set(["gluten-free", "dairy-free", "egg-free", "nut-free"])

const DIET_LABELS = Object.fromEntries(DIETS.map((diet) => [diet.id, diet.label]))

export function dietLabel(id) {
  return DIET_LABELS[id] ?? id
}

export function sortDiets(tags) {
  return DIETS.map((diet) => diet.id).filter((id) => tags.includes(id))
}

export function formatServings(servings) {
  return servings == null ? null : Number(servings).toString()
}
