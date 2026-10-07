import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useLocation, useParams } from 'react-router-dom'
import { Clock, MessageSquare } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from './Badge'
import { cn } from '@/lib/utils'
import { api, ApiError } from '@/lib/api'
import { subscribeRun, type RunNote } from '@/lib/sse'
import { formatDateTime, formatTime } from '@/lib/time'
import type { RunDetail } from '@/lib/types'
import Inbox, { isActionable } from '@/components/desk/Inbox'
import EventDetail from '@/components/desk/EventDetail'
import ChatPanel from '@/components/desk/ChatPanel'
import DocumentDialog from '@/components/desk/DocumentDialog'

type Pane = 'inbox' | 'event' | 'chat'

export default function RunPage() {
  const { id = '' } = useParams()
  const { t } = useTranslation()
  const warning = (useLocation().state as { warning?: string | null } | null)?.warning
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
    const first = run.events.find(isActionable) ?? run.events[run.events.length - 1]
    if (first) setSelected(first.node_id)
    if (!persona && run.personas.length) setPersona(run.personas[0].key)
  }, [run, selected, persona])

  const event = useMemo(() => run?.events.find((e) => e.node_id === selected) ?? null, [run, selected])
  const activePersona = run?.personas.find((p) => p.key === persona) ?? null
  const pendingCount = run?.events.filter(isActionable).length ?? 0

  const abandon = async () => {
    if (!run || !window.confirm(t('desk.abandonConfirm'))) return
    try {
      applyRun(await api<RunDetail>(`/runs/${run.id}/abandon`, { method: 'POST' }))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.error'))
    }
  }

  if (error && !run) return <p className="container mx-auto p-8 text-destructive">{error}</p>
  if (!run) return <p className="container mx-auto p-8 text-muted-foreground">{t('common.loading')}</p>

  const closed = !['active', 'scheduled'].includes(run.status)

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
        <div className="min-w-0">
          <h1 className="truncate font-semibold">{run.scenario.title}</h1>
          <p className="text-xs text-muted-foreground">{run.scenario.company_name}</p>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="flex items-center gap-1 font-mono" title={t('desk.tashkentTime')}>
            <Clock className="h-4 w-4" /> {formatTime(new Date(now))}
          </span>
          {run.status === 'active' && !run.is_work_time && <Badge variant="outline">{t('desk.offHours')}</Badge>}
          <Badge variant={closed ? 'secondary' : 'default'}>{t(`run.status.${run.status}`)}</Badge>
          {closed ? (
            <Button size="sm" asChild>
              <Link to={`/runs/${run.id}/report`}>{t('catalog.report')}</Link>
            </Button>
          ) : (
            <Button size="sm" variant="ghost" onClick={abandon}>{t('desk.abandon')}</Button>
          )}
        </div>
      </header>

      {warning && run.status !== 'completed' && (
        <p className="border-b bg-amber-50 px-4 py-2 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-100">{warning}</p>
      )}
      {run.status === 'scheduled' && (
        <p className="border-b bg-muted px-4 py-2 text-sm">{t('desk.scheduled', { date: formatDateTime(run.start_at) })}</p>
      )}
      {error && <p className="border-b px-4 py-2 text-sm text-destructive">{error}</p>}

      {/* mobil: bo'limlar orasida almashish */}
      <nav className="flex border-b lg:hidden">
        {(['inbox', 'event', 'chat'] as Pane[]).map((p) => (
          <button key={p} type="button" onClick={() => setPane(p)}
            className={cn('flex-1 py-2 text-sm', pane === p ? 'border-b-2 border-primary font-medium' : 'text-muted-foreground')}>
            {t(`desk.pane.${p}`)}
            {p === 'inbox' && pendingCount > 0 && ` (${pendingCount})`}
          </button>
        ))}
      </nav>

      <div className="grid min-h-0 flex-1 lg:grid-cols-[300px_1fr_340px]">
        <aside className={cn('min-h-0 overflow-y-auto border-r', pane !== 'inbox' && 'hidden lg:block')}>
          <div className="flex items-center justify-between border-b px-3 py-2 text-sm font-medium">
            {t('desk.inbox')}
            {pendingCount > 0 && <Badge>{pendingCount}</Badge>}
          </div>
          <Inbox
            events={run.events}
            personas={run.personas}
            selected={selected}
            now={now}
            onSelect={(nodeId) => {
              setSelected(nodeId)
              setPane('event')
            }}
          />
        </aside>

        <main className={cn('min-h-0 overflow-y-auto', pane !== 'event' && 'hidden lg:block')}>
          {event ? (
            <EventDetail run={run} event={event} personas={run.personas} now={now} onRun={applyRun} onOpenDoc={setDoc} />
          ) : (
            <p className="p-6 text-sm text-muted-foreground">{t('desk.selectEvent')}</p>
          )}
        </main>

        <aside className={cn('flex min-h-0 flex-col border-l', pane !== 'chat' && 'hidden lg:flex')}>
          <div className="flex flex-wrap gap-1 border-b p-2">
            {run.personas.map((p) => (
              <button
                key={p.key}
                type="button"
                onClick={() => {
                  setPersona(p.key)
                  setUnread((u) => ({ ...u, [p.key]: 0 }))
                }}
                className={cn(
                  'flex items-center gap-1 rounded-full border px-3 py-1 text-xs',
                  persona === p.key ? 'border-primary bg-primary/10 font-medium' : 'hover:bg-accent',
                )}
              >
                <MessageSquare className="h-3 w-3" /> {p.name.split(' ')[0]}
                {(unread[p.key] ?? 0) > 0 && (
                  <span className="rounded-full bg-destructive px-1.5 text-[10px] text-destructive-foreground">
                    {unread[p.key]}
                  </span>
                )}
              </button>
            ))}
          </div>
          {activePersona && (
            <div className="min-h-0 flex-1">
              <ChatPanel runId={run.id} persona={activePersona} refreshKey={chatRefresh} readOnly={run.status !== 'active'} />
            </div>
          )}
        </aside>
      </div>

      {doc && <DocumentDialog runId={run.id} docKey={doc} onClose={() => setDoc(null)} />}
    </div>
  )
}
