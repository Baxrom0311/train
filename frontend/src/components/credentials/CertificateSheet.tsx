import { useTranslation } from 'react-i18next'
import { Award, BadgeCheck, CalendarDays, ShieldX } from 'lucide-react'
import { Logo } from '@/components/Navbar'
import { ScoreRing } from '@/components/score'
import { formatDate } from '@/lib/time'
import type { CertificatePublic } from '@/lib/types'
import QrCode from './QrCode'

export const certificateUrl = (code: string) => `${window.location.origin}/c/${code}`

const TOP = 4

/** Sertifikat varag'i: ekranda va chop etishda bir xil (A4 albom nisbati). */
export default function CertificateSheet({ cert }: { cert: CertificatePublic }) {
  const { t, i18n } = useTranslation()
  const revoked = cert.status === 'revoked'
  const top = Object.entries(cert.competency_scores).sort((a, b) => b[1] - a[1]).slice(0, TOP)

  return (
    <div className="paper print-sheet bg-brand mx-auto w-full max-w-5xl rounded-[1.75rem] p-[3px] shadow-[0_30px_80px_-30px_hsl(158_72%_34%/0.55)]">
      <article className="relative flex aspect-auto flex-col overflow-hidden rounded-[1.6rem] bg-card px-6 py-8 sm:aspect-[297/210] sm:px-12 sm:py-10 print:h-full print:rounded-none">
        {/* fon bezagi */}
        <div aria-hidden className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full opacity-25 blur-3xl"
          style={{ background: 'radial-gradient(circle, hsl(var(--primary)) 0%, transparent 70%)' }} />
        <div aria-hidden className="pointer-events-none absolute -bottom-28 -left-20 h-72 w-72 rounded-full opacity-20 blur-3xl"
          style={{ background: 'radial-gradient(circle, hsl(var(--primary-2)) 0%, transparent 70%)' }} />
        <Award aria-hidden className="pointer-events-none absolute -bottom-10 right-6 h-64 w-64 text-primary/[0.06]" />

        <header className="relative flex flex-wrap items-start justify-between gap-4">
          <Logo />
          <div className="text-right">
            <p className="text-[11px] font-semibold uppercase tracking-[0.25em] text-muted-foreground">{t('cert.codeLabel')}</p>
            <p className="font-mono text-sm font-bold tracking-wider">{cert.code}</p>
          </div>
        </header>

        <div className="relative flex flex-1 flex-col justify-center py-8 sm:py-4">
          <p className="text-xs font-bold uppercase tracking-[0.35em] text-primary">{t('cert.title')}</p>
          <p className="mt-4 text-sm text-muted-foreground">{t('cert.awardedTo')}</p>
          <h1 className="mt-1 text-3xl font-extrabold leading-tight tracking-tight sm:text-5xl">{cert.holder_name}</h1>
          <p className="mt-4 max-w-2xl text-sm leading-relaxed sm:text-base">
            {t('cert.completed', { company: cert.company_name })}
          </p>
          <p className="mt-1 max-w-2xl text-lg font-bold leading-snug sm:text-xl">«{cert.scenario_title}»</p>
          <div className="mt-4 flex flex-wrap gap-2 text-xs">
            <span className="rounded-full border border-primary/30 bg-primary/10 px-3 py-1 font-semibold text-primary">
              {t(`catalog.sector.${cert.sector}`)}
            </span>
            <span className="rounded-full border px-3 py-1 font-medium capitalize">{cert.difficulty}</span>
            <span className="rounded-full border px-3 py-1 font-medium">{t('catalog.days', { count: cert.duration_days })}</span>
          </div>
        </div>

        <footer className="relative grid gap-6 border-t border-dashed pt-6 sm:grid-cols-[auto_1fr_auto] sm:items-end">
          <div className="flex items-center gap-3">
            {cert.overall_score !== null && <ScoreRing value={cert.overall_score} size={64} />}
            <div>
              <p className="text-xs text-muted-foreground">{t('report.overall')}</p>
              <p className="flex items-center gap-1.5 text-sm font-semibold">
                <CalendarDays className="h-3.5 w-3.5 text-muted-foreground" /> {formatDate(cert.completed_at, i18n.language)}
              </p>
            </div>
          </div>

          {top.length > 0 && (
            <ul className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs sm:justify-center">
              {top.map(([key, value]) => (
                <li key={key} className="flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                  {t(`competency.${key}`)} <b className="tabular-nums">{Math.round(value)}</b>
                </li>
              ))}
            </ul>
          )}

          <div className="flex items-end gap-3">
            <div className="text-right text-[11px] leading-tight text-muted-foreground">
              <p className={`mb-1 flex items-center justify-end gap-1 font-semibold ${revoked ? 'text-destructive' : 'text-success'}`}>
                {revoked ? <ShieldX className="h-3.5 w-3.5" /> : <BadgeCheck className="h-3.5 w-3.5" />}
                {t(revoked ? 'cert.revoked' : 'cert.valid')}
              </p>
              <p>{t('cert.scanToVerify')}</p>
              <p className="font-mono">{window.location.host}/c/{cert.code}</p>
            </div>
            <QrCode value={certificateUrl(cert.code)} label={t('cert.qr')} className="h-20 w-20 shrink-0 rounded-lg bg-white p-1.5 ring-1 ring-border" />
          </div>
        </footer>

        {revoked && (
          <div aria-hidden className="pointer-events-none absolute inset-0 grid place-items-center">
            <span className="-rotate-12 rounded-2xl border-4 border-destructive/60 px-8 py-3 text-4xl font-black uppercase tracking-widest text-destructive/60">
              {t('cert.revoked')}
            </span>
          </div>
        )}
      </article>
    </div>
  )
}
