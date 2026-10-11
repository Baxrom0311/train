import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check, Copy, Crown, Loader2, LogOut, Play, UserMinus, UsersRound, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from './Badge'
import { useAuth } from '@/context/AuthContext'
import { api, ApiError } from '@/lib/api'
import { formatDateTime, fromTashkentInput, toTashkentInput } from '@/lib/time'
import { cn } from '@/lib/utils'
import type { RunCreated, Team } from '@/lib/types'

/** Jamoa lobbysi (CONTRACT.md §29.2): taklif havolasi, rollarni band qilish, kapitan boshlaydi. */
export default function TeamPage() {
  const { id = '' } = useParams()
  const { t } = useTranslation()
  const { user } = useAuth()
  const navigate = useNavigate()
  const [team, setTeam] = useState<Team | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [missing, setMissing] = useState(false)
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState(false)
  const [startAt, setStartAt] = useState('')

  const load = useCallback(async () => {
    try {
      setTeam(await api<Team>(`/teams/${id}`))
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) setMissing(true)
      else setError(t('common.error'))
    }
  }, [id, t])

  // lobby jonli emas (SSE yo'q): a'zolar qo'shilishi va boshlanishi so'rov bilan ko'rinadi
  useEffect(() => {
    load()
    const poll = setInterval(load, 10_000)
    return () => clearInterval(poll)
  }, [load])

  // boshlangan jamoa — Run ish stoliga
  useEffect(() => {
    if (team?.run_id) navigate(`/runs/${team.run_id}`, { replace: true })
  }, [team?.run_id, navigate])

  const act = async (op: () => Promise<Team | void>) => {
    setBusy(true)
    setError(null)
    try {
      const next = await op()
      if (next) setTeam(next)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
      load()
    } finally {
      setBusy(false)
    }
  }

  if (missing) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 px-4 py-10">
        <p className="text-muted-foreground">{t('team.notFound')}</p>
        <Button variant="outline" asChild><Link to="/simulations">{t('team.back')}</Link></Button>
      </div>
    )
  }
  if (!team) {
    return <p className="mx-auto max-w-3xl px-4 py-10 text-muted-foreground">{error ?? t('common.loading')}</p>
  }

  const me = user?.id
  const forming = team.state === 'forming'
  const holder = (key: string) => team.members.find((m) => m.role === key)
  const maxSize = team.roles.length
  const missingCount = Math.max(0, team.min_size - team.members.length)
  const inviteUrl = `${window.location.origin}/teams/join/${team.invite_code}`

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(inviteUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }

  const claim = (role: string | null) =>
    act(() => api<Team>(`/teams/${team.id}/role`, { method: 'PUT', json: { role } }))
  const remove = (memberId: string, name: string) => {
    if (!window.confirm(t('team.removeConfirm', { name }))) return
    act(() => api<Team>(`/teams/${team.id}/members/${memberId}/remove`, { method: 'POST' }))
  }
  const leave = () => {
    if (!window.confirm(t('team.leaveConfirm'))) return
    act(async () => {
      await api(`/teams/${team.id}/leave`, { method: 'POST' })
      navigate('/simulations')
    })
  }
  const disband = () => {
    if (!window.confirm(t('team.disbandConfirm'))) return
    act(() => api<Team>(`/teams/${team.id}/disband`, { method: 'POST' }))
  }
  const start = () =>
    act(async () => {
      const created = await api<RunCreated>(`/teams/${team.id}/start`, {
        method: 'POST',
        json: { start_at: startAt ? fromTashkentInput(startAt) : null },
      })
      navigate(`/runs/${created.run.id}`, { state: { warning: created.warning } })
    })

  return (
    <div className="mx-auto max-w-4xl space-y-6 px-4 py-8">
      <div className="animate-rise space-y-2">
        <Button variant="ghost" size="sm" asChild className="-ml-2">
          <Link to="/simulations"><ArrowLeft className="h-4 w-4" /> {t('team.back')}</Link>
        </Button>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-extrabold tracking-tight">{team.scenario.title}</h1>
          <Badge variant={forming ? 'default' : 'secondary'}>{t(`team.state.${team.state}`)}</Badge>
        </div>
        <p className="text-muted-foreground">{t('team.title')} · {team.scenario.company_name}</p>
      </div>

      {error && <p className="glass rounded-2xl px-4 py-2.5 text-sm text-destructive">{error}</p>}

      {forming && (
        <section className="glass glow-ring space-y-3 rounded-3xl p-5">
          <h2 className="font-bold">{t('team.invite')}</h2>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Input readOnly value={inviteUrl} className="font-mono text-xs" aria-label={t('team.invite')}
              onFocus={(e) => e.currentTarget.select()} />
            <Button type="button" variant="outline" onClick={copy} className="shrink-0">
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              {copied ? t('team.copied') : t('team.copy')}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            {t('team.inviteHint', { date: formatDateTime(team.expires_at) })}
            <span className="ml-2 font-mono font-semibold tracking-widest text-foreground/80">{team.invite_code}</span>
          </p>
        </section>
      )}

      <section className="space-y-3">
        <div>
          <h2 className="text-xl font-bold">{t('team.roles')}</h2>
          {forming && <p className="text-sm text-muted-foreground">{t('team.rolesHint')}</p>}
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {team.roles.map((r) => {
            const owner = holder(r.key)
            const mine = owner?.user_id === me
            return (
              <div key={r.key} className={cn('glass flex flex-col gap-3 rounded-2xl p-4', mine && 'ring-2 ring-primary/40')}>
                <div className="flex-1 space-y-1">
                  <p className="font-bold">{r.title}</p>
                  <p className="text-sm text-muted-foreground">{r.summary}</p>
                </div>
                <div className="flex items-center justify-between gap-2 text-sm">
                  <span className={cn('truncate', owner ? 'font-medium' : 'text-muted-foreground')}>
                    {owner ? `${owner.name}${mine ? ` (${t('team.you')})` : ''}` : t('team.free')}
                  </span>
                  {forming && (mine ? (
                    <Button size="sm" variant="ghost" disabled={busy} onClick={() => claim(null)}>
                      <X className="h-4 w-4" /> {t('team.release')}
                    </Button>
                  ) : !owner && (
                    <Button size="sm" variant="outline" disabled={busy} onClick={() => claim(r.key)}>
                      {t('team.take')}
                    </Button>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="flex items-center gap-2 text-xl font-bold">
          <UsersRound className="h-5 w-5 text-primary" /> {t('team.members')}
          <span className="text-sm font-medium text-muted-foreground">{t('team.membersCount', { count: team.members.length, max: maxSize })}</span>
        </h2>
        <ul className="glass divide-y divide-border/60 rounded-2xl">
          {team.members.map((m) => (
            <li key={m.user_id} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3 text-sm">
              <div className="flex items-center gap-2">
                {m.is_captain && <Crown className="h-4 w-4 text-amber-500" aria-label={t('team.captain')} />}
                <span className="font-medium">{m.name}{m.user_id === me && ` (${t('team.you')})`}</span>
                {m.role && <Badge variant="outline">{team.roles.find((r) => r.key === m.role)?.title ?? m.role}</Badge>}
              </div>
              {forming && team.is_captain && !m.is_captain && (
                <Button size="sm" variant="ghost" disabled={busy} onClick={() => remove(m.user_id, m.name)}>
                  <UserMinus className="h-4 w-4" /> {t('team.remove')}
                </Button>
              )}
            </li>
          ))}
        </ul>
      </section>

      {forming && team.is_captain && (
        <section className="glass-strong space-y-4 rounded-3xl p-5">
          <div className="grid gap-3 sm:grid-cols-[minmax(0,16rem)_1fr] sm:items-end">
            <div className="space-y-1.5">
              <label htmlFor="team-start-at" className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t('team.startAt')}</label>
              <Input id="team-start-at" type="datetime-local" value={startAt} min={toTashkentInput(new Date())}
                onChange={(e) => setStartAt(e.target.value)} />
            </div>
            <p className="text-xs text-muted-foreground">{t('team.startAtHint')}</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button disabled={busy || missingCount > 0} onClick={start}>
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {startAt ? t('team.start') : t('team.startNow')}
            </Button>
            {missingCount > 0 && <span className="text-sm text-muted-foreground">{t('team.needMore', { count: missingCount })}</span>}
            <Button variant="ghost" className="ml-auto text-destructive" disabled={busy} onClick={disband}>
              {t('team.disband')}
            </Button>
          </div>
        </section>
      )}

      {forming && !team.is_captain && (
        <section className="glass flex flex-wrap items-center justify-between gap-3 rounded-3xl p-5">
          <p className="text-sm text-muted-foreground">{t('team.waitCaptain')}</p>
          <Button variant="outline" disabled={busy} onClick={leave}>
            <LogOut className="h-4 w-4" /> {t('team.leave')}
          </Button>
        </section>
      )}

      {team.run_id && (
        <Button asChild>
          <Link to={`/runs/${team.run_id}`}>{t('team.openRun')} <ArrowRight className="h-4 w-4" /></Link>
        </Button>
      )}
    </div>
  )
}
