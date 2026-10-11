import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowRight, Briefcase, Loader2, UsersRound } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from './Badge'
import { api, ApiError } from '@/lib/api'
import { formatDateTime } from '@/lib/time'
import type { Team, TeamInvite } from '@/lib/types'

/** Taklif havolasi `/teams/join/{code}` (CONTRACT.md §29.2): kim, qaysi ssenariy, bo'sh rollar — qo'shilish. */
export default function TeamJoinPage() {
  const { code = '' } = useParams()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [invite, setInvite] = useState<TeamInvite | null>(null)
  const [missing, setMissing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api<TeamInvite>(`/teams/invite/${encodeURIComponent(code)}`)
      .then(setInvite)
      .catch((err) => (err instanceof ApiError && err.status === 404 ? setMissing(true) : setError(t('common.error'))))
  }, [code, t])

  const join = async () => {
    setBusy(true)
    setError(null)
    try {
      const team = await api<Team>(`/teams/invite/${encodeURIComponent(code)}/join`, { method: 'POST' })
      navigate(`/teams/${team.id}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
      setBusy(false)
    }
  }

  if (missing) {
    return (
      <div className="mx-auto max-w-xl space-y-4 px-4 py-10">
        <p className="text-muted-foreground">{t('team.join.notFound')}</p>
        <Button variant="outline" asChild><Link to="/simulations">{t('team.back')}</Link></Button>
      </div>
    )
  }
  if (!invite) return <p className="mx-auto max-w-xl px-4 py-10 text-muted-foreground">{error ?? t('common.loading')}</p>

  const open = invite.state === 'forming'
  const full = invite.members >= invite.roles.length

  return (
    <div className="mx-auto max-w-xl px-4 py-10">
      <section className="glass-strong animate-rise space-y-5 rounded-3xl p-6">
        <div className="flex items-center gap-3">
          <span className="bg-brand grid h-12 w-12 place-items-center rounded-2xl text-primary-foreground">
            <UsersRound className="h-6 w-6" />
          </span>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t('team.join.title')}</p>
            <h1 className="text-xl font-extrabold">{invite.scenario.title}</h1>
          </div>
        </div>
        <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <Briefcase className="h-4 w-4" /> {invite.scenario.company_name}
        </p>
        <p className="font-medium">{t('team.join.by', { name: invite.captain_name })}</p>

        <ul className="space-y-2">
          {invite.roles.map((r) => {
            const taken = invite.taken_roles.includes(r.key)
            return (
              <li key={r.key} className="flex items-start justify-between gap-3 rounded-2xl border bg-background/50 p-3 text-sm">
                <div>
                  <p className="font-semibold">{r.title}</p>
                  <p className="text-muted-foreground">{r.summary}</p>
                </div>
                <Badge variant={taken ? 'secondary' : 'outline'}>{taken ? '✓' : t('team.free')}</Badge>
              </li>
            )
          })}
        </ul>

        <p className="text-xs text-muted-foreground">
          {t('team.join.members', { count: invite.members })} · {t('team.inviteHint', { date: formatDateTime(invite.expires_at) })}
        </p>

        {error && <p className="text-sm text-destructive">{error}</p>}

        {invite.is_member ? (
          <Button asChild className="w-full">
            <Link to={`/teams/${invite.id}`}>{t('team.join.toLobby')} <ArrowRight className="h-4 w-4" /></Link>
          </Button>
        ) : open && !full ? (
          <Button className="w-full" disabled={busy} onClick={join}>
            {busy && <Loader2 className="h-4 w-4 animate-spin" />} {t('team.join.join')}
          </Button>
        ) : (
          <p className="rounded-2xl bg-muted/60 px-4 py-3 text-sm text-muted-foreground">
            {open ? t('team.join.closed') : t(`team.state.${invite.state}`)}
          </p>
        )}
      </section>
    </div>
  )
}
