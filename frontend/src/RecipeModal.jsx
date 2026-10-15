import { useEffect, useRef, useState } from "react"
import { ALLERGY_DIETS, analyzeNutrition, formatServings, getRecipe } from "./api.js"
import DietBadges from "./DietBadges.jsx"
import FavoriteButton from "./FavoriteButton.jsx"
import NutritionPanel from "./NutritionPanel.jsx"
import RecipeImage from "./RecipeImage.jsx"

const TABS = [
  { id: "recipe", label: "Recipe" },
  { id: "nutrition", label: "Nutrition" },
]

function RecipeModal({ recipe, onClose, onToggleFavorite }) {
  const dialog_ref = useRef(null)
  const [details, set_details] = useState(null)
  const [error, set_error] = useState(null)
  const [nutrition, set_nutrition] = useState(null)
  const [analyzing, set_analyzing] = useState(false)
  const [nutrition_error, set_nutrition_error] = useState(null)
  const [tab, set_tab] = useState("recipe")

  useEffect(() => {
    dialog_ref.current.showModal()
  }, [])

  useEffect(() => {
    let cancelled = false
    getRecipe(recipe.id)
      .then((data) => {
        if (cancelled) return
        set_details(data)
        // A previous analysis is cached on the recipe, so show it right away
        set_nutrition(data.nutrition)
      })
      .catch((e) => { if (!cancelled) set_error(e.message) })
    return () => { cancelled = true }
  }, [recipe.id])

  // Clicking the backdrop (the dialog element itself, outside its content) closes it
  const handleClick = (e) => {
    if (e.target === dialog_ref.current) onClose()
  }

  const handleAnalyze = async () => {
    set_analyzing(true)
    set_nutrition_error(null)
    try {
      set_nutrition(await analyzeNutrition(recipe.id))
    } catch (e) {
      set_nutrition_error(e.message)
    } finally {
      set_analyzing(false)
    }
  }

  const servings = formatServings(recipe.servings)

  return (
    <dialog ref={dialog_ref} className="recipe-modal" onClose={onClose} onClick={handleClick}>
      <div className="recipe-modal-content">
        <button className="modal-close" type="button" onClick={onClose} aria-label="Close">×</button>
        <RecipeImage src={recipe.image} alt={recipe.name} className="recipe-modal-image" />

        <div className="recipe-modal-body">
          <div className="recipe-modal-title">
            <h2>{recipe.name}</h2>
            <FavoriteButton recipe={recipe} onToggle={onToggleFavorite} />
          </div>
          {recipe.description && <p>{recipe.description}</p>}

          <div className="recipe-card-meta">
            {servings && <span>Serves {servings}</span>}
            {recipe.serving_size && <span>Serving size {recipe.serving_size}</span>}
          </div>

          <DietBadges tags={recipe.diet_tags} />
          {recipe.diet_tags.some((tag) => ALLERGY_DIETS.has(tag)) && (
            <p className="diet-note">
              Diet tags are judged from the ingredient list by AI and may be wrong.
              If you have an allergy, check product labels.
            </p>
          )}

          {error && <p className="status error">Could not load recipe: {error}</p>}
          {!details && !error && <p className="status">Loading recipe…</p>}
          {details && (
            <>
              <div className="modal-tabs" role="tablist" aria-label="Recipe sections">
                {TABS.map((t) => (
                  <button
                    key={t.id}
                    id={`tab-${t.id}`}
                    type="button"
                    role="tab"
                    aria-selected={tab === t.id}
                    aria-controls={`panel-${t.id}`}
                    className={`modal-tab ${tab === t.id ? "active" : ""}`}
                    onClick={() => set_tab(t.id)}
                  >
                    {t.label}
                  </button>
                ))}
              </div>

              {tab === "recipe" && (
                <div id="panel-recipe" role="tabpanel" aria-labelledby="tab-recipe">
                  <h3>Ingredients</h3>
                  <ul className="ingredient-list">
                    {details.ingredients_raw.map((item, i) => <li key={i}>{item}</li>)}
                  </ul>

                  <h3>Steps</h3>
                  <ol className="step-list">
                    {details.steps.map((step, i) => <li key={i}>{step}</li>)}
                  </ol>

                  <a href={`https://www.food.com/recipe/x-${recipe.id}`} target="_blank" rel="noreferrer">
                    View on food.com
                  </a>
                </div>
              )}

              {/* The analysis keeps running if the user switches back to the recipe tab */}
              {tab === "nutrition" && (
                <div id="panel-nutrition" role="tabpanel" aria-labelledby="tab-nutrition">
                  {nutrition ? (
                    <NutritionPanel nutrition={nutrition} servings={recipe.servings} />
                  ) : (
                    <div className="nutrition-start">
                      <button type="button" className="analyze-button" onClick={handleAnalyze} disabled={analyzing}>
                        {analyzing ? "Analyzing ingredients…" : "Analyze nutrition"}
                      </button>
                      <span className="diet-note">
                        {analyzing
                          ? "Matching each ingredient to USDA FoodData Central. This takes about 15 seconds."
                          : "Estimates macro- and micronutrients from the ingredient amounts."}
                      </span>
                      {nutrition_error && <p className="status error">Analysis failed: {nutrition_error}</p>}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </dialog>
  )
}

export default RecipeModal
