import { dietLabel, sortDiets } from "./api.js"

function DietBadges({ tags, limit }) {
  const sorted = sortDiets(tags)
  const shown = limit ? sorted.slice(0, limit) : sorted
  const hidden = sorted.length - shown.length

  if (sorted.length === 0) return null
  return (
    <ul className="tag-list">
      {shown.map((tag) => <li key={tag} className="tag">{dietLabel(tag)}</li>)}
      {hidden > 0 && <li className="tag tag-more">+{hidden}</li>}
    </ul>
  )
}

export default DietBadges
