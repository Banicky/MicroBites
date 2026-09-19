import { useState } from 'react'
import "./Homepage.css"

function Homepage() {
  const [query, set_query] = useState("")

  const handleSubmit = (e) => {
    e.preventDefault()
    alert(query)
  }

  return (
    <>
      <h1>MicroBites</h1>
      <h2>Describe the meal you want and find out why it's good for you</h2>

      <form onSubmit={handleSubmit}>
        <input className='search-bar' type="text" onChange={(e) => {set_query(e.target.value)}}/>
        <button className='search-button' type='submit'>Enter</button>
      </form>
    </>
  )
}

export default Homepage
