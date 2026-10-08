import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import {
  BarChart3, BellRing, Bot, Briefcase, Check, ClipboardList, Clock, Code2, Gauge, Handshake, Mic, X, type LucideIcon,
} from 'lucide-react'
import Reveal from '@/components/landing/Reveal'
import { CompetencyBars, ScoreRing } from '@/components/score'
import { cn } from '@/lib/utils'

/*
 * "Imkoniyatlar" bo'limi (CONTRACT.md §14.2): platformaning asosiy qismlari kichik
 * interfeys namunalari bilan. Hamma raqam va matn — namuna, real foydalanuvchi ma'lumoti emas.
 */

// grafik namunasi: 6 ta ssenariy bo'yicha umumiy ball
const TREND = [58, 63, 61, 70, 74, 81]

export default function FeatureBento({ mentorName }: { mentorName?: string }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-6">
      <Tile k="mentor" Icon={Bot} className="md:col-span-2 lg:col-span-4" delay={0}><MentorChat name={mentorName} /></Tile>
      <Tile k="rubric" Icon={Gauge} className="lg:col-span-2" delay={80}><Rubric /></Tile>
      <Tile k="interview" Icon={Mic} className="lg:col-span-2" delay={0}><Interview /></Tile>
      <Tile k="vacancy" Icon={Briefcase} className="lg:col-span-2" delay={80}><Vacancy /></Tile>
      <Tile k="analytics" Icon={BarChart3} className="lg:col-span-2" delay={160}><Trend /></Tile>
      <Tile k="alerts" Icon={BellRing} className="lg:col-span-3" delay={0}><Alerts /></Tile>
      <Tile k="code" Icon={Code2} className="lg:col-span-3" delay={80}><CodeChecks /></Tile>
    </div>
  )
}

function Tile({ k, Icon, className, delay, children }: {
  k: string
  Icon: LucideIcon
  className?: string
  delay: number
  children: ReactNode
}) {
  const { t } = useTranslation()
  return (
    <Reveal delay={delay} className={cn('min-w-0', className)}>
      <article className="glass group relative flex h-full flex-col overflow-hidden rounded-3xl p-5 sm:p-6">
        {/* burchakdagi yorug'lik: kursor olib borilganda kuchayadi */}
        <div aria-hidden className="bg-brand pointer-events-none absolute -right-16 -top-16 h-40 w-40 rounded-full opacity-15 blur-3xl transition-opacity duration-500 group-hover:opacity-35" />
        <div className="relative flex items-start gap-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary/12 text-primary"><Icon className="h-5 w-5" /></span>
          <div className="min-w-0">
            <h3 className="font-bold">{t(`landing.features.${k}.title`)}</h3>
            <p className="mt-0.5 text-sm text-muted-foreground">{t(`landing.features.${k}.body`)}</p>
          </div>
        </div>
        <div aria-hidden className="relative mt-5 flex flex-1 flex-col justify-end">{children}</div>
      </article>
    </Reveal>
  )
}

function MentorChat({ name }: { name?: string }) {
  const { t } = useTranslation()
  const mentor = name ?? t('landing.features.mentor.name')
  return (
    <div className="glass-strong space-y-3 rounded-2xl p-4 text-sm">
      <div className="flex justify-end">
        <p className="bg-brand max-w-[85%] rounded-2xl rounded-br-md px-3.5 py-2 text-primary-foreground">
          {t('landing.features.mentor.student')}
        </p>
      </div>
      <div className="flex items-end gap-2">
        <span className="bg-brand grid h-7 w-7 shrink-0 place-items-center rounded-full text-xs font-bold text-primary-foreground">
          {mentor.slice(0, 1)}
        </span>
        <div className="max-w-[85%]">
          <p className="mb-1 text-xs text-muted-foreground"><b className="text-foreground">{mentor}</b> · {t('landing.desk.mentor')}</p>
          <p className="rounded-2xl rounded-bl-md border bg-background/70 px-3.5 py-2">{t('landing.features.mentor.reply')}</p>
        </div>
      </div>
      <div className="flex items-center gap-2 pl-9 text-xs text-muted-foreground">
        <span className="flex gap-1">
          {[0, 150, 300].map((d) => <span key={d} className="landing-dot h-1.5 w-1.5 rounded-full bg-primary" style={{ animationDelay: `${d}ms` }} />)}
        </span>
        {t('landing.features.mentor.typing', { name: mentor })}
      </div>
    </div>
  )
}

function Rubric() {
  const { t } = useTranslation()
  return (
    <div className="glass-strong space-y-4 rounded-2xl p-4">
      <div className="flex items-center gap-3">
        <ScoreRing value={86} size={60} />
        <div className="min-w-0">
          <p className="text-xs text-muted-foreground">{t('landing.features.rubric.attempt')}</p>
          <p className="font-semibold">{t('landing.features.rubric.verdict')}</p>
        </div>
      </div>
      <CompetencyBars compact scores={{ technical: 88, communication: 84, prioritization: 79 }} />
    </div>
  )
}

function Interview() {
  const { t } = useTranslation()
  return (
    <div className="glass-strong space-y-3 rounded-2xl p-4 text-sm">
      <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground">
        <span>{t('landing.features.interview.progress', { n: 2, total: 5 })}</span>
        <span className="flex items-center gap-1 text-primary"><Clock className="h-3.5 w-3.5" /> 03:12</span>
      </div>
      <div className="flex gap-1">
        {[0, 1, 2, 3, 4].map((i) => <span key={i} className={cn('h-1 flex-1 rounded-full', i < 2 ? 'bg-primary' : 'bg-muted')} />)}
      </div>
      <p className="font-medium leading-snug">{t('landing.features.interview.question')}</p>
      <span className="inline-flex rounded-full border border-primary/30 bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary">
        {t('landing.features.interview.followUp')}
      </span>
    </div>
  )
}

function Vacancy() {
  const { t } = useTranslation()
  const reqs = [
    { key: 'technical', need: 70, have: 82 },
    { key: 'communication', need: 65, have: 74 },
    { key: 'prioritization', need: 75, have: 68 },
  ]
  return (
    <div className="glass-strong space-y-3 rounded-2xl p-4 text-sm">
      <div className="flex items-center gap-3">
        <ScoreRing value={78} size={52} />
        <p className="font-semibold leading-snug">{t('landing.features.vacancy.match')}</p>
      </div>
      <ul className="space-y-1.5 text-xs">
        {reqs.map(({ key, need, have }) => {
          const ok = have >= need
          return (
            <li key={key} className="flex items-center gap-2">
              <span className={cn('grid h-4 w-4 shrink-0 place-items-center rounded-full', ok ? 'bg-success/15 text-success' : 'bg-destructive/15 text-destructive')}>
                {ok ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
              </span>
              <span className="min-w-0 flex-1 truncate">{t(`competency.${key}`)} ≥ {need}</span>
              <span className={cn('font-semibold tabular-nums', !ok && 'text-destructive')}>{have}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function Trend() {
  const { t } = useTranslation()
  const w = 240
  const h = 92
  const min = 50
  const max = 90
  const pts = TREND.map((v, i) => [(i / (TREND.length - 1)) * w, h - ((v - min) / (max - min)) * h] as const)
  const line = pts.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  const [lx, ly] = pts[pts.length - 1]
  return (
    <div className="glass-strong rounded-2xl p-4">
      <div className="mb-2 flex items-baseline justify-between gap-2">
        <p className="text-2xl font-extrabold tabular-nums">{TREND[TREND.length - 1]}</p>
        <span className="rounded-full bg-success/15 px-2 py-0.5 text-xs font-bold text-success">
          {t('landing.features.analytics.growth', { count: TREND[TREND.length - 1] - TREND[0] })}
        </span>
      </div>
      <svg viewBox={`-4 -6 ${w + 8} ${h + 12}`} className="h-24 w-full overflow-visible" preserveAspectRatio="none">
        <defs>
          <linearGradient id="landing-trend" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.35" />
            <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={`${line} L${w},${h} L0,${h} Z`} fill="url(#landing-trend)" />
        <path d={line} fill="none" stroke="hsl(var(--primary))" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
        <circle cx={lx} cy={ly} r="4" fill="hsl(var(--primary))" stroke="hsl(var(--background))" strokeWidth="2" vectorEffect="non-scaling-stroke" />
      </svg>
      <p className="mt-1 text-xs text-muted-foreground">{t('landing.features.analytics.caption', { count: TREND.length })}</p>
    </div>
  )
}

function Alerts() {
  const { t } = useTranslation()
  const items: { key: string; Icon: LucideIcon; tone: string }[] = [
    { key: 'task', Icon: ClipboardList, tone: 'bg-primary/12 text-primary' },
    { key: 'deadline', Icon: Clock, tone: 'bg-destructive/12 text-destructive' },
    { key: 'offer', Icon: Handshake, tone: 'bg-success/15 text-success' },
  ]
  return (
    <ul className="space-y-2">
      {items.map(({ key, Icon, tone }, i) => (
        <li key={key} className="glass-strong flex items-center gap-3 rounded-2xl px-3.5 py-2.5 text-sm"
          style={{ marginInline: `${(items.length - 1 - i) * 10}px`, opacity: 1 - (items.length - 1 - i) * 0.12 }}>
          <span className={cn('grid h-8 w-8 shrink-0 place-items-center rounded-xl', tone)}><Icon className="h-4 w-4" /></span>
          <span className="min-w-0 flex-1">
            <span className="block truncate font-semibold">{t(`landing.features.alerts.${key}.title`)}</span>
            <span className="block truncate text-xs text-muted-foreground">{t(`landing.features.alerts.${key}.body`)}</span>
          </span>
          <span className="shrink-0 text-[11px] text-muted-foreground">{t(`landing.features.alerts.${key}.when`)}</span>
        </li>
      ))}
    </ul>
  )
}

function CodeChecks() {
  const { t } = useTranslation()
  const tests: [string, boolean][] = [
    ['test_empty_cart', true],
    ['test_promo_code_once', true],
    ['test_total_rounding', false],
  ]
  // terminal har ikki mavzuda ham to'q
  return (
    <div className="overflow-hidden rounded-2xl border border-white/10 bg-[hsl(230_40%_8%)] font-mono text-xs text-slate-200 shadow-inner">
      <div className="flex items-center gap-1.5 border-b border-white/10 px-3.5 py-2">
        {['bg-rose-400/80', 'bg-slate-400/60', 'bg-emerald-400/80'].map((c) => <span key={c} className={cn('h-2.5 w-2.5 rounded-full', c)} />)}
        <span className="ml-2 text-slate-400">{t('landing.features.code.sandbox')}</span>
      </div>
      <div className="space-y-1 p-3.5">
        <p className="text-slate-400">$ pytest checks/</p>
        {tests.map(([name, ok]) => (
          <p key={name} className="flex items-center gap-2">
            <span className={ok ? 'text-emerald-400' : 'text-rose-400'}>{ok ? '✓' : '✗'}</span>
            <span className="truncate">{name}</span>
          </p>
        ))}
        <p className="pt-1 text-emerald-300">{t('landing.features.code.summary', { passed: 7, total: 8 })}</p>
      </div>
    </div>
  )
}
