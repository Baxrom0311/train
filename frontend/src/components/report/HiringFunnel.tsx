// Ishga olish voronkasi: ariza → sinov → suhbat → taklif → qabul (CONTRACT.md §27.4).
import { Fragment, useEffect, useState } from 'react'
import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import {
  AlarmClock, ArrowDown, BriefcaseBusiness, ClipboardCheck, FileText, Handshake, Hourglass, Loader2, MessagesSquare, Timer,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Stat } from '@/components/ui/stat'
import { SELECT } from '@/components/editor/fields'
import { ScoreRing } from '@/components/score'
import { CsvButton, hours, pct } from '@/components/report/shared'
import { api } from '@/lib/api'
import type { HiringOutcome, HiringReport, HiringStage } from '@/lib/types'
import { cn } from '@/lib/utils'

const STAGE_ICON: Record<HiringStage, typeof FileText> = {
  applied: FileText,
  assessment: ClipboardCheck,
  interview: MessagesSquare,
  offer: Handshake,
  hired: BriefcaseBusiness,
}

// holatlar chizig'i tartibi va rangi — yakunlanganlar chetlarda, jarayondagilar o'rtada
const OUTCOMES: { key: HiringOutcome; tone: string }[] = [
  { key: 'hired', tone: 'bg-success' },
  { key: 'offer_pending', tone: 'bg-primary' },
  { key: 'in_progress', tone: 'bg-primary/55' },
  { key: 'waiting', tone: 'bg-primary/25' },
  { key: 'offer_declined', tone: 'bg-muted-foreground/45' },
  { key: 'withdrawn', tone: 'bg-muted-foreground/25' },
  { key: 'rejected', tone: 'bg-destructive/70' },
]

const query = (days: number | null, vacancy: string) => {
  const params = new URLSearchParams()
  if (days) params.set('days', String(days))
  if (vacancy) params.set('vacancy_id', vacancy)
  const q = params.toString()
  return q ? `?${q}` : ''
}

/** `days` — sahifaning umumiy davri (§20.4); vakansiya tanlovi shu bo'limniki. */
export function HiringFunnel({ days }: { days: number | null }) {
  const { t } = useTranslation()
  const [vacancy, setVacancy] = useState('')
  const [report, setReport] = useState<HiringReport | null>(null)
  const [error, setError] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    setLoading(true)
    api<HiringReport>(`/company/vacancies/report${query(days, vacancy)}`)
      .then((r) => alive && (setReport(r), setError(false)))
      .catch(() => alive && setError(true))
      .finally(() => alive && setLoading(false))
    return () => { alive = false }
  }, [days, vacancy])

  const applied = report?.stages[0].count ?? 0
  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3 animate-rise">
        <div className="space-y-1">
          <h2 className="flex items-center gap-2 text-2xl font-extrabold tracking-tight">
            {t('hiring.title')}
            {loading && report && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
          </h2>
          <p className="text-sm text-muted-foreground">{t('hiring.subtitle')}</p>
        </div>
        <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
          <select aria-label={t('hiring.vacancy')} className={cn(SELECT, 'sm:w-64')} value={vacancy}
            onChange={(e) => setVacancy(e.target.value)}>
            <option value="">{t('hiring.allVacancies')}</option>
            {report?.vacancies.map((v) => (
              <option key={v.id} value={v.id}>{v.title}{v.status === 'closed' ? ` · ${t('vacancy.status.closed')}` : ''}</option>
            ))}
          </select>
          <CsvButton path={`/company/vacancies/report/applications.csv${query(days, vacancy)}`} name="tryjob-applications.csv"
            label={t('hiring.csv')} />
        </div>
      </div>

      {error && <p className="glass rounded-2xl px-4 py-3 text-sm text-destructive">{t('common.error')}</p>}
      {!report ? (
        !error && <Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />
      ) : applied === 0 ? (
        <div className="glass flex flex-col items-center gap-3 rounded-2xl px-6 py-12 text-center animate-rise">
          <BriefcaseBusiness className="h-8 w-8 text-muted-foreground" />
          <p className="max-w-md text-sm text-muted-foreground">{t('hiring.empty')}</p>
          <Button asChild variant="outline" size="sm"><Link to="/company/vacancies">{t('hiring.toVacancies')}</Link></Button>
        </div>
      ) : (
        <>
          {report.outcomes.stale > 0 && <StaleAlert report={report} />}
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 animate-rise">
            <Stat Icon={FileText} label={t('hiring.stats.applied')} value={applied} />
            <Stat Icon={BriefcaseBusiness} label={t('hiring.stats.hired')} value={report.outcomes.hired} accent />
            <Stat Icon={Timer} label={t('hiring.stats.firstAction')} value={hours(report.timing.first_action_hours, t)} />
            <Stat Icon={Hourglass} label={t('hiring.stats.timeToHire')} value={daysLabel(report.timing.hire_days, t)} />
          </div>
          <div className="grid gap-4 lg:grid-cols-5">
            <Stages report={report} className="lg:col-span-3" />
            <Outcomes report={report} className="lg:col-span-2" />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <Assessments report={report} />
            <Interviews report={report} />
          </div>
          {report.by_vacancy.length > 0 && !vacancy && <ByVacancy report={report} />}
        </>
      )}
    </section>
  )
}

function daysLabel(value: number | null, t: TFunction) {
  if (value === null) return '—'
  return value < 1 ? t('companyReport.lessThanDay') : t('companyReport.days', { count: Math.round(value) })
}

function StaleAlert({ report }: { report: HiringReport }) {
  const { t } = useTranslation()
  const target = report.vacancy_id ? `/company/vacancies/${report.vacancy_id}` : '/company/vacancies'
  return (
    <div role="status" className="glass flex flex-wrap items-center gap-3 rounded-2xl border-destructive/30 px-4 py-3 animate-rise">
      <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-destructive/12 text-destructive">
        <AlarmClock className="h-5 w-5" />
      </span>
      <p className="min-w-0 flex-1 text-sm">
        <b>{t('hiring.stale.title', { count: report.outcomes.stale })}</b>
        <span className="block text-muted-foreground">{t('hiring.stale.body')}</span>
      </p>
      <Button asChild size="sm" variant="outline"><Link to={target}>{t('hiring.stale.action')}</Link></Button>
    </div>
  )
}

/** Har bosqich: arizalarga nisbatan chiziq; oraliqda oldingi bosqichdan o'tish foizi (§27.1). */
function Stages({ report, className }: { report: HiringReport; className?: string }) {
  const { t } = useTranslation()
  return (
    <Card className={cn('animate-rise', className)}>
      <CardHeader><CardTitle className="text-base">{t('hiring.stages.title')}</CardTitle></CardHeader>
      <CardContent className="space-y-1">
        {report.stages.map((s, i) => {
          const Icon = STAGE_ICON[s.stage]
          return (
            <Fragment key={s.stage}>
              {i > 1 && (
                <p className="flex items-center gap-1.5 py-0.5 pl-10 text-xs text-muted-foreground">
                  <ArrowDown className="h-3.5 w-3.5" />
                  {s.step_rate === null ? t('hiring.stages.skipped') : t('hiring.stages.step', { rate: pct(s.step_rate) })}
                </p>
              )}
              <div className="flex items-center gap-3">
                <span className={cn('grid h-8 w-8 shrink-0 place-items-center rounded-lg',
                  s.stage === 'hired' ? 'bg-success/15 text-success' : 'bg-primary/12 text-primary')}>
                  <Icon className="h-4 w-4" />
                </span>
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex justify-between gap-2 text-sm">
                    <span className="truncate">{t(`hiring.stage.${s.stage}`)}</span>
                    <span className="shrink-0 tabular-nums">
                      <b>{s.count}</b>
                      {i > 0 && <span className="ml-1.5 text-muted-foreground">{pct(s.rate)}</span>}
                    </span>
                  </div>
                  <div className="h-2.5 overflow-hidden rounded-full bg-muted">
                    <div className={cn('h-full rounded-full transition-[width] duration-700', s.stage === 'hired' ? 'bg-success' : 'bg-brand')}
                      style={{ width: `${s.rate ?? 0}%` }} />
                  </div>
                </div>
              </div>
            </Fragment>
          )
        })}
        <p className="pt-3 text-xs text-muted-foreground">{t('hiring.stages.note')}</p>
      </CardContent>
    </Card>
  )
}

function Outcomes({ report, className }: { report: HiringReport; className?: string }) {
  const { t } = useTranslation()
  const total = report.stages[0].count
  const shown = OUTCOMES.filter((o) => report.outcomes[o.key] > 0)
  const lost = report.dropoff.filter((d) => d.rejected + d.withdrawn > 0)
  return (
    <Card className={cn('animate-rise', className)}>
      <CardHeader><CardTitle className="text-base">{t('hiring.outcomes.title')}</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        <div className="flex h-3 overflow-hidden rounded-full bg-muted" aria-hidden>
          {shown.map((o) => (
            <div key={o.key} className={cn('h-full', o.tone)} style={{ width: `${(report.outcomes[o.key] * 100) / total}%` }} />
          ))}
        </div>
        <ul className="grid grid-cols-1 gap-x-4 gap-y-1.5 text-sm sm:grid-cols-2 lg:grid-cols-1">
          {shown.map((o) => (
            <li key={o.key} className="flex items-center gap-2">
              <span className={cn('h-2.5 w-2.5 shrink-0 rounded-sm', o.tone)} />
              <span className="min-w-0 flex-1 truncate">{t(`hiring.outcome.${o.key}`)}</span>
              <b className="tabular-nums">{report.outcomes[o.key]}</b>
            </li>
          ))}
        </ul>
        {lost.length > 0 && (
          <div className="space-y-1.5 border-t pt-3">
            <p className="text-xs font-medium text-muted-foreground">{t('hiring.dropoff.title')}</p>
            {lost.map((d) => (
              <div key={d.stage} className="flex items-center justify-between gap-2 text-sm">
                <span>{t(`hiring.dropoff.at.${d.stage}`)}</span>
                <span className="text-xs text-muted-foreground tabular-nums">
                  {[
                    d.rejected > 0 && t('hiring.dropoff.rejected', { count: d.rejected }),
                    d.withdrawn > 0 && t('hiring.dropoff.withdrawn', { count: d.withdrawn }),
                  ].filter(Boolean).join(' · ')}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function Metric({ label, value, strong = false }: { label: string; value: number | string; strong?: boolean }) {
  return (
    <div className="rounded-xl border bg-background/60 px-3 py-2">
      <p className={cn('text-lg font-bold tabular-nums', strong && 'text-primary')}>{value}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  )
}

function Assessments({ report }: { report: HiringReport }) {
  const { t } = useTranslation()
  const a = report.assessments
  return (
    <Card className="animate-rise">
      <CardHeader className="flex-row items-center justify-between gap-3 space-y-0">
        <CardTitle className="flex items-center gap-2 text-base"><ClipboardCheck className="h-4 w-4 text-primary" />{t('hiring.assessments.title')}</CardTitle>
        {a.avg_score !== null && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {t('hiring.assessments.avgScore')}<ScoreRing value={a.avg_score} size={40} />
          </div>
        )}
      </CardHeader>
      <CardContent>
        {a.sent === 0 ? (
          <p className="text-sm text-muted-foreground">{t('hiring.assessments.none')}</p>
        ) : (
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <Metric label={t('hiring.assessments.sent')} value={a.sent} />
            <Metric label={t('hiring.assessments.started')} value={a.started} />
            <Metric label={t('hiring.assessments.completed')} value={a.completed} />
            <Metric label={t('hiring.assessments.completionRate')} value={pct(a.completion_rate)} strong />
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function Interviews({ report }: { report: HiringReport }) {
  const { t } = useTranslation()
  const i = report.interviews
  return (
    <Card className="animate-rise">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base"><MessagesSquare className="h-4 w-4 text-primary" />{t('hiring.interviews.title')}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {i.proposed === 0 ? (
          <p className="text-sm text-muted-foreground">{t('hiring.interviews.none')}</p>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Metric label={t('hiring.interviews.proposed')} value={i.proposed} />
              <Metric label={t('hiring.interviews.held')} value={i.held} />
              <Metric label={t('hiring.interviews.passRate')} value={pct(i.pass_rate)} strong />
              <Metric label={t('hiring.interviews.showRate')} value={pct(i.show_rate)} />
            </div>
            <p className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
              <span>{t('hiring.interviews.confirmed', { count: i.confirmed })}</span>
              {i.declined > 0 && <span>{t('hiring.interviews.declined', { count: i.declined })}</span>}
              {i.no_show > 0 && <span className="font-medium text-destructive">{t('hiring.interviews.noShow', { count: i.no_show })}</span>}
            </p>
          </>
        )}
      </CardContent>
    </Card>
  )
}

function ByVacancy({ report }: { report: HiringReport }) {
  const { t } = useTranslation()
  const stages: HiringStage[] = ['applied', 'assessment', 'interview', 'offer', 'hired']
  return (
    <Card className="animate-rise">
      <CardHeader><CardTitle className="text-base">{t('hiring.byVacancy.title')}</CardTitle></CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="w-full min-w-[36rem] text-sm">
          <thead>
            <tr className="border-b text-left text-xs text-muted-foreground">
              <th className="py-2 pr-3 font-medium">{t('hiring.vacancy')}</th>
              {stages.map((s) => <th key={s} className="px-2 py-2 text-right font-medium">{t(`hiring.stage.${s}`)}</th>)}
              <th className="py-2 pl-3 text-right font-medium">{t('hiring.byVacancy.hireRate')}</th>
            </tr>
          </thead>
          <tbody>
            {report.by_vacancy.map((v) => (
              <tr key={v.vacancy_id} className="border-b last:border-0">
                <td className="max-w-xs py-2.5 pr-3">
                  <Link to={`/company/vacancies/${v.vacancy_id}`} className="block truncate font-medium hover:text-primary hover:underline">{v.title}</Link>
                  {v.status !== 'open' && <span className="text-xs text-muted-foreground">{t(`vacancy.status.${v.status}`)}</span>}
                </td>
                {stages.map((s) => (
                  <td key={s} className={cn('px-2 py-2.5 text-right tabular-nums', s === 'hired' && v.hired > 0 && 'font-semibold text-success')}>
                    {v[s] || '—'}
                  </td>
                ))}
                <td className="py-2.5 pl-3 text-right tabular-nums">{v.hired ? pct(v.hire_rate) : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  )
}
