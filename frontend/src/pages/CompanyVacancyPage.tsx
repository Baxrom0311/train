// /company/vacancies/:id (CONTRACT.md §23.8): vakansiya, arizalar va mos nomzodlar.
// Ariza — talabaning roziligi: yopiq profil ham shu yerda ko'rinadi; email faqat taklif qabul qilinganda.
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Inbox, Loader2, Pencil, Send, Sparkles, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Segmented } from '@/components/ui/segmented'
import { CompetencyBars, ScoreRing } from '@/components/score'
import Initials from '@/components/talent/Initials'
import OfferForm from '@/components/talent/OfferForm'
import { ApplicationBadge, FitBadge, GapChips, VacancyMeta, VacancyStatusBadge } from '@/components/vacancies/parts'
import { api, ApiError } from '@/lib/api'
import { formatDateTime } from '@/lib/time'
import type { CandidateCard, CompanyApplication, CompanyVacancy, Fit, VacancyMatch } from '@/lib/types'

type Tab = 'applications' | 'matches'

export default function CompanyVacancyPage() {
  const { id = '' } = useParams()
  const { t } = useTranslation()
  const [vacancy, setVacancy] = useState<CompanyVacancy | null>(null)
  const [applications, setApplications] = useState<CompanyApplication[] | null>(null)
  const [matches, setMatches] = useState<VacancyMatch[] | null>(null)
  const [tab, setTab] = useState<Tab>('applications')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [offerTo, setOfferTo] = useState<CandidateCard | null>(null)

  const load = useCallback(async () => {
    try {
      const [v, a, m] = await Promise.all([
        api<CompanyVacancy>(`/company/vacancies/${id}`),
        api<CompanyApplication[]>(`/company/vacancies/${id}/applications`),
        api<VacancyMatch[]>(`/company/vacancies/${id}/matches`),
      ])
      setVacancy(v)
      setApplications(a)
      setMatches(m)
    } catch (err) {
      setError(err instanceof ApiError && err.status === 404 ? t('vacancy.notFound') : t('common.error'))
    }
  }, [id, t])
  useEffect(() => { load() }, [load])

  const setStatus = async (status: 'open' | 'closed') => {
    setBusy(true)
    setError(null)
    try {
      setVacancy(await api<CompanyVacancy>(`/company/vacancies/${id}/status`, { method: 'POST', json: { status } }))
    } catch (err) {
      setError(err instanceof ApiError && err.status === 409 ? t('vacancy.editor.limit') : t('common.error'))
    } finally {
      setBusy(false)
    }
  }

  const reject = async (a: CompanyApplication) => {
    if (!window.confirm(t('vacancy.company.rejectConfirm', { name: a.candidate.full_name }))) return
    try {
      await api(`/company/vacancies/${id}/applications/${a.id}/reject`, { method: 'POST' })
      await load()
    } catch {
      setError(t('common.error'))
    }
  }

  if (!vacancy) {
    return <div className="grid place-items-center py-24">{error ? <p className="text-destructive">{error}</p> : <Loader2 className="h-6 w-6 animate-spin text-primary" />}</div>
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-8">
      <div className="flex items-start gap-3 animate-rise">
        <Button variant="ghost" size="icon" asChild aria-label={t('common.back')}>
          <Link to="/company/vacancies"><ArrowLeft className="h-4 w-4" /></Link>
        </Button>
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-3xl font-extrabold tracking-tight">{vacancy.title}</h1>
            <VacancyStatusBadge status={vacancy.status} />
          </div>
          <VacancyMeta vacancy={vacancy} />
        </div>
      </div>

      <div className="flex flex-wrap gap-2 animate-rise">
        <Button variant="outline" asChild>
          <Link to={`/company/vacancies/${id}/edit`}><Pencil className="h-4 w-4" /> {t('common.edit')}</Link>
        </Button>
        {vacancy.status === 'open' ? (
          <Button variant="outline" disabled={busy} onClick={() => setStatus('closed')}>{t('vacancy.company.close')}</Button>
        ) : (
          <Button disabled={busy} onClick={() => setStatus('open')}>
            <Send className="h-4 w-4" /> {t(vacancy.status === 'draft' ? 'vacancy.editor.publish' : 'vacancy.company.reopen')}
          </Button>
        )}
      </div>

      <section className="glass grid gap-4 rounded-3xl p-5 sm:grid-cols-[minmax(0,1fr)_16rem]">
        <p className="whitespace-pre-line text-sm leading-relaxed">{vacancy.description}</p>
        <div className="space-y-2 text-sm">
          <p className="font-semibold">{t('vacancy.requirements')}</p>
          {Object.keys(vacancy.requirements).length === 0 && <p className="text-xs text-muted-foreground">{t('vacancy.noRequirements')}</p>}
          <ul className="space-y-1">
            {Object.entries(vacancy.requirements).map(([k, v]) => (
              <li key={k} className="flex justify-between gap-2"><span>{t(`competency.${k}`)}</span><span className="font-bold tabular-nums">≥ {v}</span></li>
            ))}
            {vacancy.min_score !== null && (
              <li className="flex justify-between gap-2 border-t pt-1"><span>{t('vacancy.minScore')}</span><span className="font-bold tabular-nums">≥ {vacancy.min_score}</span></li>
            )}
          </ul>
        </div>
      </section>

      {error && <p className="glass rounded-2xl px-4 py-3 text-sm text-destructive">{error}</p>}

      <Segmented<Tab> label={t('vacancy.company.sections')} value={tab} onChange={setTab} options={[
        { value: 'applications', label: `${t('vacancy.company.applications')} (${vacancy.counts.applications})` },
        { value: 'matches', label: `${t('vacancy.company.matches')} (${matches?.length ?? 0})` },
      ]} />

      {tab === 'applications' && (
        <List empty={t('vacancy.company.noApplications')} Icon={Inbox} items={applications}>
          {applications?.map((a) => (
            <CandidateRow key={a.id} candidate={a.candidate} fit={a.fit}
              aside={<><ApplicationBadge status={a.status} /><span className="text-xs text-muted-foreground">{formatDateTime(a.created_at)}</span></>}
              note={a.note}
              actions={a.status === 'applied' && (
                <>
                  <Button size="sm" onClick={() => setOfferTo(a.candidate)}><Send className="h-4 w-4" /> {t('vacancy.company.offer')}</Button>
                  <Button size="sm" variant="ghost" onClick={() => reject(a)}><X className="h-4 w-4" /> {t('vacancy.company.reject')}</Button>
                </>
              )} />
          ))}
        </List>
      )}
      {tab === 'matches' && (
        <List empty={t('vacancy.company.noMatches')} Icon={Sparkles} items={matches}>
          <p className="text-xs text-muted-foreground">{t('vacancy.company.matchesHint')}</p>
          {matches?.map((m) => (
            <CandidateRow key={m.id} candidate={m} fit={m.fit}
              aside={m.applied && <span className="text-xs font-semibold text-primary">{t('vacancy.company.alreadyApplied')}</span>}
              actions={<Button size="sm" variant="outline" onClick={() => setOfferTo(m)}><Send className="h-4 w-4" /> {t('vacancy.company.offer')}</Button>} />
          ))}
        </List>
      )}

      <Dialog open={offerTo !== null} onOpenChange={(open) => !open && setOfferTo(null)}>
        <DialogContent closeLabel={t('common.close')} aria-describedby={undefined}>
          <DialogTitle className="sr-only">{t('talent.offer.title')}</DialogTitle>
          {offerTo && (
            <div className="space-y-4 overflow-y-auto p-6">
              <div className="flex items-center gap-3 pr-8">
                <Initials name={offerTo.full_name} />
                <p className="font-bold">{offerTo.full_name}</p>
              </div>
              <OfferForm candidateId={offerTo.id} vacancyId={vacancy.id} defaultPosition={vacancy.title} onSent={load} />
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

function List({ items, empty, Icon, children }: { items: unknown[] | null; empty: string; Icon: typeof Inbox; children: React.ReactNode }) {
  if (items === null) return <Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />
  if (!items.length) {
    return (
      <div className="glass flex flex-col items-center gap-2 rounded-2xl px-6 py-12 text-center">
        <Icon className="h-7 w-7 text-muted-foreground" />
        <p className="max-w-md text-sm text-muted-foreground">{empty}</p>
      </div>
    )
  }
  return <div className="space-y-3">{children}</div>
}

function CandidateRow({ candidate: c, fit, aside, note, actions }: {
  candidate: CandidateCard
  fit: Fit
  aside?: React.ReactNode
  note?: string | null
  actions?: React.ReactNode
}) {
  const { t } = useTranslation()
  return (
    <Card className="animate-rise">
      <CardContent className="grid gap-4 p-5 md:grid-cols-[minmax(0,1fr)_14rem]">
        <div className="min-w-0 space-y-3">
          <div className="flex items-center gap-3">
            <Initials name={c.full_name} />
            <div className="min-w-0 flex-1">
              <p className="truncate font-bold">{c.full_name}</p>
              <p className="text-xs text-muted-foreground">
                {t('talent.runsCompleted', { count: c.runs_completed })}
                {c.sectors.length > 0 && ' · ' + c.sectors.map((s) => t(`catalog.sector.${s}`)).join(', ')}
              </p>
            </div>
            {c.overall_score !== null && <ScoreRing value={c.overall_score} size={48} />}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <FitBadge fit={fit} />
            {fit.sector_match && <span className="text-xs text-muted-foreground">{t('vacancy.fit.sectorMatch')}</span>}
            {aside}
          </div>
          <GapChips gaps={fit.gaps} />
          {note && <p className="rounded-xl bg-muted/50 px-3 py-2 text-sm italic">“{note}”</p>}
          {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
        </div>
        <CompetencyBars scores={c.top_competencies} compact />
      </CardContent>
    </Card>
  )
}
