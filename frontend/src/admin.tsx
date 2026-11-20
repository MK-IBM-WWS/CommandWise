import { useEffect, useState, type FormEvent } from 'react'
import { api, distributionNames, errorText, targetLabel, type Account, type RagDocuments } from './api'
import { Brand } from './brand'

function dateToday() {
  const date = new Date()
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return local.toISOString().slice(0, 10)
}

export function AdminPage({ account, logout }: { account: Account; logout: () => Promise<void> }) {
  const [docs, setDocs] = useState<RagDocuments>()
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [busy, setBusy] = useState(false)

  async function load() {
    try { setDocs(await api<RagDocuments>('/admin/documents')) }
    catch (err) { setError(errorText(err)) }
  }
  useEffect(() => { void load() }, [])

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const data = new FormData(form)
    const file = data.get('file')
    setError('')
    setSuccess('')
    if (!(file instanceof File) || !file.name.toLowerCase().endsWith('.md') || file.size > 512 * 1024) {
      setError('Выберите Markdown-файл .md размером до 512 КиБ.')
      return
    }
    setBusy(true)
    try {
      const published = await api<{ document_id: string; corpus_version: string }>('/admin/documents', { method: 'POST', body: data })
      form.reset()
      setSuccess(`Документ «${published.document_id}» опубликован. Версия корпуса ${published.corpus_version}.`)
      await load()
    } catch (err) { setError(errorText(err)) }
    finally { setBusy(false) }
  }

  return <div className="admin">
    <header className="admin-header"><Brand /><div>{account.login} <button className="small-btn" onClick={() => void logout().catch(err => setError(errorText(err)))}>Выйти</button></div></header>
    <main className="admin-main">
      <h1>Управление корпусом</h1>
      {error && <p className="notice error" role="alert">{error}</p>}
      {success && <p className="notice" role="status">{success}</p>}
      <section className="card admin-card">
        <h2>Добавить документ</h2>
        <p className="sub">Markdown в UTF-8 до 512 КиБ с разделами второго или третьего уровня.</p>
        <form onSubmit={upload}>
          <div className="admin-fields">
            <label className="field">Идентификатор<input name="document_id" placeholder="systemctl" pattern="[a-z0-9][a-z0-9_\-]{0,63}" maxLength={64} required /></label>
            <label className="field">Документ<input name="file" type="file" accept=".md,text/markdown" required /></label>
            <label className="field">Пакет<input name="package" maxLength={80} required /></label>
            <label className="field">Версия пакета<input name="package_version" maxLength={80} required /></label>
            <label className="field">Дистрибутив<select name="distribution" defaultValue="debian">{Object.entries(distributionNames).map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>
            <label className="field">Версия дистрибутива<input name="release" maxLength={48} defaultValue="13" required /></label>
            <label className="field">Ссылка на оригинал<input name="source_url" type="url" placeholder="https://…" maxLength={2048} required /></label>
            <label className="field">Дата проверки<input name="collected_at" type="date" defaultValue={dateToday()} required /></label>
          </div>
          <button className="btn" disabled={busy}>{busy ? 'Обновляем индекс…' : 'Опубликовать документ'}</button>
        </form>
      </section>
      <section className="card admin-card">
        <div className="admin-table-header"><h2>Документы</h2><button className="small-btn" onClick={() => void load()}>Обновить</button></div>
        {docs && <>
          <p className="sub">Версия корпуса {docs.corpus_version} · {docs.items.length} документов</p>
          <div className="table-scroll"><table><thead><tr><th>Документ</th><th>Пакет</th><th>Проверено для</th></tr></thead>
            <tbody>{docs.items.map(doc => <tr key={doc.document_id}>
              <td><a href={doc.source_url.match(/^https?:\/\//) ? doc.source_url : undefined} target="_blank" rel="noreferrer">{doc.document_id}</a></td>
              <td>{[doc.package, doc.package_version].filter(Boolean).join(' ')}</td>
              <td>{doc.verified_targets.map(targetLabel).join(', ') || 'Черновик'}</td>
            </tr>)}</tbody>
          </table></div>
        </>}
      </section>
    </main>
  </div>
}
