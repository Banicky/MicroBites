import { useState } from "react"
import { redeemAccessCode } from "./api.js"

// Shown to logged-in accounts that haven't entered the shared access code yet
function AccessCodePage({ user, onUnlocked, onLogout }) {
  const [code, set_code] = useState("")
  const [error, set_error] = useState(null)
  const [submitting, set_submitting] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    set_submitting(true)
    set_error(null)
    try {
      onUnlocked(await redeemAccessCode(code))
    } catch (err) {
      set_error(err.message)
      set_submitting(false)
    }
  }

  return (
    <main className="page auth-page">
      <h1>MicroBites</h1>
      <form className="auth-form" onSubmit={handleSubmit}>
        <h2>Enter your access code</h2>
        <p className="auth-switch">
          MicroBites is in private testing. Enter the access code you were given to start searching.
          You only need to do this once.
        </p>

        <label>
          Access code
          <input type="text" value={code} required autoComplete="off" spellCheck={false}
            onChange={(e) => set_code(e.target.value)} />
        </label>

        {error && <p className="status error">{error}</p>}

        <button className="search-button auth-submit" type="submit" disabled={submitting}>
          {submitting ? "Checking…" : "Unlock"}
        </button>

        <p className="auth-switch">
          Signed in as {user.email}.{" "}
          <button type="button" className="link-button" onClick={onLogout}>Log out</button>
        </p>
      </form>
    </main>
  )
}

export default AccessCodePage
