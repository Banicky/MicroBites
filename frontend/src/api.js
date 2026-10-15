// Same origin as the app (proxied to the API), so the session cookie is sent automatically
const API_URL = import.meta.env.VITE_API_URL ?? "/api"

let on_unauthorized = () => {}
let on_access_required = () => {}

// Lets the app return to the login page when a session expires mid-use
export function setUnauthorizedHandler(handler) {
  on_unauthorized = handler
}

// Lets the app show the access code page if the account loses access mid-use
export function setAccessRequiredHandler(handler) {
  on_access_required = handler
}

async function request(path, { method = "GET", body } = {}) {
  const response = await fetch(API_URL + path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!response.ok) {
    const data = await response.json().catch(() => null)
    if (response.status === 401 && !path.startsWith("/auth/")) on_unauthorized()
    if (response.status === 403 && data?.detail === "Access code required") on_access_required()
    throw new Error(errorMessage(data?.detail) ?? `Request failed (${response.status})`)
  }
  return response.json()
}

// FastAPI validation errors arrive as a list of {msg} objects
function errorMessage(detail) {
  if (Array.isArray(detail)) return detail.map((d) => d.msg.replace(/^Value error, /, "")).join("; ")
  return detail
}

export function getCurrentUser() {
  return request("/auth/me")
}

export function login(email, password) {
  return request("/auth/login", { method: "POST", body: { email, password } })
}

export function register(email, password) {
  return request("/auth/register", { method: "POST", body: { email, password } })
}

export function logout() {
  return request("/auth/logout", { method: "POST" })
}

export function redeemAccessCode(code) {
  return request("/auth/access-code", { method: "POST", body: { code } })
}

export function searchRecipes(query, diets = []) {
  const params = new URLSearchParams({ q: query })
  diets.forEach((diet) => params.append("diet", diet))
  return request(`/search?${params}`)
}

export function getRecipe(id) {
  return request(`/recipes/${id}`)
}

export function analyzeNutrition(id) {
  return request(`/recipes/${id}/nutrition`, { method: "POST" })
}

export function getFavorites() {
  return request("/favorites")
}

export function setFavorite(id, is_favorite) {
  return request(`/favorites/${id}`, { method: is_favorite ? "PUT" : "DELETE" })
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
