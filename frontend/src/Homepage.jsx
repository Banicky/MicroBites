import { useRef, useState } from 'react'
import "./Homepage.css"
import { DIETS, dietLabel, getFavorites, searchRecipes, setFavorite } from './api.js'
import RecipeCard from './RecipeCard.jsx'
import RecipeModal from './RecipeModal.jsx'

function Homepage({ user, onLogout }) {
  const [view, set_view] = useState("search")
  const [query, set_query] = useState("")
  const [diets, set_diets] = useState([])
  const [results, set_results] = useState(null)
  const [loading, set_loading] = useState(false)
  const [error, set_error] = useState(null)
  const [favorites, set_favorites] = useState(null)
  const [favorites_error, set_favorites_error] = useState(null)
  const [selected, set_selected] = useState(null)
  // Only the latest request may update results, so quick filter toggles can't land out of order
  const latest_request = useRef(0)

  const runSearch = async (text, selected_diets) => {
    if (!text.trim()) return
    const request = ++latest_request.current
    set_loading(true)
    set_error(null)
    try {
      const data = await searchRecipes(text.trim(), selected_diets)
      if (request === latest_request.current) set_results(data)
    } catch (e) {
      if (request === latest_request.current) set_error(e.message)
    } finally {
      if (request === latest_request.current) set_loading(false)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    runSearch(query, diets)
  }

  // Filters narrow the current search; before any search they are just remembered for the first one
  const toggleDiet = (diet) => {
    const next = diets.includes(diet) ? diets.filter((d) => d !== diet) : [...diets, diet]
    set_diets(next)
    if (results) runSearch(results.query, next)
  }

  const showFavorites = async () => {
    set_view("favorites")
    set_favorites_error(null)
    try {
      set_favorites(await getFavorites())
    } catch (e) {
      set_favorites_error(e.message)
    }
  }

  // Applies a favorite change everywhere the recipe is shown
  const applyFavorite = (recipe, is_favorite) => {
    const update = (r) => (r.id === recipe.id ? { ...r, is_favorite } : r)
    set_results((current) => current && { ...current, results: current.results.map(update) })
    set_favorites((current) => {
      if (!current) return current
      if (!is_favorite) return current.filter((r) => r.id !== recipe.id)
      return current.some((r) => r.id === recipe.id) ? current.map(update) : [{ ...recipe, is_favorite }, ...current]
    })
    set_selected((current) => current && update(current))
  }

  // Updates the UI right away and reverts if the request fails
  const toggleFavorite = async (recipe) => {
    const next = !recipe.is_favorite
    applyFavorite(recipe, next)
    try {
      await setFavorite(recipe.id, next)
    } catch {
      applyFavorite(recipe, !next)
    }
  }

  return (
    <main className="page">
      <nav className="top-bar">
        <div className="view-switch" role="group" aria-label="View">
          <button type="button" className={view === "search" ? "active" : ""} aria-pressed={view === "search"}
            onClick={() => set_view("search")}>
            Search
          </button>
          <button type="button" className={view === "favorites" ? "active" : ""} aria-pressed={view === "favorites"}
            onClick={showFavorites}>
            Favorites
          </button>
        </div>
        <div className="account">
          <span>{user.email}</span>
          <button type="button" className="link-button" onClick={onLogout}>Log out</button>
        </div>
      </nav>

      {view === "search" && (
        <>
          <header className="hero">
            <h1>MicroBites</h1>
            <h2>Describe the meal you want and find out why it's good for you</h2>

            <form onSubmit={handleSubmit}>
              <input
                className='search-bar'
                type="search"
                value={query}
                placeholder="e.g. low carb recipe with chicken"
                aria-label="Describe a meal"
                onChange={(e) => {set_query(e.target.value)}}
              />
              <button className='search-button' type='submit' disabled={loading}>
                {loading ? "Searching…" : "Search"}
              </button>
            </form>

            <div className="diet-filters" role="group" aria-label="Diet filters">
              {DIETS.map((diet) => (
                <button
                  key={diet.id}
                  type="button"
                  className={`diet-filter ${diets.includes(diet.id) ? "active" : ""}`}
                  aria-pressed={diets.includes(diet.id)}
                  onClick={() => toggleDiet(diet.id)}
                >
                  {diet.label}
                </button>
              ))}
            </div>
          </header>

          {error && <p className="status error">Search failed: {error}</p>}

          {results && !error && (
            <section>
              <p className="status">
                {results.results.length} matches for “{results.query}”
                {results.diets.length > 0 && <> · {results.diets.map(dietLabel).join(", ")} only</>}
              </p>
              {results.results.length === 0 && (
                <p className="status">No recipes fit all the selected diets. Try removing a filter.</p>
              )}
              <div className="results-grid">
                {results.results.map((recipe) => (
                  <RecipeCard key={recipe.id} recipe={recipe} onOpen={set_selected} onToggleFavorite={toggleFavorite} />
                ))}
              </div>
            </section>
          )}
        </>
      )}

      {view === "favorites" && (
        <section>
          <h1 className="favorites-title">Your favorites</h1>
          {favorites_error && <p className="status error">Could not load favorites: {favorites_error}</p>}
          {!favorites && !favorites_error && <p className="status">Loading…</p>}
          {favorites?.length === 0 && (
            <p className="status">No favorites yet. Tap the heart on any recipe to save it here.</p>
          )}
          {favorites?.length > 0 && (
            <div className="results-grid">
              {favorites.map((recipe) => (
                <RecipeCard key={recipe.id} recipe={recipe} onOpen={set_selected} onToggleFavorite={toggleFavorite} />
              ))}
            </div>
          )}
        </section>
      )}

      {selected && (
        <RecipeModal key={selected.id} recipe={selected} onClose={() => set_selected(null)}
          onToggleFavorite={toggleFavorite} />
      )}
    </main>
  )
}

export default Homepage
