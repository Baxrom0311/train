import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlarmClock, ClipboardCheck, Loader2, Send, UsersRound } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { api, ApiError } from '@/lib/api'
import { formatTime } from '@/lib/time'
import type { ChatMessage, Persona } from '@/lib/types'
import Avatar from './Avatar'
import { reflow } from './RichText'

const PURPOSE_ICON = { review: ClipboardCheck, nudge: AlarmClock }

/**
 * Personaj chati yoki (`persona` null) jamoa chati (CONTRACT.md §29.3). Jamoaviy Run'da
 * `me` beriladi: "o'zimniki" — muallif bo'yicha, jamoadoshlar xabari ismi bilan.
 */
export default function ChatPanel({
  runId,
  persona,
  refreshKey,
  readOnly,
  me,
}: {
  runId: string
  persona: Persona | null
  refreshKey: number
  readOnly: boolean
  me?: string
}) {
  const { t } = useTranslation()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [waiting, setWaiting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottom = useRef<HTMLDivElement>(null)
  const url = persona ? `/runs/${runId}/chat/${persona.key}` : `/runs/${runId}/team-chat`

  useEffect(() => {
    let cancelled = false
    api<ChatMessage[]>(url)
      .then((m) => !cancelled && setMessages(m))
      .catch(() => !cancelled && setError(t('common.error')))
    return () => {
      cancelled = true
    }
  }, [url, refreshKey, t])

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: 'end' })
  }, [messages, waiting])

  const send = async () => {
    const text = draft.trim()
    if (!text || waiting) return
    setWaiting(true)
    setError(null)
    try {
      // jamoa chatida AI javob bermaydi — faqat yuborilgan xabar qaytadi
      const added = persona
        ? await api<{ message: ChatMessage; reply: ChatMessage }>(url, { method: 'POST', json: { text } })
          .then((res) => [res.message, res.reply])
        : [await api<ChatMessage>(url, { method: 'POST', json: { text } })]
      setDraft('')
      setMessages((m) => {
        const seen = new Set(m.map((x) => x.id))
        return [...m, ...added.filter((x) => !seen.has(x.id))]
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
        {persona ? <Avatar persona={persona} /> : (
          <span className="bg-brand grid h-9 w-9 shrink-0 place-items-center rounded-full text-primary-foreground">
            <UsersRound className="h-4 w-4" />
          </span>
        )}
        <div className="min-w-0">
        <p className="font-bold">{persona ? persona.name : t('desk.team.chat')}</p>
        <p className="truncate text-xs text-muted-foreground">
          {persona ? persona.role : t('desk.team.chatHint')}
          {persona?.kind === 'mentor' && !/mentor/i.test(persona.role) && ` · ${t('desk.chat.mentor')}`}
        </p>
        </div>
      </div>
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 && <p className="text-sm text-muted-foreground">{t(persona ? 'desk.chat.empty' : 'desk.team.chatEmpty')}</p>}
        {messages.map((m) => {
          const student = m.sender === 'student'
          const mine = student && (me === undefined || m.author_id === me)
          const Tag = m.purpose ? PURPOSE_ICON[m.purpose] : null
          return (
            <div key={m.id} className={cn('flex flex-col animate-rise', mine ? 'items-end' : 'items-start')}>
              {student && !mine && m.author_name && (
                <span className="mb-0.5 text-[11px] font-semibold text-muted-foreground">{m.author_name}</span>
              )}
              {Tag && (
                <span className="mb-1 flex items-center gap-1 text-[11px] font-semibold text-primary">
                  <Tag className="h-3.5 w-3.5" /> {t(`desk.chat.purpose.${m.purpose}`)}
                </span>
              )}
              <div className={cn(
                'max-w-[85%] whitespace-pre-wrap rounded-2xl px-3.5 py-2 text-sm leading-relaxed shadow-sm',
                mine ? 'bg-brand rounded-br-md text-primary-foreground'
                  : student ? 'rounded-bl-md bg-primary/12' : 'rounded-bl-md bg-background/85',
                m.purpose && 'ring-1 ring-primary/30',
              )}>
                {student ? m.body : reflow(m.body)}
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
        {waiting && persona && (
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
