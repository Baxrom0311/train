import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, Briefcase, CalendarDays, Search, User, Users, UsersRound } from 'lucide-react'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from './Badge'
import { SECTOR_ART } from '@/components/sectorArt'
import { api, ApiError } from '@/lib/api'
import { formatDateTime } from '@/lib/time'
import { SECTORS, type RunCreated, type RunSummary, type Scenario, type Sector, type Team } from '@/lib/types'

const OPEN = ['scheduled', 'active']

const CHIP = 'rounded-full border px-3.5 py-1.5 text-sm font-medium transition-colors'
const CHIP_ON = 'border-primary/50 bg-primary/15 text-primary'
const CHIP_OFF = 'border-border/60 bg-background/40 text-muted-foreground hover:text-foreground'

export default function SimulationsPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [teams, setTeams] = useState<Team[]>([])
  const [query, setQuery] = useState('')
  const [sector, setSector] = useState<Sector | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [starting, setStarting] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([api<Scenario[]>('/scenarios'), api<RunSummary[]>('/runs/my'), api<Team[]>('/teams/my')])
      .then(([s, r, tm]) => {
        setScenarios(s)
        setRuns(r)
        setTeams(tm)
      })
      .catch(() => setError(t('common.error')))
  }, [t])

  // jamoadan chiqilgan Run (§29.3) — faqat tarixda, hisobot bilan
  const isOpen = (r: RunSummary) => OPEN.includes(r.status) && !r.left
  const openRun = runs.find(isOpen)
  const history = runs.filter((r) => !isOpen(r))
  const teamFor = (scenarioId: string) => teams.find((x) => x.scenario.id === scenarioId)
  const q = query.trim().toLowerCase()
  const visible = scenarios.filter(
    (s) => (!sector || s.sector === sector)
      && (!q || s.title.toLowerCase().includes(q) || s.company_name.toLowerCase().includes(q)),
  )
  // filtrda faqat katalogda bor sohalar
  const sectors = SECTORS.filter((x) => scenarios.some((s) => s.sector === x))

  const start = async (scenarioId: string) => {
    setStarting(scenarioId)
    setError(null)
    try {
      const created = await api<RunCreated>('/runs', { method: 'POST', json: { scenario_id: scenarioId } })
      navigate(`/runs/${created.run.id}`, { state: { warning: created.warning } })
    } catch (err) {
      setError(err instanceof ApiError && err.status === 409 ? t('catalog.alreadyOpen') : t('common.error'))
      setStarting(null)
    }
  }

  // §29.2: kapitan jamoa tuzadi — lobbyga o'tadi va havolani ulashadi
  const formTeam = async (scenarioId: string) => {
    setStarting(scenarioId)
    setError(null)
    try {
      const team = await api<Team>('/teams', { method: 'POST', json: { scenario_id: scenarioId } })
      navigate(`/teams/${team.id}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
      setStarting(null)
    }
  }

  return (
    <div className="mx-auto max-w-7xl space-y-8 px-4 py-8">
      <div className="animate-rise space-y-2">
        <h1 className="text-4xl font-extrabold tracking-tight">{t('simulations.title')}</h1>
        <p className="max-w-2xl text-muted-foreground">{t('catalog.subtitle')}</p>
      </div>

      {openRun && (
        <div className="glass glow-ring animate-rise flex flex-wrap items-center justify-between gap-4 rounded-2xl p-5">
          <div className="flex items-center gap-4">
            <span className="grid h-11 w-11 place-items-center rounded-xl bg-primary/15 text-primary">
              <span className="h-2.5 w-2.5 rounded-full bg-primary animate-glow" />
            </span>
            <div>
              <p className="font-bold">{openRun.scenario.title}</p>
              <p className="text-sm text-muted-foreground">
                {t('catalog.openRun', { date: formatDateTime(openRun.ends_at) })}
              </p>
            </div>
          </div>
          <Button asChild>
            <Link to={`/runs/${openRun.id}`}>
              {t('catalog.continue')} <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>
      )}

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="relative w-full max-w-sm">
          <Search className="pointer-events-none absolute z-10 left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input className="pl-10" placeholder={t('simulations.search')} value={query}
            onChange={(e) => setQuery(e.target.value)} />
        </div>
        {sectors.length > 1 && (
          <div className="flex flex-wrap gap-2" role="group" aria-label={t('talent.filter.sector')}>
            <button type="button" aria-pressed={sector === null} onClick={() => setSector(null)}
              className={`${CHIP} ${sector === null ? CHIP_ON : CHIP_OFF}`}>
              {t('talent.filter.any')}
            </button>
            {sectors.map((x) => (
              <button key={x} type="button" aria-pressed={sector === x} onClick={() => setSector(sector === x ? null : x)}
                className={`${CHIP} ${sector === x ? CHIP_ON : CHIP_OFF}`}>
                {t(`catalog.sector.${x}`)}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
        {visible.map((s, i) => {
          const art = SECTOR_ART[s.sector]
          return (
            <Card key={s.id} style={{ animationDelay: `${i * 60}ms` }}
              className="group animate-rise flex flex-col overflow-hidden transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_24px_60px_-20px_hsl(var(--primary)/0.45)]">
              <div className={`relative h-32 overflow-hidden bg-gradient-to-br ${art.glow}`}>
                <art.Icon className="absolute -right-4 -bottom-6 h-36 w-36 text-foreground/10 transition-transform duration-500 group-hover:scale-110 group-hover:-rotate-6" />
                <div className="absolute left-5 top-5 flex gap-2">
                  <Badge variant="outline">{t(`catalog.sector.${s.sector}`)}</Badge>
                  <Badge variant="outline">{s.difficulty}</Badge>
                </div>
                {s.team && (
                  <span className="absolute bottom-3 left-5 inline-flex items-center gap-1.5 rounded-full bg-background/80 px-2.5 py-1 text-xs font-semibold text-primary shadow-sm">
                    <UsersRound className="h-3.5 w-3.5" /> {t('catalog.teamBadge', { min: s.team.min_size, max: s.team.max_size })}
                  </span>
                )}
              </div>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">{s.title}</CardTitle>
                <CardDescription className="flex items-center gap-1.5 font-medium">
                  <Briefcase className="h-3.5 w-3.5" /> {s.company_name}
                </CardDescription>
              </CardHeader>
              <CardContent className="flex-1">
                <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1.5">
                    <CalendarDays className="h-3.5 w-3.5" /> {t('catalog.days', { count: s.duration_days })}
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Users className="h-3.5 w-3.5" /> {t('catalog.realTime')}
                  </span>
                </div>
              </CardContent>
              <CardFooter className="gap-2">
                {s.team ? (
                  <TeamActions scenario={s} team={teamFor(s.id)} busy={Boolean(openRun) || starting !== null}
                    onForm={() => formTeam(s.id)} onSolo={() => start(s.id)} />
                ) : (
                  <Button className="w-full" disabled={Boolean(openRun) || starting !== null} onClick={() => start(s.id)}>
                    {t('simulations.startSim')} <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                  </Button>
                )}
              </CardFooter>
            </Card>
          )
        })}
        {!error && visible.length === 0 && (
          <p className="text-muted-foreground">{t(scenarios.length ? 'catalog.noMatch' : 'catalog.empty')}</p>
        )}
      </div>

      {teams.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-xl font-bold">{t('catalog.myTeams')}</h2>
          <div className="glass divide-y divide-border/60 rounded-2xl">
            {teams.map((tm) => (
              <div key={tm.id} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3.5 text-sm">
                <div>
                  <p className="font-medium">{tm.scenario.title}</p>
                  <p className="text-muted-foreground">
                    {t('catalog.teamMembers', { count: tm.members.length })} · {tm.members.map((m) => m.name).join(', ')}
                  </p>
                </div>
                <Button size="sm" asChild>
                  <Link to={`/teams/${tm.id}`}>{t('catalog.toLobby')} <ArrowRight className="h-4 w-4" /></Link>
                </Button>
              </div>
            ))}
          </div>
        </section>
      )}

      {history.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-xl font-bold">{t('catalog.history')}</h2>
          <div className="glass divide-y divide-border/60 rounded-2xl">
            {history.map((r) => (
              <div key={r.id} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3.5 text-sm">
                <div>
                  <p className="font-medium">{r.scenario.title}</p>
                  <p className="text-muted-foreground">{formatDateTime(r.start_at)}</p>
                </div>
                <div className="flex items-center gap-2">
                  {r.team_size !== null && (
                    <Badge variant="outline" className="gap-1"><UsersRound className="h-3 w-3" /> {t('catalog.teamRun')}</Badge>
                  )}
                  <Badge variant="outline">{r.left ? t('catalog.left') : t(`run.status.${r.status}`)}</Badge>
                  <Button size="sm" variant="outline" asChild>
                    <Link to={`/runs/${r.id}/report`}>{t('catalog.report')}</Link>
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

/** Jamoaviy ssenariy (§29): jamoa tuzish yoki yakka o'tish; yig'ilayotgan jamoa bo'lsa — lobbyga. */
function TeamActions({ scenario, team, busy, onForm, onSolo }: {
  scenario: Scenario
  team: Team | undefined
  busy: boolean
  onForm: () => void
  onSolo: () => void
}) {
  const { t } = useTranslation()
  if (team) {
    return (
      <Button className="w-full" asChild>
        <Link to={`/teams/${team.id}`}>
          <UsersRound className="h-4 w-4" /> {t('catalog.toLobby')}
        </Link>
      </Button>
    )
  }
  return (
    <>
      <Button className="flex-1" disabled={busy} onClick={onForm} aria-label={`${t('catalog.formTeam')}: ${scenario.title}`}>
        <UsersRound className="h-4 w-4" /> {t('catalog.formTeam')}
      </Button>
      <Button variant="outline" disabled={busy} onClick={onSolo} title={t('catalog.soloHint')}>
        <User className="h-4 w-4" /> {t('catalog.solo')}
      </Button>
    </>
  )
}
