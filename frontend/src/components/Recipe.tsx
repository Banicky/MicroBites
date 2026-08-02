import { useState } from 'react'
import { Link } from 'react-router-dom'

const INGREDIENTS = [
  '8oz wide rice noodles',
  '2 chicken breasts, sliced',
  '3 Thai chilies, minced',
  '2 tbsp soy sauce',
  '1 cup Thai basil',
  '1 tbsp fish sauce',
  '1 tbsp dark soy sauce',
  '1 tbsp sugar',
  '4 cloves garlic, minced',
  '2 tbsp vegetable oil',
  '1 red bell pepper, sliced',
]

const STEPS = [
  'Soak the rice noodles in warm water until pliable, about 20 minutes, then drain.',
  'Whisk together the soy sauce, fish sauce, dark soy sauce, and sugar in a small bowl.',
  'Heat the oil in a wok over high heat. Add the garlic and chilies, stir-frying until fragrant.',
  'Add the chicken and cook, stirring occasionally, until browned and cooked through.',
  'Add the noodles, bell pepper, and sauce mixture. Toss until the noodles are coated and tender.',
  'Stir in the Thai basil until just wilted, then serve immediately.',
]

const REVIEWS = [
  { name: 'Sarah M.', rating: 5, text: 'So good and quick to make, better than takeout!' },
  { name: 'James T.', rating: 4, text: 'Great flavor, added extra chilies for heat.' },
  { name: 'Priya K.', rating: 5, text: 'Family favorite now, make it every week.' },
]

const TABS = ['Ingredients', 'Steps', 'Reviews'] as const
type Tab = (typeof TABS)[number]

function Recipe() {
  const [activeTab, setActiveTab] = useState<Tab>('Ingredients')
  const [checked, setChecked] = useState<boolean[]>(() => INGREDIENTS.map(() => false))

  const toggleChecked = (index: number) => {
    setChecked((prev) => prev.map((value, i) => (i === index ? !value : value)))
  }

  return (
    <div className="min-h-screen bg-[bisque] text-[#1a1a1a] [font-family:'Comic_Sans_MS','Segoe_UI',system-ui,sans-serif]">
      <header className="flex items-center gap-2.5 px-12 py-8">
        <Link to="/" className="text-[28px] leading-none no-underline" role="img" aria-label="Recipe">
          🥘
        </Link>
        <Link to="/" className="text-[22px] font-bold text-[#1a1a1a] no-underline">
          RecipeScout
        </Link>
      </header>

      <main className="max-w-5xl mx-auto px-6 pb-20 flex flex-col md:flex-row gap-10">
        <div className="md:w-2/5 md:sticky md:top-8 md:self-start">
          <div
            className="aspect-[4/3] w-full rounded-[20px] border-2 border-dashed border-[#1a1a1a]/40"
            style={{
              backgroundImage:
                'repeating-linear-gradient(-45deg, #ede4d3 0px, #ede4d3 12px, #f5eee0 12px, #f5eee0 24px)',
            }}
          />
        </div>

        <div className="flex-1 flex flex-col gap-6">
          <div>
            <h1 className="text-4xl md:text-5xl font-extrabold m-0">Drunken Noodles (Pad Kee Mao)</h1>
            <p className="text-lg text-[#6b5a45] mt-3 mb-0">
              ★4.7 (312) · 20 min · Easy · Thai
            </p>
          </div>

          <div className="flex gap-3">
            <button className="bg-[#1a1a1a] text-white border-none rounded-2xl px-7 py-3.5 font-bold text-base cursor-pointer hover:bg-[#333] flex items-center gap-2">
              Save <span aria-hidden="true">♡</span>
            </button>
            <button className="bg-white text-[#1a1a1a] border-2 border-[#1a1a1a] rounded-2xl px-7 py-3.5 font-bold text-base cursor-pointer hover:bg-[#fff7ee]">
              Share
            </button>
          </div>

          <div className="border-b-2 border-[#1a1a1a] flex gap-8">
            {TABS.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`pb-3 text-lg font-bold bg-transparent border-none cursor-pointer ${
                  activeTab === tab ? 'text-[#1a1a1a]' : 'text-[#1a1a1a]/40'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          {activeTab === 'Ingredients' && (
            <ul className="list-none m-0 p-0 grid sm:grid-cols-2 gap-x-8 gap-y-4">
              {INGREDIENTS.map((ingredient, index) => (
                <li key={ingredient}>
                  <button
                    onClick={() => toggleChecked(index)}
                    className="flex items-center gap-3 bg-transparent border-none cursor-pointer text-left p-0"
                  >
                    <span
                      className={`shrink-0 w-5 h-5 rounded-[4px] border-2 border-[#1a1a1a] flex items-center justify-center text-xs ${
                        checked[index] ? 'bg-[#1a1a1a] text-white' : 'bg-transparent'
                      }`}
                    >
                      {checked[index] ? '✓' : ''}
                    </span>
                    <span className={`text-base ${checked[index] ? 'line-through text-[#1a1a1a]/40' : ''}`}>
                      {ingredient}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {activeTab === 'Steps' && (
            <ol className="list-decimal list-outside m-0 pl-5 flex flex-col gap-4 text-base">
              {STEPS.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          )}

          {activeTab === 'Reviews' && (
            <div className="flex flex-col gap-4">
              {REVIEWS.map((review) => (
                <div key={review.name} className="bg-white/60 rounded-2xl border-2 border-[#1a1a1a]/20 p-5">
                  <p className="font-bold m-0">
                    {review.name} <span className="font-normal">{'★'.repeat(review.rating)}</span>
                  </p>
                  <p className="mt-2 mb-0 text-[#1a1a1a]/80">{review.text}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

export default Recipe
