import { useState } from "react"
import { login, register } from "./api.js"

function AuthPage({ onAuthenticated }) {
  const [mode, set_mode] = useState("login")
  const [email, set_email] = useState("")
  const [password, set_password] = useState("")
  const [confirm, set_confirm] = useState("")
  const [error, set_error] = useState(null)
  const [submitting, set_submitting] = useState(false)

  const is_register = mode === "register"

  const switchMode = () => {
    set_mode(is_register ? "login" : "register")
    set_error(null)
    set_confirm("")
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (is_register && password !== confirm) {
      set_error("Passwords don't match")
      return
    }
    set_submitting(true)
    set_error(null)
    try {
      onAuthenticated(await (is_register ? register : login)(email, password))
    } catch (err) {
      set_error(err.message)
      set_submitting(false)
    }
  }

  return (
    <main className="page auth-page">
      <h1>MicroBites</h1>
      <form className="auth-form" onSubmit={handleSubmit}>
        <h2>{is_register ? "Create an account" : "Log in"}</h2>

        <label>
          Email
          <input type="email" value={email} autoComplete="email" required
            onChange={(e) => set_email(e.target.value)} />
        </label>
        <label>
          Password
          <input type="password" value={password} required minLength={8}
            autoComplete={is_register ? "new-password" : "current-password"}
            onChange={(e) => set_password(e.target.value)} />
        </label>
        {is_register && (
          <label>
            Confirm password
            <input type="password" value={confirm} required minLength={8} autoComplete="new-password"
              onChange={(e) => set_confirm(e.target.value)} />
          </label>
        )}

        {error && <p className="status error">{error}</p>}

        <button className="search-button auth-submit" type="submit" disabled={submitting}>
          {submitting ? "Please wait…" : is_register ? "Create account" : "Log in"}
        </button>

        <p className="auth-switch">
          {is_register ? "Already have an account?" : "New to MicroBites?"}{" "}
          <button type="button" className="link-button" onClick={switchMode}>
            {is_register ? "Log in" : "Create an account"}
          </button>
        </p>
      </form>
    </main>
  )
}

export default AuthPage
