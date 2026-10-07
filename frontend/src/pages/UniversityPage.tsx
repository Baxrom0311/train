import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Activity, GraduationCap, Loader2, Mail, Search, Trophy, UserMinus, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Stat } from '@/components/ui/stat'
import { CompetencyBars, ScoreRing } from '@/components/score'
import CandidateProfileView from '@/components/talent/CandidateProfileView'
import Initials from '@/components/talent/Initials'
import { Badge } from './Badge'
import { api, ApiError } from '@/lib/api'
import { formatDateTime } from '@/lib/time'
import { SECTORS, type Sector, type StudentDetail, type StudentPage, type StudentRow, type UniversityOverview } from '@/lib/types'

const PAGE = 25
const SELECT = 'h-10 rounded-xl border border-input bg-background/60 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring'

interface Filters {
  q: string
  sector: Sector | ''
  results: '' | 'yes' | 'no'
  sort: 'score' | 'recent' | 'name'
}

function query(f: Filters, offset: number) {
  const p = new URLSearchParams({ sort: f.sort, limit: String(PAGE), offset: String(offset) })
  if (f.q.trim()) p.set('q', f.q.trim())
  if (f.sector) p.set('sector', f.sector)
  if (f.results) p.set('has_results', String(f.results === 'yes'))
  return `/university/students?${p}`
}

export default function UniversityPage() {
  const { t } = useTranslation()
  const [overview, setOverview] = useState<UniversityOverview | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [openId, setOpenId] = useState<string | null>(null)
  // ajratilgandan keyin ro'yxat va statistika qayta yuklanadi
  const [version, setVersion] = useState(0)

  useEffect(() => {
    api<UniversityOverview>('/university/overview')
      .then(setOverview)
      .catch((err) => setError(err instanceof ApiError && err.status === 403 ? t('university.notVerified') : t('common.error')))
  }, [t, version])

  if (error) return <p className="mx-auto max-w-6xl px-4 py-8 text-destructive">{error}</p>
  if (!overview) return <Loader2 className="mx-auto mt-16 h-6 w-6 animate-spin text-muted-foreground" />

  const competencies = Object.fromEntries(Object.entries(overview.competencies).sort((a, b) => b[1] - a[1]))

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-8">
      <div className="space-y-2 animate-rise">
        <h1 className="text-4xl font-extrabold tracking-tight">{overview.university.name}</h1>
        <p className="text-muted-foreground">{overview.university.city} · {t('university.subtitle')}</p>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 animate-rise">
        <Stat Icon={Users} label={t('university.stats.students')} value={overview.students_total} />
        <Stat Icon={GraduationCap} label={t('university.stats.withResults')} value={overview.students_with_results} />
        <Stat Icon={Trophy} label={t('university.stats.avgScore')} value={overview.avg_score ?? '—'} />
        <Stat Icon={Activity} label={t('university.stats.inProgress')} value={overview.runs_in_progress} />
      </div>

      {overview.students_with_results > 0 && (
        <div className="grid gap-4 lg:grid-cols-3">
          <Card className="animate-rise">
            <CardHeader><CardTitle className="text-base">{t('university.top')}</CardTitle></CardHeader>
            <CardContent className="space-y-1">
              {overview.top_students.map((s, i) => (
                <button key={s.id} type="button" onClick={() => setOpenId(s.id)}
                  className="flex w-full items-center gap-3 rounded-xl px-2 py-2 text-left transition-colors hover:bg-muted/60">
                  <span className="w-4 text-sm font-bold text-muted-foreground tabular-nums">{i + 1}</span>
                  <Initials name={s.full_name} className="h-8 w-8 text-xs" />
                  <span className="min-w-0 flex-1 truncate text-sm font-medium">{s.full_name}</span>
                  <span className="text-sm font-extrabold tabular-nums">{Math.round(s.overall_score ?? 0)}</span>
                </button>
              ))}
            </CardContent>
          </Card>
          <Card className="animate-rise">
            <CardHeader><CardTitle className="text-base">{t('university.sectors')}</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {overview.sectors.map((s) => (
                <div key={s.sector} className="flex items-center justify-between gap-3 rounded-xl border bg-background/60 px-3 py-2">
                  <div>
                    <p className="text-sm font-semibold">{t(`catalog.sector.${s.sector}`)}</p>
                    <p className="text-xs text-muted-foreground">{t('university.studentsCount', { count: s.students })}</p>
                  </div>
                  {s.avg_score !== null && <ScoreRing value={s.avg_score} size={44} />}
                </div>
              ))}
            </CardContent>
          </Card>
          <Card className="animate-rise">
            <CardHeader><CardTitle className="text-base">{t('university.competencies')}</CardTitle></CardHeader>
            <CardContent><CompetencyBars scores={competencies} compact /></CardContent>
          </Card>
        </div>
      )}

      <Students version={version} onOpen={setOpenId} empty={overview.students_total === 0} />

      <StudentDialog id={openId} onClose={() => setOpenId(null)} onDetached={() => setVersion((v) => v + 1)} />
    </div>
  )
}

function Students({ version, onOpen, empty }: { version: number; onOpen: (id: string) => void; empty: boolean }) {
  const { t } = useTranslation()
  const [filters, setFilters] = useState<Filters>({ q: '', sector: '', results: '', sort: 'score' })
  const [items, setItems] = useState<StudentRow[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async (f: Filters, offset: number) => {
    setLoading(true)
    setError(null)
    try {
      const page = await api<StudentPage>(query(f, offset))
      setItems((prev) => (offset ? [...prev, ...page.items] : page.items))
      setTotal(page.total)
    } catch {
      setError(t('common.error'))
    } finally {
      setLoading(false)
    }
  }, [t])

  // qidiruv har harfda so'rov yubormasin
  useEffect(() => {
    const id = setTimeout(() => load(filters, 0), 250)
    return () => clearTimeout(id)
  }, [filters, load, version])

  const set = <K extends keyof Filters>(key: K, value: Filters[K]) => setFilters((f) => ({ ...f, [key]: value }))

  if (empty) {
    return (
      <Card className="animate-rise">
        <CardContent className="flex flex-col items-center gap-3 p-10 text-center">
          <GraduationCap className="h-10 w-10 text-muted-foreground" />
          <p className="font-semibold">{t('university.noStudents')}</p>
          <p className="max-w-md text-sm text-muted-foreground">{t('university.noStudentsHint')}</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="animate-rise">
      <CardHeader className="space-y-4">
        <CardTitle className="text-base">{t('university.students')} <span className="text-muted-foreground">· {total}</span></CardTitle>
        <div className="flex flex-wrap gap-2">
          <div className="relative min-w-[200px] flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 z-10 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input className="pl-9" value={filters.q} onChange={(e) => set('q', e.target.value)}
              placeholder={t('university.search')} aria-label={t('university.search')} />
          </div>
          <select className={SELECT} value={filters.sector} aria-label={t('talent.filter.sector')}
            onChange={(e) => set('sector', e.target.value as Filters['sector'])}>
            <option value="">{t('talent.filter.any')}</option>
            {SECTORS.map((s) => <option key={s} value={s}>{t(`catalog.sector.${s}`)}</option>)}
          </select>
          <select className={SELECT} value={filters.results} aria-label={t('university.filters.results')}
            onChange={(e) => set('results', e.target.value as Filters['results'])}>
            <option value="">{t('university.filters.all')}</option>
            <option value="yes">{t('university.filters.withResults')}</option>
            <option value="no">{t('university.filters.noResults')}</option>
          </select>
          <select className={SELECT} value={filters.sort} aria-label={t('talent.filter.sort')}
            onChange={(e) => set('sort', e.target.value as Filters['sort'])}>
            <option value="score">{t('talent.filter.byScore')}</option>
            <option value="recent">{t('talent.filter.byRecent')}</option>
            <option value="name">{t('university.sortName')}</option>
          </select>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        {error && <p className="text-sm text-destructive">{error}</p>}
        {!loading && items.length === 0 && !error && (
          <p className="py-8 text-center text-sm text-muted-foreground">{t('university.noMatch')}</p>
        )}
        <ul className="divide-y">
          {items.map((s) => (
            <li key={s.id}>
              <button type="button" onClick={() => onOpen(s.id)}
                className="flex w-full items-center gap-3 rounded-xl px-2 py-3 text-left transition-colors hover:bg-muted/50 sm:gap-4">
                <Initials name={s.full_name} className="h-10 w-10 text-sm" />
                <div className="min-w-0 flex-1 space-y-1">
                  <p className="truncate font-semibold">{s.full_name}</p>
                  <p className="truncate text-xs text-muted-foreground">{s.email}</p>
                  {(s.sectors.length > 0 || s.runs_in_progress > 0) && (
                    <div className="flex flex-wrap items-center gap-1.5">
                      {s.sectors.map((sec) => <Badge key={sec} variant="outline">{t(`catalog.sector.${sec}`)}</Badge>)}
                      {s.runs_in_progress > 0 && <Badge variant="secondary">{t('university.inProgressCount', { count: s.runs_in_progress })}</Badge>}
                    </div>
                  )}
                </div>
                <div className="hidden w-44 text-right text-xs text-muted-foreground sm:block">
                  {s.runs_completed > 0
                    ? <>{t('talent.runsCompleted', { count: s.runs_completed })}<br />{s.last_completed_at && formatDateTime(s.last_completed_at)}</>
                    : t('university.noResultsYet')}
                </div>
                <div className="grid w-12 shrink-0 place-items-center">
                  {s.overall_score !== null ? <ScoreRing value={s.overall_score} size={44} /> : <span className="text-muted-foreground">—</span>}
                </div>
              </button>
            </li>
          ))}
        </ul>
        {loading && <Loader2 className="mx-auto h-5 w-5 animate-spin text-muted-foreground" />}
        {!loading && items.length < total && (
          <Button variant="outline" className="w-full" onClick={() => load(filters, items.length)}>{t('talent.more')}</Button>
        )}
      </CardContent>
    </Card>
  )
}

function StudentDialog({ id, onClose, onDetached }: { id: string | null; onClose: () => void; onDetached: () => void }) {
  const { t } = useTranslation()
  const [student, setStudent] = useState<StudentDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    setStudent(null)
    setError(null)
    if (id) api<StudentDetail>(`/university/students/${id}`).then(setStudent).catch(() => setError(t('common.error')))
  }, [id, t])

  const detach = async () => {
    if (!student || !window.confirm(t('university.detachConfirm', { name: student.full_name }))) return
    setBusy(true)
    try {
      await api(`/university/students/${student.id}`, { method: 'DELETE' })
      onDetached()
      onClose()
    } catch {
      setError(t('common.error'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={id !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent closeLabel={t('common.close')}>
        <DialogTitle className="sr-only">{student?.full_name ?? t('university.student')}</DialogTitle>
        <DialogDescription className="sr-only">{t('university.subtitle')}</DialogDescription>
        <div className="overflow-y-auto p-6">
          {error && <p className="text-sm text-destructive">{error}</p>}
          {!student && !error && <Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />}
          {student && (
            <div className="space-y-6">
              {student.runs_completed > 0
                ? <CandidateProfileView profile={student} />
                : (
                  <div className="flex items-center gap-4 pr-8">
                    <Initials name={student.full_name} className="h-14 w-14 text-base" />
                    <div>
                      <h2 className="text-xl font-extrabold">{student.full_name}</h2>
                      <p className="text-sm text-muted-foreground">{t('university.noResultsYet')}</p>
                    </div>
                  </div>
                )}

              {student.in_progress.length > 0 && (
                <section className="space-y-2">
                  <h3 className="font-semibold">{t('university.inProgress')}</h3>
                  {student.in_progress.map((r) => (
                    <div key={r.scenario_title + r.ends_at} className="flex items-center justify-between gap-3 rounded-2xl border bg-background/60 px-4 py-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold">{r.scenario_title}</p>
                        <p className="text-xs text-muted-foreground">{t(`catalog.sector.${r.sector}`)} · {t('university.endsAt', { at: formatDateTime(r.ends_at) })}</p>
                      </div>
                      <Badge variant="outline">{t(`run.status.${r.status}`)}</Badge>
                    </div>
                  ))}
                </section>
              )}

              <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
                <a href={`mailto:${student.email}`} className="flex items-center gap-2 text-sm text-primary hover:underline">
                  <Mail className="h-4 w-4" /> {student.email}
                </a>
                <Button variant="ghost" size="sm" className="text-destructive" disabled={busy} onClick={detach}>
                  <UserMinus className="mr-1 h-4 w-4" /> {t('university.detach')}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">{t('university.privacyNote')}</p>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
