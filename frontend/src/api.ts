export type Account = { id: string; login: string; role: 'user' | 'admin' }
export type Target = { distribution: string }
export type Distribution = { id: string; label: string }
export type Corpus = { corpus_version: string; distributions: Distribution[] }
export type Chat = Target & { id: string; title: string; status: 'idle' | 'queued' | 'generating'; created_at: string }
export type Source = Target & { ref: number; chunk_id: string; document_id: string; title: string; section: string; source_url: string }
export type Snapshot = Source & { text: string; command: string; package_version: string; corpus_version: string; collected_at?: string }
export type Message = {
  id: string; role: 'user' | 'assistant'; content: string;
  status: 'queued' | 'generating' | 'complete' | 'cancelled' | 'error';
  sources: Source[]; created_at: string; finish_reason?: string; error?: string
}
export type RagDocument = {
  document_id: string; package: string; package_version: string; source_url: string;
  collected_at: string; verified_targets: Target[]
}
export type RagDocuments = { corpus_version: string; items: RagDocument[] }

type ErrorPayload = { error?: { code?: string; message?: string; message_id?: string } }

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) { super(message) }
}

export function errorText(error: unknown) {
  if (error instanceof ApiError) return error.message
  return 'Не удалось связаться с сервером. Проверьте соединение.'
}

async function request(path: string, options: RequestInit = {}) {
  const response = await fetch('/api/v1' + path, { ...options, credentials: 'same-origin' })
  if (!response.ok) {
    const result: ErrorPayload = await response.json().catch(() => ({}))
    if (response.status === 401 && !['/auth/login', '/auth/register'].includes(path)) {
      window.dispatchEvent(new Event('commandwise:unauthorized'))
    }
    throw new ApiError(response.status, result.error?.code ?? '', result.error?.message ?? 'Сервер не смог обработать запрос.')
  }
  return response
}

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await request(path, options)
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export function json(body: unknown): RequestInit {
  return { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
}

type StreamEvent =
  | { kind: 'status'; message_id: string; status: 'queued' | 'generating' }
  | { kind: 'sources'; message_id: string; sources: Source[] }
  | { kind: 'token'; delta: string }
  | { kind: 'done'; message_id: string; finish_reason: string }
  | { kind: 'error'; message: string; code: string }

export async function streamQuestion(chatID: string, content: string, requestID: string, signal: AbortSignal, onEvent: (event: StreamEvent) => void) {
  const response = await request('/chats/' + chatID + '/messages', {
    ...json({ content, client_request_id: requestID, stream: true }),
    signal,
  })
  if (!response.body || !response.headers.get('Content-Type')?.startsWith('text/event-stream')) {
    throw new ApiError(502, 'INVALID_STREAM', 'Поток ответа недоступен. Проверьте историю чата.')
  }
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  let pending = ''
  try {
    for (;;) {
      const { value, done } = await reader.read()
      if (done) throw new ApiError(502, 'STREAM_ENDED', 'Поток прервался. Состояние вопроса синхронизируется с историей.')
      pending += value
      const frames = pending.split(/\r?\n\r?\n/)
      pending = frames.pop() ?? ''
      for (const frame of frames) {
        const lines = frame.split(/\r?\n/)
        const kind = lines.find(line => line.startsWith('event:'))?.slice(6).trim()
        const data = lines.filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n')
        if (!kind || !data) continue
        const event = { ...JSON.parse(data), kind } as StreamEvent
        onEvent(event)
        if (kind === 'done' || kind === 'error') return
      }
    }
  } finally {
    await reader.cancel().catch(() => undefined)
  }
}

export function newRequestID() {
  if (crypto.randomUUID) return crypto.randomUUID()
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  bytes[6] = (bytes[6] & 15) | 64
  bytes[8] = (bytes[8] & 63) | 128
  const hex = Array.from(bytes, value => value.toString(16).padStart(2, '0')).join('')
  return [hex.slice(0, 8), hex.slice(8, 12), hex.slice(12, 16), hex.slice(16, 20), hex.slice(20)].join('-')
}

export const distributionNames: Record<string,string> = { debian: 'Debian', fedora: 'Fedora', arch: 'Arch Linux' }
export const targetLabel = (value: Target) => distributionNames[value.distribution] ?? value.distribution
