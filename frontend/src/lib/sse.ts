// fetch asosidagi SSE mijozi (CONTRACT.md §9.8): EventSource Authorization header yubora olmaydi.
import { authHeaders, refreshTokens } from './api'

export type RunNote = { type: string; [key: string]: unknown }

const RETRY_MS = 5000

/** `/runs/{id}/stream`ga ulanadi, uzilsa qayta ulanadi. Qaytgan funksiya — to'xtatish. */
export function subscribeRun(runId: string, onNote: (note: RunNote) => void): () => void {
  const controller = new AbortController()

  const connect = async () => {
    while (!controller.signal.aborted) {
      try {
        const r = await fetch(`/api/v1/runs/${runId}/stream`, {
          headers: { Accept: 'text/event-stream', ...authHeaders() },
          signal: controller.signal,
        })
        if (r.status === 401 && (await refreshTokens())) continue
        if (!r.ok || !r.body) throw new Error(`SSE ${r.status}`)
        await readStream(r.body, onNote)
      } catch {
        if (controller.signal.aborted) return
      }
      await new Promise((resolve) => setTimeout(resolve, RETRY_MS))
    }
  }
  connect()
  return () => controller.abort()
}

async function readStream(body: ReadableStream<Uint8Array>, onNote: (note: RunNote) => void) {
  const reader = body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) return
    buffer += value
    let sep: number
    while ((sep = buffer.indexOf('\n\n')) >= 0) {
      const block = buffer.slice(0, sep)
      buffer = buffer.slice(sep + 2)
      const data = block
        .split('\n')
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.slice(5).trimStart())
        .join('\n')
      if (!data) continue // ': ping', 'retry:'
      try {
        onNote(JSON.parse(data))
      } catch {
        // noto'g'ri JSON — e'tiborsiz
      }
    }
  }
}
