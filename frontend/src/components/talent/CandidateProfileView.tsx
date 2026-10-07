import { useTranslation } from 'react-i18next'
import { Award, CheckCircle2 } from 'lucide-react'
import { CompetencyBars, ScoreRing } from '@/components/score'
import { Badge } from '@/pages/Badge'
import { formatDateTime } from '@/lib/time'
import type { CandidateProfile } from '@/lib/types'
import Initials from './Initials'

/** Kompaniya ko'radigan profil (talaba o'z sahifasida ham aynan shuni ko'radi). */
export default function CandidateProfileView({ profile }: { profile: CandidateProfile }) {
  const { t } = useTranslation()
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4 pr-8">
        <Initials name={profile.full_name} className="h-14 w-14 text-base" />
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-xl font-extrabold">{profile.full_name}</h2>
          <p className="text-sm text-muted-foreground">
            {t('talent.runsCompleted', { count: profile.runs_completed })}
            {profile.sectors.length > 0 && ' · ' + profile.sectors.map((s) => t(`catalog.sector.${s}`)).join(', ')}
          </p>
        </div>
        {profile.overall_score !== null && <ScoreRing value={profile.overall_score} size={64} />}
      </div>

      {Object.keys(profile.competencies).length > 0 && (
        <section className="space-y-2">
          <h3 className="font-semibold">{t('report.competencies')}</h3>
          <CompetencyBars scores={Object.fromEntries(Object.entries(profile.competencies).sort((a, b) => b[1] - a[1]))} />
        </section>
      )}

      <section className="space-y-3">
        <h3 className="font-semibold">{t('talent.runs')}</h3>
        {profile.runs.map((run) => (
          <article key={run.scenario_title + run.completed_at} className="rounded-2xl border bg-background/60 p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="font-semibold">{run.scenario_title}</p>
                <p className="text-xs text-muted-foreground">
                  {run.company_name} · {formatDateTime(run.completed_at)}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline"><Award className="mr-1 h-3 w-3" />{t('talent.certificate')}</Badge>
                {run.overall_score !== null && <ScoreRing value={run.overall_score} size={44} />}
              </div>
            </div>
            {run.strengths.length > 0 && (
              <ul className="mt-3 space-y-1 text-sm">
                {run.strengths.map((s) => (
                  <li key={s} className="flex gap-2">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success" /> {s}
                  </li>
                ))}
              </ul>
            )}
          </article>
        ))}
      </section>
    </div>
  )
}
