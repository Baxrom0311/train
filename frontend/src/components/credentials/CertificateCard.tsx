import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Award, ShieldX } from 'lucide-react'
import { ScoreRing } from '@/components/score'
import { formatDate } from '@/lib/time'
import type { CertificatePublic } from '@/lib/types'

/** Ro'yxatdagi sertifikat (portfolio va "Portfolio" sahifasi). */
export default function CertificateCard({ cert, actions }: { cert: CertificatePublic; actions?: ReactNode }) {
  const { t, i18n } = useTranslation()
  const revoked = cert.status === 'revoked'
  return (
    <article className={`group relative overflow-hidden rounded-2xl border bg-background/60 p-4 transition-shadow hover:shadow-[0_18px_40px_-24px_hsl(var(--primary)/0.6)] ${revoked ? 'opacity-70' : ''}`}>
      <div aria-hidden className="bg-brand absolute inset-y-0 left-0 w-1" />
      <div className="flex items-start gap-3 pl-1">
        <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${revoked ? 'bg-destructive/10 text-destructive' : 'bg-primary/12 text-primary'}`}>
          {revoked ? <ShieldX className="h-5 w-5" /> : <Award className="h-5 w-5" />}
        </span>
        <div className="min-w-0 flex-1">
          <Link to={`/c/${cert.code}`} className="font-semibold leading-snug hover:underline">{cert.scenario_title}</Link>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {t(`catalog.sector.${cert.sector}`)} · {formatDate(cert.completed_at, i18n.language)}
          </p>
          <p className="mt-1 font-mono text-[11px] text-muted-foreground">
            {cert.code}{revoked && <span className="ml-2 font-sans font-semibold text-destructive">{t('cert.revoked')}</span>}
          </p>
        </div>
        {cert.overall_score !== null && <ScoreRing value={cert.overall_score} size={48} />}
      </div>
      {actions && <div className="mt-3 flex flex-wrap gap-2 pl-1">{actions}</div>}
    </article>
  )
}
