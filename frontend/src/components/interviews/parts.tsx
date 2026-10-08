// AI suhbat mashqi UI bo'laklari (CONTRACT.md §24.7): boshlash, holat belgisi,
// vakansiya sahifasidagi "Suhbatga tayyorlanish" kartasi.
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { Loader2, MessagesSquare, Play } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ScoreRing } from '@/components/score'
import { api, ApiError } from '@/lib/api'
import { formatDateTime } from '@/lib/time'
import type { InterviewCard, InterviewDetail, InterviewStatus } from '@/lib/types'
import { cn } from '@/lib/utils'

const LANGS = ['uz', 'ru', 'en']

/** Suhbatni boshlaydi; faol suhbat bo'lsa (409) — unga o'tadi. */
export function useStartInterview() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const start = useCallback(async (vacancyId: string) => {
    setStarting(true)
    setError(null)
    const lang = i18n.language.slice(0, 2)
    try {
      const created = await api<InterviewDetail>('/interviews', {
        method: 'POST',
        json: { vacancy_id: vacancyId, lang: LANGS.includes(lang) ? lang : 'uz' },
      })
      navigate(`/interviews/${created.id}`)
    } catch (err) {
      const detail = err instanceof ApiError ? (err.detail as { interview_id?: string } | undefined) : undefined
      if (err instanceof ApiError && err.status === 409 && detail?.interview_id) {
        navigate(`/interviews/${detail.interview_id}`)
        return
      }
      setError(err instanceof ApiError && err.status === 429 ? t('interview.dailyLimit') : t('common.error'))
      setStarting(false)
    }
  }, [i18n.language, navigate, t])

  return { start, starting, error }
}

const STATUS_TONE: Record<InterviewStatus, string> = {
  active: 'bg-primary/12 text-primary',
  evaluating: 'bg-amber-500/15 text-amber-700 dark:text-amber-300',
  completed: 'bg-success/15 text-success',
  failed: 'bg-destructive/12 text-destructive',
  abandoned: 'bg-muted text-muted-foreground',
}

export function InterviewStatusBadge({ status }: { status: InterviewStatus }) {
  const { t } = useTranslation()
  return (
    <span className={cn('inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold', STATUS_TONE[status])}>
      {t(`interview.status.${status}`)}
    </span>
  )
}

/** Vakansiya sahifasida: shu vakansiya bo'yicha oxirgi suhbat va boshlash tugmasi. */
export function PrepareCard({ vacancyId }: { vacancyId: string }) {
  const { t } = useTranslation()
  const [mine, setMine] = useState<InterviewCard[] | null>(null)
  const { start, starting, error } = useStartInterview()

  useEffect(() => {
    api<InterviewCard[]>('/interviews')
      .then((all) => setMine(all.filter((i) => i.vacancy_id === vacancyId)))
      .catch(() => setMine([]))
  }, [vacancyId])

  const active = mine?.find((i) => i.status === 'active')
  const last = mine?.find((i) => i.status !== 'abandoned')
  const best = mine?.reduce<number | null>((acc, i) => (i.score !== null && (acc === null || i.score > acc) ? i.score : acc), null)

  return (
    <section className="glass space-y-4 rounded-3xl p-5">
      <div className="flex items-start gap-3">
        <span className="bg-brand grid h-10 w-10 shrink-0 place-items-center rounded-2xl text-primary-foreground shadow-sm">
          <MessagesSquare className="h-5 w-5" />
        </span>
        <div className="min-w-0">
          <p className="font-bold">{t('interview.prepare.title')}</p>
          <p className="text-xs text-muted-foreground">{t('interview.prepare.hint')}</p>
        </div>
      </div>

      {mine === null && <Loader2 className="mx-auto h-5 w-5 animate-spin text-muted-foreground" />}
      {last && !active && (
        <Link to={`/interviews/${last.id}`} className="flex items-center gap-3 rounded-2xl border bg-background/40 px-3 py-2.5 hover:border-primary/50">
          {last.score !== null ? <ScoreRing value={last.score} size={40} /> : null}
          <span className="min-w-0 flex-1">
            <span className="block text-sm font-semibold">{t('interview.prepare.last')}</span>
            <span className="text-xs text-muted-foreground">{formatDateTime(last.created_at)}</span>
          </span>
          <InterviewStatusBadge status={last.status} />
        </Link>
      )}
      {best !== null && best !== undefined && mine && mine.filter((i) => i.score !== null).length > 1 && (
        <p className="text-xs text-muted-foreground">{t('interview.prepare.best', { score: Math.round(best) })}</p>
      )}

      {active ? (
        <Button className="w-full" asChild>
          <Link to={`/interviews/${active.id}`}><Play className="h-4 w-4" /> {t('interview.continue')}</Link>
        </Button>
      ) : (
        <Button className="w-full" variant={last ? 'outline' : 'default'} disabled={starting || mine === null} onClick={() => start(vacancyId)}>
          {starting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          {t(last ? 'interview.again' : 'interview.start')}
        </Button>
      )}
      {error && <p className="text-sm text-destructive">{error}</p>}
    </section>
  )
}
