// /company/vacancies (CONTRACT.md §23.8): kompaniya vakansiyalari — holat, arizalar, mos nomzodlar.
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { BriefcaseBusiness, Inbox, Loader2, Plus, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { VacancyMeta, VacancyStatusBadge } from '@/components/vacancies/parts'
import { api, ApiError } from '@/lib/api'
import { formatDateTime } from '@/lib/time'
import type { CompanyVacancy } from '@/lib/types'

export default function CompanyVacanciesPage() {
  const { t } = useTranslation()
  const [items, setItems] = useState<CompanyVacancy[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api<CompanyVacancy[]>('/company/vacancies')
      .then(setItems)
      .catch((err) => setError(err instanceof ApiError && err.status === 403 ? t('talent.notVerified') : t('common.error')))
  }, [t])

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-8">
      <div className="flex flex-wrap items-end justify-between gap-4 animate-rise">
        <div className="space-y-2">
          <h1 className="text-4xl font-extrabold tracking-tight">{t('vacancy.company.title')}</h1>
          <p className="text-muted-foreground">{t('vacancy.company.subtitle')}</p>
        </div>
        <Button asChild>
          <Link to="/company/vacancies/new"><Plus className="h-4 w-4" /> {t('vacancy.company.new')}</Link>
        </Button>
      </div>

      {error && <p className="glass rounded-2xl px-4 py-3 text-sm text-destructive">{error}</p>}
      {items === null && !error && <Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />}
      {items?.length === 0 && (
        <div className="glass flex flex-col items-center gap-3 rounded-2xl px-6 py-16 text-center">
          <BriefcaseBusiness className="h-8 w-8 text-muted-foreground" />
          <p className="font-semibold">{t('vacancy.company.empty')}</p>
          <p className="max-w-md text-sm text-muted-foreground">{t('vacancy.company.emptyHint')}</p>
        </div>
      )}

      <div className="space-y-3">
        {items?.map((v, i) => (
          <Link key={v.id} to={`/company/vacancies/${v.id}`} className="block animate-rise" style={{ animationDelay: `${i * 40}ms` }}>
            <Card className="transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_24px_60px_-24px_hsl(var(--primary)/0.45)]">
              <CardContent className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center">
                <div className="min-w-0 flex-1 space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="font-bold">{v.title}</h2>
                    <VacancyStatusBadge status={v.status} />
                  </div>
                  <VacancyMeta vacancy={v} />
                  <p className="text-xs text-muted-foreground">
                    {t(`catalog.sector.${v.sector}`)} · {v.published_at
                      ? t('vacancy.company.published', { date: formatDateTime(v.published_at) })
                      : t('vacancy.company.created', { date: formatDateTime(v.created_at) })}
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-2 sm:w-64">
                  <Counter Icon={Inbox} value={v.counts.applications} label={t('vacancy.company.applications')}
                    extra={v.counts.new ? t('vacancy.company.newCount', { count: v.counts.new }) : undefined} />
                  <Counter Icon={Sparkles} value={v.counts.matches} label={t('vacancy.company.matches')} />
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  )
}

function Counter({ Icon, value, label, extra }: { Icon: typeof Inbox; value: number; label: string; extra?: string }) {
  return (
    <div className="rounded-2xl border bg-background/40 px-3 py-2">
      <p className="flex items-center gap-1.5 text-lg font-extrabold tabular-nums"><Icon className="h-4 w-4 text-primary" />{value}</p>
      <p className="text-[11px] leading-tight text-muted-foreground">{label}</p>
      {extra && <p className="text-[11px] font-semibold text-primary">{extra}</p>}
    </div>
  )
}
