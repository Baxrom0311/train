// /vacancies/:id (CONTRACT.md §23.8): talaba vakansiyani ko'radi — talablar va o'z ballari,
// mashq qilish uchun ssenariylar, ariza berish yoki qaytarib olish, sinov suhbati (§24.7),
// kompaniya chaqirgan suhbat vaqtini tanlash (§25.6).
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, CalendarDays, CheckCircle2, Loader2, Play, Send, Undo2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ScoreRing } from '@/components/score'
import { PrepareCard } from '@/components/interviews/parts'
import { StudentMeetingCard } from '@/components/vacancies/meetings'
import { ApplicationBadge, FitBadge, VacancyMeta } from '@/components/vacancies/parts'
import { useAuth } from '@/context/AuthContext'
import { api, ApiError } from '@/lib/api'
import type { PracticeScenario, RunCreated, VacancyDetail } from '@/lib/types'
import { cn } from '@/lib/utils'

export default function VacancyPage() {
  const { id = '' } = useParams()
  const { t } = useTranslation()
  const { can } = useAuth()
  const [v, setV] = useState<VacancyDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    api<VacancyDetail>(`/vacancies/${id}`)
      .then(setV)
      .catch((err) => setError(err instanceof ApiError && err.status === 404 ? t('vacancy.notFound') : t('common.error')))
  }, [id, t])
  useEffect(load, [load])

  if (!v) {
    return <div className="grid place-items-center py-24">{error ? <p className="text-destructive">{error}</p> : <Loader2 className="h-6 w-6 animate-spin text-primary" />}</div>
  }

  const requirements = Object.entries(v.requirements)
  const gaps = new Set<string>(v.my_fit?.gaps.map((g) => g.competency) ?? [])

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-8">
      <div className="flex items-start gap-3 animate-rise">
        <Button variant="ghost" size="icon" asChild aria-label={t('common.back')}>
          <Link to="/vacancies"><ArrowLeft className="h-4 w-4" /></Link>
        </Button>
        <div className="min-w-0 flex-1 space-y-2">
          <h1 className="text-3xl font-extrabold tracking-tight">{v.title}</h1>
          <VacancyMeta vacancy={v} company={v.company.name} />
          <p className="text-xs text-muted-foreground">{v.company.industry} · {t(`catalog.sector.${v.sector}`)}</p>
        </div>
      </div>

      {/* telefonda: tavsif → talablar → ariza → mashq; kompyuterda ariza o'ng ustunda */}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="min-w-0 space-y-6 lg:col-start-1">
          <section className="glass-strong rounded-3xl p-5 sm:p-6">
            <p className="whitespace-pre-line leading-relaxed">{v.description}</p>
          </section>

          <section className="glass space-y-4 rounded-3xl p-5 sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="font-bold">{t('vacancy.requirements')}</h2>
              {v.my_fit && <FitBadge fit={v.my_fit} />}
            </div>
            {requirements.length === 0 && <p className="text-sm text-muted-foreground">{t('vacancy.noRequirements')}</p>}
            <ul className="space-y-3">
              {requirements.map(([k, required]) => {
                const mine = v.my_competencies[k]
                return (
                  <li key={k} className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span className="flex items-center gap-1.5">
                        {!gaps.has(k) && v.my_fit && <CheckCircle2 className="h-3.5 w-3.5 text-success" />}
                        {t(`competency.${k}`)}
                      </span>
                      <span className="tabular-nums">
                        <span className={cn('font-bold', gaps.has(k) ? 'text-amber-600 dark:text-amber-300' : 'text-foreground')}>
                          {mine === undefined ? '—' : Math.round(mine)}
                        </span>
                        <span className="text-muted-foreground"> / {required}</span>
                      </span>
                    </div>
                    {/* chiziq — o'z balli, belgi — talab */}
                    <div className="relative h-2.5 rounded-full bg-muted">
                      <div className={cn('h-full rounded-full', gaps.has(k) ? 'bg-amber-500' : 'bg-brand')} style={{ width: `${Math.min(100, mine ?? 0)}%` }} />
                      <span className="absolute -top-1 h-4.5 w-0.5 rounded bg-foreground/70" style={{ left: `${required}%` }} aria-hidden />
                    </div>
                  </li>
                )
              })}
            </ul>
            {v.min_score !== null && (
              <p className="flex justify-between border-t pt-3 text-sm">
                <span>{t('vacancy.minScore')}</span>
                <span className="tabular-nums"><b>{v.my_overall === null ? '—' : Math.round(v.my_overall)}</b> <span className="text-muted-foreground">/ {v.min_score}</span></span>
              </p>
            )}
          </section>
        </div>

        <aside className="h-fit space-y-4 lg:sticky lg:top-24 lg:col-start-2 lg:row-span-2 lg:row-start-1">
          {v.application_status !== 'withdrawn' && v.interviews.length > 0 && (
            <StudentMeetingCard vacancyId={v.id} vacancyTitle={v.title} company={v.company.name} interviews={v.interviews} onChange={load} />
          )}
          <ApplyCard v={v} onChange={load} />
          {can('practice_interviews') && <PrepareCard vacancyId={v.id} />}
        </aside>

        {v.practice.length > 0 && <div className="min-w-0 lg:col-start-1"><Practice items={v.practice} /></div>}
      </div>
    </div>
  )
}

function ApplyCard({ v, onChange }: { v: VacancyDetail; onChange: () => void }) {
  const { t } = useTranslation()
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const act = async (path: 'apply' | 'withdraw') => {
    setBusy(true)
    setError(null)
    try {
      await api(`/vacancies/${v.id}/${path}`, { method: 'POST', ...(path === 'apply' ? { json: { note: note || null } } : {}) })
      onChange()
    } catch (err) {
      setError(err instanceof ApiError && err.status === 422 ? t('vacancy.student.noProfile') : err instanceof ApiError ? err.message : t('common.error'))
    } finally {
      setBusy(false)
    }
  }

  const status = v.application_status
  const canApply = v.status === 'open' && (status === null || status === 'withdrawn')

  return (
    <section className="glass space-y-4 rounded-3xl p-5">
      <div className="flex items-center gap-4">
        {v.my_fit ? <ScoreRing value={v.my_fit.fit} size={64} /> : null}
        <div className="min-w-0">
          <p className="font-bold">{v.my_fit ? t(v.my_fit.meets ? 'vacancy.fit.meets' : 'vacancy.fit.partial') : t('vacancy.student.noFit')}</p>
          <p className="text-xs text-muted-foreground">{t('vacancy.student.fitHint')}</p>
        </div>
      </div>

      {status && status !== 'withdrawn' && (
        <div className="flex items-center justify-between gap-2 rounded-2xl border bg-background/40 px-3 py-2.5 text-sm">
          {t('vacancy.student.yourApplication')} <ApplicationBadge status={status} />
        </div>
      )}
      {status === 'offered' && (
        <Link to="/offers" className="block text-sm font-semibold text-primary hover:underline">{t('vacancy.student.seeOffer')}</Link>
      )}
      {v.status !== 'open' && <p className="text-sm text-muted-foreground">{t('vacancy.student.closed')}</p>}

      {canApply && (
        <div className="space-y-2">
          <Textarea rows={3} maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)}
            placeholder={t('vacancy.student.notePlaceholder')} aria-label={t('vacancy.student.note')} />
          <Button className="w-full" disabled={busy || !v.my_fit} onClick={() => act('apply')}>
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />} {t('vacancy.student.apply')}
          </Button>
          <p className="text-xs text-muted-foreground">{v.my_fit ? t('vacancy.student.consent') : t('vacancy.student.noProfile')}</p>
        </div>
      )}
      {(status === 'applied' || status === 'interviewing') && (
        <Button variant="ghost" className="w-full" disabled={busy}
          onClick={() => (status === 'applied' || window.confirm(t('meeting.student.withdrawConfirm'))) && act('withdraw')}>
          <Undo2 className="h-4 w-4" /> {t('vacancy.student.withdraw')}
        </Button>
      )}
      {error && <p className="text-sm text-destructive">{error}</p>}
    </section>
  )
}

function Practice({ items }: { items: PracticeScenario[] }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [starting, setStarting] = useState<string | null>(null)
  const [error, setError] = useState('')

  const start = async (id: string) => {
    setStarting(id)
    setError('')
    try {
      const created = await api<RunCreated>('/runs', { method: 'POST', json: { scenario_id: id } })
      navigate(`/runs/${created.run.id}`, { state: { warning: created.warning } })
    } catch (err) {
      setError(err instanceof ApiError && err.status === 409 ? t('catalog.alreadyOpen') : t('common.error'))
      setStarting(null)
    }
  }

  return (
    <section className="glass space-y-3 rounded-3xl p-5 sm:p-6">
      <div>
        <h2 className="font-bold">{t('vacancy.student.practice')}</h2>
        <p className="text-xs text-muted-foreground">{t('vacancy.student.practiceHint')}</p>
      </div>
      <ul className="space-y-2">
        {items.map((p) => (
          <li key={p.scenario_id} className="flex flex-wrap items-center gap-3 rounded-2xl border bg-background/40 p-3">
            <div className="min-w-0 flex-1">
              <p className="font-semibold">{p.title}</p>
              <p className="flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
                {p.company_name} · <CalendarDays className="h-3 w-3" /> {t('catalog.days', { count: p.duration_days })}
              </p>
              {Object.keys(p.practices).length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {Object.entries(p.practices).map(([k, n]) => (
                    <span key={k} className="rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary">{t(`competency.${k}`)} ×{n}</span>
                  ))}
                </div>
              )}
            </div>
            {p.completed ? (
              <span className="flex items-center gap-1 text-xs font-semibold text-success"><CheckCircle2 className="h-4 w-4" /> {t('vacancy.student.done')}</span>
            ) : (
              <Button size="sm" variant="outline" disabled={starting !== null} onClick={() => start(p.scenario_id)}>
                {starting === p.scenario_id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />} {t('vacancy.student.start')}
              </Button>
            )}
          </li>
        ))}
      </ul>
      {error && <p className="text-sm text-destructive">{error}</p>}
    </section>
  )
}
