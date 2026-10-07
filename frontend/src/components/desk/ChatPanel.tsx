import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2, Send } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { api, ApiError } from '@/lib/api'
import { formatTime } from '@/lib/time'
import type { ChatMessage, Persona } from '@/lib/types'
import Avatar from './Avatar'
import { reflow } from './RichText'

export default function ChatPanel({
  runId,
  persona,
  refreshKey,
  readOnly,
}: {
  runId: string
  persona: Persona
  refreshKey: number
  readOnly: boolean
}) {
  const { t } = useTranslation()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [waiting, setWaiting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottom = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let cancelled = false
    api<ChatMessage[]>(`/runs/${runId}/chat/${persona.key}`)
      .then((m) => !cancelled && setMessages(m))
      .catch(() => !cancelled && setError(t('common.error')))
    return () => {
      cancelled = true
    }
  }, [runId, persona.key, refreshKey, t])

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: 'end' })
  }, [messages, waiting])

  const send = async () => {
    const text = draft.trim()
    if (!text || waiting) return
    setWaiting(true)
    setError(null)
    try {
      const res = await api<{ message: ChatMessage; reply: ChatMessage }>(`/runs/${runId}/chat/${persona.key}`, {
        method: 'POST',
        json: { text },
      })
      setDraft('')
      setMessages((m) => {
        const seen = new Set(m.map((x) => x.id))
        return [...m, ...[res.message, res.reply].filter((x) => !seen.has(x.id))]
      })
    } catch (err) {
      setError(err instanceof ApiError && err.status === 429 ? t('desk.chat.tooFast') : (err as Error).message)
    } finally {
      setWaiting(false)
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center gap-3 border-y border-border/60 px-4 py-3">
        <Avatar persona={persona} />
        <div className="min-w-0">
        <p className="font-bold">{persona.name}</p>
        <p className="truncate text-xs text-muted-foreground">
          {persona.role}
          {persona.kind === 'mentor' && !/mentor/i.test(persona.role) && ` · ${t('desk.chat.mentor')}`}
        </p>
        </div>
      </div>
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 && <p className="text-sm text-muted-foreground">{t('desk.chat.empty')}</p>}
        {messages.map((m) => {
          const mine = m.sender === 'student'
          return (
            <div key={m.id} className={cn('flex flex-col animate-rise', mine ? 'items-end' : 'items-start')}>
              <div className={cn(
                'max-w-[85%] whitespace-pre-wrap rounded-2xl px-3.5 py-2 text-sm leading-relaxed shadow-sm',
                mine ? 'bg-brand rounded-br-md text-primary-foreground' : 'rounded-bl-md bg-background/85',
              )}>
                {mine ? m.body : reflow(m.body)}
                {m.link_url && (
                  <a href={m.link_url} target="_blank" rel="noreferrer noopener" className="block underline">
                    {m.link_url}
                  </a>
                )}
              </div>
              <span className="mt-0.5 text-[10px] text-muted-foreground">{formatTime(m.created_at)}</span>
            </div>
          )
        })}
        {waiting && (
          <p className="flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="h-3 w-3 animate-spin" /> {t('desk.chat.typing', { name: persona.name })}
          </p>
        )}
        <div ref={bottom} />
      </div>
      {!readOnly && (
        <div className="space-y-2 border-t border-border/60 p-3">
          {error && <p className="text-xs text-destructive">{error}</p>}
          <div className="flex gap-2">
            <Textarea
              rows={2}
              className="min-h-0 resize-none"
              placeholder={t('desk.chat.placeholder')}
              value={draft}
              maxLength={4000}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  send()
                }
              }}
            />
            <Button size="icon" className="h-11 w-11 shrink-0" onClick={send} disabled={waiting || !draft.trim()} aria-label={t('desk.chat.send')}>
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
