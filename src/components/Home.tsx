import { useState, type SubmitEvent } from 'react'
import './Home.css'

function Home() {
  const [inputText, setInputText] = useState('')

  const handleSubmit = (e: SubmitEvent<HTMLFormElement>) => {
    e.preventDefault()

    if (inputText.trim() === '') return

    console.log('Submitted text')
    setInputText('')
  }

  return (
    <div className="home">

      <header className="home-header">
        <span className="home-logo" role="img" aria-label="Recipe">
          🥘
        </span>
        <span className="home-brand">RecipeScout</span>
      </header>

      <main className="home-main">
        <h1 className="home-title">What are you craving?</h1>
        <p className="home-subtitle">
          Describe a dish, ingredients, or mood — we'll find the recipe.
        </p>

        <form className="home-form" onSubmit={handleSubmit}>
          <textarea
            className="home-textarea"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder='"something spicy with chicken and noodles, ready in 20 min…"'
            rows={3}
          />
          <div className="home-actions">
            <button type="submit" className="home-submit">
              Find recipes ↵
            </button>
          </div>
        </form>

      </main>

    </div>
  )
}

export default Home
