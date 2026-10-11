import { useTranslation } from 'react-i18next'
import { BadgeCheck, Globe, GraduationCap, Languages, Mail, MapPin, Phone } from 'lucide-react'
import { Logo } from '@/components/Navbar'
import { formatDate } from '@/lib/time'
import type { Cv, CvExperience, CvSettings } from '@/lib/types'
import QrCode from './QrCode'

export type CvLang = 'uz' | 'ru' | 'en'

const portfolioUrl = (slug: string) => `${window.location.origin}/p/${slug}`
const bare = (url: string) => url.replace(/^https?:\/\//, '').replace(/\/$/, '')

/**
 * CV varag'i (CONTRACT.md §28): ekranda — jonli ko'rinish, chop etishda — A4 kitob.
 * Matn `lang` tilida (interfeys tilidan alohida); `settings` — formadagi, saqlanmagan bo'lsa ham.
 */
export default function CvSheet({ cv, settings, lang }: { cv: Cv; settings: CvSettings; lang: CvLang }) {
  const { i18n } = useTranslation()
  const t = i18n.getFixedT(lang)
  const hidden = new Set(settings.hidden_run_ids)
  const experience = cv.experience.filter((e) => !hidden.has(e.run_id))
  const competencies = Object.entries(cv.competencies)
  const languages = settings.languages.filter((l) => l.trim())

  return (
    <div className="paper cv-sheet mx-auto w-full max-w-[210mm] overflow-hidden rounded-2xl bg-card shadow-[0_30px_80px_-30px_hsl(158_72%_34%/0.45)] ring-1 ring-border">
      <div aria-hidden className="bg-brand h-1.5 print:h-1" />
      <article className="px-6 py-7 text-[13px] leading-relaxed sm:px-10 sm:py-9 print:px-[14mm] print:py-0 print:text-[10.5pt]">
        <header className="flex items-start gap-6 border-b pb-5">
          <div className="min-w-0 flex-1 space-y-2">
            <h1 className="text-3xl font-extrabold leading-tight tracking-tight">{cv.full_name}</h1>
            {cv.headline && <p className="text-base font-semibold text-primary">{cv.headline}</p>}
            <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
              <Contact Icon={Mail}>{cv.email}</Contact>
              {settings.phone && <Contact Icon={Phone}>{settings.phone}</Contact>}
              {settings.city && <Contact Icon={MapPin}>{settings.city}</Contact>}
              {cv.links.map((l) => (
                <Contact key={l.url} Icon={Globe}>
                  <a href={l.url} target="_blank" rel="noopener noreferrer nofollow" className="hover:text-primary">
                    <span className="font-semibold text-foreground">{l.label}</span> {bare(l.url)}
                  </a>
                </Contact>
              ))}
            </ul>
          </div>
          {cv.portfolio_slug && (
            <div className="hidden shrink-0 flex-col items-center gap-1 sm:flex print:flex">
              <QrCode value={portfolioUrl(cv.portfolio_slug)} label={t('cv.sheet.portfolio')}
                className="h-[72px] w-[72px] rounded-lg bg-white p-1 ring-1 ring-border" />
              <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{t('cv.sheet.portfolio')}</span>
            </div>
          )}
        </header>

        <div className="grid gap-x-8 gap-y-6 pt-6 sm:grid-cols-[minmax(0,1fr)_13.5rem] print:grid-cols-[minmax(0,1fr)_52mm]">
          <main className="min-w-0 space-y-6">
            {cv.about && (
              <Block title={t('cv.sheet.about')}>
                <p className="whitespace-pre-wrap">{cv.about}</p>
              </Block>
            )}
            <Block title={t('cv.sheet.experience')} hint={t('cv.sheet.experienceHint')}>
              {experience.length === 0
                ? <p className="text-muted-foreground">{t('cv.sheet.noExperience')}</p>
                : <div className="space-y-5">{experience.map((e) => <Entry key={e.run_id} e={e} lang={lang} />)}</div>}
            </Block>
          </main>

          <aside className="min-w-0 space-y-6">
            {cv.overall_score !== null && (
              <div className="flex items-center gap-3 rounded-xl bg-primary/8 p-3">
                <span className="text-3xl font-extrabold tabular-nums text-primary">{Math.round(cv.overall_score)}</span>
                <span className="text-xs leading-tight text-muted-foreground">{t('cv.sheet.overall')}</span>
              </div>
            )}
            {competencies.length > 0 && (
              <Block title={t('cv.sheet.skills')}>
                <ul className="space-y-2">
                  {competencies.map(([key, value]) => (
                    <li key={key} className="space-y-1 break-inside-avoid">
                      <div className="flex justify-between gap-2 text-xs">
                        <span>{t(`competency.${key}`, { defaultValue: key })}</span>
                        <b className="tabular-nums">{Math.round(value)}</b>
                      </div>
                      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                        <div className="bg-brand h-full rounded-full" style={{ width: `${Math.min(100, value)}%` }} />
                      </div>
                    </li>
                  ))}
                </ul>
              </Block>
            )}
            {cv.sectors.length > 0 && (
              <Block title={t('cv.sheet.sectors')}>
                <div className="flex flex-wrap gap-1.5">
                  {cv.sectors.map((s) => (
                    <span key={s} className="rounded-full border border-primary/30 bg-primary/10 px-2.5 py-0.5 text-xs font-semibold text-primary">
                      {t(`catalog.sector.${s}`, { defaultValue: s })}
                    </span>
                  ))}
                </div>
              </Block>
            )}
            {cv.university && (
              <Block title={t('cv.sheet.education')}>
                <p className="flex gap-2">
                  <GraduationCap className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                  <span><b>{cv.university.name}</b><br /><span className="text-muted-foreground">{cv.university.city}</span></span>
                </p>
              </Block>
            )}
            {languages.length > 0 && (
              <Block title={t('cv.sheet.languages')}>
                <ul className="space-y-1">
                  {languages.map((l) => (
                    <li key={l} className="flex gap-2"><Languages className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" /> {l}</li>
                  ))}
                </ul>
              </Block>
            )}
          </aside>
        </div>

        <footer className="mt-8 flex items-end justify-between gap-4 border-t pt-4 text-[10px] leading-snug text-muted-foreground break-inside-avoid">
          <p className="max-w-[46ch]">{t('cv.sheet.footer', { host: window.location.host })}</p>
          <div className="flex shrink-0 flex-col items-end gap-1">
            <Logo />
            <span>{t('cv.sheet.generated', { date: formatDate(cv.generated_at, lang) })}</span>
          </div>
        </footer>
      </article>
    </div>
  )
}

function Contact({ Icon, children }: { Icon: typeof Mail; children: React.ReactNode }) {
  return (
    <li className="flex min-w-0 items-center gap-1.5">
      <Icon className="h-3.5 w-3.5 shrink-0 text-primary" />
      <span className="min-w-0 break-all">{children}</span>
    </li>
  )
}

function Block({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2.5">
      <h2 className="flex items-baseline gap-2 border-b border-primary/25 pb-1 text-[11px] font-extrabold uppercase tracking-[0.18em] text-primary break-after-avoid">
        {title}
        {hint && <span className="text-[10px] font-medium normal-case tracking-normal text-muted-foreground">{hint}</span>}
      </h2>
      {children}
    </section>
  )
}

/** Bitta simulyatsiya: nima, qayerda (fictional), qachon, natija va kuchli tomonlar. */
function Entry({ e, lang }: { e: CvExperience; lang: CvLang }) {
  const { i18n } = useTranslation()
  const t = i18n.getFixedT(lang)
  const start = formatDate(e.started_at, lang)
  const end = formatDate(e.completed_at, lang)
  const facts = [
    e.tasks_total > 0 && t('cv.sheet.tasks', { submitted: e.tasks_submitted, total: e.tasks_total }),
    e.on_time_rate !== null && t('cv.sheet.onTime', { rate: Math.round(e.on_time_rate) }),
  ].filter(Boolean)

  return (
    <article className="break-inside-avoid space-y-1.5">
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-bold leading-snug">{e.scenario_title}</h3>
        {e.overall_score !== null && (
          <span className="shrink-0 rounded-lg bg-primary/10 px-2 py-0.5 text-xs font-extrabold tabular-nums text-primary">
            {Math.round(e.overall_score)}<span className="font-semibold text-primary/70">/100</span>
          </span>
        )}
      </div>
      <p className="text-xs text-muted-foreground">
        <b className="font-semibold text-foreground">{e.company_name}</b>
        {' · '}{t('cv.sheet.simulation')}
        {' · '}{t(`catalog.sector.${e.sector}`, { defaultValue: e.sector })}
        {' · '}{t(`editor.difficulty.${e.difficulty}`, { defaultValue: e.difficulty })}
        {' · '}{start === end ? end : `${start} – ${end}`}
      </p>
      {(facts.length > 0 || e.strengths.length > 0) && (
        <ul className="list-disc space-y-0.5 pl-4 marker:text-primary">
          {facts.length > 0 && <li>{facts.join(', ')}</li>}
          {e.strengths.map((s) => <li key={s}>{s}</li>)}
        </ul>
      )}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px]">
        {Object.entries(e.top_competencies).map(([key, value]) => (
          <span key={key} className="flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-primary" />
            {t(`competency.${key}`, { defaultValue: key })} <b className="tabular-nums">{Math.round(value)}</b>
          </span>
        ))}
        {e.certificate_code && (
          <a href={`/c/${e.certificate_code}`} target="_blank" rel="noopener noreferrer"
            className="flex items-center gap-1 font-semibold text-success hover:underline">
            <BadgeCheck className="h-3.5 w-3.5" />
            {t('cv.sheet.certificate')} <span className="font-mono">{window.location.host}/c/{e.certificate_code}</span>
          </a>
        )}
      </div>
    </article>
  )
}
