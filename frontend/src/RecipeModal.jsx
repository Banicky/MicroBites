import { useEffect, useRef, useState } from "react"
import { ALLERGY_DIETS, formatServings, getRecipe } from "./api.js"
import DietBadges from "./DietBadges.jsx"
import RecipeImage from "./RecipeImage.jsx"

function RecipeModal({ recipe, onClose }) {
  const dialog_ref = useRef(null)
  const [details, set_details] = useState(null)
  const [error, set_error] = useState(null)

  useEffect(() => {
    dialog_ref.current.showModal()
  }, [])

  useEffect(() => {
    let cancelled = false
    getRecipe(recipe.id)
      .then((data) => { if (!cancelled) set_details(data) })
      .catch((e) => { if (!cancelled) set_error(e.message) })
    return () => { cancelled = true }
  }, [recipe.id])

  // Clicking the backdrop (the dialog element itself, outside its content) closes it
  const handleClick = (e) => {
    if (e.target === dialog_ref.current) onClose()
  }

  const servings = formatServings(recipe.servings)

  return (
    <dialog ref={dialog_ref} className="recipe-modal" onClose={onClose} onClick={handleClick}>
      <div className="recipe-modal-content">
        <button className="modal-close" type="button" onClick={onClose} aria-label="Close">×</button>
        <RecipeImage src={recipe.image} alt={recipe.name} className="recipe-modal-image" />

        <div className="recipe-modal-body">
          <h2>{recipe.name}</h2>
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
            </>
          )}
        </div>
      </div>
    </dialog>
  )
}

export default RecipeModal
