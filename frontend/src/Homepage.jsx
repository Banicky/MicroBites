import { useRef, useState } from 'react'
import "./Homepage.css"
import { DIETS, dietLabel, searchRecipes } from './api.js'
import RecipeCard from './RecipeCard.jsx'
import RecipeModal from './RecipeModal.jsx'

const EXAMPLES = ["low carb recipe with chicken", "gluten free cookies", "baked chicken using cheese"]

function Homepage() {
  const [query, set_query] = useState("")
  const [diets, set_diets] = useState([])
  const [results, set_results] = useState(null)
  const [loading, set_loading] = useState(false)
  const [error, set_error] = useState(null)
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

  const handleExample = (example) => {
    set_query(example)
    runSearch(example, diets)
  }

  // Filters narrow the current search; before any search they are just remembered for the first one
  const toggleDiet = (diet) => {
    const next = diets.includes(diet) ? diets.filter((d) => d !== diet) : [...diets, diet]
    set_diets(next)
    if (results) runSearch(results.query, next)
  }

  return (
    <main className="page">
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

        <div className="examples">
          {EXAMPLES.map((example) => (
            <button key={example} type="button" className="example" onClick={() => handleExample(example)}>
              {example}
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
              <RecipeCard key={recipe.id} recipe={recipe} onOpen={set_selected} />
            ))}
          </div>
        </section>
      )}

      {selected && <RecipeModal key={selected.id} recipe={selected} onClose={() => set_selected(null)} />}
    </main>
  )
}

export default Homepage
