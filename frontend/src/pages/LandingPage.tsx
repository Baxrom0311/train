import { useEffect, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import {
  ArrowRight, Award, BadgeCheck, Bot, Briefcase, Building2, CalendarClock, Check, ChevronDown, ChevronRight, Clock,
  GraduationCap, Handshake, Layers, MousePointerClick, School, Sparkles, X, type LucideIcon,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Logo } from '@/components/Navbar'
import DeskPreview from '@/components/landing/DeskPreview'
import FeatureBento from '@/components/landing/FeatureBento'
import Reveal from '@/components/landing/Reveal'
import '@/components/landing/landing.css'
import CertificateSheet from '@/components/credentials/CertificateSheet'
import { ScoreRing } from '@/components/score'
import { SECTOR_ART } from '@/components/sectorArt'
import { VerifyForm } from '@/pages/CertificatePage'
import { api } from '@/lib/api'
import { SECTORS, type CertificatePublic, type Sector, type Showcase, type ShowcaseScenario } from '@/lib/types'
import { cn } from '@/lib/utils'

// `completed_runs` bundan kam bo'lsa raqam ko'rsatilmaydi (§14.2)
const MIN_RUNS_SHOWN = 100
const STEPS: { key: string; Icon: LucideIcon }[] = [
  { key: 'pick', Icon: MousePointerClick },
  { key: 'work', Icon: CalendarClock },
  { key: 'review', Icon: Bot },
  { key: 'certificate', Icon: Award },
  { key: 'offers', Icon: Handshake },
]
const FAQ = ['free', 'time', 'companies', 'grading', 'verify', 'privacy']

/** Kirmagan mehmon uchun ochiq bosh sahifa (CONTRACT.md §14). */
export default function LandingPage() {
  const { t } = useTranslation()
  const [data, setData] = useState<Showcase | null>(null)

  useEffect(() => {
    api<Showcase>('/showcase').then(setData).catch(() => setData({ stats: { scenarios: 0, sectors: 0, completed_runs: 0 }, scenarios: [] }))
  }, [])

  const scenarios = data?.scenarios ?? []
  // hero'da har sohadan bittadan, 1 kunliklar oldin
  const featured = SECTORS.flatMap((sector) => {
    const pick = [...scenarios].filter((s) => s.sector === sector).sort((a, b) => a.duration_days - b.duration_days)[0]
    return pick ? [pick] : []
  })
  const mentorName = scenarios.find((s) => s.mentor)?.mentor?.name

  return (
    <div className="overflow-x-clip">
      <Hero scenarios={featured} />
      {scenarios.length > 0 && <Marquee scenarios={scenarios} />}
      {data && <Numbers stats={data.stats} />}
      <Section id="features" eyebrow={t('landing.features.eyebrow')} title={t('landing.features.title')} subtitle={t('landing.features.subtitle')}>
        <FeatureBento mentorName={mentorName} />
      </Section>
      <Sectors scenarios={scenarios} />
      <HowItWorks />
      <Compare />
      {featured[0] && <CertificateDemo scenario={featured[0]} />}
      <Audience />
      <Faq />
      <CallToAction />
      <Footer />
    </div>
  )
}

function Section({ id, eyebrow, title, subtitle, children, className }: {
  id?: string
  eyebrow: string
  title: string
  subtitle?: string
  children: ReactNode
  className?: string
}) {
  return (
    <section id={id} className={cn('mx-auto max-w-6xl scroll-mt-24 px-4 py-16 sm:py-24', className)}>
      <Reveal className="mx-auto mb-10 max-w-2xl text-center sm:mb-14">
        <Eyebrow>{eyebrow}</Eyebrow>
        <h2 className="mt-4 text-3xl font-extrabold tracking-tight text-balance sm:text-5xl">{title}</h2>
        {subtitle && <p className="mt-4 text-pretty text-muted-foreground sm:text-lg">{subtitle}</p>}
      </Reveal>
      {children}
    </section>
  )
}

function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <p className="inline-flex items-center gap-2 rounded-full border border-primary/25 bg-primary/8 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.22em] text-primary">
      <span className="bg-brand h-1.5 w-1.5 rounded-full" /> {children}
    </p>
  )
}

function Hero({ scenarios }: { scenarios: ShowcaseScenario[] }) {
  const { t } = useTranslation()
  return (
    <section className="relative">
      {/* hero'ning o'z yorug'ligi va to'ri — umumiy Backdrop ustida */}
      <div aria-hidden className="landing-grid pointer-events-none absolute inset-x-0 -top-24 h-[44rem]" />
      <div aria-hidden className="pointer-events-none absolute left-1/2 top-0 h-[30rem] w-[min(60rem,120vw)] -translate-x-1/2 rounded-full opacity-30 blur-3xl dark:opacity-25"
        style={{ background: 'radial-gradient(closest-side, hsl(var(--primary)), transparent)' }} />

      <div className="relative mx-auto grid max-w-6xl items-center gap-20 px-4 pb-12 pt-10 sm:pt-20 lg:grid-cols-[1.15fr_1fr] lg:gap-14 lg:pb-20">
        <div className="animate-rise min-w-0 space-y-7">
          <span className="glass inline-flex items-center gap-2 rounded-full py-1 pl-1.5 pr-3.5 text-xs font-semibold">
            <span className="bg-brand inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-primary-foreground">
              <Sparkles className="h-3 w-3" /> AI
            </span>
            {t('landing.hero.badge')}
          </span>
          <h1 className="text-[2.6rem] font-extrabold leading-[1.05] tracking-tight text-balance sm:text-6xl lg:text-[4rem]">
            {t('landing.hero.titleStart')}{' '}
            {/* marker chizig'i qatordan qatorga ko'chganda ham har qatorda chiziladi */}
            <span className="bg-[linear-gradient(transparent_68%,hsl(var(--primary)/0.16)_68%)] [box-decoration-break:clone] [-webkit-box-decoration-break:clone]">
              <span className="text-brand">{t('landing.hero.titleAccent')}</span>
            </span>
          </h1>
          <p className="max-w-xl text-pretty text-lg leading-relaxed text-muted-foreground">{t('landing.hero.subtitle')}</p>
          <div className="flex flex-wrap gap-3">
            <Button size="lg" asChild className="group">
              <Link to="/register">
                {t('landing.hero.start')} <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <a href="#audience">{t('landing.hero.forOrgs')}</a>
            </Button>
          </div>
          <ul className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted-foreground">
            {['free', 'realTime', 'certificate'].map((k) => (
              <li key={k} className="flex items-center gap-1.5"><BadgeCheck className="h-4 w-4 text-primary" /> {t(`landing.hero.point.${k}`)}</li>
            ))}
          </ul>
        </div>

        <div className="animate-rise relative mx-auto w-full min-w-0 max-w-md lg:max-w-none" style={{ animationDelay: '120ms' }}>
          <div aria-hidden className="bg-brand absolute -inset-4 rounded-[2.5rem] opacity-25 blur-3xl dark:opacity-30" />
          <div className="landing-tilt relative">
            {scenarios.length > 0 ? <DeskPreview scenarios={scenarios} /> : <div className="glass-strong h-[26rem] rounded-3xl" />}
          </div>
          <HeroChips />
        </div>
      </div>
    </section>
  )
}

/** Ish stoli atrofidagi suzuvchi namunalar: baho, dedlayn, taklif (bezak, ekran o'quvchiga yashirin). */
function HeroChips() {
  const { t } = useTranslation()
  return (
    <div aria-hidden className="pointer-events-none">
      <div className="landing-float glass-strong absolute -top-16 left-4 hidden items-center gap-2.5 rounded-2xl p-2.5 pr-4 sm:flex lg:-top-10 lg:left-[38%]">
        <ScoreRing value={86} size={44} />
        <div className="text-xs">
          <p className="text-muted-foreground">{t('landing.hero.chip.scoreLabel')}</p>
          <p className="font-bold">{t('landing.hero.chip.score')}</p>
        </div>
      </div>
      <div className="landing-float glass-strong absolute -bottom-8 -right-3 hidden items-center gap-2.5 rounded-2xl p-2.5 pr-4 sm:flex lg:-right-6"
        style={{ animationDelay: '-2s' }}>
        <span className="relative grid h-9 w-9 place-items-center rounded-xl bg-destructive/12 text-destructive">
          <span className="landing-ping absolute inset-0 rounded-xl bg-destructive/20" />
          <Clock className="relative h-4 w-4" />
        </span>
        <div className="text-xs">
          <p className="text-muted-foreground">{t('landing.hero.chip.deadlineLabel')}</p>
          <p className="font-bold">{t('landing.hero.chip.deadline')}</p>
        </div>
      </div>
      <div className="landing-float glass-strong absolute -bottom-8 -left-3 hidden items-center gap-2.5 rounded-2xl p-2.5 pr-4 sm:flex lg:-left-6"
        style={{ animationDelay: '-4s' }}>
        <span className="grid h-9 w-9 place-items-center rounded-xl bg-success/15 text-success"><Handshake className="h-4 w-4" /></span>
        <div className="text-xs">
          <p className="text-muted-foreground">{t('landing.hero.chip.offerLabel')}</p>
          <p className="font-bold">{t('landing.hero.chip.offer')}</p>
        </div>
      </div>
    </div>
  )
}

/** Ssenariylar lentasi: sarlavha va fictional kompaniya nomi (showcase'dan). */
function Marquee({ scenarios }: { scenarios: ShowcaseScenario[] }) {
  // juda qisqa ro'yxat lentani bo'sh qoldirmasin
  const base = scenarios.length < 6 ? [...scenarios, ...scenarios] : scenarios
  return (
    <div aria-hidden className="landing-marquee overflow-hidden py-6">
      <div className="flex w-max gap-3">
        {[...base, ...base].map((s, i) => {
          const art = SECTOR_ART[s.sector]
          return (
            <span key={`${s.slug}-${i}`} className="glass flex shrink-0 items-center gap-2.5 rounded-full py-2 pl-2 pr-4 text-sm">
              <span className="bg-brand grid h-7 w-7 place-items-center rounded-full text-primary-foreground"><art.Icon className="h-3.5 w-3.5" /></span>
              <span className="font-semibold">{s.company_name}</span>
              <span className="max-w-[18rem] truncate text-muted-foreground">{s.title}</span>
            </span>
          )
        })}
      </div>
    </div>
  )
}

function Numbers({ stats }: { stats: Showcase['stats'] }) {
  const { t } = useTranslation()
  const items = [
    { value: String(stats.scenarios), label: t('landing.numbers.scenarios'), Icon: Layers },
    { value: String(stats.sectors), label: t('landing.numbers.sectors'), Icon: Briefcase },
    { value: '09–18', label: t('landing.numbers.workday'), Icon: Clock },
    stats.completed_runs >= MIN_RUNS_SHOWN
      ? { value: String(stats.completed_runs), label: t('landing.numbers.completed'), Icon: Award }
      : { value: '24/7', label: t('landing.numbers.mentor'), Icon: Bot },
  ]
  return (
    <div className="mx-auto max-w-6xl px-4">
      <Reveal className="glass grid grid-cols-2 overflow-hidden rounded-3xl sm:grid-cols-4">
        {items.map(({ value, label, Icon }, i) => (
          <div key={label} className={cn(
            'relative flex flex-col gap-2 p-5 sm:p-6',
            i % 2 === 1 && 'border-l border-border/60',
            i >= 2 && 'border-t border-border/60 sm:border-t-0',
            i === 2 && 'sm:border-l',
          )}>
            <Icon className="h-5 w-5 text-primary" />
            <p className="text-brand text-3xl font-extrabold tabular-nums sm:text-4xl">{value}</p>
            <p className="text-xs leading-snug text-muted-foreground sm:text-sm">{label}</p>
          </div>
        ))}
      </Reveal>
    </div>
  )
}

function Sectors({ scenarios }: { scenarios: ShowcaseScenario[] }) {
  const { t } = useTranslation()
  const bySector = (sector: Sector) => scenarios.filter((s) => s.sector === sector)
  return (
    <Section id="sectors" eyebrow={t('landing.sectors.eyebrow')} title={t('landing.sectors.title')} subtitle={t('landing.sectors.subtitle')}>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {SECTORS.map((sector, i) => {
          const art = SECTOR_ART[sector]
          const items = bySector(sector)
          return (
            <Reveal key={sector} delay={i * 70} className="min-w-0">
              <article className="glass group flex h-full flex-col overflow-hidden rounded-3xl transition-all duration-300 hover:-translate-y-1.5 hover:shadow-[0_24px_60px_-24px_hsl(var(--primary)/0.55)]">
                <div className={cn('relative h-28 bg-gradient-to-br', art.glow)}>
                  <art.Icon aria-hidden className="absolute -bottom-5 -right-3 h-28 w-28 text-foreground/10 transition-transform duration-500 group-hover:-rotate-6 group-hover:scale-110" />
                  <span className="glass-strong absolute left-4 top-4 grid h-11 w-11 place-items-center rounded-2xl text-primary">
                    <art.Icon className="h-5 w-5" />
                  </span>
                  {items.length > 0 && (
                    <span className="glass-strong absolute right-3 top-4 rounded-full px-2 py-0.5 text-[11px] font-bold tabular-nums">
                      {t('landing.sectors.count', { count: items.length })}
                    </span>
                  )}
                </div>
                <div className="flex flex-1 flex-col gap-2 p-4">
                  <h3 className="text-lg font-bold">{t(`catalog.sector.${sector}`)}</h3>
                  <p className="text-sm text-muted-foreground">{t(`landing.sectors.about.${sector}`)}</p>
                  <ul className="mt-auto space-y-1.5 pt-2">
                    {items.slice(0, 2).map((s) => (
                      <li key={s.slug} className="rounded-xl border bg-background/50 px-2.5 py-1.5 text-xs">
                        <p className="line-clamp-2 font-medium">{s.title}</p>
                        <p className="text-muted-foreground">{t('catalog.days', { count: s.duration_days })} · {t('landing.sectors.tasks', { count: s.tasks })}</p>
                      </li>
                    ))}
                    {items.length === 0 && <li className="text-xs italic text-muted-foreground">{t('landing.sectors.soon')}</li>}
                  </ul>
                </div>
              </article>
            </Reveal>
          )
        })}
      </div>
    </Section>
  )
}

function HowItWorks() {
  const { t } = useTranslation()
  return (
    <Section id="how" eyebrow={t('landing.how.eyebrow')} title={t('landing.how.title')} subtitle={t('landing.how.subtitle')}>
      <ol className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {STEPS.map(({ key, Icon }, i) => (
          <li key={key} className={cn('relative min-w-0', i === STEPS.length - 1 && 'sm:col-span-2 lg:col-span-1')}>
            <Reveal delay={i * 90} className="h-full">
              <div className="glass group relative h-full overflow-hidden rounded-3xl p-5">
                <span aria-hidden className="text-brand absolute -right-1 -top-3 select-none text-7xl font-extrabold opacity-15 transition-opacity group-hover:opacity-30">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <span className="bg-brand relative grid h-12 w-12 place-items-center rounded-2xl text-primary-foreground shadow-[0_10px_30px_-12px_hsl(var(--primary)/0.8)]">
                  <Icon className="h-5 w-5" />
                </span>
                <h3 className="relative mt-4 font-bold">{t(`landing.how.${key}.title`)}</h3>
                <p className="relative mt-1 text-sm text-muted-foreground">{t(`landing.how.${key}.body`)}</p>
              </div>
            </Reveal>
            {i < STEPS.length - 1 && (
              <span aria-hidden className="glass-strong absolute -right-4 top-1/2 z-10 hidden h-7 w-7 -translate-y-1/2 place-items-center rounded-full text-primary lg:grid">
                <ChevronRight className="h-4 w-4" />
              </span>
            )}
          </li>
        ))}
      </ol>
    </Section>
  )
}

/** Odatiy onlayn kurs va TryJob: farq bir qarashda. */
function Compare() {
  const { t } = useTranslation()
  const rows = t('landing.compare.rows', { returnObjects: true }) as { course: string; tryjob: string }[]
  return (
    <Section id="compare" eyebrow={t('landing.compare.eyebrow')} title={t('landing.compare.title')} subtitle={t('landing.compare.subtitle')}>
      <div className="mx-auto grid max-w-5xl gap-4 md:grid-cols-2">
        <Reveal>
          <div className="h-full rounded-3xl border border-dashed border-border bg-background/40 p-6">
            <p className="text-sm font-bold uppercase tracking-wider text-muted-foreground">{t('landing.compare.course')}</p>
            <ul className="mt-5 space-y-3.5">
              {rows.map((r) => (
                <li key={r.course} className="flex gap-3 text-sm text-muted-foreground">
                  <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-muted"><X className="h-3 w-3" /></span>
                  {r.course}
                </li>
              ))}
            </ul>
          </div>
        </Reveal>
        <Reveal delay={100}>
          <div className="glass glow-ring relative h-full overflow-hidden rounded-3xl p-6">
            <div aria-hidden className="bg-brand absolute -right-20 -top-20 h-48 w-48 rounded-full opacity-20 blur-3xl" />
            <p className="relative flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-primary">
              <Sparkles className="h-4 w-4" /> TryJob
            </p>
            <ul className="relative mt-5 space-y-3.5">
              {rows.map((r) => (
                <li key={r.tryjob} className="flex gap-3 text-sm font-medium">
                  <span className="bg-brand mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full text-primary-foreground"><Check className="h-3 w-3" /></span>
                  {r.tryjob}
                </li>
              ))}
            </ul>
          </div>
        </Reveal>
      </div>
    </Section>
  )
}

function CertificateDemo({ scenario }: { scenario: ShowcaseScenario }) {
  const { t } = useTranslation()
  // namuna: fictional ism va ssenariyning o'zi; kod hech qaysi sertifikatga tegishli emas
  const sample: CertificatePublic = {
    code: 'TJ-NAMU-NA23',
    status: 'valid',
    holder_name: t('landing.certificate.sampleName'),
    scenario_title: scenario.title,
    company_name: scenario.company_name,
    sector: scenario.sector,
    difficulty: scenario.difficulty,
    duration_days: scenario.duration_days,
    completed_at: new Date().toISOString(),
    issued_at: new Date().toISOString(),
    overall_score: 86,
    competency_scores: { technical: 88, communication: 84, prioritization: 81, initiative: 79 },
    revoked_at: null,
    revoked_reason: null,
  }
  return (
    <Section id="certificate" eyebrow={t('landing.certificate.eyebrow')} title={t('landing.certificate.title')} subtitle={t('landing.certificate.subtitle')}>
      <Reveal className="relative">
        <div aria-hidden className="bg-brand absolute inset-x-10 inset-y-6 rounded-[3rem] opacity-20 blur-3xl" />
        <span className="absolute -top-3 left-1/2 z-10 -translate-x-1/2 rounded-full border bg-background px-3 py-1 text-xs font-bold uppercase tracking-widest text-muted-foreground shadow-sm">
          {t('landing.certificate.sample')}
        </span>
        <div className="pointer-events-none relative select-none" aria-hidden>
          <CertificateSheet cert={sample} />
        </div>
      </Reveal>
      <Reveal className="glass mx-auto mt-8 max-w-xl space-y-3 rounded-3xl p-5 text-center">
        <p className="font-semibold">{t('landing.certificate.verifyTitle')}</p>
        <p className="text-sm text-muted-foreground">{t('landing.certificate.verifyHint')}</p>
        <VerifyForm />
      </Reveal>
    </Section>
  )
}

function Audience() {
  const { t } = useTranslation()
  const cards: { key: string; Icon: LucideIcon; to: string; highlight?: boolean }[] = [
    { key: 'student', Icon: GraduationCap, to: '/register', highlight: true },
    { key: 'company', Icon: Building2, to: '/register?as=company' },
    { key: 'university', Icon: School, to: '/register?as=university' },
  ]
  return (
    <Section id="audience" eyebrow={t('landing.audience.eyebrow')} title={t('landing.audience.title')}>
      <div className="grid gap-4 md:grid-cols-3">
        {cards.map(({ key, Icon, to, highlight }, i) => (
          <Reveal key={key} delay={i * 90}>
            <article className={cn('glass relative flex h-full flex-col overflow-hidden rounded-3xl p-6', highlight && 'glow-ring')}>
              {highlight && <div aria-hidden className="bg-brand absolute inset-x-0 top-0 h-1" />}
              <span className={cn('grid h-12 w-12 place-items-center rounded-2xl', highlight ? 'bg-brand text-primary-foreground' : 'bg-primary/12 text-primary')}>
                <Icon className="h-6 w-6" />
              </span>
              <h3 className="mt-4 text-xl font-bold">{t(`landing.audience.${key}.title`)}</h3>
              <p className={cn('mt-1 font-semibold', highlight ? 'text-brand text-2xl font-extrabold' : 'text-sm text-primary')}>
                {t(`landing.audience.${key}.price`)}
              </p>
              <ul className="mt-5 flex-1 space-y-2.5 text-sm">
                {(t(`landing.audience.${key}.points`, { returnObjects: true }) as string[]).map((p) => (
                  <li key={p} className="flex gap-2"><BadgeCheck className="mt-0.5 h-4 w-4 shrink-0 text-primary" /> {p}</li>
                ))}
              </ul>
              <Button className="mt-6 w-full" variant={highlight ? 'default' : 'outline'} asChild>
                <Link to={to}>{t(`landing.audience.${key}.cta`)}</Link>
              </Button>
            </article>
          </Reveal>
        ))}
      </div>
    </Section>
  )
}

function Faq() {
  const { t } = useTranslation()
  return (
    <section id="faq" className="mx-auto grid max-w-6xl scroll-mt-24 gap-10 px-4 py-16 sm:py-24 lg:grid-cols-[1fr_1.6fr] lg:gap-16">
      <Reveal className="lg:sticky lg:top-28 lg:self-start">
        <Eyebrow>{t('landing.faq.eyebrow')}</Eyebrow>
        <h2 className="mt-4 text-3xl font-extrabold tracking-tight text-balance sm:text-5xl">{t('landing.faq.title')}</h2>
        <p className="mt-4 text-muted-foreground">{t('landing.faq.subtitle')}</p>
        <Button className="mt-6" variant="outline" asChild>
          <Link to="/register">{t('landing.hero.start')} <ArrowRight className="h-4 w-4" /></Link>
        </Button>
      </Reveal>
      <div className="space-y-3">
        {FAQ.map((key, i) => (
          <Reveal key={key} delay={i * 50}>
            <details className="glass group rounded-2xl px-5 py-4 transition-shadow open:pb-5 open:shadow-[0_16px_40px_-20px_hsl(var(--primary)/0.45)]">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-semibold [&::-webkit-details-marker]:hidden">
                {t(`landing.faq.${key}.q`)}
                <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-primary/10 text-primary transition-transform group-open:rotate-180">
                  <ChevronDown className="h-4 w-4" />
                </span>
              </summary>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{t(`landing.faq.${key}.a`)}</p>
            </details>
          </Reveal>
        ))}
      </div>
    </section>
  )
}

function CallToAction() {
  const { t } = useTranslation()
  return (
    <div className="mx-auto max-w-6xl px-4 pb-16">
      <Reveal className="bg-brand relative overflow-hidden rounded-[2rem] px-6 py-14 text-center text-primary-foreground sm:px-12 sm:py-20">
        <div aria-hidden className="absolute inset-0 opacity-20"
          style={{ backgroundImage: 'radial-gradient(hsl(0 0% 100% / 0.6) 1px, transparent 1px)', backgroundSize: '18px 18px' }} />
        <div aria-hidden className="animate-drift-1 absolute -left-20 -top-24 h-72 w-72 rounded-full bg-white/25 blur-3xl" />
        <div aria-hidden className="animate-drift-2 absolute -bottom-28 -right-16 h-80 w-80 rounded-full blur-3xl"
          style={{ background: 'hsl(var(--glow-3) / 0.7)' }} />
        <div className="relative mx-auto max-w-2xl space-y-5">
          <h2 className="text-3xl font-extrabold tracking-tight text-balance sm:text-5xl">{t('landing.cta.title')}</h2>
          <p className="mx-auto max-w-xl text-lg opacity-90">{t('landing.cta.subtitle')}</p>
          <div className="flex flex-wrap justify-center gap-3 pt-2">
            <Button size="lg" variant="secondary" asChild className="shadow-xl">
              <Link to="/register">{t('landing.hero.start')} <ArrowRight className="h-4 w-4" /></Link>
            </Button>
            <Button size="lg" variant="ghost" asChild className="text-primary-foreground ring-1 ring-white/40 hover:bg-white/15 hover:text-primary-foreground">
              <Link to="/login">{t('nav.login')}</Link>
            </Button>
          </div>
        </div>
      </Reveal>
    </div>
  )
}

function Footer() {
  const { t } = useTranslation()
  const year = new Date().getFullYear()
  return (
    <footer className="border-t border-border/60">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-2">
          <Logo />
          <p className="max-w-md text-xs">{t('landing.footer.note')}</p>
        </div>
        <nav className="flex flex-wrap gap-x-5 gap-y-2">
          <a href="#features" className="hover:text-foreground">{t('landing.footer.features')}</a>
          <a href="#how" className="hover:text-foreground">{t('landing.footer.how')}</a>
          <a href="#certificate" className="hover:text-foreground">{t('landing.footer.verify')}</a>
          <a href="#faq" className="hover:text-foreground">{t('landing.footer.faq')}</a>
          <Link to="/login" className="hover:text-foreground">{t('nav.login')}</Link>
        </nav>
        <p className="text-xs">© {year} TryJob</p>
      </div>
    </footer>
  )
}
