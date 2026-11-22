import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { api, errorText, json, type Account } from './api'

export type AccountMenuProps = {
  account: Account
  onAccountChange: (account: Account) => void
  logout: () => Promise<void>
}

export function AccountMenu({ account, onAccountChange, logout, onError }: AccountMenuProps & { onError: (message: string) => void }) {
  const [open, setOpen] = useState(false)
  return <div className="me">
    <button type="button" className="profile-trigger" title={account.login} aria-haspopup="dialog" onClick={() => setOpen(true)}>
      <span className="ava" aria-hidden="true">{account.login.slice(0, 1).toUpperCase()}</span>
      <span>{account.login}</span>
    </button>
    <button type="button" className="small-btn" onClick={() => void logout().catch(err => onError(errorText(err)))}>Выйти</button>
    {open && <AccountEditor account={account} ownProfile onSaved={onAccountChange} onClose={() => setOpen(false)} />}
  </div>
}

export function AccountEditor({ account, ownProfile, onSaved, onClose }: {
  account: Account
  ownProfile: boolean
  onSaved: (account: Account) => void
  onClose: () => void
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  const title = useId()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const userPasswordRules = account.role === 'user' ? { minLength: 8, maxLength: 72 } : {}

  useEffect(() => { dialog.current?.showModal() }, [])

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const login = String(form.get('login')).trim().toLowerCase()
    const newPassword = String(form.get('new_password'))
    if (newPassword !== form.get('repeat_password')) {
      setError('Новые пароли не совпадают.')
      return
    }
    const update: { login?: string; new_password?: string; current_password?: string } = {}
    if (login !== account.login) update.login = login
    if (newPassword) update.new_password = newPassword
    if (!update.login && !update.new_password) {
      dialog.current?.close()
      return
    }
    if (ownProfile) update.current_password = String(form.get('current_password'))

    setBusy(true)
    setError('')
    try {
      const path = ownProfile ? '/auth/me' : '/admin/users/' + account.id
      const saved = await api<Account>(path, json(update, 'PATCH'))
      onSaved(saved)
      dialog.current?.close()
    } catch (err) { setError(errorText(err)) }
    finally { setBusy(false) }
  }

  return <dialog ref={dialog} aria-labelledby={title} onClose={onClose} onCancel={event => { if (busy) event.preventDefault() }}>
    <h2 id={title}>{ownProfile ? 'Настройки профиля' : 'Редактирование аккаунта'}</h2>
    <p className="sub">Никнейм используется для входа.</p>
    <form onSubmit={save}>
      <label className="field">Никнейм<input name="login" defaultValue={account.login} autoComplete={ownProfile ? 'username' : 'off'}
        minLength={3} maxLength={40} pattern={'[a-zA-Z0-9_.\\-]{3,40}'} required disabled={busy} /></label>
      {ownProfile && <label className="field">Текущий пароль<input name="current_password" type="password" autoComplete="current-password" required disabled={busy} /></label>}
      <label className="field">Новый пароль<input name="new_password" type="password" autoComplete="new-password" {...userPasswordRules} disabled={busy} /></label>
      <label className="field">Повторите новый пароль<input name="repeat_password" type="password" autoComplete="new-password" {...userPasswordRules} disabled={busy} /></label>
      {error && <p role="alert" className="notice error">{error}</p>}
      <div className="actions">
        <button type="button" className="btn ghost" onClick={() => dialog.current?.close()} disabled={busy}>Отмена</button>
        <button className="btn" disabled={busy}>{busy ? 'Сохраняем…' : 'Сохранить'}</button>
      </div>
    </form>
  </dialog>
}
