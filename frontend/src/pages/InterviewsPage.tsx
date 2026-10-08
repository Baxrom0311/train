// /interviews (CONTRACT.md §24.7): talabaning sinov suhbatlari — yangilari tepada.
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Loader2, MessagesSquare } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { ScoreRing } from '@/components/score'
import { InterviewStatusBadge } from '@/components/interviews/parts'
import { api } from '@/lib/api'
import { formatDateTime } from '@/lib/time'
import type { InterviewCard } from '@/lib/types'

export default function InterviewsPage() {
  const { t } = useTranslation()
  const [items, setItems] = useState<InterviewCard[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api<InterviewCard[]>('/interviews').then(setItems).catch(() => setError(t('common.error')))
  }, [t])

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-8">
      <div className="space-y-2 animate-rise">
        <h1 className="text-4xl font-extrabold tracking-tight">{t('interview.list.title')}</h1>
        <p className="text-muted-foreground">{t('interview.list.subtitle')}</p>
      </div>

      {error && <p className="glass rounded-2xl px-4 py-3 text-sm text-destructive">{error}</p>}
      {items === null && !error && <Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />}
      {items?.length === 0 && (
        <div className="glass flex flex-col items-center gap-3 rounded-2xl px-6 py-16 text-center">
          <MessagesSquare className="h-8 w-8 text-muted-foreground" />
          <p className="max-w-md text-sm text-muted-foreground">{t('interview.list.empty')}</p>
          <Link to="/vacancies" className="text-sm font-semibold text-primary hover:underline">{t('interview.list.toVacancies')}</Link>
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-2">
        {items?.map((iv, i) => (
          <Link key={iv.id} to={`/interviews/${iv.id}`} className="block animate-rise" style={{ animationDelay: `${i * 40}ms` }}>
            <Card className="h-full transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_24px_60px_-20px_hsl(var(--primary)/0.45)]">
              <CardContent className="flex items-center gap-4 p-5">
                {iv.score !== null ? (
                  <ScoreRing value={iv.score} size={56} />
                ) : (
                  <span className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-muted text-muted-foreground"><MessagesSquare className="h-5 w-5" /></span>
                )}
                <div className="min-w-0 flex-1 space-y-1">
                  <p className="truncate font-bold">{iv.position}</p>
                  <p className="truncate text-xs text-muted-foreground">{iv.company_name} · {formatDateTime(iv.created_at)}</p>
                  <InterviewStatusBadge status={iv.status} />
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  )
}
