import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Loader2, Send, SlidersHorizontal, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { CompetencyBars, ScoreRing } from '@/components/score'
import CandidateProfileView from '@/components/talent/CandidateProfileView'
import Initials from '@/components/talent/Initials'
import OfferForm from '@/components/talent/OfferForm'
import { Badge } from './Badge'
import { api, ApiError } from '@/lib/api'
import { formatDateTime } from '@/lib/time'
import { COMPETENCIES, SECTORS, type CandidateCard, type CandidatePage, type CandidateProfile, type Sector } from '@/lib/types'

const PAGE = 12
const SELECT = 'h-10 rounded-xl border border-input bg-background/60 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring'

interface Filters {
  sector: Sector | ''
  competency: string
  minScore: number
  sort: 'score' | 'recent'
}

function query(f: Filters, offset: number) {
  const p = new URLSearchParams({ sort: f.sort, limit: String(PAGE), offset: String(offset) })
  if (f.sector) p.set('sector', f.sector)
  if (f.competency) p.set('competency', f.competency)
  if (f.minScore > 0) p.set('min_score', String(f.minScore))
  return `/talents?${p}`
}

export default function TalentsPage() {
  const { t } = useTranslation()
  const [filters, setFilters] = useState<Filters>({ sector: '', competency: '', minScore: 0, sort: 'score' })
  const [items, setItems] = useState<CandidateCard[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [openId, setOpenId] = useState<string | null>(null)

  const load = useCallback(async (f: Filters, offset: number) => {
    setLoading(true)
    setError(null)
    try {
      const page = await api<CandidatePage>(query(f, offset))
      setItems((prev) => (offset ? [...prev, ...page.items] : page.items))
      setTotal(page.total)
    } catch (err) {
      setError(err instanceof ApiError && err.status === 403 ? t('talent.notVerified') : t('common.error'))
    } finally {
      setLoading(false)
    }
  }, [t])

  // filtr o'zgarsa — boshidan; slayder har siljishda so'rov yubormasin
  useEffect(() => {
    const timer = setTimeout(() => load(filters, 0), 250)
    return () => clearTimeout(timer)
  }, [filters, load])

  const set = <K extends keyof Filters>(key: K, value: Filters[K]) => setFilters((f) => ({ ...f, [key]: value }))

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-8">
      <div className="flex flex-wrap items-end justify-between gap-4 animate-rise">
        <div className="space-y-2">
          <h1 className="text-4xl font-extrabold tracking-tight">{t('talent.title')}</h1>
          <p className="text-muted-foreground">{t('talent.subtitle')}</p>
        </div>
        <Button variant="outline" asChild>
          <Link to="/talents/offers"><Send className="h-4 w-4" /> {t('talent.sentOffers')}</Link>
        </Button>
      </div>

      <div className="glass grid grid-cols-2 items-end gap-3 rounded-2xl p-4 animate-rise sm:flex sm:flex-wrap sm:gap-4">
        <SlidersHorizontal className="mb-2.5 hidden h-4 w-4 text-primary sm:block" />
        <label className="space-y-1 text-xs font-medium text-muted-foreground">
          {t('talent.filter.sector')}
          <select className={`${SELECT} block w-full sm:w-auto`} value={filters.sector} onChange={(e) => set('sector', e.target.value as Sector | '')}>
            <option value="">{t('talent.filter.any')}</option>
            {SECTORS.map((s) => <option key={s} value={s}>{t(`catalog.sector.${s}`)}</option>)}
          </select>
        </label>
        <label className="space-y-1 text-xs font-medium text-muted-foreground">
          {t('talent.filter.competency')}
          <select className={`${SELECT} block w-full sm:w-auto`} value={filters.competency} onChange={(e) => set('competency', e.target.value)}>
            <option value="">{t('talent.filter.overall')}</option>
            {COMPETENCIES.map((c) => <option key={c} value={c}>{t(`competency.${c}`)}</option>)}
          </select>
        </label>
        <label className="col-span-2 min-w-44 flex-1 space-y-1 text-xs font-medium text-muted-foreground sm:max-w-64">
          <span className="flex justify-between">
            {t('talent.filter.minScore')} <span className="tabular-nums text-foreground">{filters.minScore}</span>
          </span>
          <input type="range" min={0} max={100} step={5} value={filters.minScore}
            onChange={(e) => set('minScore', Number(e.target.value))}
            className="block h-10 w-full accent-[hsl(var(--primary))]" />
        </label>
        <label className="space-y-1 text-xs font-medium text-muted-foreground">
          {t('talent.filter.sort')}
          <select className={`${SELECT} block w-full sm:w-auto`} value={filters.sort} onChange={(e) => set('sort', e.target.value as Filters['sort'])}>
            <option value="score">{t('talent.filter.byScore')}</option>
            <option value="recent">{t('talent.filter.byRecent')}</option>
          </select>
        </label>
        <p className="col-span-2 text-right text-sm text-muted-foreground sm:mb-2.5 sm:ml-auto">{t('talent.found', { count: total })}</p>
      </div>

      {error && <p className="glass rounded-2xl px-4 py-3 text-sm text-destructive">{error}</p>}

      {!error && !loading && items.length === 0 && (
        <div className="glass flex flex-col items-center gap-2 rounded-2xl px-6 py-16 text-center">
          <Users className="h-8 w-8 text-muted-foreground" />
          <p className="font-semibold">{t('talent.empty')}</p>
          <p className="max-w-md text-sm text-muted-foreground">{t('talent.emptyHint')}</p>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((c, i) => (
          <button key={c.id} type="button" onClick={() => setOpenId(c.id)}
            className="text-left animate-rise" style={{ animationDelay: `${(i % PAGE) * 40}ms` }}>
            <Card className="h-full transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_24px_60px_-20px_hsl(var(--primary)/0.45)]">
              <CardContent className="space-y-4 p-5">
                <div className="flex items-center gap-3">
                  <Initials name={c.full_name} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-bold">{c.full_name}</p>
                    <p className="text-xs text-muted-foreground">
                      {t('talent.runsCompleted', { count: c.runs_completed })}
                    </p>
                  </div>
                  {c.overall_score !== null && <ScoreRing value={c.overall_score} size={52} />}
                </div>
                <CompetencyBars scores={c.top_competencies} compact />
                <div className="flex flex-wrap items-center gap-1.5">
                  {c.sectors.map((s) => <Badge key={s} variant="secondary">{t(`catalog.sector.${s}`)}</Badge>)}
                  {c.last_completed_at && (
                    <span className="ml-auto text-xs text-muted-foreground">{formatDateTime(c.last_completed_at)}</span>
                  )}
                </div>
              </CardContent>
            </Card>
          </button>
        ))}
      </div>

      {loading && <Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />}
      {!loading && items.length < total && (
        <div className="flex justify-center">
          <Button variant="outline" onClick={() => load(filters, items.length)}>{t('talent.more')}</Button>
        </div>
      )}

      <CandidateDialog id={openId} onClose={() => setOpenId(null)} />
    </div>
  )
}

function CandidateDialog({ id, onClose }: { id: string | null; onClose: () => void }) {
  const { t } = useTranslation()
  const [profile, setProfile] = useState<CandidateProfile | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setProfile(null)
    setError(null)
    if (id) api<CandidateProfile>(`/talents/${id}`).then(setProfile).catch(() => setError(t('talent.gone')))
  }, [id, t])

  return (
    <Dialog open={id !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent closeLabel={t('common.close')} aria-describedby={undefined}>
        <DialogTitle className="sr-only">{profile?.full_name ?? t('talent.title')}</DialogTitle>
        <div className="overflow-y-auto p-6">
          {error && <p className="text-sm text-destructive">{error}</p>}
          {!profile && !error && <Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />}
          {profile && (
            <div className="space-y-8">
              <CandidateProfileView profile={profile} />
              <OfferForm candidateId={profile.id} />
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
