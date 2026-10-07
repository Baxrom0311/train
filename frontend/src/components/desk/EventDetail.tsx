import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { FileText, Lightbulb, Loader2, MessageCircle, Paperclip } from 'lucide-react'
import { ScoreRing } from '@/components/score'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { api, ApiError, uploadFile } from '@/lib/api'
import { formatDateTime, remaining } from '@/lib/time'
import type { AnswerType, HintResult, Persona, RunDetail, RunEvent, SubmissionResult } from '@/lib/types'
import RichText from './RichText'
import { StatusLabel } from './Inbox'

const ANSWERABLE = ['task', 'incident', 'day_end']

export default function EventDetail({
  run,
  event,
  personas,
  now,
  onRun,
  onOpenDoc,
  onAskMentor,
}: {
  run: RunDetail
  event: RunEvent
  personas: Persona[]
  now: number
  onRun: (run: RunDetail) => void
  onOpenDoc: (key: string) => void
  onAskMentor?: () => void
}) {
  const { t } = useTranslation()
  const sender = personas.find((p) => p.key === event.from_persona)
  const open = run.status === 'active'
  const visibleStatus = ['delivered', 'submitted', 'missed'].includes(event.status)
  const canAnswer =
    open && ANSWERABLE.includes(event.type) && visibleStatus && event.attempts_used < event.max_attempts
  const canDecide = open && event.type === 'decision' && event.choice === null && visibleStatus
  const left = event.status === 'delivered' && event.due_at ? remaining(event.due_at, now) : null
  // oldingi urinish baholanmaguncha qayta yuborish formasi ko'rsatilmaydi
  const evaluating = event.last_eval_status === 'pending' || event.last_eval_status === 'queued_retry'

  return (
    <article className="mx-auto max-w-3xl space-y-6 p-6 lg:p-8">
      <header className="space-y-1">
        <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${
            event.type === 'incident' ? 'bg-destructive/12 text-destructive' : 'bg-primary/12 text-primary'
          }`}>{t(`desk.type.${event.type}`)}</span>
          {sender && <span className="font-medium text-foreground/80">{sender.name}<span className="font-normal text-muted-foreground"> · {sender.role}</span></span>}
          {event.delivered_at && <span className="ml-auto tabular-nums">{formatDateTime(event.delivered_at)}</span>}
        </div>
        {event.type !== 'message' && (
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <StatusLabel event={event} />
            {event.due_at && (
              <span className="text-muted-foreground">
                {t('desk.due', { time: formatDateTime(event.due_at) })}
                {left && ` (${t('desk.left', { time: left.label })})`}
              </span>
            )}
          </div>
        )}
      </header>

      <RichText className="text-[15px]" text={event.brief || t('desk.dayEndDefault')} />

      {event.attachments.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {event.attachments.map((a) => (
            <Button key={a.key} variant="outline" size="sm" onClick={() => onOpenDoc(a.key)}>
              <FileText className="mr-1 h-4 w-4" /> {a.title}
            </Button>
          ))}
        </div>
      )}

      {event.type === 'decision' && <Decision run={run} event={event} canDecide={canDecide} onRun={onRun} />}

      {ANSWERABLE.includes(event.type) && (
        <Feedback event={event} mentor={personas.find((p) => p.kind === 'mentor')} onAskMentor={onAskMentor} />
      )}

      {canAnswer && !evaluating && (
        <AnswerForm key={event.node_id + event.attempts_used} run={run} event={event} onRun={onRun} />
      )}

      {open && ['task', 'incident'].includes(event.type) && visibleStatus && <Hints runId={run.id} nodeId={event.node_id} />}
    </article>
  )
}

function Decision({ run, event, canDecide, onRun }: { run: RunDetail; event: RunEvent; canDecide: boolean; onRun: (r: RunDetail) => void }) {
  const { t } = useTranslation()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const choose = async (option: string) => {
    setBusy(true)
    setError(null)
    try {
      const res = await api<SubmissionResult>(`/runs/${run.id}/events/${event.node_id}/decide`, {
        method: 'POST',
        json: { option },
      })
      onRun(res.run)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-2">
      {event.options.map((o, i) => (
        <button
          key={o.key}
          type="button"
          disabled={!canDecide || busy}
          onClick={() => choose(o.key)}
          className={`flex w-full items-start gap-3 rounded-xl border bg-background/60 p-4 text-left text-sm transition-all enabled:hover:-translate-y-0.5 enabled:hover:border-primary/50 enabled:hover:shadow-md disabled:cursor-default ${
            event.choice === o.key ? 'border-primary bg-primary/8 font-semibold ring-2 ring-primary/20' : ''
          }`}
        >
          <span className={`grid h-6 w-6 shrink-0 place-items-center rounded-full text-xs font-bold ${
            event.choice === o.key ? 'bg-brand text-primary-foreground' : 'bg-muted text-muted-foreground'
          }`}>{String.fromCharCode(65 + i)}</span>
          {o.label}
        </button>
      ))}
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  )
}

function Feedback({ event, mentor, onAskMentor }: { event: RunEvent; mentor?: Persona; onAskMentor?: () => void }) {
  const { t } = useTranslation()
  if (event.attempts_used === 0) return null
  const evaluating = event.last_eval_status === 'pending' || event.last_eval_status === 'queued_retry'
  return (
    <div className="space-y-3 rounded-2xl border bg-background/60 p-5 text-sm">
      <div className="flex items-center justify-between gap-4">
        <span className="font-semibold">{t('desk.attempts', { used: event.attempts_used, max: event.max_attempts })}</span>
        {event.last_score !== null && <ScoreRing value={event.last_score} />}
      </div>
      {evaluating && (
        <p className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> {t('desk.evaluating')}
        </p>
      )}
      {event.last_eval_status === 'failed' && <p className="text-muted-foreground">{t('desk.evalFailed')}</p>}
      {event.last_feedback && <p className="whitespace-pre-wrap">{event.last_feedback}</p>}
      {/* mentor shu baho bo'yicha chatda izoh yozgan (CONTRACT.md §9.13) */}
      {mentor && onAskMentor && event.last_score !== null && (
        <Button variant="outline" size="sm" onClick={onAskMentor}>
          <MessageCircle className="mr-1.5 h-4 w-4" /> {t('desk.askMentor', { name: mentor.name })}
        </Button>
      )}
    </div>
  )
}

function AnswerForm({ run, event, onRun }: { run: RunDetail; event: RunEvent; onRun: (r: RunDetail) => void }) {
  const { t } = useTranslation()
  const types: AnswerType[] = event.type === 'day_end' ? ['text'] : event.answer_types
  const [text, setText] = useState('')
  const [code, setCode] = useState('')
  const [link, setLink] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [expanded, setExpanded] = useState(event.attempts_used === 0)
  const empty = !text.trim() && !code.trim() && !link.trim() && !file

  if (!expanded) {
    return (
      <div className="border-t pt-4">
        <Button variant="outline" onClick={() => setExpanded(true)}>
          {t('desk.resubmit')} ({event.max_attempts - event.attempts_used})
        </Button>
      </div>
    )
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const fileId = file ? (await uploadFile(file, run.id)).id : undefined
      const res = await api<SubmissionResult>(`/runs/${run.id}/events/${event.node_id}/submit`, {
        method: 'POST',
        json: {
          text: text.trim() || undefined,
          code: code.trim() || undefined,
          link_url: link.trim() || undefined,
          file_id: fileId,
        },
      })
      onRun(res.run)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4 border-t pt-4">
      <h3 className="font-semibold">{event.attempts_used ? t('desk.resubmit') : t('desk.yourAnswer')}</h3>
      {types.includes('text') && (
        <div className="space-y-1">
          <Label htmlFor="answer-text">{t('desk.answer.text')}</Label>
          <Textarea id="answer-text" rows={6} value={text} onChange={(e) => setText(e.target.value)} maxLength={10000} />
        </div>
      )}
      {types.includes('code') && (
        <div className="space-y-1">
          <Label htmlFor="answer-code">{t('desk.answer.code')}</Label>
          <Textarea id="answer-code" rows={10} className="font-mono text-xs" spellCheck={false} value={code}
            onChange={(e) => setCode(e.target.value)} maxLength={10000} />
        </div>
      )}
      {types.includes('link') && (
        <div className="space-y-1">
          <Label htmlFor="answer-link">{t('desk.answer.link')}</Label>
          <Input id="answer-link" type="url" placeholder="https://" value={link} onChange={(e) => setLink(e.target.value)} />
        </div>
      )}
      {types.includes('file') && (
        <div className="space-y-1">
          <Label htmlFor="answer-file" className="flex items-center gap-1">
            <Paperclip className="h-3 w-3" /> {t('desk.answer.file')}
          </Label>
          <Input id="answer-file" type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        </div>
      )}
      {error && <p className="text-sm text-destructive">{error}</p>}
      <Button type="submit" disabled={busy || empty}>
        {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {t('desk.submit')}
      </Button>
    </form>
  )
}

function Hints({ runId, nodeId }: { runId: string; nodeId: string }) {
  const { t } = useTranslation()
  const [hints, setHints] = useState<string[]>([])
  const [info, setInfo] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    setHints([])
    setInfo(null)
  }, [nodeId])

  const ask = async () => {
    if (!window.confirm(t('desk.hintConfirm'))) return
    setBusy(true)
    try {
      const res = await api<HintResult>(`/runs/${runId}/events/${nodeId}/hint`, { method: 'POST' })
      setHints((h) => [...h, res.hint])
      setInfo(t('desk.hintLeft', { count: res.hints_left }))
    } catch (err) {
      setInfo(err instanceof ApiError ? err.message : t('common.error'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-2 border-t pt-4">
      {hints.map((h, i) => (
        <p key={i} className="animate-rise rounded-xl border border-amber-300/50 bg-amber-50/80 p-3 text-sm text-amber-900 dark:border-violet-400/25 dark:bg-violet-400/10 dark:text-violet-100">
          💡 {h}
        </p>
      ))}
      <div className="flex items-center gap-3">
        <Button variant="outline" size="sm" onClick={ask} disabled={busy}>
          <Lightbulb className="mr-1 h-4 w-4" /> {t('desk.hint')}
        </Button>
        {info && <span className="text-xs text-muted-foreground">{info}</span>}
      </div>
    </div>
  )
}
