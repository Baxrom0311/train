import { useEffect, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import {
  ArrowRight, Award, BadgeCheck, Bot, Briefcase, Building2, CalendarClock, ChevronDown, Clock, GraduationCap,
  Handshake, Layers, MousePointerClick, School, Sparkles, type LucideIcon,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Logo } from '@/components/Navbar'
import DeskPreview from '@/components/landing/DeskPreview'
import CertificateSheet from '@/components/credentials/CertificateSheet'
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

  return (
    <div className="overflow-x-clip">
      <Hero scenarios={featured} />
      {data && <Numbers stats={data.stats} />}
      <Sectors scenarios={scenarios} />
      <HowItWorks />
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
    <section id={id} className={cn('mx-auto max-w-6xl scroll-mt-24 px-4 py-14 sm:py-20', className)}>
      <div className="mx-auto mb-10 max-w-2xl text-center">
        <p className="text-xs font-bold uppercase tracking-[0.25em] text-primary">{eyebrow}</p>
        <h2 className="mt-3 text-3xl font-extrabold tracking-tight sm:text-4xl">{title}</h2>
        {subtitle && <p className="mt-3 text-muted-foreground">{subtitle}</p>}
      </div>
      {children}
    </section>
  )
}

function Hero({ scenarios }: { scenarios: ShowcaseScenario[] }) {
  const { t } = useTranslation()
  return (
    <section className="mx-auto grid max-w-6xl items-center gap-10 px-4 pb-10 pt-10 sm:pt-16 lg:grid-cols-[1.1fr_1fr] lg:gap-14">
      <div className="animate-rise min-w-0 space-y-6">
        <span className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
          <Sparkles className="h-3.5 w-3.5" /> {t('landing.hero.badge')}
        </span>
        <h1 className="text-4xl font-extrabold leading-[1.08] tracking-tight sm:text-6xl">
          {t('landing.hero.titleStart')} <span className="text-brand">{t('landing.hero.titleAccent')}</span>
        </h1>
        <p className="max-w-xl text-lg leading-relaxed text-muted-foreground">{t('landing.hero.subtitle')}</p>
        <div className="flex flex-wrap gap-3">
          <Button size="lg" asChild>
            <Link to="/register">{t('landing.hero.start')} <ArrowRight className="h-4 w-4" /></Link>
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
      <div className="animate-rise mx-auto w-full min-w-0 max-w-md lg:max-w-none" style={{ animationDelay: '120ms' }}>
        {scenarios.length > 0 ? <DeskPreview scenarios={scenarios} /> : <div className="glass-strong h-[26rem] rounded-3xl" />}
      </div>
    </section>
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
      <div className="glass grid grid-cols-2 gap-px overflow-hidden rounded-2xl sm:grid-cols-4">
        {items.map(({ value, label, Icon }) => (
          <div key={label} className="flex items-center gap-3 p-4 sm:p-5">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary/12 text-primary"><Icon className="h-5 w-5" /></span>
            <div className="min-w-0">
              <p className="text-2xl font-extrabold tabular-nums">{value}</p>
              <p className="text-xs leading-snug text-muted-foreground">{label}</p>
            </div>
          </div>
        ))}
      </div>
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
            <article key={sector} style={{ animationDelay: `${i * 60}ms` }}
              className="glass group animate-rise flex flex-col overflow-hidden rounded-2xl transition-transform duration-300 hover:-translate-y-1">
              <div className={cn('relative h-20 bg-gradient-to-br', art.glow)}>
                <art.Icon aria-hidden className="absolute -bottom-4 -right-2 h-24 w-24 text-foreground/10 transition-transform duration-500 group-hover:scale-110" />
                <art.Icon className="absolute left-4 top-4 h-6 w-6 text-primary" />
              </div>
              <div className="flex flex-1 flex-col gap-2 p-4">
                <h3 className="font-bold">{t(`catalog.sector.${sector}`)}</h3>
                <p className="text-sm text-muted-foreground">{t(`landing.sectors.about.${sector}`)}</p>
                <ul className="mt-auto space-y-1.5 pt-2">
                  {items.slice(0, 2).map((s) => (
                    <li key={s.slug} className="rounded-lg border bg-background/50 px-2.5 py-1.5 text-xs">
                      <p className="line-clamp-2 font-medium">{s.title}</p>
                      <p className="text-muted-foreground">{t('catalog.days', { count: s.duration_days })} · {t('landing.sectors.tasks', { count: s.tasks })}</p>
                    </li>
                  ))}
                  {items.length === 0 && <li className="text-xs italic text-muted-foreground">{t('landing.sectors.soon')}</li>}
                </ul>
              </div>
            </article>
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
      <ol className="relative grid gap-4 md:grid-cols-5">
        <div aria-hidden className="bg-brand absolute left-[10%] right-[10%] top-7 hidden h-px opacity-40 md:block" />
        {STEPS.map(({ key, Icon }, i) => (
          <li key={key} className="relative flex gap-4 md:flex-col md:items-center md:text-center">
            <span className="bg-brand relative grid h-14 w-14 shrink-0 place-items-center rounded-2xl text-primary-foreground shadow-[0_10px_30px_-12px_hsl(var(--primary)/0.8)]">
              <Icon className="h-6 w-6" />
              <span className="absolute -right-1.5 -top-1.5 grid h-5 w-5 place-items-center rounded-full bg-background text-[10px] font-bold text-primary ring-1 ring-primary/40">{i + 1}</span>
            </span>
            <div>
              <h3 className="font-bold">{t(`landing.how.${key}.title`)}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{t(`landing.how.${key}.body`)}</p>
            </div>
          </li>
        ))}
      </ol>
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
      <div className="relative">
        <span className="absolute -top-3 left-1/2 z-10 -translate-x-1/2 rounded-full border bg-background px-3 py-1 text-xs font-bold uppercase tracking-widest text-muted-foreground shadow-sm">
          {t('landing.certificate.sample')}
        </span>
        <div className="pointer-events-none select-none" aria-hidden>
          <CertificateSheet cert={sample} />
        </div>
      </div>
      <div className="glass mx-auto mt-8 max-w-xl space-y-3 rounded-2xl p-5 text-center">
        <p className="font-semibold">{t('landing.certificate.verifyTitle')}</p>
        <p className="text-sm text-muted-foreground">{t('landing.certificate.verifyHint')}</p>
        <VerifyForm />
      </div>
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
        {cards.map(({ key, Icon, to, highlight }) => (
          <article key={key} className={cn('glass flex flex-col rounded-2xl p-6', highlight && 'glow-ring')}>
            <span className="grid h-12 w-12 place-items-center rounded-2xl bg-primary/12 text-primary"><Icon className="h-6 w-6" /></span>
            <h3 className="mt-4 text-xl font-bold">{t(`landing.audience.${key}.title`)}</h3>
            <p className="mt-1 text-sm font-semibold text-primary">{t(`landing.audience.${key}.price`)}</p>
            <ul className="mt-4 flex-1 space-y-2 text-sm">
              {(t(`landing.audience.${key}.points`, { returnObjects: true }) as string[]).map((p) => (
                <li key={p} className="flex gap-2"><BadgeCheck className="mt-0.5 h-4 w-4 shrink-0 text-primary" /> {p}</li>
              ))}
            </ul>
            <Button className="mt-6 w-full" variant={highlight ? 'default' : 'outline'} asChild>
              <Link to={to}>{t(`landing.audience.${key}.cta`)}</Link>
            </Button>
          </article>
        ))}
      </div>
    </Section>
  )
}

function Faq() {
  const { t } = useTranslation()
  return (
    <Section id="faq" eyebrow={t('landing.faq.eyebrow')} title={t('landing.faq.title')}>
      <div className="mx-auto max-w-3xl space-y-3">
        {FAQ.map((key) => (
          <details key={key} className="glass group rounded-2xl px-5 py-4 open:pb-5">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-semibold [&::-webkit-details-marker]:hidden">
              {t(`landing.faq.${key}.q`)}
              <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180" />
            </summary>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{t(`landing.faq.${key}.a`)}</p>
          </details>
        ))}
      </div>
    </Section>
  )
}

function CallToAction() {
  const { t } = useTranslation()
  return (
    <div className="mx-auto max-w-6xl px-4 pb-14">
      <div className="bg-brand relative overflow-hidden rounded-3xl px-6 py-12 text-center text-primary-foreground sm:px-12">
        <div aria-hidden className="absolute inset-0 opacity-20"
          style={{ backgroundImage: 'radial-gradient(hsl(0 0% 100% / 0.6) 1px, transparent 1px)', backgroundSize: '18px 18px' }} />
        <div className="relative space-y-4">
          <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl">{t('landing.cta.title')}</h2>
          <p className="mx-auto max-w-xl opacity-90">{t('landing.cta.subtitle')}</p>
          <Button size="lg" variant="secondary" asChild>
            <Link to="/register">{t('landing.hero.start')} <ArrowRight className="h-4 w-4" /></Link>
          </Button>
        </div>
      </div>
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
