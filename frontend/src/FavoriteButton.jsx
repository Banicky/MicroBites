function FavoriteButton({ recipe, onToggle, className = "" }) {
  const label = recipe.is_favorite ? `Remove ${recipe.name} from favorites` : `Save ${recipe.name} to favorites`
  return (
    <button
      type="button"
      className={`favorite-button ${recipe.is_favorite ? "active" : ""} ${className}`}
      aria-pressed={recipe.is_favorite}
      aria-label={label}
      title={recipe.is_favorite ? "Remove from favorites" : "Save to favorites"}
      onClick={(e) => {
        e.stopPropagation()
        onToggle(recipe)
      }}
    >
      {recipe.is_favorite ? "♥" : "♡"}
    </button>
  )
}

export default FavoriteButton
