import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'
import { Award, ExternalLink, GraduationCap, Loader2, UserX } from 'lucide-react'
import { CompetencyBars, ScoreRing } from '@/components/score'
import Initials from '@/components/talent/Initials'
import CertificateCard from '@/components/credentials/CertificateCard'
import { api, ApiError } from '@/lib/api'
import type { PortfolioPublic } from '@/lib/types'

/** Talabaning ochiq portfoliosi `/p/:slug` (CONTRACT.md §13.2) — login shart emas. */
export default function PortfolioPublicPage() {
  const { slug = '' } = useParams()
  const { t } = useTranslation()
  const [data, setData] = useState<PortfolioPublic | null>(null)
  const [state, setState] = useState<'loading' | 'ok' | 'missing' | 'error'>('loading')

  useEffect(() => {
    api<PortfolioPublic>(`/portfolios/${encodeURIComponent(slug)}`)
      .then((p) => {
        setData(p)
        setState('ok')
      })
      .catch((e) => setState(e instanceof ApiError && e.status === 404 ? 'missing' : 'error'))
  }, [slug])

  useEffect(() => {
    if (data) document.title = `${data.full_name} · TryJob`
    return () => {
      document.title = 'TryJob'
    }
  }, [data])

  if (state === 'loading') {
    return <p className="flex items-center justify-center gap-2 p-16 text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" /> {t('common.loading')}</p>
  }
  if (state !== 'ok' || !data) {
    return (
      <div className="mx-auto max-w-md space-y-3 px-4 py-20 text-center animate-rise">
        <UserX className="mx-auto h-12 w-12 text-muted-foreground" />
        <h1 className="text-2xl font-extrabold">{t(state === 'missing' ? 'portfolio.notFound' : 'common.error')}</h1>
        {state === 'missing' && <p className="text-muted-foreground">{t('portfolio.notFoundHint')}</p>}
      </div>
    )
  }

  const competencies = Object.fromEntries(Object.entries(data.competencies).sort((a, b) => b[1] - a[1]))
  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-8">
      <section className="glass-strong glow-ring animate-rise relative overflow-hidden rounded-3xl p-6 sm:p-8">
        <div aria-hidden className="pointer-events-none absolute -right-20 -top-24 h-64 w-64 rounded-full opacity-30 blur-3xl"
          style={{ background: 'radial-gradient(circle, hsl(var(--primary)) 0%, transparent 70%)' }} />
        <div className="relative flex flex-col gap-6 sm:flex-row sm:items-center">
          <Initials name={data.full_name} className="h-20 w-20 rounded-3xl text-2xl" />
          <div className="min-w-0 flex-1 space-y-2">
            <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">{data.full_name}</h1>
            {data.headline && <p className="text-lg text-muted-foreground">{data.headline}</p>}
            <div className="flex flex-wrap items-center gap-2 text-sm">
              {data.university && (
                <span className="flex items-center gap-1.5 rounded-full border bg-background/50 px-3 py-1">
                  <GraduationCap className="h-4 w-4 text-primary" /> {data.university.name}, {data.university.city}
                </span>
              )}
              {data.sectors.map((s) => (
                <span key={s} className="rounded-full border border-primary/30 bg-primary/10 px-3 py-1 font-medium text-primary">
                  {t(`catalog.sector.${s}`)}
                </span>
              ))}
            </div>
          </div>
          {data.overall_score !== null && (
            <div className="flex flex-col items-center gap-1">
              <ScoreRing value={data.overall_score} size={84} />
              <span className="text-xs text-muted-foreground">{t('report.overall')}</span>
            </div>
          )}
        </div>
        {data.links.length > 0 && (
          <div className="relative mt-6 flex flex-wrap gap-2">
            {data.links.map((l) => (
              <a key={l.url} href={l.url} target="_blank" rel="noopener noreferrer nofollow"
                className="flex items-center gap-1.5 rounded-xl border bg-background/60 px-3 py-1.5 text-sm font-medium transition-colors hover:border-primary/50 hover:text-primary">
                <ExternalLink className="h-3.5 w-3.5" /> {l.label}
              </a>
            ))}
          </div>
        )}
      </section>

      <div className="grid gap-6 lg:grid-cols-[1fr_1.4fr]">
        <div className="space-y-6">
          {data.about && (
            <section className="glass animate-rise rounded-2xl p-5" style={{ animationDelay: '60ms' }}>
              <h2 className="mb-2 font-bold">{t('portfolio.about')}</h2>
              <p className="whitespace-pre-wrap text-sm leading-relaxed">{data.about}</p>
            </section>
          )}
          {Object.keys(competencies).length > 0 && (
            <section className="glass animate-rise rounded-2xl p-5" style={{ animationDelay: '120ms' }}>
              <h2 className="mb-3 font-bold">{t('report.competencies')}</h2>
              <CompetencyBars scores={competencies} />
            </section>
          )}
        </div>
        <section className="glass animate-rise space-y-3 rounded-2xl p-5" style={{ animationDelay: '180ms' }}>
          <h2 className="flex items-center gap-2 font-bold">
            <Award className="h-4 w-4 text-primary" /> {t('portfolio.certificates', { count: data.certificates.length })}
          </h2>
          {data.certificates.length === 0
            ? <p className="text-sm text-muted-foreground">{t('portfolio.noCertificates')}</p>
            : data.certificates.map((c) => <CertificateCard key={c.code} cert={c} />)}
        </section>
      </div>
      <p className="text-center text-xs text-muted-foreground">{t('portfolio.footer')}</p>
    </div>
  )
}
