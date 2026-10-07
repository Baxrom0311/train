import { useEffect, useState } from 'react'
import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { AlarmClock, CheckCircle2, Download, Loader2, MessageSquareReply, Send, Timer, Trophy, Users, Zap } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Segmented } from '@/components/ui/segmented'
import { Stat } from '@/components/ui/stat'
import { CompetencyBars, ScoreRing } from '@/components/score'
import { api, ApiError, download } from '@/lib/api'
import { formatDateTime, formatMonth } from '@/lib/time'
import type { CompanyReport } from '@/lib/types'
import { cn } from '@/lib/utils'

// davr tanlovi (CONTRACT.md §20.4); null — butun tarix
const PERIODS = [30, 90, 365, null] as const
type Period = (typeof PERIODS)[number]

const pct = (v: number | null) => (v === null ? '—' : `${Math.round(v)}%`)

export default function CompanyReportPage() {
  const { t } = useTranslation()
  const [days, setDays] = useState<Period>(90)
  const [report, setReport] = useState<CompanyReport | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    setLoading(true)
    api<CompanyReport>(`/talents/report${days ? `?days=${days}` : ''}`)
      .then((r) => alive && (setReport(r), setError(null)))
      .catch((err) => alive && setError(err instanceof ApiError && err.status === 403 ? t('talent.notVerified') : t('common.error')))
      .finally(() => alive && setLoading(false))
    return () => { alive = false }
  }, [days, t])

  if (error && !report) return <p className="mx-auto max-w-6xl px-4 py-8 text-destructive">{error}</p>
  if (!report) return <Loader2 className="mx-auto mt-16 h-6 w-6 animate-spin text-muted-foreground" />

  const { offers, pool } = report
  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-8">
      <div className="flex flex-wrap items-end justify-between gap-4 animate-rise">
        <div className="space-y-1">
          <h1 className="text-4xl font-extrabold tracking-tight">{t('companyReport.title')}</h1>
          <p className="text-muted-foreground">
            {report.company.name} · {t('companyReport.generated', { date: formatDateTime(report.generated_at) })}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <PeriodPicker value={days} onChange={setDays} busy={loading} />
          <CsvButton path={`/talents/report/offers.csv${days ? `?days=${days}` : ''}`} name="tryjob-offers.csv" label={t('companyReport.csv.offers')} />
          <CsvButton path="/talents/report/candidates.csv" name="tryjob-candidates.csv" label={t('companyReport.csv.candidates')} />
        </div>
      </div>
      {error && <p className="glass rounded-2xl px-4 py-3 text-sm text-destructive">{error}</p>}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 animate-rise">
        <Stat Icon={Send} label={t('companyReport.stats.sent')} value={offers.sent} />
        <Stat Icon={MessageSquareReply} label={t('companyReport.stats.responseRate')} value={pct(offers.response_rate)} />
        <Stat Icon={CheckCircle2} label={t('companyReport.stats.acceptanceRate')} value={pct(offers.acceptance_rate)} />
        <Stat Icon={Timer} label={t('companyReport.stats.medianResponse')} value={hours(offers.median_response_hours, t)} />
      </div>

      {offers.sent === 0 ? (
        <div className="glass flex flex-col items-center gap-3 rounded-2xl px-6 py-12 text-center animate-rise">
          <Send className="h-8 w-8 text-muted-foreground" />
          <p className="max-w-md text-sm text-muted-foreground">{t('companyReport.noOffers')}</p>
          <Button asChild variant="outline" size="sm"><Link to="/talents">{t('companyReport.toTalents')}</Link></Button>
        </div>
      ) : (
        <>
          <div className="grid gap-4 lg:grid-cols-5">
            <Funnel report={report} className="lg:col-span-2" />
            <Months report={report} className="lg:col-span-3" />
          </div>
          <Positions report={report} />
        </>
      )}

      <section className="space-y-4">
        <div className="animate-rise">
          <h2 className="text-2xl font-extrabold tracking-tight">{t('companyReport.pool.title')}</h2>
          <p className="text-sm text-muted-foreground">{t('companyReport.pool.subtitle')}</p>
        </div>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 animate-rise">
          <Stat Icon={Users} label={t('companyReport.pool.candidates')} value={pool.candidates} />
          <Stat Icon={Zap} label={days ? t('companyReport.pool.activeDays', { count: days }) : t('companyReport.pool.active')} value={pool.active_in_period} />
          <Stat Icon={Trophy} label={t('companyReport.pool.avgScore')} value={pool.avg_score ?? '—'} />
        </div>
        {pool.candidates > 0 && <Pool report={report} />}
      </section>
    </div>
  )
}

function hours(value: number | null, t: TFunction): string {
  if (value === null) return '—'
  if (value < 1) return t('companyReport.lessThanHour')
  if (value < 48) return t('companyReport.hours', { count: Math.round(value) })
  return t('companyReport.days', { count: Math.round(value / 24) })
}

function PeriodPicker({ value, onChange, busy }: { value: Period; onChange: (p: Period) => void; busy: boolean }) {
  const { t } = useTranslation()
  const options = PERIODS.map((p) => ({ value: p, label: p ? t('companyReport.period.days', { count: p }) : t('companyReport.period.all') }))
  return <Segmented options={options} value={value} onChange={onChange} busy={busy} label={t('companyReport.period.label')} />
}

function CsvButton({ path, name, label }: { path: string; name: string; label: string }) {
  const { t } = useTranslation()
  const [state, setState] = useState<'idle' | 'busy' | 'error'>('idle')
  const run = () => {
    setState('busy')
    download(path, name).then(() => setState('idle'), () => setState('error'))
  }
  return (
    <Button variant="outline" size="sm" onClick={run} disabled={state === 'busy'} title={state === 'error' ? t('common.error') : undefined}
      className={cn(state === 'error' && 'border-destructive text-destructive')}>
      {state === 'busy' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
      {label}
    </Button>
  )
}

/** Voronka: har bosqich yuborilganlarga nisbatan (CONTRACT.md §20.2). */
function Funnel({ report, className }: { report: CompanyReport; className?: string }) {
  const { t } = useTranslation()
  const o = report.offers
  const steps = [
    { key: 'sent', value: o.sent },
    { key: 'viewed', value: o.viewed },
    { key: 'responded', value: o.responded },
    { key: 'accepted', value: o.accepted },
  ]
  return (
    <Card className={cn('animate-rise', className)}>
      <CardHeader><CardTitle className="text-base">{t('companyReport.funnel.title')}</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        {steps.map((s, i) => (
          <div key={s.key} className="space-y-1">
            <div className="flex justify-between text-sm">
              <span>{t(`companyReport.funnel.${s.key}`)}</span>
              <span className="tabular-nums">
                <b>{s.value}</b>
                {i > 0 && <span className="ml-1.5 text-muted-foreground">{Math.round((s.value * 100) / o.sent)}%</span>}
              </span>
            </div>
            <div className="h-3 overflow-hidden rounded-full bg-muted">
              <div className="bg-brand h-full rounded-full transition-[width] duration-700" style={{ width: `${(s.value * 100) / o.sent}%` }} />
            </div>
          </div>
        ))}
        <div className="flex flex-wrap gap-x-4 gap-y-1 border-t pt-3 text-xs text-muted-foreground">
          <span>{t('companyReport.funnel.declined', { count: o.declined })}</span>
          <span>{t('companyReport.funnel.pending', { count: o.pending })}</span>
          {o.overdue > 0 && (
            <span className="flex items-center gap-1 font-medium text-destructive">
              <AlarmClock className="h-3.5 w-3.5" /> {t('companyReport.funnel.overdue', { count: o.overdue })}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

/** Oylar bo'yicha ustunlar: butun ustun — yuborilgan, ichida qabul va rad. */
function Months({ report, className }: { report: CompanyReport; className?: string }) {
  const { t, i18n } = useTranslation()
  const months = report.by_month.slice(-12)
  const max = Math.max(1, ...months.map((m) => m.sent))
  return (
    <Card className={cn('animate-rise', className)}>
      <CardHeader className="flex-row flex-wrap items-center justify-between gap-x-3 gap-y-2 space-y-0">
        <CardTitle className="text-base">{t('companyReport.months.title')}</CardTitle>
        <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
          <Legend className="bg-primary/25" label={t('companyReport.funnel.sent')} />
          <Legend className="bg-success" label={t('companyReport.funnel.accepted')} />
          <Legend className="bg-destructive/70" label={t('companyReport.months.declined')} />
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex h-44 items-end gap-1.5 sm:gap-2">
          {months.map((m, i) => {
            const newYear = i === 0 || m.month.endsWith('-01')
            const label = formatMonth(m.month, i18n.language, newYear && months.length > 1)
            return (
              <div key={m.month} className="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-1"
                title={`${label}: ${m.sent} / ${m.accepted} / ${m.declined}`}>
                <span className="text-[11px] font-semibold tabular-nums text-muted-foreground">{m.sent || ''}</span>
                <div className="flex w-full max-w-10 flex-col justify-end overflow-hidden rounded-t-md bg-primary/25"
                  style={{ height: `${(m.sent / max) * 100}%` }}>
                  <div className="bg-destructive/70" style={{ height: `${m.sent ? (m.declined / m.sent) * 100 : 0}%` }} />
                  <div className="bg-success" style={{ height: `${m.sent ? (m.accepted / m.sent) * 100 : 0}%` }} />
                </div>
                <span className="w-full truncate text-center text-[11px] text-muted-foreground">{label}</span>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}

function Legend({ className, label }: { className: string; label: string }) {
  return <span className="flex items-center gap-1 whitespace-nowrap"><span className={cn('h-2.5 w-2.5 rounded-sm', className)} />{label}</span>
}

function Positions({ report }: { report: CompanyReport }) {
  const { t } = useTranslation()
  return (
    <Card className="animate-rise">
      <CardHeader><CardTitle className="text-base">{t('companyReport.positions.title')}</CardTitle></CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="w-full min-w-[28rem] text-sm">
          <thead>
            <tr className="border-b text-left text-xs text-muted-foreground">
              <th className="py-2 pr-3 font-medium">{t('companyReport.positions.position')}</th>
              <th className="px-3 py-2 text-right font-medium">{t('companyReport.funnel.sent')}</th>
              <th className="px-3 py-2 text-right font-medium">{t('companyReport.funnel.accepted')}</th>
              <th className="px-3 py-2 text-right font-medium">{t('companyReport.months.declined')}</th>
              <th className="py-2 pl-3 text-right font-medium">{t('companyReport.positions.pending')}</th>
            </tr>
          </thead>
          <tbody>
            {report.by_position.map((p) => (
              <tr key={p.position_title} className="border-b last:border-0">
                <td className="max-w-xs truncate py-2.5 pr-3 font-medium">{p.position_title}</td>
                <td className="px-3 py-2.5 text-right tabular-nums">{p.sent}</td>
                <td className={cn('px-3 py-2.5 text-right tabular-nums', p.accepted > 0 && 'font-semibold text-success')}>{p.accepted || '—'}</td>
                <td className="px-3 py-2.5 text-right tabular-nums">{p.declined || '—'}</td>
                <td className="py-2.5 pl-3 text-right tabular-nums">{p.pending || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  )
}

function Pool({ report }: { report: CompanyReport }) {
  const { t } = useTranslation()
  const { pool } = report
  const max = Math.max(1, ...pool.score_bands.map((b) => b.candidates))
  const competencies = Object.fromEntries(Object.entries(pool.competencies).sort((a, b) => b[1] - a[1]))
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card className="animate-rise">
        <CardHeader><CardTitle className="text-base">{t('companyReport.pool.bands')}</CardTitle></CardHeader>
        <CardContent className="space-y-2.5">
          {[...pool.score_bands].reverse().map((b) => (
            <div key={b.band} className="flex items-center gap-3 text-sm">
              <span className="w-14 shrink-0 tabular-nums text-muted-foreground">{b.band}</span>
              <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-muted">
                <div className="bg-brand h-full rounded-full transition-[width] duration-700" style={{ width: `${(b.candidates / max) * 100}%` }} />
              </div>
              <span className="w-8 text-right font-semibold tabular-nums">{b.candidates}</span>
            </div>
          ))}
        </CardContent>
      </Card>
      <Card className="animate-rise">
        <CardHeader><CardTitle className="text-base">{t('university.sectors')}</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {pool.sectors.map((s) => (
            <div key={s.sector} className="flex items-center justify-between gap-3 rounded-xl border bg-background/60 px-3 py-2">
              <div>
                <p className="text-sm font-semibold">{t(`catalog.sector.${s.sector}`)}</p>
                <p className="text-xs text-muted-foreground">{t('talent.found', { count: s.candidates })}</p>
              </div>
              {s.avg_score !== null && <ScoreRing value={s.avg_score} size={44} />}
            </div>
          ))}
        </CardContent>
      </Card>
      <Card className="animate-rise">
        <CardHeader><CardTitle className="text-base">{t('university.competencies')}</CardTitle></CardHeader>
        <CardContent><CompetencyBars scores={competencies} compact /></CardContent>
      </Card>
    </div>
  )
}
