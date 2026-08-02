import { Routes, Route } from 'react-router-dom'
import Home from './components/Home'
import Recipe from './components/Recipe'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/recipe" element={<Recipe />} />
    </Routes>
  )
}

export default App
