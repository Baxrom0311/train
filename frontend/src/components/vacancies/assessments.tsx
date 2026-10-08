// Sinov topshirig'i (CONTRACT.md §26.2): kompaniya arizachiga o'z ssenariysini yuboradi,
// talaba uni oddiy Run sifatida o'tadi, natija faqat shu kompaniyaga ko'rinadi.
import { useEffect, useState } from 'react'
import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { Clock, FileText, FlaskConical, Loader2, Play, Plus, Send, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Segmented } from '@/components/ui/segmented'
import { Textarea } from '@/components/ui/textarea'
import { CompetencyBars, ScoreRing } from '@/components/score'
import { SELECT } from '@/components/editor/fields'
import type { ScenarioAdmin } from '@/components/editor/model'
import { api, ApiError } from '@/lib/api'
import type { Assessment, AssessmentState, MyAssessment } from '@/lib/types'
import { cn } from '@/lib/utils'
import { useWhen } from './meetings'

const DAYS = [1, 3, 5, 7, 14]
const DEFAULT_DAYS = 5

/** Kompaniya yangisini yuborolmaydigan holatlar — backend `unfinished` bilan bir xil. */
const UNFINISHED: AssessmentState[] = ['assigned', 'overdue', 'in_progress', 'evaluating']
export const hasUnfinished = (items: MyAssessment[]) => items.some((a) => UNFINISHED.includes(a.state))

const TONE: Record<AssessmentState, string> = {
  assigned: 'bg-amber-500/15 text-amber-700 dark:text-amber-300',
  overdue: 'bg-muted text-muted-foreground',
  in_progress: 'bg-primary/12 text-primary',
  evaluating: 'bg-primary/12 text-primary',
  completed: 'bg-success/15 text-success',
  incomplete: 'bg-destructive/12 text-destructive',
  abandoned: 'bg-muted text-muted-foreground',
  cancelled: 'bg-muted text-muted-foreground',
}

export function AssessmentBadge({ state }: { state: AssessmentState }) {
  const { t } = useTranslation()
  return <span className={cn('inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold', TONE[state])}>{t(`assessment.state.${state}`)}</span>
}

/** 409 — holat boshqa oynada o'zgargan (boshlangan, bekor qilingan, muddat o'tgan). */
function errorText(err: unknown, t: TFunction): string {
  if (err instanceof ApiError && err.status === 409) return t('assessment.errors.conflict')
  if (err instanceof ApiError && err.status === 404) return t('assessment.errors.gone')
  return t('common.error')
}

function Header({ a }: { a: MyAssessment }) {
  const { t } = useTranslation()
  return (
    <div className="flex flex-wrap items-center gap-2">
      <FlaskConical className="h-4 w-4 text-primary" />
      <span className="min-w-0 text-sm font-semibold">{a.scenario_title}</span>
      <AssessmentBadge state={a.state} />
      <span className="ml-auto text-xs text-muted-foreground">{t('catalog.days', { count: a.duration_days })}</span>
    </div>
  )
}

// ── Kompaniya: yuborish formasi ─────────────────────────────────────

export function AssignForm({ vacancyId, applicationId, onDone }: {
  vacancyId: string
  applicationId: string
  onDone: () => void
}) {
  const { t } = useTranslation()
  const [scenarios, setScenarios] = useState<ScenarioAdmin[] | null>(null)
  const [scenarioId, setScenarioId] = useState('')
  const [days, setDays] = useState(DEFAULT_DAYS)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api<ScenarioAdmin[]>('/company/scenarios')
      .then((list) => {
        // faqat faol va nashr qilingan versiyasi bor ssenariy yuboriladi (§26.2)
        const ready = list.filter((s) => s.is_active && s.versions.some((v) => v.status === 'published'))
        setScenarios(ready)
        setScenarioId((cur) => cur || ready[0]?.id || '')
      })
      .catch(() => { setScenarios([]); setError(t('common.error')) })
  }, [t])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!scenarioId) return
    setBusy(true)
    setError(null)
    try {
      await api(`/company/vacancies/${vacancyId}/applications/${applicationId}/assessments`, {
        method: 'POST', json: { scenario_id: scenarioId, start_within_days: days, note: note.trim() || null },
      })
      onDone()
    } catch (err) {
      setError(errorText(err, t))
      setBusy(false)
    }
  }

  if (scenarios === null) return <Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />
  if (scenarios.length === 0) {
    return (
      <div className="space-y-3 text-center">
        <p className="text-sm text-muted-foreground">{error ?? t('assessment.form.noScenarios')}</p>
        <Button asChild variant="outline">
          <Link to="/company/scenarios/new"><Plus className="h-4 w-4" /> {t('assessment.form.create')}</Link>
        </Button>
      </div>
    )
  }

  const picked = scenarios.find((s) => s.id === scenarioId)
  return (
    <form onSubmit={submit} className="space-y-4">
      <label className="block space-y-1.5">
        <span className="text-sm font-semibold">{t('assessment.form.scenario')}</span>
        <select value={scenarioId} onChange={(e) => setScenarioId(e.target.value)} className={SELECT}>
          {scenarios.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
        </select>
        {picked && (
          <span className="block text-xs text-muted-foreground">
            {t(`catalog.sector.${picked.sector}`)} · {t('catalog.days', { count: picked.duration_days })}
          </span>
        )}
      </label>
      <div className="space-y-1.5">
        <p className="text-sm font-semibold">{t('assessment.form.startWithin')}</p>
        <Segmented<number> label={t('assessment.form.startWithin')} value={days} onChange={setDays}
          options={DAYS.map((d) => ({ value: d, label: t('assessment.form.days', { count: d }) }))} />
      </div>
      <label className="block space-y-1.5">
        <span className="text-sm font-semibold">{t('assessment.form.note')}</span>
        <Textarea rows={3} maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)}
          placeholder={t('assessment.form.notePlaceholder')} />
      </label>
      <p className="text-xs text-muted-foreground">{t('assessment.form.privacy')}</p>
      {error && <p className="text-sm text-destructive">{error}</p>}
      <Button type="submit" className="w-full" disabled={busy || !scenarioId}>
        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />} {t('assessment.form.send')}
      </Button>
    </form>
  )
}

// ── Kompaniya: ariza ostidagi sinov holati va natijasi ──────────────

export function CompanyAssessmentPanel({ vacancyId, applicationId, assessments, candidateName, onChange }: {
  vacancyId: string
  applicationId: string
  assessments: Assessment[]
  candidateName: string
  onChange: () => void
}) {
  const { t } = useTranslation()
  const when = useWhen()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const latest = assessments[0]
  if (!latest) return null
  const earlier = assessments.slice(1).filter((a) => a.state !== 'cancelled')
  const r = latest.result

  const cancel = async () => {
    if (!window.confirm(t('assessment.company.cancelConfirm', { name: candidateName }))) return
    setBusy(true)
    setError(null)
    try {
      await api(`/company/vacancies/${vacancyId}/applications/${applicationId}/assessments/${latest.id}/cancel`, { method: 'POST' })
      onChange()
    } catch (err) {
      setError(errorText(err, t))
      if (err instanceof ApiError && err.status === 409) onChange()   // eskirgan holatni yangilaymiz
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-2.5 rounded-2xl border border-primary/20 bg-primary/5 p-3">
      <Header a={latest} />
      {latest.state === 'assigned' && <p className="text-xs text-muted-foreground">{t('assessment.company.waiting', { when: when(latest.start_by) })}</p>}
      {latest.state === 'overdue' && <p className="text-xs text-muted-foreground">{t('assessment.company.overdue', { when: when(latest.start_by) })}</p>}
      {latest.state === 'in_progress' && latest.started_at && (
        <p className="flex items-center gap-1.5 text-xs text-muted-foreground"><Clock className="h-3.5 w-3.5" /> {t('assessment.company.started', { when: when(latest.started_at) })}</p>
      )}
      {latest.state === 'evaluating' && <p className="text-xs text-muted-foreground">{t('assessment.company.evaluating')}</p>}
      {latest.state === 'abandoned' && <p className="text-xs text-muted-foreground">{t('assessment.company.abandoned')}</p>}
      {latest.note && latest.status === 'assigned' && <p className="text-sm italic text-muted-foreground">“{latest.note}”</p>}

      {r && (
        <div className="grid gap-3 border-t border-primary/15 pt-2.5 sm:grid-cols-[minmax(0,1fr)_12rem]">
          <div className="min-w-0 space-y-2">
            <div className="flex items-center gap-3">
              {r.overall_score !== null && <ScoreRing value={Math.round(r.overall_score)} size={44} />}
              <div className="text-xs text-muted-foreground">
                <p className="font-semibold text-foreground">{t('assessment.company.result')}</p>
                <p>{t('report.onTime')}: {r.on_time_rate === null ? '—' : `${Math.round(r.on_time_rate)}%`}</p>
              </div>
            </div>
            {r.summary && <p className="text-sm leading-relaxed">{r.summary}</p>}
            {r.strengths.length > 0 && <Points title={t('assessment.company.strengths')} items={r.strengths} />}
            {r.improvements.length > 0 && <Points title={t('assessment.company.improvements')} items={r.improvements} />}
          </div>
          {Object.keys(r.competency_scores).length > 0 && <CompetencyBars scores={r.competency_scores} compact />}
        </div>
      )}

      {latest.status === 'assigned' && (
        <Button size="sm" variant="ghost" disabled={busy} onClick={cancel}>
          <X className="h-4 w-4" /> {t('assessment.company.cancel')}
        </Button>
      )}
      {earlier.length > 0 && (
        <p className="text-xs text-muted-foreground">
          {earlier.map((a) => `${a.scenario_title}: ${a.result?.overall_score != null ? Math.round(a.result.overall_score) : t(`assessment.state.${a.state}`)}`).join(' · ')}
        </p>
      )}
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  )
}

function Points({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="text-sm">
      <p className="text-xs font-semibold text-muted-foreground">{title}</p>
      <ul className="list-disc space-y-0.5 pl-5">{items.map((x, i) => <li key={i}>{x}</li>)}</ul>
    </div>
  )
}

// ── Talaba: vakansiya sahifasidagi sinov kartasi ────────────────────

export function StudentAssessmentCard({ vacancyId, company, assessments, onChange }: {
  vacancyId: string
  company: string
  assessments: MyAssessment[]
  onChange: () => void
}) {
  const { t } = useTranslation()
  const when = useWhen()
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const latest = assessments[0]
  if (!latest) return null

  const start = async () => {
    if (!window.confirm(t('assessment.student.startConfirm', { count: latest.duration_days }))) return
    setBusy(true)
    setError(null)
    try {
      const r = await api<{ run_id: string; warning: string | null }>(`/vacancies/${vacancyId}/assessments/${latest.id}/start`, { method: 'POST' })
      navigate(`/runs/${r.run_id}`, { state: { warning: r.warning } })
    } catch (err) {
      setError(errorText(err, t))
      setBusy(false)
      if (err instanceof ApiError && (err.status === 409 || err.status === 404)) onChange()
    }
  }

  const waiting = latest.state === 'assigned'
  return (
    <section className={cn('glass space-y-3 rounded-3xl p-5', waiting && 'border-amber-400/40')}>
      <div className="space-y-1">
        <h2 className="font-bold">{t('assessment.student.title')}</h2>
        <p className="text-xs text-muted-foreground">{t('assessment.student.privacy', { company })}</p>
      </div>
      <Header a={latest} />
      {latest.note && waiting && <p className="rounded-xl bg-muted/50 px-3 py-2 text-sm italic">“{latest.note}”</p>}

      {waiting && (
        <>
          <p className="flex items-center gap-1.5 text-sm font-semibold"><Clock className="h-4 w-4 text-primary" /> {t('assessment.student.startBy', { when: when(latest.start_by) })}</p>
          <p className="text-xs text-muted-foreground">{t('assessment.student.howItWorks')}</p>
          <Button className="w-full" disabled={busy} onClick={start}>
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />} {t('assessment.student.start')}
          </Button>
        </>
      )}
      {latest.state === 'overdue' && <p className="text-sm text-muted-foreground">{t('assessment.student.overdue')}</p>}
      {latest.state === 'cancelled' && <p className="text-sm text-muted-foreground">{t('assessment.student.cancelled')}</p>}
      {latest.state === 'abandoned' && <p className="text-sm text-muted-foreground">{t('assessment.student.abandoned')}</p>}
      {latest.run_id && (latest.state === 'in_progress' || latest.state === 'evaluating') && (
        <Button asChild className="w-full" variant={latest.state === 'in_progress' ? 'default' : 'outline'}>
          <Link to={`/runs/${latest.run_id}`}><Play className="h-4 w-4" /> {t('assessment.student.continue')}</Link>
        </Button>
      )}
      {latest.state === 'evaluating' && <p className="text-xs text-muted-foreground">{t('assessment.student.evaluating')}</p>}
      {latest.run_id && (latest.state === 'completed' || latest.state === 'incomplete') && (
        <>
          <p className="text-sm text-muted-foreground">{t('assessment.student.done', { company })}</p>
          <Button asChild className="w-full" variant="outline">
            <Link to={`/runs/${latest.run_id}/report`}><FileText className="h-4 w-4" /> {t('assessment.student.report')}</Link>
          </Button>
        </>
      )}
      {error && <p className="text-sm text-destructive">{error}</p>}
    </section>
  )
}
