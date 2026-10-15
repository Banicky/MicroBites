import { useEffect, useState } from "react"
import { getCurrentUser, logout, setAccessRequiredHandler, setUnauthorizedHandler } from "./api.js"
import AccessCodePage from "./AccessCodePage.jsx"
import AuthPage from "./AuthPage.jsx"
import Homepage from "./Homepage.jsx"

// Shows the login page until there is a session, then the access code page
// until the account is unlocked, then the app
function App() {
  // undefined while checking the session cookie, null when logged out
  const [user, set_user] = useState(undefined)

  useEffect(() => {
    setUnauthorizedHandler(() => set_user(null))
    setAccessRequiredHandler(() => set_user((current) => current && { ...current, has_access: false }))
    getCurrentUser().then(set_user).catch(() => set_user(null))
  }, [])

  const handleLogout = async () => {
    await logout().catch(() => {})
    set_user(null)
  }

  if (user === undefined) return <p className="status page">Loading…</p>
  if (user === null) return <AuthPage onAuthenticated={set_user} />
  if (!user.has_access) return <AccessCodePage user={user} onUnlocked={set_user} onLogout={handleLogout} />
  return <Homepage user={user} onLogout={handleLogout} />
}

export default App
