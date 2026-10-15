import { useState } from "react"

// Shows the food.com photo, or an empty placeholder when there is none or it fails to load
function RecipeImage({ src, alt, className = "" }) {
  const [failed, set_failed] = useState(false)

  if (!src || failed) {
    return <div className={`recipe-image recipe-image-placeholder ${className}`} aria-hidden="true" />
  }
  return (
    <img
      className={`recipe-image ${className}`}
      src={src}
      alt={alt}
      loading="lazy"
      onError={() => set_failed(true)}
    />
  )
}

export default RecipeImage
