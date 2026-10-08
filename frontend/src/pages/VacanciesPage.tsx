// /vacancies (CONTRACT.md §23.8): talabaga ochiq vakansiyalar — moslik foizi bo'yicha,
// soha filtri; tepada o'z arizalari (suhbat bo'lsa — vaqti, §25.6).
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { BriefcaseBusiness, CalendarCheck2, Loader2, Trophy } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Segmented } from '@/components/ui/segmented'
import { useWhen } from '@/components/vacancies/meetings'
import { ApplicationBadge, FitBadge, VacancyMeta } from '@/components/vacancies/parts'
import { api } from '@/lib/api'
import { formatDateTime } from '@/lib/time'
import { SECTORS, type MyApplication, type Sector, type VacancyCard } from '@/lib/types'
import { cn } from '@/lib/utils'

export default function VacanciesPage() {
  const { t } = useTranslation()
  const when = useWhen()
  const [sector, setSector] = useState<Sector | ''>('')
  const [items, setItems] = useState<VacancyCard[] | null>(null)
  const [mine, setMine] = useState<MyApplication[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api<MyApplication[]>('/users/me/applications').then(setMine).catch(() => setMine([]))
  }, [])

  useEffect(() => {
    setLoading(true)
    api<VacancyCard[]>(`/vacancies${sector ? `?sector=${sector}` : ''}`)
      .then((v) => { setItems(v); setError(null) })
      .catch(() => setError(t('common.error')))
      .finally(() => setLoading(false))
  }, [sector, t])

  const noProfile = items !== null && items.length > 0 && items.every((v) => v.my_fit === null)
  const active = mine.filter((a) => a.status !== 'withdrawn')

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-8">
      <div className="space-y-2 animate-rise">
        <h1 className="text-4xl font-extrabold tracking-tight">{t('vacancy.student.title')}</h1>
        <p className="text-muted-foreground">{t('vacancy.student.subtitle')}</p>
      </div>

      {active.length > 0 && (
        <section className="glass space-y-3 rounded-3xl p-5 animate-rise">
          <h2 className="font-bold">{t('vacancy.student.myApplications')}</h2>
          <ul className="divide-y">
            {active.map((a) => (
              <li key={a.id}>
                <Link to={`/vacancies/${a.vacancy_id}`} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-2.5 hover:text-primary">
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-semibold">{a.vacancy_title}</span>
                    <span className="text-xs text-muted-foreground">{a.company_name} · {formatDateTime(a.created_at)}</span>
                    {a.interview && (
                      <span className={cn('mt-1 flex items-center gap-1.5 text-xs font-semibold',
                        a.interview.status === 'proposed' && !a.interview.expired ? 'text-amber-700 dark:text-amber-300' : 'text-primary')}>
                        <CalendarCheck2 className="h-3.5 w-3.5" />
                        {a.interview.status === 'confirmed' && a.interview.starts_at
                          ? t('meeting.student.on', { when: when(a.interview.starts_at) })
                          : t(a.interview.expired ? 'meeting.status.expired' : 'meeting.student.pickNeeded')}
                      </span>
                    )}
                  </span>
                  {a.vacancy_status === 'closed' && <span className="text-xs text-muted-foreground">{t('vacancy.student.closed')}</span>}
                  <ApplicationBadge status={a.status} />
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="-mx-4 overflow-x-auto px-4 [scrollbar-width:none]">
        <div className="w-max">
          <Segmented<Sector | ''> label={t('talent.filter.sector')} value={sector} onChange={setSector} busy={loading}
            options={[{ value: '', label: t('talent.filter.any') }, ...SECTORS.map((s) => ({ value: s, label: t(`catalog.sector.${s}`) }))]} />
        </div>
      </div>

      {noProfile && (
        <p className="glass flex items-center gap-2 rounded-2xl px-4 py-3 text-sm">
          <Trophy className="h-4 w-4 shrink-0 text-primary" /> {t('vacancy.student.noProfile')}{' '}
          <Link to="/simulations" className="font-semibold text-primary hover:underline">{t('growth.recs.catalog')}</Link>
        </p>
      )}
      {error && <p className="glass rounded-2xl px-4 py-3 text-sm text-destructive">{error}</p>}
      {items === null && !error && <Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />}
      {items?.length === 0 && (
        <div className="glass flex flex-col items-center gap-2 rounded-2xl px-6 py-16 text-center">
          <BriefcaseBusiness className="h-8 w-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">{t('vacancy.student.empty')}</p>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {items?.map((v, i) => (
          <Link key={v.id} to={`/vacancies/${v.id}`} className="block animate-rise" style={{ animationDelay: `${i * 40}ms` }}>
            <Card className="h-full transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_24px_60px_-20px_hsl(var(--primary)/0.45)]">
              <CardContent className="flex h-full flex-col gap-3 p-5">
                <div className="flex items-start justify-between gap-3">
                  <h2 className="font-bold leading-snug">{v.title}</h2>
                  {v.my_fit && <FitBadge fit={v.my_fit} className="shrink-0" />}
                </div>
                <VacancyMeta vacancy={v} company={v.company.name} />
                <p className="line-clamp-2 text-sm text-muted-foreground">{v.description}</p>
                <div className="mt-auto flex flex-wrap items-center gap-2 pt-1 text-xs text-muted-foreground">
                  <span>{t(`catalog.sector.${v.sector}`)}</span>
                  {v.published_at && <span>· {formatDateTime(v.published_at)}</span>}
                  {v.application_status && <span className="ml-auto"><ApplicationBadge status={v.application_status} /></span>}
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  )
}
