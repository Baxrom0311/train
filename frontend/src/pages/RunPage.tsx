import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ArrowLeft, Crown, Inbox as InboxIcon, LogOut, Moon, Sun, Sunrise, Sunset, UsersRound, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from './Badge'
import { cn } from '@/lib/utils'
import { api, ApiError } from '@/lib/api'
import { subscribeRun, type RunNote } from '@/lib/sse'
import { daypart, formatDateTime, formatTime, workdayProgress, type Daypart } from '@/lib/time'
import type { Persona, RunDetail, RunTeam } from '@/lib/types'
import Inbox, { isActionable, isMine } from '@/components/desk/Inbox'
import EventDetail from '@/components/desk/EventDetail'
import ChatPanel from '@/components/desk/ChatPanel'
import DocumentDialog from '@/components/desk/DocumentDialog'
import Avatar from '@/components/desk/Avatar'

type Pane = 'inbox' | 'event' | 'chat'

// jamoa chati kanali (backend `TEAM_CHANNEL`, §29.3) — personaj kalitlari bilan bir qatorda
const TEAM_CHAT = '_team'

export default function RunPage() {
  const { id = '' } = useParams()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const warning = (useLocation().state as { warning?: string | null } | null)?.warning
  const [params, setParams] = useSearchParams()
  const wanted = params.get('event')
  const [run, setRun] = useState<RunDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [persona, setPersona] = useState<string | null>(null)
  const [unread, setUnread] = useState<Record<string, number>>({})
  const [chatRefresh, setChatRefresh] = useState(0)
  const [doc, setDoc] = useState<string | null>(null)
  const [pane, setPane] = useState<Pane>('inbox')
  const [offset, setOffset] = useState(0) // server − mijoz soati
  const [tick, setTick] = useState(Date.now())
  const known = useRef<Set<string>>(new Set())
  const personaRef = useRef<string | null>(null)
  personaRef.current = persona

  const applyRun = useCallback((r: RunDetail) => {
    setOffset(new Date(r.now).getTime() - Date.now())
    setRun(r)
    // yangi kelgan skript xabarlar — o'sha personaj chatida o'qilmagan
    const fresh = r.events.filter((e) => !known.current.has(e.node_id))
    if (known.current.size > 0) {
      setUnread((u) => {
        const next = { ...u }
        for (const e of fresh) {
          if (e.from_persona && e.from_persona !== personaRef.current) next[e.from_persona] = (next[e.from_persona] ?? 0) + 1
        }
        return next
      })
    }
    fresh.forEach((e) => known.current.add(e.node_id))
  }, [])

  const load = useCallback(async () => {
    try {
      applyRun(await api<RunDetail>(`/runs/${id}`))
    } catch (err) {
      setError(err instanceof ApiError && err.status === 404 ? t('desk.notFound') : t('common.error'))
    }
  }, [id, applyRun, t])

  // SSE + zaxira so'rov (cron/aloqa kechiksa ham holat yangilanadi)
  useEffect(() => {
    load()
    let timer: ReturnType<typeof setTimeout> | undefined
    const reload = () => {
      clearTimeout(timer)
      timer = setTimeout(load, 300)
    }
    const stop = subscribeRun(id, (note: RunNote) => {
      if (note.type === 'chat_message' || note.type === 'hint' || note.type === 'event_delivered') {
        const key = note.persona_key as string | undefined
        if (!key || key === personaRef.current) setChatRefresh((n) => n + 1)
        else setUnread((u) => ({ ...u, [key]: (u[key] ?? 0) + 1 }))
      }
      reload()
    })
    const poll = setInterval(load, 60_000)
    return () => {
      stop()
      clearInterval(poll)
      clearTimeout(timer)
    }
  }, [id, load])

  useEffect(() => {
    const i = setInterval(() => setTick(Date.now()), 15_000)
    return () => clearInterval(i)
  }, [])
  const now = tick + offset

  // birinchi yuklanishda — eng eski javob kutayotgan hodisa, bo'lmasa oxirgisi
  useEffect(() => {
    if (!run || selected) return
    const first = run.events.find((e) => isActionable(e) && isMine(e, run.team)) ?? run.events[run.events.length - 1]
    if (first) setSelected(first.node_id)
    if (!persona && run.personas.length) setPersona(run.personas[0].key)
  }, [run, selected, persona])

  // bildirishnoma havolasi `?event=` (§22.2) — o'sha hodisa ochiladi, parametr URL'dan olib tashlanadi
  useEffect(() => {
    if (!run || !wanted) return
    if (run.events.some((e) => e.node_id === wanted)) {
      setSelected(wanted)
      setPane('event')
    }
    setParams((p) => {
      p.delete('event')
      return p
    }, { replace: true })
  }, [run, wanted, setParams])

  const event = useMemo(() => run?.events.find((e) => e.node_id === selected) ?? null, [run, selected])
  const activePersona = run?.personas.find((p) => p.key === persona) ?? null
  const mentor = run?.personas.find((p) => p.kind === 'mentor') ?? null
  const openChat = (key: string) => {
    setPersona(key)
    setUnread((u) => ({ ...u, [key]: 0 }))
    setPane('chat')
  }
  const pendingCount = run?.events.filter((e) => isActionable(e) && isMine(e, run.team)).length ?? 0
  const unreadCount = Object.values(unread).reduce((a, b) => a + b, 0)
  const badge: Record<Pane, number> = { inbox: pendingCount, event: 0, chat: unreadCount }

  const abandon = async () => {
    if (!run || !window.confirm(t(run.team ? 'desk.team.abandonConfirm' : 'desk.abandonConfirm'))) return
    try {
      applyRun(await api<RunDetail>(`/runs/${run.id}/abandon`, { method: 'POST' }))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    }
  }

  // §29.3: kapitandan boshqa a'zo jamoadan chiqadi — Run jamoa uchun davom etadi
  const leave = async () => {
    if (!run || !window.confirm(t('desk.team.leaveConfirm'))) return
    try {
      await api(`/runs/${run.id}/leave`, { method: 'POST' })
      navigate('/simulations')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    }
  }

  // fon yorug'ligi Toshkent vaqtiga ergashadi (index.css: [data-daypart])
  const part = daypart(new Date(now))
  useEffect(() => {
    document.documentElement.dataset.daypart = part
    return () => {
      delete document.documentElement.dataset.daypart
    }
  }, [part])

  if (error && !run) return <p className="mx-auto max-w-7xl p-8 text-destructive">{error}</p>
  if (!run) return <p className="mx-auto max-w-7xl p-8 text-muted-foreground">{t('common.loading')}</p>

  const closed = !['active', 'scheduled'].includes(run.status)
  const team = run.team
  // jamoaviy Run'ni faqat kapitan to'xtatadi, qolganlar — chiqadi
  const member = team !== null && team.captain_id !== team.me

  return (
    <div className="h-desk mx-auto flex max-w-[1600px] flex-col gap-2 p-2 sm:gap-3 sm:p-3">
      <header className="glass flex items-center justify-between gap-2 rounded-2xl px-2 py-2 animate-rise sm:flex-wrap sm:gap-3 sm:px-4 sm:py-3">
        <div className="flex min-w-0 flex-1 items-center gap-1 sm:gap-3">
          <Button variant="ghost" size="icon" asChild aria-label={t('nav.simulations')}>
            <Link to="/simulations"><ArrowLeft className="h-4 w-4" /></Link>
          </Button>
          <div className="min-w-0">
            <h1 className="line-clamp-2 text-sm font-bold leading-tight sm:truncate sm:text-base">{run.scenario.title}</h1>
            <p className="hidden text-xs text-muted-foreground sm:block">{run.scenario.company_name}</p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1 sm:gap-3">
          <DeskClock now={now} part={part} off={run.status === 'active' && !run.is_work_time} />
          {/* telefonda faol holat belgisi tushiriladi — joy sarlavhaga */}
          <Badge variant={closed ? 'secondary' : 'default'} className={cn(!closed && 'hidden sm:inline-flex')}>{t(`run.status.${run.status}`)}</Badge>
          {closed ? (
            <Button size="sm" asChild>
              <Link to={`/runs/${run.id}/report`}>{t('catalog.report')}</Link>
            </Button>
          ) : member ? (
            <Button size="sm" variant="ghost" onClick={leave} aria-label={t('desk.team.leave')} title={t('desk.team.leave')}>
              <LogOut className="h-4 w-4 sm:hidden" />
              <span className="hidden sm:inline">{t('desk.team.leave')}</span>
            </Button>
          ) : (
            <Button size="sm" variant="ghost" onClick={abandon} aria-label={t('desk.abandon')} title={t('desk.abandon')}>
              <X className="h-4 w-4 sm:hidden" />
              <span className="hidden sm:inline">{t('desk.abandon')}</span>
            </Button>
          )}
        </div>
      </header>

      {team && <TeamStrip team={team} />}

      {warning && run.status !== 'completed' && (
        <p className="glass rounded-2xl border-amber-400/40 px-4 py-2.5 text-sm text-amber-800 dark:text-amber-200">{warning}</p>
      )}
      {run.status === 'scheduled' && (
        <p className="glass rounded-2xl px-4 py-2.5 text-sm">{t('desk.scheduled', { date: formatDateTime(run.start_at) })}</p>
      )}
      {error && <p className="glass rounded-2xl px-4 py-2.5 text-sm text-destructive">{error}</p>}

      {/* mobil: bo'limlar orasida almashish */}
      <nav className="glass flex gap-1 rounded-2xl p-1 lg:hidden">
        {(['inbox', 'event', 'chat'] as Pane[]).map((p) => (
          <button key={p} type="button" onClick={() => setPane(p)}
            className={cn('flex-1 rounded-xl py-2 text-sm font-medium transition-colors',
              pane === p ? 'bg-brand text-primary-foreground shadow' : 'text-muted-foreground')}>
            {t(`desk.pane.${p}`)}
            {badge[p] > 0 && (
              <span className={cn('ml-1.5 inline-grid h-5 min-w-5 place-items-center rounded-full px-1 text-[11px] font-bold',
                pane === p ? 'bg-primary-foreground/25' : p === 'chat' ? 'bg-destructive text-destructive-foreground' : 'bg-primary/15 text-primary')}>
                {badge[p]}
              </span>
            )}
          </button>
        ))}
      </nav>

      <div className="grid min-h-0 flex-1 gap-3 lg:grid-cols-[320px_1fr_360px]">
        <aside className={cn('glass flex min-h-0 flex-col overflow-hidden rounded-2xl', pane !== 'inbox' && 'hidden lg:flex')}>
          <div className="flex items-center justify-between px-4 py-3 text-sm font-bold">
            <span className="flex items-center gap-2"><InboxIcon className="h-4 w-4 text-primary" /> {t('desk.inbox')}</span>
            {pendingCount > 0 && <Badge>{pendingCount}</Badge>}
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-2">
            <Inbox
              events={run.events}
              personas={run.personas}
              team={team}
              selected={selected}
              now={now}
              onSelect={(nodeId) => {
                setSelected(nodeId)
                setPane('event')
              }}
            />
          </div>
        </aside>

        <main className={cn('glass-strong min-h-0 overflow-y-auto rounded-2xl', pane !== 'event' && 'hidden lg:block')}>
          {event ? (
            <div key={event.node_id} className="animate-rise">
              <EventDetail run={run} event={event} personas={run.personas} now={now} onRun={applyRun} onOpenDoc={setDoc}
                onAskMentor={mentor ? () => openChat(mentor.key) : undefined} />
            </div>
          ) : (
            <p className="p-6 text-sm text-muted-foreground">{t('desk.selectEvent')}</p>
          )}
        </main>

        <aside className={cn('glass flex min-h-0 flex-col overflow-hidden rounded-2xl', pane !== 'chat' && 'hidden lg:flex')}>
          <div className="flex gap-2 overflow-x-auto px-3 pt-3 pb-2">
            {team && (
              <TeamChip active={persona === TEAM_CHAT} unread={unread[TEAM_CHAT] ?? 0} onClick={() => openChat(TEAM_CHAT)} />
            )}
            {run.personas.map((p) => (
              <PersonaChip key={p.key} persona={p} active={persona === p.key} unread={unread[p.key] ?? 0}
                onClick={() => openChat(p.key)} />
            ))}
          </div>
          {(activePersona || (team && persona === TEAM_CHAT)) && (
            <div className="min-h-0 flex-1">
              <ChatPanel key={persona} runId={run.id} persona={activePersona} refreshKey={chatRefresh}
                readOnly={run.status !== 'active'} me={team?.me} />
            </div>
          )}
        </aside>
      </div>

      {doc && <DocumentDialog runId={run.id} docKey={doc} onClose={() => setDoc(null)} />}
    </div>
  )
}

const PART_ICON = { morning: Sunrise, afternoon: Sun, evening: Sunset }

function DeskClock({ now, part, off }: { now: number; part: Daypart; off: boolean }) {
  const { t } = useTranslation()
  const Icon = off ? Moon : PART_ICON[part]
  const progress = workdayProgress(new Date(now))
  return (
    <div className="flex items-center gap-2 rounded-xl bg-background/50 px-2 py-1.5 sm:gap-2.5 sm:px-3" title={off ? `${t('desk.tashkentTime')} · ${t('desk.offHours')}` : t('desk.tashkentTime')}>
      <Icon className="h-4 w-4 text-primary" />
      <div className="leading-none">
        <p className="font-mono text-base font-bold tabular-nums">{formatTime(new Date(now))}</p>
        <div className="mt-1 h-1 w-14 overflow-hidden rounded-full bg-muted sm:w-20" aria-hidden>
          <div className="bg-brand h-full rounded-full transition-[width] duration-1000" style={{ width: `${progress * 100}%` }} />
        </div>
      </div>
      {off && <span className="hidden text-xs text-muted-foreground sm:inline">{t('desk.offHours')}</span>}
    </div>
  )
}

function PersonaChip({ persona, active, unread, onClick }: { persona: Persona; active: boolean; unread: number; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} title={`${persona.name} · ${persona.role}`}
      className={cn('relative flex shrink-0 flex-col items-center gap-1 rounded-xl px-2 py-1.5 text-[11px] font-medium transition-colors',
        active ? 'bg-primary/12 text-primary' : 'text-muted-foreground hover:bg-accent/60')}>
      <Avatar persona={persona} active={active} />
      {persona.name.split(' ')[0]}
      {unread > 0 && (
        <span className="absolute right-1 top-0.5 grid h-4 min-w-4 place-items-center rounded-full bg-destructive px-1 text-[10px] font-bold text-destructive-foreground animate-glow">
          {unread}
        </span>
      )}
    </button>
  )
}

/** Jamoa a'zolari va rollari (§29.3): kim nimaga mas'ul — bir qarashda. */
function TeamStrip({ team }: { team: RunTeam }) {
  const { t } = useTranslation()
  const title = (key: string) => team.roles.find((r) => r.key === key)?.title ?? key
  return (
    <div className="glass flex items-center gap-2 overflow-x-auto rounded-2xl px-3 py-2 text-xs sm:gap-3 sm:px-4">
      <span className="flex shrink-0 items-center gap-1.5 font-bold">
        <UsersRound className="h-4 w-4 text-primary" /> {t('desk.team.title')}
      </span>
      {team.members.map((m) => (
        <span key={m.user_id} className={cn('flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1',
          m.user_id === team.me ? 'bg-primary/12 text-primary' : 'bg-background/60')}>
          {m.is_captain && <Crown className="h-3 w-3 text-amber-500" aria-label={t('desk.team.captain')} />}
          <span className="font-semibold">{m.name.split(' ')[0]}</span>
          {m.roles.length > 0 && <span className="text-muted-foreground">· {m.roles.map(title).join(', ')}</span>}
        </span>
      ))}
    </div>
  )
}

function TeamChip({ active, unread, onClick }: { active: boolean; unread: number; onClick: () => void }) {
  const { t } = useTranslation()
  return (
    <button type="button" onClick={onClick} title={t('desk.team.chat')}
      className={cn('relative flex shrink-0 flex-col items-center gap-1 rounded-xl px-2 py-1.5 text-[11px] font-medium transition-colors',
        active ? 'bg-primary/12 text-primary' : 'text-muted-foreground hover:bg-accent/60')}>
      <span className={cn('grid h-9 w-9 place-items-center rounded-full',
        active ? 'bg-brand text-primary-foreground ring-2 ring-primary/40 ring-offset-2 ring-offset-background' : 'bg-secondary text-secondary-foreground')}>
        <UsersRound className="h-4 w-4" />
      </span>
      {t('desk.team.title')}
      {unread > 0 && (
        <span className="absolute right-1 top-0.5 grid h-4 min-w-4 place-items-center rounded-full bg-destructive px-1 text-[10px] font-bold text-destructive-foreground animate-glow">
          {unread}
        </span>
      )}
    </button>
  )
}
