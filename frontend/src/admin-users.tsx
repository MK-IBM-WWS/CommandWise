import { useEffect, useId, useRef, useState, type FormEvent } from 'react'
import { AccountEditor } from './account'
import { api, errorText, type Account } from './api'

function DeleteAccount({ account, onDeleted, onClose }: { account: Account; onDeleted: () => void; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  const title = useId()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { dialog.current?.showModal() }, [])

  async function remove(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api('/admin/users/' + account.id, { method: 'DELETE' })
      onDeleted()
      dialog.current?.close()
    } catch (err) { setError(errorText(err)) }
    finally { setBusy(false) }
  }

  return <dialog ref={dialog} aria-labelledby={title} onClose={onClose} onCancel={event => { if (busy) event.preventDefault() }}>
    <h2 id={title}>Удалить аккаунт?</h2>
    <form onSubmit={remove}>
      <p className="sub delete-account-text">Аккаунт «{account.login}» и вся его история чатов будут удалены.</p>
      {error && <p className="notice error" role="alert">{error}</p>}
      <div className="actions">
        <button type="button" className="btn ghost" disabled={busy} onClick={() => dialog.current?.close()}>Отмена</button>
        <button className="btn danger-btn" disabled={busy}>{busy ? 'Удаляем…' : 'Удалить аккаунт'}</button>
      </div>
    </form>
  </dialog>
}

export function AdminUsers({ account, onAccountChange }: { account: Account; onAccountChange: (account: Account) => void }) {
  const [users, setUsers] = useState<Account[]>()
  const [filter, setFilter] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [action, setAction] = useState<{ kind: 'edit' | 'delete'; user: Account }>()

  async function load(signal?: AbortSignal) {
    setError('')
    setLoading(true)
    try { setUsers((await api<{ items: Account[] }>('/admin/users', { signal })).items) }
    catch (err) { if (!signal?.aborted) setError(errorText(err)) }
    finally { if (!signal?.aborted) setLoading(false) }
  }
  useEffect(() => {
    const controller = new AbortController()
    void load(controller.signal)
    return () => controller.abort()
  }, [])

  function save(updated: Account) {
    setUsers(items => items?.map(user => user.id === updated.id ? updated : user))
    if (updated.id === account.id) onAccountChange(updated)
  }

  const visible = users?.map(user => user.id === account.id ? account : user)
    .filter(user => user.login.includes(filter.trim().toLowerCase()))
    .sort((a, b) => a.login.localeCompare(b.login))

  return <section className="card admin-card" aria-label="Аккаунты">
    <div className="admin-users-tools">
      <label className="field"><input type="search" value={filter} onChange={event => setFilter(event.target.value)}
        aria-label="Поиск по никнейму" placeholder="Поиск по никнейму" /></label>
      <button type="button" className="small-btn" disabled={loading} onClick={() => void load()}>Обновить</button>
    </div>
    {error && <p className="notice error" role="alert">{error}</p>}
    {loading && !users && <p role="status">Загружаем аккаунты…</p>}
    {visible?.length === 0 && <p className="sub">Аккаунты не найдены.</p>}
    {visible && visible.length > 0 && <div className="table-scroll">
      <table className="users-table">
        <thead><tr><th scope="col">Никнейм</th><th scope="col">Роль</th><th scope="col">Действия</th></tr></thead>
        <tbody>{visible.map(user => <tr key={user.id}>
          <td>{user.login}{user.id === account.id && <small className="current-account-note">Вы</small>}</td>
          <td>{user.role === 'admin' ? 'Администратор' : 'Пользователь'}</td>
          <td><div className="user-actions">
            <button type="button" className="small-btn" aria-label={`Редактировать ${user.login}`} onClick={() => setAction({ kind: 'edit', user })}>Редактировать</button>
            {user.id !== account.id && <button type="button" className="small-btn danger-link" aria-label={`Удалить ${user.login}`}
              onClick={() => setAction({ kind: 'delete', user })}>Удалить</button>}
          </div></td>
        </tr>)}</tbody>
      </table>
    </div>}
    {action?.kind === 'edit' && <AccountEditor account={action.user} ownProfile={action.user.id === account.id}
      onSaved={save} onClose={() => setAction(undefined)} />}
    {action?.kind === 'delete' && <DeleteAccount account={action.user} onClose={() => setAction(undefined)}
      onDeleted={() => setUsers(items => items?.filter(user => user.id !== action.user.id))} />}
  </section>
}
