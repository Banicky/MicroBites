import { useState } from "react"

function formatAmount(amount, unit) {
  if (unit === "kcal" || unit === "mg" || amount >= 100) return Math.round(amount).toLocaleString()
  if (amount >= 10) return amount.toFixed(0)
  return amount.toFixed(1)
}

function NutrientTable({ nutrients, divisor }) {
  return (
    <table className="nutrient-table">
      <tbody>
        {nutrients.map((n) => {
          const amount = n.amount / divisor
          const percent = n.daily_value ? Math.round((amount / n.daily_value) * 100) : null
          return (
            <tr key={n.key}>
              <th scope="row">{n.label}</th>
              <td>{formatAmount(amount, n.unit)} {n.unit}</td>
              <td className="nutrient-dv">{percent == null ? "" : `${percent}%`}</td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

function NutritionPanel({ nutrition, servings }) {
  const has_servings = servings != null && Number(servings) > 0
  const [per_serving, set_per_serving] = useState(has_servings)
  const divisor = per_serving ? Number(servings) : 1

  const macros = nutrition.nutrients.filter((n) => n.group === "macro")
  const micros = nutrition.nutrients.filter((n) => n.group === "micro")
  const unmatched = nutrition.ingredients.filter((i) => i.status === "unmatched")

  return (
    <div className="nutrition-panel">
      <div className="nutrition-toggle" role="group" aria-label="Amounts shown">
        <button type="button" className={per_serving ? "active" : ""} disabled={!has_servings}
          aria-pressed={per_serving} onClick={() => set_per_serving(true)}>
          Per serving{has_servings ? ` (1 of ${Number(servings)})` : ""}
        </button>
        <button type="button" className={per_serving ? "" : "active"}
          aria-pressed={!per_serving} onClick={() => set_per_serving(false)}>
          Whole recipe
        </button>
      </div>

      <div className="nutrition-columns">
        <section>
          <h4>Macronutrients</h4>
          <NutrientTable nutrients={macros} divisor={divisor} />
        </section>
        <section>
          <h4>Micronutrients</h4>
          <NutrientTable nutrients={micros} divisor={divisor} />
        </section>
      </div>

      {unmatched.length > 0 && (
        <p className="diet-note">
          Not counted ({unmatched.length}): {unmatched.map((i) => i.line).join("; ")}
        </p>
      )}

      <details className="nutrition-details">
        <summary>How this was calculated</summary>
        <ul>
          {nutrition.ingredients.map((i, index) => (
            <li key={index}>
              <span>{i.line}</span>
              {i.status === "matched" && <> → {i.food}, {i.grams} g{i.note && <em> ({i.note})</em>}</>}
              {i.status === "skipped" && <em> (skipped: no measurable amount)</em>}
              {i.status === "unmatched" && <em> (no USDA match)</em>}
            </li>
          ))}
        </ul>
      </details>

      <p className="diet-note">
        Estimates from USDA FoodData Central. Ingredient matches and weights are chosen by AI and may be off.
        % Daily Value is based on a 2,000 calorie diet.
      </p>
    </div>
  )
}

export default NutritionPanel
