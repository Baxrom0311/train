import { useEffect, useState } from 'react'
import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'
import { Activity, AlertTriangle, Bot, CheckCircle2, Coins, Loader2, PlayCircle, Trophy, UserPlus, Users } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Segmented } from '@/components/ui/segmented'
import { Stat } from '@/components/ui/stat'
import { api } from '@/lib/api'
import { formatDateTime, formatDayMonth } from '@/lib/time'
import type { PlatformStats as Stats } from '@/lib/types'
import { cn } from '@/lib/utils'

// §21.3
const PERIODS = [7, 30, 90] as const
type Period = (typeof PERIODS)[number]
// navbat "tiqildi" deyiladigan chegara (§21.4)
const STALE_MINUTES = 30

const num = (v: number) => new Intl.NumberFormat('en-US').format(v).replace(/,/g, ' ')
const pct = (v: number | null) => (v === null ? '—' : `${Math.round(v)}%`)

/** 1 234 567 → "1.2M"; kichik sonlar to'liq. */
function compact(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
  if (v >= 10_000) return `${Math.round(v / 1000)}K`
  return num(v)
}

function usd(v: number | null): string {
  if (v === null) return '—'
  return v > 0 && v < 0.01 ? '<$0.01' : `$${v.toFixed(2)}`
}

export default function PlatformStats() {
  const { t } = useTranslation()
  const [days, setDays] = useState<Period>(30)
  const [stats, setStats] = useState<Stats | null>(null)
  const [error, setError] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    setLoading(true)
    api<Stats>(`/admin/platform?days=${days}`)
      .then((s) => alive && (setStats(s), setError(false)))
      .catch(() => alive && setError(true))
      .finally(() => alive && setLoading(false))
    return () => { alive = false }
  }, [days])

  if (!stats) {
    return error
      ? <p className="glass rounded-2xl px-4 py-3 text-sm text-destructive">{t('common.error')}</p>
      : <Loader2 className="mx-auto mt-8 h-6 w-6 animate-spin text-muted-foreground" />
  }

  const { users, runs, ai } = stats
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">{t('platform.generated', { date: formatDateTime(stats.generated_at) })}</p>
        <Segmented
          options={PERIODS.map((p) => ({ value: p, label: t('platform.days', { count: p }) }))}
          value={days} onChange={setDays} busy={loading} label={t('platform.period')} />
      </div>
      {error && <p className="glass rounded-2xl px-4 py-3 text-sm text-destructive">{t('common.error')}</p>}

      <QueueAlert stats={stats} />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 animate-rise">
        <Stat Icon={Users} label={t('platform.stats.students')} value={users.students} />
        <Stat Icon={UserPlus} label={t('platform.stats.newStudents')} value={users.new_students} />
        <Stat Icon={Activity} label={t('platform.stats.activeStudents')} value={users.active_students} />
        <Stat Icon={PlayCircle} label={t('platform.stats.inProgress')} value={runs.in_progress} />
        <Stat Icon={CheckCircle2} label={t('platform.stats.completionRate')} value={pct(runs.completion_rate)} />
        <Stat Icon={Trophy} label={t('platform.stats.avgScore')} value={runs.avg_score ?? '—'} />
        <Stat Icon={Bot} label={t('platform.stats.aiTokens')} value={compact(ai.tokens_in + ai.tokens_out)} />
        <Stat Icon={Coins} label={ai.cost_complete ? t('platform.stats.aiCost') : t('platform.stats.aiCostPartial')} value={usd(ai.cost_usd)} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card className="animate-rise">
          <CardHeader className="flex-row flex-wrap items-center justify-between gap-x-3 gap-y-2 space-y-0">
            <CardTitle className="text-base">{t('platform.activity')}</CardTitle>
            <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
              <Legend className="bg-primary/25" label={t('platform.runsStarted')} />
              <Legend className="bg-success" label={t('platform.runsCompleted')} />
            </div>
          </CardHeader>
          <CardContent>
            <DayBars
              days={stats.daily.map((d) => d.day)}
              values={stats.daily.map((d) => Math.max(d.runs_started, d.runs_completed))}
              inner={stats.daily.map((d) => d.runs_completed)}
              title={(i) => {
                const d = stats.daily[i]
                return t('platform.activityTip', { day: formatDayMonth(d.day), started: d.runs_started, completed: d.runs_completed, students: d.new_students })
              }} />
            <p className="mt-3 text-xs text-muted-foreground">
              {t('platform.runsSummary', { started: runs.started, completed: runs.completed, expired: runs.expired, abandoned: runs.abandoned })}
            </p>
          </CardContent>
        </Card>
        <Card className="animate-rise">
          <CardHeader className="flex-row flex-wrap items-center justify-between gap-x-3 gap-y-2 space-y-0">
            <CardTitle className="text-base">{t('platform.aiDaily')}</CardTitle>
            <span className="text-xs text-muted-foreground">{t('platform.aiCalls', { calls: num(ai.calls), failures: num(ai.failures) })}</span>
          </CardHeader>
          <CardContent>
            <DayBars
              days={stats.daily.map((d) => d.day)}
              values={stats.daily.map((d) => d.ai_tokens)}
              title={(i) => {
                const d = stats.daily[i]
                return `${formatDayMonth(d.day)}: ${num(d.ai_tokens)} · ${usd(d.ai_cost_usd)}`
              }} />
            <p className="mt-3 text-xs text-muted-foreground">
              {t('platform.tokensSplit', { input: compact(ai.tokens_in), output: compact(ai.tokens_out) })}
              {!ai.cost_complete && <> · {t('platform.pricesMissing')}</>}
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Evaluation stats={stats} />
        <AiBreakdown stats={stats} className="lg:col-span-2" />
      </div>

      <Scenarios stats={stats} />
    </div>
  )
}

/** Kutish vaqti: 90 daqiqagacha daqiqada, keyin soatda, 2 kundan keyin kunda. */
function waited(t: TFunction, minutes: number): string {
  if (minutes < 90) return t('platform.minutes', { count: minutes })
  if (minutes < 48 * 60) return t('platform.hours', { count: Math.round(minutes / 60) })
  return t('platform.daysAgo', { count: Math.round(minutes / 1440) })
}

function QueueAlert({ stats }: { stats: Stats }) {
  const { t } = useTranslation()
  const ev = stats.evaluation
  const stale = (ev.oldest_pending_minutes ?? 0) > STALE_MINUTES
  const problems = [
    ev.failed > 0 && t('platform.alert.failed', { count: ev.failed }),
    stale && t('platform.alert.stale', { time: waited(t, ev.oldest_pending_minutes ?? 0) }),
    ev.queue_jobs === null && t('platform.alert.redis'),
  ].filter(Boolean)
  if (!problems.length) return null
  return (
    <div role="alert" className="glass flex items-start gap-3 rounded-2xl border-destructive/40 px-4 py-3 text-sm animate-rise">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
      <div>
        <p className="font-semibold">{t('platform.alert.title')}</p>
        <p className="text-muted-foreground">{problems.join(' · ')}</p>
      </div>
    </div>
  )
}

/** Kunlik ustunlar; `inner` — ustun ichidagi ikkinchi qiymat (masalan, tugagan Run'lar). */
function DayBars({ days, values, inner, title }: {
  days: string[]
  values: number[]
  inner?: number[]
  title: (i: number) => string
}) {
  const max = Math.max(1, ...values)
  const ticks = new Set([0, Math.floor((days.length - 1) / 2), days.length - 1])
  return (
    <div>
      <div className={cn('flex h-36 items-end', days.length > 31 ? 'gap-px' : 'gap-1')}>
        {values.map((v, i) => (
          <div key={days[i]} title={title(i)} className="group flex h-full min-w-0 flex-1 items-end">
            <div className="flex w-full flex-col justify-end overflow-hidden rounded-t-sm bg-primary/25 transition-colors group-hover:bg-primary/40"
              style={{ height: v ? `max(3px, ${(v / max) * 100}%)` : 0 }}>
              {inner && <div className="bg-success" style={{ height: `${v ? (inner[i] / v) * 100 : 0}%` }} />}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-1.5 flex justify-between text-[11px] text-muted-foreground tabular-nums">
        {[...ticks].map((i) => <span key={i}>{formatDayMonth(days[i])}</span>)}
      </div>
    </div>
  )
}

function Legend({ className, label }: { className: string; label: string }) {
  return <span className="flex items-center gap-1 whitespace-nowrap"><span className={cn('h-2.5 w-2.5 rounded-sm', className)} />{label}</span>
}

function Evaluation({ stats }: { stats: Stats }) {
  const { t } = useTranslation()
  const ev = stats.evaluation
  const rows: [string, string | number, boolean][] = [
    [t('platform.queue.pending'), ev.pending, false],
    [t('platform.queue.retry'), ev.queued_retry, ev.queued_retry > 0],
    [t('platform.queue.failed'), ev.failed, ev.failed > 0],
    [t('platform.queue.oldest'), ev.oldest_pending_minutes === null ? '—' : waited(t, ev.oldest_pending_minutes),
      (ev.oldest_pending_minutes ?? 0) > STALE_MINUTES],
    [t('platform.queue.jobs'), ev.queue_jobs ?? '—', ev.queue_jobs === null],
  ]
  return (
    <Card className="animate-rise">
      <CardHeader><CardTitle className="text-base">{t('platform.queue.title')}</CardTitle></CardHeader>
      <CardContent className="space-y-2">
        {rows.map(([label, value, bad]) => (
          <div key={label} className="flex items-center justify-between rounded-xl border bg-background/60 px-3 py-2 text-sm">
            <span className="text-muted-foreground">{label}</span>
            <span className={cn('font-semibold tabular-nums', bad && 'text-destructive')}>{value}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

function purposeLabel(t: TFunction, purpose: string) {
  return t(`platform.purpose.${purpose}`, { defaultValue: purpose })
}

function AiBreakdown({ stats, className }: { stats: Stats; className?: string }) {
  const { t } = useTranslation()
  const { ai } = stats
  const total = Math.max(1, ai.tokens_in + ai.tokens_out)
  return (
    <Card className={cn('animate-rise', className)}>
      <CardHeader><CardTitle className="text-base">{t('platform.aiTitle')}</CardTitle></CardHeader>
      <CardContent className="space-y-5">
        {ai.by_purpose.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t('platform.noAi')}</p>
        ) : (
          <div className="space-y-2.5">
            {ai.by_purpose.map((p) => (
              <div key={p.purpose} className="space-y-1">
                <div className="flex justify-between gap-3 text-sm">
                  <span>{purposeLabel(t, p.purpose)}</span>
                  <span className="tabular-nums text-muted-foreground">
                    {t('platform.callsShort', { count: p.calls })} · <b className="text-foreground">{compact(p.tokens)}</b> · {usd(p.cost_usd)}
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-muted">
                  <div className="bg-brand h-full rounded-full" style={{ width: `${(p.tokens / total) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        )}
        {ai.by_provider.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[30rem] text-sm">
              <thead>
                <tr className="border-b text-left text-xs text-muted-foreground">
                  <th className="py-2 pr-3 font-medium">{t('platform.provider')}</th>
                  <th className="px-3 py-2 text-right font-medium">{t('platform.calls')}</th>
                  <th className="px-3 py-2 text-right font-medium">{t('platform.failures')}</th>
                  <th className="px-3 py-2 text-right font-medium">{t('platform.tokens')}</th>
                  <th className="py-2 pl-3 text-right font-medium">{t('platform.cost')}</th>
                </tr>
              </thead>
              <tbody>
                {ai.by_provider.map((p) => (
                  <tr key={`${p.provider}/${p.model}`} className="border-b last:border-0">
                    <td className="py-2 pr-3"><span className="font-medium">{p.provider}</span> <span className="text-xs text-muted-foreground">{p.model}</span></td>
                    <td className="px-3 py-2 text-right tabular-nums">{num(p.calls)}</td>
                    <td className={cn('px-3 py-2 text-right tabular-nums', p.failures > 0 && 'text-destructive')}>{num(p.failures)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{compact(p.tokens_in + p.tokens_out)}</td>
                    <td className="py-2 pl-3 text-right tabular-nums">{usd(p.cost_usd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function Scenarios({ stats }: { stats: Stats }) {
  const { t } = useTranslation()
  if (!stats.scenarios.length) return null
  return (
    <Card className="animate-rise">
      <CardHeader><CardTitle className="text-base">{t('platform.scenarios')}</CardTitle></CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="w-full min-w-[34rem] text-sm">
          <thead>
            <tr className="border-b text-left text-xs text-muted-foreground">
              <th className="py-2 pr-3 font-medium">{t('platform.scenario')}</th>
              <th className="px-3 py-2 text-right font-medium">{t('platform.runsStarted')}</th>
              <th className="px-3 py-2 text-right font-medium">{t('platform.runsCompleted')}</th>
              <th className="px-3 py-2 text-right font-medium">{t('platform.stats.completionRate')}</th>
              <th className="py-2 pl-3 text-right font-medium">{t('platform.stats.avgScore')}</th>
            </tr>
          </thead>
          <tbody>
            {stats.scenarios.map((s) => (
              <tr key={s.scenario_id} className="border-b last:border-0">
                <td className="py-2.5 pr-3">
                  <p className="font-medium">{s.title}</p>
                  <p className="text-xs text-muted-foreground">{t(`catalog.sector.${s.sector}`)}</p>
                </td>
                <td className="px-3 py-2.5 text-right tabular-nums">{s.started}</td>
                <td className="px-3 py-2.5 text-right tabular-nums">{s.completed}</td>
                <td className="px-3 py-2.5 text-right tabular-nums">{pct(s.completion_rate)}</td>
                <td className="py-2.5 pl-3 text-right font-semibold tabular-nums">{s.avg_score ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  )
}
