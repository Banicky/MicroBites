import { formatServings } from "./api.js"
import DietBadges from "./DietBadges.jsx"
import FavoriteButton from "./FavoriteButton.jsx"
import RecipeImage from "./RecipeImage.jsx"

function RecipeCard({ recipe, onOpen, onToggleFavorite }) {
  const servings = formatServings(recipe.servings)

  // The heart sits beside the card button, not inside it: buttons can't contain buttons
  return (
    <div className="recipe-card-wrap">
      <button className="recipe-card" type="button" onClick={() => onOpen(recipe)}>
        <RecipeImage src={recipe.image} alt={recipe.name} />
        <div className="recipe-card-body">
          <h3>{recipe.name}</h3>
          {recipe.description && <p className="recipe-card-description">{recipe.description}</p>}
          <div className="recipe-card-meta">
            {servings && <span>Serves {servings}</span>}
            {recipe.score != null && <span>{Math.round(recipe.score * 100)}% match</span>}
          </div>
          <DietBadges tags={recipe.diet_tags} limit={4} />
        </div>
      </button>
      <FavoriteButton recipe={recipe} onToggle={onToggleFavorite} className="on-card" />
    </div>
  )
}

export default RecipeCard
