import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { Briefcase, CalendarDays, Search } from 'lucide-react'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from './Badge'
import { api, ApiError } from '@/lib/api'
import { formatDateTime } from '@/lib/time'
import type { RunCreated, RunSummary, Scenario } from '@/lib/types'

const OPEN = ['scheduled', 'active']

export default function SimulationsPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [query, setQuery] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [starting, setStarting] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([api<Scenario[]>('/scenarios'), api<RunSummary[]>('/runs/my')])
      .then(([s, r]) => {
        setScenarios(s)
        setRuns(r)
      })
      .catch(() => setError(t('common.error')))
  }, [t])

  const openRun = runs.find((r) => OPEN.includes(r.status))
  const q = query.trim().toLowerCase()
  const visible = scenarios.filter(
    (s) => !q || s.title.toLowerCase().includes(q) || s.company_name.toLowerCase().includes(q),
  )

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

  return (
    <div className="container mx-auto px-4 py-8 space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">{t('simulations.title')}</h1>
        <p className="text-muted-foreground mt-2">{t('catalog.subtitle')}</p>
      </div>

      {openRun && (
        <Card className="border-primary/40">
          <CardContent className="flex flex-wrap items-center justify-between gap-4 p-4">
            <div>
              <p className="font-medium">{openRun.scenario.title}</p>
              <p className="text-sm text-muted-foreground">
                {t('catalog.openRun', { date: formatDateTime(openRun.ends_at) })}
              </p>
            </div>
            <Button asChild>
              <Link to={`/runs/${openRun.id}`}>{t('catalog.continue')}</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input className="pl-9" placeholder={t('simulations.search')} value={query}
          onChange={(e) => setQuery(e.target.value)} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {visible.map((s) => (
          <Card key={s.id} className="flex flex-col">
            <CardHeader className="pb-3">
              <CardTitle className="text-base leading-snug">{s.title}</CardTitle>
              <CardDescription className="flex items-center gap-1 text-xs font-medium">
                <Briefcase className="h-3 w-3" /> {s.company_name}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex-1 space-y-3">
              <div className="flex flex-wrap gap-2">
                <Badge variant="secondary">{t(`catalog.sector.${s.sector}`)}</Badge>
                <Badge variant="outline">{s.difficulty}</Badge>
              </div>
              <p className="flex items-center text-xs text-muted-foreground">
                <CalendarDays className="h-3 w-3 mr-1" />
                {t('catalog.days', { count: s.duration_days })}
              </p>
            </CardContent>
            <CardFooter className="pt-3">
              <Button size="sm" className="w-full" disabled={Boolean(openRun) || starting !== null}
                onClick={() => start(s.id)}>
                {t('simulations.startSim')}
              </Button>
            </CardFooter>
          </Card>
        ))}
        {!error && scenarios.length === 0 && <p className="text-muted-foreground">{t('catalog.empty')}</p>}
      </div>

      {runs.some((r) => !OPEN.includes(r.status)) && (
        <section className="space-y-3">
          <h2 className="text-xl font-semibold">{t('catalog.history')}</h2>
          <div className="divide-y rounded-xl border">
            {runs.filter((r) => !OPEN.includes(r.status)).map((r) => (
              <div key={r.id} className="flex flex-wrap items-center justify-between gap-2 p-3 text-sm">
                <div>
                  <p className="font-medium">{r.scenario.title}</p>
                  <p className="text-muted-foreground">{formatDateTime(r.start_at)}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline">{t(`run.status.${r.status}`)}</Badge>
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
