import { useState, type SubmitEvent } from 'react'
import { useNavigate } from 'react-router-dom'

function Home() {
  const [inputText, setInputText] = useState('')
  const navigate = useNavigate()

  const handleSubmit = async (e: SubmitEvent<HTMLFormElement>) => {
    e.preventDefault()

    if (inputText.trim() === '') return

    await fetch('http://localhost:8000/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: inputText }),
    })

    setInputText('')
    navigate('/recipe')
  }

  return (
    <div className="min-h-screen bg-[bisque] flex flex-col text-[#1a1a1a] [font-family:'Comic_Sans_MS','Segoe_UI',system-ui,sans-serif]">

      <header className="flex items-center gap-2.5 px-12 py-8">
        <span className="text-[28px] leading-none" role="img" aria-label="Recipe">
          🥘
        </span>
        <span className="text-[22px] font-bold">RecipeScout</span>
      </header>

      <main className="flex-1 w-full max-w-[640px] mx-auto px-6 pt-10 pb-20 flex flex-col items-center justify-center gap-6 text-center">
        <h1 className="text-[44px] font-extrabold m-0">What are you craving?</h1>
        <p className="text-[17px] text-[#6b5a45] m-0">
          Describe a dish, ingredients, or mood — we'll find the recipe.
        </p>

        <form className="w-full flex flex-col gap-4" onSubmit={handleSubmit}>
          <textarea
            className="w-full min-h-[120px] border-2 border-[#1a1a1a] rounded-[20px] bg-white p-5 text-base text-[#1a1a1a] text-left resize-y placeholder:text-[#8a7a63] focus:outline-none focus:shadow-[0_0_0_3px_rgba(26,26,26,0.15)]"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder='"something spicy with chicken and noodles, ready in 20 min…"'
            rows={3}
          />
          <div className="flex justify-end">
            <button type="submit" className="bg-[#1a1a1a] text-white border-none rounded-[14px] px-7 py-3.5 font-bold text-base cursor-pointer hover:bg-[#333]">
              Find recipes ↵
            </button>
          </div>
        </form>

      </main>

    </div>
  )
}

export default Home
