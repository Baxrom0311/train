// /interviews/:id (CONTRACT.md §24.7): AI suhbatdosh bilan sinov suhbati — chat,
// baholanish kutilishi va natija (umumiy ball, kompetensiyalar, har savol bo'yicha izoh).
import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft, CheckCircle2, ChevronDown, Lightbulb, ListChecks, Loader2, MessageSquareText, MessagesSquare, RotateCcw, Send,
  Sparkles, Target, TrendingUp, UserRound, X,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { CompetencyBars, ScoreRing } from '@/components/score'
import { InterviewStatusBadge, useStartInterview } from '@/components/interviews/parts'
import { api, ApiError } from '@/lib/api'
import { formatTime } from '@/lib/time'
import type { InterviewAnswerFeedback, InterviewDetail, InterviewMessage } from '@/lib/types'
import { cn } from '@/lib/utils'

const MIN_ANSWER = 10
const MAX_ANSWER = 3000
const POLL_MS = 3000

export default function InterviewPage() {
  const { id = '' } = useParams()
  const { t } = useTranslation()
  const [iv, setIv] = useState<InterviewDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    api<InterviewDetail>(`/interviews/${id}`)
      .then((d) => { setIv(d); setError(null) })
      .catch((err) => setError(err instanceof ApiError && err.status === 404 ? t('interview.notFound') : t('common.error')))
  }, [id, t])
  useEffect(load, [load])

  // baholanayotganda natijani kutamiz
  useEffect(() => {
    if (iv?.status !== 'evaluating') return
    const timer = window.setInterval(load, POLL_MS)
    return () => window.clearInterval(timer)
  }, [iv?.status, load])

  if (!iv) {
    return <div className="grid place-items-center py-24">{error ? <p className="text-destructive">{error}</p> : <Loader2 className="h-6 w-6 animate-spin text-primary" />}</div>
  }

  const back = iv.vacancy_id ? `/vacancies/${iv.vacancy_id}` : '/interviews'

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-8">
      <div className="flex items-start gap-3 animate-rise">
        <Button variant="ghost" size="icon" asChild aria-label={t('common.back')}>
          <Link to={back}><ArrowLeft className="h-4 w-4" /></Link>
        </Button>
        <div className="min-w-0 flex-1 space-y-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-primary">{t('interview.kicker')}</p>
          <h1 className="text-2xl font-extrabold tracking-tight sm:text-3xl">{iv.position}</h1>
          <p className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            {iv.company_name} · {t(`catalog.sector.${iv.sector}`)} <InterviewStatusBadge status={iv.status} />
          </p>
        </div>
      </div>

      {iv.status === 'completed' && iv.feedback ? (
        <Result iv={iv} />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]">
          <Conversation iv={iv} onChange={setIv} />
          <aside className="h-fit space-y-4 lg:sticky lg:top-24">
            <Progress iv={iv} />
            {iv.status === 'active' && <Tips />}
          </aside>
        </div>
      )}
    </div>
  )
}

// ── Suhbat ───────────────────────────────────────────────────────────

function Conversation({ iv, onChange }: { iv: InterviewDetail; onChange: (d: InterviewDetail) => void }) {
  const { t } = useTranslation()
  const [draft, setDraft] = useState('')
  const [pending, setPending] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const bottom = useRef<HTMLDivElement>(null)
  const scrolled = useRef(false)

  // ochilganda — darhol oxiriga, keyingi xabarlarda — silliq
  useEffect(() => {
    bottom.current?.scrollIntoView({ block: 'end', behavior: scrolled.current ? 'smooth' : 'auto' })
    scrolled.current = true
  }, [iv.messages.length, pending])

  const text = draft.trim()
  const canSend = iv.status === 'active' && !busy && text.length >= MIN_ANSWER

  const send = async () => {
    if (!canSend) return
    setBusy(true)
    setPending(text)
    setError(null)
    try {
      onChange(await api<InterviewDetail>(`/interviews/${iv.id}/answer`, { method: 'POST', json: { text } }))
      setDraft('')
    } catch (err) {
      setError(err instanceof ApiError && err.status === 429 ? t('desk.chat.tooFast') : t('common.error'))
    } finally {
      setPending(null)
      setBusy(false)
    }
  }

  const act = async (path: 'abandon' | 'retry') => {
    if (path === 'abandon' && !window.confirm(t('interview.abandonConfirm'))) return
    setBusy(true)
    setError(null)
    try {
      onChange(await api<InterviewDetail>(`/interviews/${iv.id}/${path}`, { method: 'POST' }))
    } catch {
      setError(t('common.error'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="min-w-0 space-y-4">
      <div className="glass-strong space-y-4 rounded-3xl p-4 sm:p-6">
        {iv.messages.map((m) => <Bubble key={m.id} m={m} total={iv.total_questions} />)}
        {pending && (
          <>
            <Bubble m={{ id: 'pending', seq: -1, role: 'candidate', kind: 'answer', question_index: iv.current, body: pending, created_at: new Date().toISOString() }} total={iv.total_questions} faded />
            <p className="flex items-center gap-2 pl-11 text-xs text-muted-foreground">
              <span className="flex gap-1" aria-hidden>
                {[0, 1, 2].map((i) => <span key={i} className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary/70" style={{ animationDelay: `${i * 120}ms` }} />)}
              </span>
              {t('interview.reading')}
            </p>
          </>
        )}
        {/* yopishqoq javob maydoni oxirgi xabarni yopmasin */}
        <div ref={bottom} className={cn(iv.status === 'active' && 'scroll-mb-56')} />
      </div>

      {iv.status === 'active' && (
        <div className="glass sticky bottom-3 z-10 space-y-2 rounded-3xl p-3 shadow-lg sm:p-4">
          <Textarea
            rows={4}
            className="resize-y bg-background/70"
            placeholder={t('interview.placeholder')}
            aria-label={t('interview.answerLabel')}
            value={draft}
            maxLength={MAX_ANSWER}
            disabled={busy}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault()
                send()
              }
            }}
          />
          <div className="flex flex-wrap items-center gap-2">
            <span className={cn('text-xs tabular-nums', text.length > 0 && text.length < MIN_ANSWER ? 'text-amber-600 dark:text-amber-300' : 'text-muted-foreground')}>
              {text.length < MIN_ANSWER ? t('interview.minLength', { count: MIN_ANSWER }) : `${draft.length}/${MAX_ANSWER}`}
            </span>
            <span className="hidden text-xs text-muted-foreground sm:inline">· {t('interview.shortcut')}</span>
            <div className="ml-auto flex gap-2">
              <Button variant="ghost" size="sm" disabled={busy} onClick={() => act('abandon')}>
                <X className="h-4 w-4" /> {t('interview.abandon')}
              </Button>
              <Button size="sm" disabled={!canSend} onClick={send}>
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />} {t('interview.send')}
              </Button>
            </div>
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>
      )}

      {iv.status === 'evaluating' && (
        <div className="glass flex items-center gap-4 rounded-3xl p-5 animate-rise">
          <Loader2 className="h-8 w-8 shrink-0 animate-spin text-primary" />
          <div>
            <p className="font-bold">{t('interview.evaluating')}</p>
            <p className="text-sm text-muted-foreground">{t('interview.evaluatingHint')}</p>
          </div>
        </div>
      )}
      {iv.status === 'failed' && (
        <div className="glass space-y-3 rounded-3xl p-5">
          <p className="font-bold">{t('interview.failed')}</p>
          <p className="text-sm text-muted-foreground">{t('interview.failedHint')}</p>
          <Button disabled={busy} onClick={() => act('retry')}><RotateCcw className="h-4 w-4" /> {t('interview.retry')}</Button>
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>
      )}
      {iv.status === 'abandoned' && (
        <div className="glass flex flex-wrap items-center gap-3 rounded-3xl p-5">
          <p className="flex-1 text-sm text-muted-foreground">{t('interview.abandoned')}</p>
          {iv.vacancy_id && <AgainButton vacancyId={iv.vacancy_id} />}
        </div>
      )}
    </section>
  )
}

function Bubble({ m, total, faded }: { m: InterviewMessage; total: number; faded?: boolean }) {
  const { t } = useTranslation()
  const mine = m.role === 'candidate'
  const label = m.kind === 'question'
    ? t('interview.questionOf', { n: m.question_index + 1, total })
    : m.kind === 'follow_up' ? t('interview.followUp') : null
  return (
    <div className={cn('flex gap-3 animate-rise', mine && 'flex-row-reverse', faded && 'opacity-70')}>
      {!mine && (
        <span className="bg-brand grid h-8 w-8 shrink-0 place-items-center rounded-full text-primary-foreground shadow-sm" aria-hidden>
          <UserRound className="h-4 w-4" />
        </span>
      )}
      <div className={cn('flex min-w-0 max-w-[88%] flex-col', mine ? 'items-end' : 'items-start')}>
        {label && <span className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-primary">{label}</span>}
        <div className={cn(
          'whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm',
          mine ? 'bg-brand rounded-br-md text-primary-foreground' : 'rounded-bl-md border bg-background/85',
          m.kind === 'follow_up' && 'ring-1 ring-primary/30',
        )}>
          {m.body}
        </div>
        <span className="mt-0.5 text-[10px] text-muted-foreground">{formatTime(m.created_at)}</span>
      </div>
    </div>
  )
}

function Progress({ iv }: { iv: InterviewDetail }) {
  const { t } = useTranslation()
  const done = iv.status === 'active' ? iv.current : iv.total_questions
  return (
    <section className="glass space-y-4 rounded-3xl p-5">
      <div className="flex items-baseline justify-between">
        <h2 className="font-bold">{t('interview.progress')}</h2>
        <span className="text-sm tabular-nums text-muted-foreground">{Math.min(done + (iv.status === 'active' ? 1 : 0), iv.total_questions)} / {iv.total_questions}</span>
      </div>
      <ol className="flex gap-1.5" aria-hidden>
        {Array.from({ length: iv.total_questions }, (_, i) => (
          <li key={i} className={cn('h-2 flex-1 rounded-full', i < done ? 'bg-brand' : i === done && iv.status === 'active' ? 'bg-primary/40' : 'bg-muted')} />
        ))}
      </ol>
      <div className="space-y-2">
        <p className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground"><Target className="h-3.5 w-3.5" /> {t('interview.focus')}</p>
        <div className="flex flex-wrap gap-1.5">
          {iv.focus.map((c) => (
            <span key={c} className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary">{t(`competency.${c}`)}</span>
          ))}
        </div>
      </div>
    </section>
  )
}

function Tips() {
  const { t } = useTranslation()
  const steps = ['situation', 'task', 'action', 'result'] as const
  return (
    <section className="glass space-y-3 rounded-3xl p-5">
      <h2 className="flex items-center gap-2 font-bold"><Lightbulb className="h-4 w-4 text-primary" /> {t('interview.tips.title')}</h2>
      <ol className="space-y-2 text-sm">
        {steps.map((s, i) => (
          <li key={s} className="flex gap-2">
            <span className="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-primary/12 text-[11px] font-bold text-primary">{i + 1}</span>
            <span><b>{t(`interview.tips.${s}`)}</b> <span className="text-muted-foreground">— {t(`interview.tips.${s}Hint`)}</span></span>
          </li>
        ))}
      </ol>
      <p className="text-xs text-muted-foreground">{t('interview.tips.private')}</p>
    </section>
  )
}

// ── Natija ───────────────────────────────────────────────────────────

function verdict(score: number) {
  return score >= 75 ? 'strong' : score >= 50 ? 'solid' : 'practice'
}

function Result({ iv }: { iv: InterviewDetail }) {
  const { t } = useTranslation()
  const fb = iv.feedback!
  const score = iv.score ?? 0
  return (
    <div className="space-y-6">
      <section className="glass-strong grid gap-6 rounded-3xl p-5 animate-rise sm:p-6 md:grid-cols-[auto_minmax(0,1fr)_16rem]">
        <div className="flex items-center gap-4 md:flex-col md:items-start">
          <ScoreRing value={score} size={96} />
          <p className="text-lg font-extrabold">{t(`interview.verdict.${verdict(score)}`)}</p>
        </div>
        <div className="space-y-2">
          <h2 className="flex items-center gap-2 font-bold"><Sparkles className="h-4 w-4 text-primary" /> {t('interview.summary')}</h2>
          <p className="leading-relaxed">{fb.summary}</p>
        </div>
        {iv.competency_scores && (
          <div className="space-y-2">
            <h2 className="text-sm font-bold">{t('interview.byCompetency')}</h2>
            <CompetencyBars scores={iv.competency_scores} compact />
          </div>
        )}
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        <ListCard Icon={CheckCircle2} tone="text-success" title={t('interview.strengths')} items={fb.strengths} />
        <ListCard Icon={TrendingUp} tone="text-primary" title={t('interview.improvements')} items={fb.improvements} />
      </div>

      <section className="space-y-3">
        <h2 className="flex items-center gap-2 text-lg font-bold"><ListChecks className="h-5 w-5 text-primary" /> {t('interview.perQuestion')}</h2>
        {fb.answers.map((a) => <AnswerReview key={a.index} a={a} iv={iv} />)}
      </section>

      <details className="glass group rounded-3xl p-5">
        <summary className="flex cursor-pointer list-none items-center gap-2 font-bold">
          <MessagesSquare className="h-4 w-4 text-primary" /> {t('interview.transcript')}
          <ChevronDown className="ml-auto h-4 w-4 transition-transform group-open:rotate-180" />
        </summary>
        <div className="mt-4 space-y-4">
          {iv.messages.map((m) => <Bubble key={m.id} m={m} total={iv.total_questions} />)}
        </div>
      </details>

      <div className="flex flex-wrap gap-2">
        {iv.vacancy_id && <AgainButton vacancyId={iv.vacancy_id} />}
        <Button variant="outline" asChild><Link to="/interviews">{t('interview.all')}</Link></Button>
      </div>
    </div>
  )
}

function ListCard({ Icon, tone, title, items }: { Icon: typeof Sparkles; tone: string; title: string; items: string[] }) {
  if (!items.length) return null
  return (
    <section className="glass space-y-3 rounded-3xl p-5">
      <h2 className="font-bold">{title}</h2>
      <ul className="space-y-2">
        {items.map((s) => (
          <li key={s} className="flex gap-2 text-sm"><Icon className={cn('mt-0.5 h-4 w-4 shrink-0', tone)} /> {s}</li>
        ))}
      </ul>
    </section>
  )
}

function AnswerReview({ a, iv }: { a: InterviewAnswerFeedback; iv: InterviewDetail }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const own = iv.messages.filter((m) => m.question_index === a.index && (m.role === 'candidate' || m.kind === 'follow_up'))
  const tone = a.score >= 75 ? 'bg-success/15 text-success' : a.score >= 50 ? 'bg-primary/12 text-primary' : 'bg-amber-500/15 text-amber-700 dark:text-amber-300'
  return (
    <article className="glass space-y-3 rounded-3xl p-5 animate-rise">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1 space-y-1">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {t('interview.questionOf', { n: a.index + 1, total: iv.total_questions })} · {t(`competency.${a.competency}`)}
          </p>
          <p className="font-semibold leading-snug">{a.question}</p>
        </div>
        <span className={cn('shrink-0 rounded-full px-2.5 py-1 text-sm font-bold tabular-nums', tone)}>{a.score}</span>
      </div>
      <button type="button" onClick={() => setOpen((o) => !o)} className="flex items-center gap-1 text-xs font-semibold text-primary hover:underline" aria-expanded={open}>
        <ChevronDown className={cn('h-3.5 w-3.5 transition-transform', open && 'rotate-180')} /> {t(open ? 'interview.hideAnswer' : 'interview.showAnswer')}
      </button>
      {open && (
        <div className="space-y-2 rounded-2xl bg-muted/50 p-3 text-sm">
          {own.map((m) => (
            <p key={m.id} className={cn('whitespace-pre-wrap', m.kind === 'follow_up' && 'italic text-muted-foreground')}>{m.body}</p>
          ))}
        </div>
      )}
      <p className="flex gap-2 text-sm"><MessageSquareText className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" /> {a.comment}</p>
      <p className="flex gap-2 rounded-2xl border border-primary/25 bg-primary/5 p-3 text-sm">
        <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-primary" /> <span><b>{t('interview.better')}</b> {a.better}</span>
      </p>
    </article>
  )
}

function AgainButton({ vacancyId }: { vacancyId: string }) {
  const { t } = useTranslation()
  const { start, starting, error } = useStartInterview()
  return (
    <span className="inline-flex flex-col gap-1">
      <Button disabled={starting} onClick={() => start(vacancyId)}>
        {starting ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />} {t('interview.again')}
      </Button>
      {error && <span className="text-xs text-destructive">{error}</span>}
    </span>
  )
}
