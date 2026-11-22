import { Children, Fragment, useEffect, useLayoutEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Brand } from './brand'
import { AccountMenu, type AccountMenuProps } from './account'
import {
  api, ApiError, errorText, json, newRequestID, streamQuestion, targetLabel,
  type Chat, type Corpus, type Message, type Snapshot, type Source,
} from './api'

type Live = { id: string; text: string; status: Message['status']; sources: Source[]; finish?: string; error?: string }
type Connection = { controller: AbortController; accepted: boolean }
type Attempt = { text: string; id: string }
const activeStatus = (status?: string) => status === 'queued' || status === 'generating'
const statusLabel = (status: string) => status === 'queued' ? 'В очереди' : 'Генерируется'

function CodeBlock({ children }: { children: ReactNode }) {
  const code = useRef<HTMLPreElement>(null)
  const [label, setLabel] = useState('Копировать')
  async function copy() {
    try {
      await navigator.clipboard.writeText(code.current?.textContent ?? '')
      setLabel('Скопировано')
    } catch { setLabel('Выделите код для копирования') }
  }
  return <div className="code-block">
    <button type="button" className="small-btn" onClick={() => void copy()}>{label}</button>
    <pre ref={code}>{children}</pre>
  </div>
}

function Markdown({ text, sources = [], openSource }: { text: string; sources?: Source[]; openSource?: (source: Source) => void }) {
  function linkCitations(children: ReactNode) {
    return Children.map(children, child => {
      if (!openSource || !sources.length || typeof child !== 'string') return child
      return child.split(/(\[\d+\])/g).map((part, index) => {
        const match = part.match(/^\[(\d+)\]$/)
        const source = match && sources.find(item => item.ref === Number(match[1]))
        return source
          ? <button key={index} type="button" className="citation" onClick={() => openSource(source)} aria-label={`Источник ${source.ref}`}>{part}</button>
          : <Fragment key={index}>{part}</Fragment>
      })
    })
  }
  return <div className="markdown"><ReactMarkdown skipHtml remarkPlugins={[remarkGfm]} components={{
    pre: ({ children }) => <CodeBlock>{children}</CodeBlock>,
    p: ({ children }) => <p>{linkCitations(children)}</p>,
    li: ({ children }) => <li>{linkCitations(children)}</li>,
    a: ({ children, href }) => <a href={href} target="_blank" rel="noreferrer">{children}</a>,
    img: ({ alt }) => <span>{alt}</span>,
  }}>{text}</ReactMarkdown></div>
}

export function ChatPage({ account, onAccountChange, logout }: AccountMenuProps) {
  const [chats, setChats] = useState<Chat[]>([])
  const [corpus, setCorpus] = useState<Corpus>()
  const [chatID, setChatID] = useState('')
  const selected = useRef('')
  const [conversation, setConversation] = useState<{ id: string; items: Message[] }>()
  const [refresh, setRefresh] = useState(0)
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [sending, setSending] = useState<Record<string, boolean>>({})
  const [live, setLive] = useState<Record<string, Live>>({})
  const [error, setError] = useState('')
  const [chatErrors, setChatErrors] = useState<Record<string, string>>({})
  const [sidebar, setSidebar] = useState(false)
  const [distribution, setDistribution] = useState('')
  const [creating, setCreating] = useState(false)
  const [stopping, setStopping] = useState(false)
  const [source, setSource] = useState<Snapshot>()
  const [sourceError, setSourceError] = useState('')
  const sourceRequest = useRef<AbortController | null>(null)
  const newDialog = useRef<HTMLDialogElement>(null)
  const sourceDialog = useRef<HTMLDialogElement>(null)
  const thread = useRef<HTMLElement>(null)
  const pin = useRef(true)
  const connections = useRef(new Map<string, Connection>())
  const attempts = useRef(new Map<string, Attempt>())
  const accountKey = 'commandwise.chat.' + account.id
  const current = chats.find(item => item.id === chatID)
  const currentLive = live[chatID]
  const messages = conversation?.id === chatID ? conversation.items : []
  const pending = messages.find(message => activeStatus(message.status))
  const liveAlreadySaved = messages.some(message => message.id === currentLive?.id)
  const pendingID = pending?.id ?? (!liveAlreadySaved && activeStatus(currentLive?.status) ? currentLive.id : undefined)
  const busy = Boolean(sending[chatID] || pendingID || activeStatus(current?.status))

  function select(id: string) {
    const previous = connections.current.get(selected.current)
    if (id !== selected.current && previous?.accepted) previous.controller.abort()
    selected.current = id
    pin.current = true
    setChatID(id)
    setSidebar(false)
    if (id) localStorage.setItem(accountKey, id)
    else localStorage.removeItem(accountKey)
  }

  async function loadChats(signal?: AbortSignal) {
    const { items } = await api<{ items: Chat[] }>('/chats', { signal })
    setChats(items)
    if (!items.some(item => item.id === selected.current)) {
      const stored = localStorage.getItem(accountKey)
      select(items.find(item => item.id === stored)?.id ?? items[0]?.id ?? '')
    }
  }

  function reload() {
    void loadChats().catch(err => setError(errorText(err)))
    setRefresh(value => value + 1)
  }

  useEffect(() => {
    const controller = new AbortController()
    let loading = false
    async function check() {
      if (loading) return
      loading = true
      try { await loadChats(controller.signal) }
      catch (err) { if (!controller.signal.aborted) setError(errorText(err)) }
      finally { loading = false }
    }
    void check()
    const timer = window.setInterval(check, 1300)
    return () => {
      controller.abort()
      window.clearInterval(timer)
      connections.current.forEach(item => item.controller.abort())
      sourceRequest.current?.abort()
    }
  }, [])

  useEffect(() => {
    if (!chatID) return
    const controller = new AbortController()
    let loading = false
    async function pull() {
      if (loading) return
      loading = true
      try {
        const { items } = await api<{ items: Message[] }>('/chats/' + chatID + '/messages', { signal: controller.signal })
        if (!controller.signal.aborted) {
          setConversation(previous => previous?.id === chatID && JSON.stringify(previous.items) === JSON.stringify(items) ? previous : { id: chatID, items })
        }
      } catch (err) {
        if (!controller.signal.aborted && (!(err instanceof ApiError) || err.status !== 404)) setError(errorText(err))
      } finally { loading = false }
    }
    void pull()
    const timer = window.setInterval(pull, busy ? 700 : 2900)
    return () => { controller.abort(); window.clearInterval(timer) }
  }, [chatID, refresh, busy])

  useLayoutEffect(() => {
    const box = thread.current
    if (box && pin.current) box.scrollTop = box.scrollHeight
  }, [conversation, currentLive, chatID])

  async function openNew() {
    setError('')
    try {
      const actual = await api<Corpus>('/corpus')
      const first = actual.distributions[0]
      setCorpus(actual)
      setDistribution(first?.id ?? '')
      newDialog.current?.showModal()
    } catch (err) { setError(errorText(err)) }
  }

  async function create(event: FormEvent) {
    event.preventDefault()
    setCreating(true)
    setError('')
    try {
      const newChat = await api<Chat>('/chats', json({ distribution }))
      setChats(items => [newChat, ...items.filter(item => item.id !== newChat.id)])
      select(newChat.id)
      newDialog.current?.close()
    } catch (err) {
      newDialog.current?.close()
      setError(errorText(err))
    } finally { setCreating(false) }
  }

  async function remove() {
    if (!current || !window.confirm(`Удалить чат «${current.title}» и его историю?`)) return
    try {
      await api('/chats/' + current.id, { method: 'DELETE' })
      setChats(items => items.filter(item => item.id !== current.id))
      if (selected.current === current.id) select('')
      reload()
    } catch (err) { setError(errorText(err)) }
  }

  function errorFor(id: string, text: string) { setChatErrors(values => ({ ...values, [id]: text })) }

  async function send(event: FormEvent) {
    event.preventDefault()
    const text = drafts[chatID]?.trim()
    if (!text || busy || connections.current.has(chatID)) return
    const id = chatID
    const oldAttempt = attempts.current.get(id)
    const requestID = oldAttempt?.text === text ? oldAttempt.id : newRequestID()
    attempts.current.set(id, { text, id: requestID })
    const connection = { controller: new AbortController(), accepted: false }
    connections.current.set(id, connection)
    setSending(values => ({ ...values, [id]: true }))
    errorFor(id, '')
    setLive(values => {
      const next = { ...values }
      delete next[id]
      return next
    })
    let currentAnswer: Live | undefined
    try {
      await streamQuestion(id, text, requestID, connection.controller.signal, event => {
        switch (event.kind) {
          case 'status':
            if (!connection.accepted) {
              connection.accepted = true
              attempts.current.delete(id)
              setDrafts(values => values[id]?.trim() === text ? { ...values, [id]: '' } : values)
              if (selected.current !== id) connection.controller.abort()
            }
            currentAnswer = { ...(currentAnswer ?? { id: event.message_id, text: '', sources: [] }), status: event.status }
            break
          case 'sources': if (currentAnswer) currentAnswer = { ...currentAnswer, sources: event.sources }; break
          case 'token': if (currentAnswer) currentAnswer = { ...currentAnswer, text: currentAnswer.text + event.delta }; break
          case 'done':
            if (currentAnswer) currentAnswer = { ...currentAnswer, status: event.finish_reason === 'cancelled' ? 'cancelled' : 'complete', finish: event.finish_reason }
            break
          case 'error':
            if (currentAnswer) currentAnswer = { ...currentAnswer, status: 'error', error: event.message }
            else errorFor(id, event.message)
            break
        }
        if (currentAnswer) {
          const snapshot = currentAnswer
          setLive(values => ({ ...values, [id]: snapshot }))
        }
      })
    } catch (err) {
      if (err instanceof ApiError && err.code === 'REQUEST_EXISTS') {
        attempts.current.delete(id)
        setDrafts(values => values[id]?.trim() === text ? { ...values, [id]: '' } : values)
      } else if (!connection.controller.signal.aborted) errorFor(id, errorText(err))
    } finally {
      connections.current.delete(id)
      setSending(values => ({ ...values, [id]: false }))
      if (!currentAnswer || activeStatus(currentAnswer.status)) {
        setLive(values => {
          const next = { ...values }
          delete next[id]
          return next
        })
      }
      reload()
    }
  }

  async function stop() {
    if (!pendingID) return
    setStopping(true)
    try {
      await api('/chats/' + chatID + '/messages/' + pendingID + '/cancel', { method: 'POST' })
      reload()
    } catch (err) { errorFor(chatID, errorText(err)) }
    finally { setStopping(false) }
  }

  async function inspect(message: Message, card: Source) {
    sourceRequest.current?.abort()
    const controller = new AbortController()
    sourceRequest.current = controller
    setSource(undefined)
    setSourceError('')
    sourceDialog.current?.showModal()
    try {
      setSource(await api<Snapshot>(`/chats/${chatID}/messages/${message.id}/sources/${encodeURIComponent(card.chunk_id)}`, { signal: controller.signal }))
    } catch (err) { if (!controller.signal.aborted) setSourceError(errorText(err)) }
  }

  const display = currentLive && !messages.some(message => message.id === currentLive.id)
    ? [...messages, { id: currentLive.id, role: 'assistant', content: '', status: currentLive.status, sources: [], created_at: '' } satisfies Message]
    : messages

  return <div className="app">
    {sidebar && <button className="side-backdrop" aria-label="Скрыть список чатов" onClick={() => setSidebar(false)} />}
    <aside className={'side' + (sidebar ? ' side-open' : '')}>
      <Brand />
      <button className="new" type="button" onClick={() => void openNew()} disabled={chats.length >= 10}>+ Новый чат</button>
      <p className="chat-count">{chats.length} из 10 чатов</p>
      <nav className="hist" aria-label="История чатов">
        {chats.map(chat => <button key={chat.id} className={chat.id === chatID ? 'on' : ''} aria-current={chat.id === chatID ? 'page' : undefined} onClick={() => select(chat.id)}>
          <span>{chat.title}</span>
          <small>{targetLabel(chat)}{activeStatus(chat.status) ? ' · ' + statusLabel(chat.status) : ''}</small>
        </button>)}
      </nav>
      <AccountMenu account={account} onAccountChange={onAccountChange} logout={logout} onError={setError} />
    </aside>
    <main className="chat">
      <header className="chat-header">
        <button className="small-btn sidebar-toggle" aria-expanded={sidebar} onClick={() => setSidebar(!sidebar)}>Чаты</button>
        <div className="chat-heading"><strong>{current?.title ?? 'Чат с документацией'}</strong>{current && <small>{targetLabel(current)}</small>}</div>
        {current && <button className="small-btn" disabled={busy} onClick={() => void remove()}>Удалить</button>}
      </header>
      {(error || chatErrors[chatID]) && <p role="alert" className="notice error inline-error">{chatErrors[chatID] || error}
        <button className="small-btn" onClick={() => { setError(''); errorFor(chatID, '') }}>Закрыть</button>
      </p>}
      <section className="msgs" ref={thread} aria-label="Сообщения" onScroll={event => {
        const box = event.currentTarget
        pin.current = box.scrollHeight - box.scrollTop - box.clientHeight < 100
      }}>
        <div>
          {!current && <div className="empty"><h1>Команды Linux</h1><p>Выберите дистрибутив, чтобы получить ответ по его документации.</p><button className="btn" onClick={() => void openNew()}>Создать чат</button></div>}
          {current && !display.length && <p className="sub">Задайте вопрос о команде или задаче в {targetLabel(current)}.</p>}
          {display.map(message => {
            const overlay = currentLive?.id === message.id && activeStatus(message.status) ? currentLive : undefined
            const state = overlay?.status ?? message.status
            const text = overlay && overlay.text.length > message.content.length ? overlay.text : message.content
            const sources = overlay?.sources.length ? overlay.sources : message.sources
            return <article key={message.id} className={'m ' + (message.role === 'user' ? 'u' : 'ai')}>
              {message.role === 'user' ? <p className="user-text">{text}</p> : <Markdown text={text} sources={sources} openSource={card => void inspect(message, card)} />}
              {activeStatus(state) && <p className="message-status" role="status">{statusLabel(state)}…</p>}
              {state === 'error' && <p className="message-status" role="alert">{overlay?.error || message.error || 'Генерация прервана.'}</p>}
              {state === 'cancelled' && <p className="message-status">Остановлено</p>}
              {(overlay?.finish ?? message.finish_reason) === 'length' && <p className="message-status">Достигнут лимит длины ответа.</p>}
              {sources.length > 0 && <div className="sources">{sources.map(source => <button key={source.chunk_id} className="small-btn" onClick={() => void inspect(message, source)}>
                [{source.ref}] {source.section || source.title}
              </button>)}</div>}
            </article>
          })}
        </div>
      </section>
      {current && <form className="composer" onSubmit={send}>
        <textarea key={chatID} name="question" value={drafts[chatID] ?? ''} onChange={event => setDrafts(values => ({ ...values, [chatID]: event.target.value }))}
          onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); event.currentTarget.form?.requestSubmit() } }}
          rows={1} placeholder="Напишите сообщение" aria-label="Сообщение" maxLength={4000} />
        {busy ? <button type="button" className="small-btn stop" onClick={() => void stop()} disabled={!pendingID || stopping}>Остановить</button>
          : <button className="send" aria-label="Отправить" disabled={!drafts[chatID]?.trim()}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 19V5M5 12l7-7 7 7"/></svg>
          </button>}
      </form>}
    </main>
    <dialog ref={newDialog}>
      <form onSubmit={create}>
        <h2>Новый чат</h2>
        <p className="sub">Выберите систему, по которой будете задавать вопросы.</p>
        <label className="field">Дистрибутив<select value={distribution} required onChange={event => setDistribution(event.target.value)}>
          {corpus?.distributions.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}
        </select></label>
        <div className="actions"><button className="btn ghost" type="button" onClick={() => newDialog.current?.close()}>Отмена</button>
          <button className="btn" disabled={creating || !distribution}>Создать чат</button></div>
      </form>
    </dialog>
    <dialog className="source-dialog" ref={sourceDialog} onClose={() => sourceRequest.current?.abort()}>
      <div className="admin-table-header"><h2>Источник</h2><button className="small-btn" onClick={() => sourceDialog.current?.close()}>Закрыть</button></div>
      {sourceError ? <p role="alert">{sourceError}</p> : source ? <>
        <p className="sub">{source.command} · {source.section}{source.package_version ? ' · ' + source.package_version : ''}</p>
        <Markdown text={source.text} />
        {/^https?:\/\//.test(source.source_url) && <p><a className="text-link" href={source.source_url} target="_blank" rel="noreferrer">Открыть оригинал</a></p>}
      </> : <p role="status">Загружаем фрагмент…</p>}
    </dialog>
  </div>
}
