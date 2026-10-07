// /dashboard (talaba) — "Mening o'sishim" (CONTRACT.md §17.3).
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import {
  Activity, ArrowRight, Award, BookOpenCheck, Briefcase, CalendarDays, Clock, Loader2, Minus, Play,
  Sparkles, Target, TrendingDown, TrendingUp, Trophy, type LucideIcon,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Stat } from '@/components/ui/stat'
import { ScoreChart, Sparkline, type ChartPoint } from '@/components/analytics/charts'
import { SECTOR_ART } from '@/components/sectorArt'
import MyUniversityCard from '@/components/university/MyUniversityCard'
import { homeFor, useAuth } from '@/context/AuthContext'
import { api, ApiError } from '@/lib/api'
import { formatDateTime } from '@/lib/time'
import type { CompetencyTrend, Recommendation, RunCreated, RunSummary, StudentAnalytics, Trend } from '@/lib/types'
import { cn } from '@/lib/utils'

const OPEN = ['scheduled', 'active']

const TREND: Record<Trend, { Icon: LucideIcon; tone: string }> = {
  up: { Icon: TrendingUp, tone: 'bg-success/12 text-success' },
  down: { Icon: TrendingDown, tone: 'bg-destructive/12 text-destructive' },
  flat: { Icon: Minus, tone: 'bg-muted text-muted-foreground' },
  new: { Icon: Sparkles, tone: 'bg-primary/12 text-primary' },
}

const round = (v: number | null) => (v === null ? '—' : Math.round(v))

export default function DashboardPage() {
  const { t } = useTranslation()
  const { user, can } = useAuth()
  const [data, setData] = useState<StudentAnalytics | null>(null)
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [error, setError] = useState('')
  // dashboard — talaba sahifasi; boshqalar o'z bosh sahifasiga
  const elsewhere = Boolean(user) && !can('receive_offers')

  useEffect(() => {
    if (!user || elsewhere) return
    Promise.all([api<StudentAnalytics>('/users/me/analytics'), api<RunSummary[]>('/runs/my')])
      .then(([a, r]) => { setData(a); setRuns(r) })
      .catch(() => setError(t('common.error')))
  }, [user, elsewhere, t])

  if (elsewhere) return <Navigate to={homeFor(user)} replace />

  const openRun = runs.find((r) => OPEN.includes(r.status))
  const s = data?.summary

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8">
      <div className="animate-rise space-y-2">
        <p className="text-sm font-semibold text-primary">{user && t('dashboard.welcomeName', { name: user.full_name })}</p>
        <h1 className="text-4xl font-extrabold tracking-tight">{t('growth.title')}</h1>
        <p className="max-w-2xl text-muted-foreground">{t('growth.subtitle')}</p>
      </div>

      {openRun && (
        <div className="glass glow-ring animate-rise flex flex-wrap items-center justify-between gap-4 rounded-2xl p-5">
          <div className="flex min-w-0 items-center gap-4">
            <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-primary/15 text-primary">
              <span className="h-2.5 w-2.5 rounded-full bg-primary animate-glow" />
            </span>
            <div className="min-w-0">
              <p className="truncate font-bold">{openRun.scenario.title}</p>
              <p className="text-sm text-muted-foreground">{t('catalog.openRun', { date: formatDateTime(openRun.ends_at) })}</p>
            </div>
          </div>
          <Button asChild>
            <Link to={`/runs/${openRun.id}`}>{t('catalog.continue')} <ArrowRight className="h-4 w-4" /></Link>
          </Button>
        </div>
      )}

      {error && <p className="rounded-2xl bg-destructive/10 px-4 py-2.5 text-sm font-medium text-destructive">{error}</p>}
      {!data && !error && <div className="grid place-items-center py-16"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>}

      {data && s && s.completed === 0 && <EmptyState hasOpenRun={Boolean(openRun)} />}

      {data && s && s.completed > 0 && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
            <Stat Icon={BookOpenCheck} label={t('growth.stats.completed')} value={s.completed} />
            <Stat Icon={Activity} label={t('growth.stats.avgScore')} value={round(s.avg_score)} />
            <Stat Icon={Trophy} label={t('growth.stats.bestScore')} value={round(s.best_score)} />
            <Stat Icon={Clock} label={t('growth.stats.onTime')} value={s.on_time_rate === null ? '—' : `${Math.round(s.on_time_rate)}%`} />
            <Stat Icon={Award} label={t('growth.stats.certificates')} value={s.certificates} accent />
          </div>

          <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
            <div className="min-w-0 space-y-6">
              <ScoreSection data={data} />
              <CompetencySection items={data.competencies} />
            </div>
            <aside className="min-w-0 space-y-6">
              <FocusSection data={data} />
              <Recommendations items={data.recommendations} />
              <Sectors data={data} />
            </aside>
          </div>
        </>
      )}

      {data && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <RecentRuns runs={runs} />
          {can('join_university') && <MyUniversityCard />}
        </div>
      )}
    </div>
  )
}

function Section({ Icon, title, hint, children, className }: {
  Icon: LucideIcon
  title: string
  hint?: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <section className={cn('glass animate-rise space-y-4 rounded-3xl p-5', className)}>
      <div className="flex items-start gap-3">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-primary/12 text-primary"><Icon className="h-4.5 w-4.5" /></span>
        <div className="min-w-0">
          <h2 className="font-bold leading-tight">{title}</h2>
          {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
        </div>
      </div>
      {children}
    </section>
  )
}

function EmptyState({ hasOpenRun }: { hasOpenRun: boolean }) {
  const { t } = useTranslation()
  return (
    <div className="glass-strong animate-rise relative overflow-hidden rounded-3xl p-8 sm:p-10">
      <TrendingUp className="absolute -bottom-10 -right-6 h-56 w-56 text-primary/10" aria-hidden />
      <div className="relative max-w-xl space-y-3">
        <h2 className="text-2xl font-extrabold tracking-tight">{t('growth.empty.title')}</h2>
        <p className="text-muted-foreground">{t(hasOpenRun ? 'growth.empty.bodyOpen' : 'growth.empty.body')}</p>
        {!hasOpenRun && (
          <Button asChild className="mt-2">
            <Link to="/simulations">{t('growth.empty.cta')} <ArrowRight className="h-4 w-4" /></Link>
          </Button>
        )}
      </div>
    </div>
  )
}

function ScoreSection({ data }: { data: StudentAnalytics }) {
  const { t } = useTranslation()
  const points: ChartPoint[] = data.timeline
    .filter((p) => p.overall_score !== null)
    .map((p) => ({ id: p.run_id, title: p.scenario_title, date: p.completed_at, score: p.overall_score as number }))
  return (
    <Section Icon={Activity} title={t('growth.chart.title')} hint={t('growth.chart.hint')}>
      {points.length ? <ScoreChart points={points} label={t('growth.chart.title')} /> : <p className="text-sm text-muted-foreground">{t('growth.chart.none')}</p>}
      {points.length === 1 && <p className="text-xs text-muted-foreground">{t('growth.chart.single')}</p>}
    </Section>
  )
}

function DeltaBadge({ c }: { c: CompetencyTrend }) {
  const { t } = useTranslation()
  const { Icon, tone } = TREND[c.trend]
  const text = c.delta === null ? t('growth.trend.new') : `${c.delta > 0 ? '+' : ''}${Math.round(c.delta)}`
  return (
    <span title={t(`growth.trend.${c.trend}`)}
      className={cn('inline-flex w-16 shrink-0 items-center justify-center gap-1 rounded-full px-2 py-0.5 text-xs font-bold tabular-nums', tone)}>
      <Icon className="h-3 w-3" /> {text}
    </span>
  )
}

function CompetencySection({ items }: { items: CompetencyTrend[] }) {
  const { t } = useTranslation()
  return (
    <Section Icon={Target} title={t('growth.competencies.title')} hint={t('growth.competencies.hint')}>
      <ul className="divide-y divide-border/60">
        {items.map((c) => (
          <li key={c.key} className="flex items-center gap-3 py-2.5">
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold">{t(`competency.${c.key}`)}</p>
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-muted">
                <div className="bg-brand h-full rounded-full transition-[width] duration-700" style={{ width: `${Math.min(100, c.current)}%` }} />
              </div>
            </div>
            <Sparkline values={c.values} className="hidden sm:block" />
            <span className="w-9 shrink-0 text-right text-lg font-extrabold tabular-nums">{Math.round(c.current)}</span>
            <DeltaBadge c={c} />
          </li>
        ))}
      </ul>
    </Section>
  )
}

function FocusSection({ data }: { data: StudentAnalytics }) {
  const { t } = useTranslation()
  if (!data.focus.length && !data.improvements.length) return null
  return (
    <Section Icon={Target} title={t('growth.focus.title')} hint={t('growth.focus.hint')}>
      <div className="grid gap-2">
        {data.focus.map((f) => {
          const { Icon, tone } = TREND[f.trend]
          return (
            <div key={f.key} className="flex items-center gap-3 rounded-2xl border bg-background/40 px-3 py-2.5">
              <span className="min-w-0 flex-1 truncate text-sm font-semibold">{t(`competency.${f.key}`)}</span>
              <span className={cn('inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold', tone)}>
                <Icon className="h-3 w-3" /> {t(`growth.trend.${f.trend}`)}
              </span>
              <span className="text-lg font-extrabold tabular-nums">{Math.round(f.current)}</span>
            </div>
          )
        })}
      </div>
      {data.improvements.length > 0 && (
        <div className="space-y-2">
          <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            <Sparkles className="h-3.5 w-3.5 text-primary" /> {t('growth.focus.ai')}
          </p>
          <ul className="space-y-1.5 text-sm">
            {data.improvements.map((x) => (
              <li key={x} className="flex gap-2"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />{x}</li>
            ))}
          </ul>
        </div>
      )}
    </Section>
  )
}

function Recommendations({ items }: { items: Recommendation[] }) {
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
    <Section Icon={Play} title={t('growth.recs.title')} hint={t('growth.recs.hint')}>
      {!items.length && (
        <p className="text-sm text-muted-foreground">
          {t('growth.recs.none')}{' '}
          <Link to="/simulations" className="font-semibold text-primary hover:underline">{t('growth.recs.catalog')}</Link>
        </p>
      )}
      <ul className="space-y-3">
        {items.map((r) => {
          const art = SECTOR_ART[r.sector]
          return (
            <li key={r.scenario_id} className="overflow-hidden rounded-2xl border bg-background/40">
              <div className={cn('flex items-center gap-3 bg-gradient-to-br p-3', art.glow)}>
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-background/60"><art.Icon className="h-4.5 w-4.5 text-foreground/70" /></span>
                <div className="min-w-0">
                  <p className="truncate text-sm font-bold">{r.title}</p>
                  <p className="flex items-center gap-1 truncate text-xs text-muted-foreground">
                    <Briefcase className="h-3 w-3" /> {r.company_name} · <CalendarDays className="h-3 w-3" /> {t('catalog.days', { count: r.duration_days })}
                  </p>
                </div>
              </div>
              <div className="flex items-end gap-2 p-3">
                <div className="flex min-w-0 flex-1 flex-wrap gap-1.5">
                  {Object.entries(r.practices).map(([k, n]) => (
                    <span key={k} className="rounded-full bg-primary/12 px-2 py-0.5 text-[11px] font-semibold text-primary">
                      {t(`competency.${k}`)} · {t('growth.recs.tasks', { count: n })}
                    </span>
                  ))}
                </div>
                <Button size="sm" className="shrink-0" disabled={starting !== null} onClick={() => start(r.scenario_id)}>
                  {starting === r.scenario_id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />} {t('growth.recs.start')}
                </Button>
              </div>
            </li>
          )
        })}
      </ul>
      {error && <p className="text-sm text-destructive" role="alert">{error}</p>}
    </Section>
  )
}

function Sectors({ data }: { data: StudentAnalytics }) {
  const { t } = useTranslation()
  return (
    <Section Icon={Briefcase} title={t('growth.sectors.title')}>
      <ul className="space-y-2">
        {data.sectors.map((x) => {
          const art = SECTOR_ART[x.sector]
          return (
            <li key={x.sector} className="flex items-center gap-3 text-sm">
              <span className={cn('grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-gradient-to-br', art.glow)}><art.Icon className="h-4 w-4 text-foreground/70" /></span>
              <span className="min-w-0 flex-1 truncate font-semibold">{t(`catalog.sector.${x.sector}`)}</span>
              <span className="text-xs text-muted-foreground">{t('growth.sectors.runs', { count: x.runs })}</span>
              <span className="w-8 text-right font-bold tabular-nums">{round(x.avg_score)}</span>
            </li>
          )
        })}
      </ul>
    </Section>
  )
}

function RecentRuns({ runs }: { runs: RunSummary[] }) {
  const { t } = useTranslation()
  return (
    <Section Icon={Clock} title={t('dashboard.recentActivity')}>
      {runs.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t('dashboard.noActivity')}</p>
      ) : (
        <ul className="divide-y divide-border/60 text-sm">
          {runs.slice(0, 5).map((r) => {
            const open = OPEN.includes(r.status)
            return (
              <li key={r.id}>
                <Link to={open ? `/runs/${r.id}` : `/runs/${r.id}/report`} className="flex items-center justify-between gap-3 py-2.5 hover:text-primary">
                  <span className="min-w-0">
                    <span className="block truncate font-semibold">{r.scenario.title}</span>
                    <span className="block text-xs text-muted-foreground">{formatDateTime(r.start_at)}</span>
                  </span>
                  <span className={cn('shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold',
                    open ? 'bg-primary/12 text-primary' : r.status === 'completed' ? 'bg-success/12 text-success' : 'bg-muted text-muted-foreground')}>
                    {t(`run.status.${r.status}`)}
                  </span>
                </Link>
              </li>
            )
          })}
        </ul>
      )}
    </Section>
  )
}
