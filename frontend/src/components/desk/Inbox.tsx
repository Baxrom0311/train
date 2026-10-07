import { useTranslation } from 'react-i18next'
import { AlertTriangle, CheckCircle2, CircleDot, ClipboardList, Flag, GitFork, Mail, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatTime, remaining } from '@/lib/time'
import type { Persona, RunEvent } from '@/lib/types'

const TYPE_ICON = {
  message: Mail,
  task: ClipboardList,
  incident: AlertTriangle,
  decision: GitFork,
  day_end: Flag,
}

export function isActionable(e: RunEvent) {
  return e.type !== 'message' && e.status === 'delivered'
}

export default function Inbox({
  events,
  personas,
  selected,
  onSelect,
  now,
}: {
  events: RunEvent[]
  personas: Persona[]
  selected: string | null
  onSelect: (nodeId: string) => void
  now: number
}) {
  const { t } = useTranslation()
  const names = Object.fromEntries(personas.map((p) => [p.key, p.name]))
  // yangi hodisalar tepada; javob kutayotganlar alohida ajralib turadi
  const ordered = [...events].reverse()

  if (ordered.length === 0) {
    return <p className="p-4 text-sm text-muted-foreground">{t('desk.inboxEmpty')}</p>
  }

  return (
    <ul className="space-y-1">
      {ordered.map((e) => {
        const Icon = TYPE_ICON[e.type]
        const left = isActionable(e) && e.due_at ? remaining(e.due_at, now) : null
        return (
          <li key={e.node_id} className="animate-rise">
            <button
              type="button"
              onClick={() => onSelect(e.node_id)}
              className={cn(
                'relative flex w-full gap-3 rounded-xl px-3 py-3 text-left transition-all hover:bg-background/60',
                selected === e.node_id && 'bg-background/80 shadow-sm ring-1 ring-primary/25',
                e.type === 'incident' && isActionable(e) && 'ring-1 ring-destructive/40',
              )}
            >
              <span className={cn(
                'grid h-8 w-8 shrink-0 place-items-center rounded-lg',
                e.type === 'incident' ? 'bg-destructive/12 text-destructive' : isActionable(e) ? 'bg-primary/12 text-primary' : 'bg-muted text-muted-foreground',
              )}>
                <Icon className="h-4 w-4" />
              </span>
              {isActionable(e) && <span className="absolute right-2.5 top-2.5 h-2 w-2 rounded-full bg-primary animate-glow" />}
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2 pr-3 text-xs text-muted-foreground">
                  <span className="truncate">
                    {e.from_persona ? names[e.from_persona] : t(`desk.type.${e.type}`)}
                  </span>
                  <span>{e.delivered_at && formatTime(e.delivered_at)}</span>
                </div>
                <p className={cn('truncate text-sm', isActionable(e) ? 'font-bold' : 'text-foreground/80')}>
                  {e.brief.split('\n')[0] || t(`desk.type.${e.type}`)}
                </p>
                <div className="mt-1 flex items-center gap-2 text-xs">
                  <StatusLabel event={e} />
                  {left && (
                    <span className={cn('text-muted-foreground', left.minutes < 15 && 'font-medium text-destructive')}>
                      ⏱ {left.label}
                    </span>
                  )}
                </div>
              </div>
            </button>
          </li>
        )
      })}
    </ul>
  )
}

export function StatusLabel({ event }: { event: RunEvent }) {
  const { t } = useTranslation()
  if (event.type === 'message') return null
  const map = {
    delivered: { Icon: CircleDot, cls: 'text-primary' },
    submitted: { Icon: CheckCircle2, cls: 'text-success' },
    missed: { Icon: XCircle, cls: 'text-destructive' },
    pending: { Icon: CircleDot, cls: 'text-muted-foreground' },
    skipped: { Icon: CircleDot, cls: 'text-muted-foreground' },
  }[event.status]
  return (
    <span className={cn('inline-flex items-center gap-1', map.cls)}>
      <map.Icon className="h-3 w-3" /> {t(`desk.status.${event.status}`)}
    </span>
  )
}
