// Vakansiya UI bo'laklari (CONTRACT.md §23): moslik belgisi, yetishmayotgan
// kompetensiyalar, shartlar qatori, holat belgilari. Kompaniya va talaba sahifalari umumiy.
import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'
import { BadgeCheck, Banknote, Briefcase, Building2, MapPin } from 'lucide-react'
import { Badge } from '@/pages/Badge'
import type { ApplicationStatus, Fit, FitGap, Vacancy, VacancyStatus } from '@/lib/types'
import { cn } from '@/lib/utils'

/** "6 000 000 – 9 000 000 so'm" — bo'sh joy bilan guruhlash (uz/ru odati), til mustaqil. */
export function formatSalary(min: number | null, max: number | null, t: TFunction): string | null {
  const n = (v: number) => String(v).replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
  if (min !== null && max !== null) return min === max ? t('vacancy.salary.exact', { v: n(min) }) : t('vacancy.salary.range', { min: n(min), max: n(max) })
  if (min !== null) return t('vacancy.salary.from', { v: n(min) })
  if (max !== null) return t('vacancy.salary.upTo', { v: n(max) })
  return null
}

/** Moslik foizi: talabga yetgan — yashil, ≥ 70 — asosiy rang, aks holda — ogohlantiruvchi. */
export function FitBadge({ fit, className }: { fit: Fit; className?: string }) {
  const { t } = useTranslation()
  const tone = fit.meets
    ? 'bg-success/15 text-success'
    : fit.fit >= 70 ? 'bg-primary/12 text-primary' : 'bg-amber-500/15 text-amber-700 dark:text-amber-300'
  return (
    <span className={cn('inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold tabular-nums', tone, className)}
      title={fit.meets ? t('vacancy.fit.meets') : t('vacancy.fit.partial')}>
      {fit.meets && <BadgeCheck className="h-3.5 w-3.5" />}
      {t('vacancy.fit.value', { value: Math.round(fit.fit) })}
    </span>
  )
}

export function GapChips({ gaps }: { gaps: FitGap[] }) {
  const { t } = useTranslation()
  if (!gaps.length) return null
  return (
    <div className="flex flex-wrap gap-1.5">
      {gaps.map((g) => (
        <span key={g.competency} className="rounded-full border border-amber-400/40 bg-amber-500/10 px-2 py-0.5 text-[11px] font-medium text-amber-800 dark:text-amber-200">
          {t(`competency.${g.competency}`)}: {g.actual === null ? '—' : Math.round(g.actual)} / {g.required}
        </span>
      ))}
    </div>
  )
}

/** Bandlik, format, joy va maosh — bitta qatorda. */
export function VacancyMeta({ vacancy, company }: { vacancy: Vacancy; company?: string }) {
  const { t } = useTranslation()
  const salary = formatSalary(vacancy.salary_min, vacancy.salary_max, t)
  const item = 'inline-flex items-center gap-1'
  return (
    <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
      {company && <span className={cn(item, 'font-semibold text-foreground')}><Building2 className="h-3.5 w-3.5" />{company}</span>}
      <span className={item}><Briefcase className="h-3.5 w-3.5" />{t(`vacancy.employment.${vacancy.employment}`)} · {t(`vacancy.format.${vacancy.work_format}`)}</span>
      {vacancy.location && <span className={item}><MapPin className="h-3.5 w-3.5" />{vacancy.location}</span>}
      {salary && <span className={item}><Banknote className="h-3.5 w-3.5" />{salary}</span>}
    </p>
  )
}

export function VacancyStatusBadge({ status }: { status: VacancyStatus }) {
  const { t } = useTranslation()
  return <Badge variant={status === 'open' ? 'default' : status === 'draft' ? 'outline' : 'secondary'}>{t(`vacancy.status.${status}`)}</Badge>
}

const APPLICATION_TONE: Record<ApplicationStatus, string> = {
  applied: 'bg-primary/12 text-primary',
  interviewing: 'bg-amber-500/15 text-amber-700 dark:text-amber-300',
  offered: 'bg-success/15 text-success',
  rejected: 'bg-destructive/12 text-destructive',
  withdrawn: 'bg-muted text-muted-foreground',
}

export function ApplicationBadge({ status }: { status: ApplicationStatus }) {
  const { t } = useTranslation()
  return (
    <span className={cn('inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold', APPLICATION_TONE[status])}>
      {t(`vacancy.application.${status}`)}
    </span>
  )
}
