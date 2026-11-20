import { useEffect, useState, type FormEvent } from 'react'
import { createRoot } from 'react-dom/client'
import { api, ApiError, errorText, json, type Account } from './api'
import { ChatPage } from './chat'
import { AdminPage } from './admin'
import './style.css'

import { Brand } from './brand'

function SignIn({ onAccount }: { onAccount: (a: Account) => void }) {
  const [register, setRegister] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    const login = String(values.get('login'))
    const password = String(values.get('password'))
    if (register && password !== values.get('repeat')) { setError('Пароли не совпадают.'); return }
    setBusy(true)
    setError('')
    try {
      const { user } = await api<{ user: Account }>(register ? '/auth/register' : '/auth/login', json({ login, password }))
      onAccount(user)
    } catch (err) {
      setError(errorText(err))
    } finally { setBusy(false) }
  }
  return <main className="center"><section className="card">
    <Brand />
    <h1>Добро пожаловать</h1>
    <p className="sub">Войдите в помощник по документации Linux.</p>
    <div className="tabs">
      <button type="button" aria-pressed={!register} onClick={() => { setRegister(false); setError('') }} disabled={busy}>Вход</button>
      <button type="button" aria-pressed={register} onClick={() => { setRegister(true); setError('') }} disabled={busy}>Регистрация</button>
    </div>
    <form key={String(register)} onSubmit={submit}>
      <label className="field">Логин<input name="login" autoComplete="username" minLength={3} maxLength={40} required /></label>
      <label className="field">Пароль<input name="password" type="password" autoComplete={register ? 'new-password' : 'current-password'} minLength={8} required /></label>
      {register && <label className="field">Повторите пароль<input name="repeat" type="password" autoComplete="new-password" required /></label>}
      {error && <p className="notice error" role="alert">{error}</p>}
      <button className="btn" disabled={busy}>{register ? 'Создать аккаунт' : 'Войти'}</button>
    </form>
  </section></main>
}

function App() {
  const [account, setAccount] = useState<Account | null | undefined>()
  const [error, setError] = useState('')
  async function restore() {
    setError('')
    try { setAccount(await api<Account>('/auth/me')) }
    catch (err) {
      if (err instanceof ApiError && err.status === 401) setAccount(null)
      else setError(errorText(err))
    }
  }
  useEffect(() => {
    const reset = () => setAccount(null)
    window.addEventListener('commandwise:unauthorized', reset)
    void restore()
    return () => window.removeEventListener('commandwise:unauthorized', reset)
  }, [])
  useEffect(() => {
    if (!account) return
    const path = account.role === 'admin' ? '/admin' : '/'
    if (window.location.pathname !== path) window.history.replaceState(null, '', path)
  }, [account])
  async function logout() {
    await api('/auth/logout', { method: 'POST' })
    window.history.replaceState(null, '', '/')
    setAccount(null)
  }
  if (account === undefined) return <main className="center"><div className="card">
    <Brand />
    {error ? <><p role="alert">{error}</p><button className="btn" onClick={() => void restore()}>Повторить</button></> : <p role="status">Проверяем сессию…</p>}
  </div></main>
  if (account === null) return <SignIn onAccount={setAccount} />
  if (account.role === 'admin') return <AdminPage account={account} logout={logout} />
  return <ChatPage key={account.id} account={account} logout={logout} />
}

createRoot(document.getElementById('root')!).render(<App />)
