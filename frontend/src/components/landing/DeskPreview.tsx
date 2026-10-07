import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { CheckCircle2, ClipboardList, Clock, GitBranch, MessageSquare, Siren, Sunset, type LucideIcon } from 'lucide-react'
import { SECTOR_ART } from '@/components/sectorArt'
import { formatTime, tashkentHours } from '@/lib/time'
import type { NodeType, ShowcaseScenario, ShowcaseSlot } from '@/lib/types'
import { cn } from '@/lib/utils'

const ICON: Record<NodeType, LucideIcon> = {
  message: MessageSquare,
  task: ClipboardList,
  incident: Siren,
  decision: GitBranch,
  day_end: Sunset,
}
const ROTATE_MS = 7000
const WORKDAY_END = 18

const hours = (at: string) => {
  const [h, m] = at.split(':').map(Number)
  return h + m / 60
}

/** Landing hero'sidagi "ish stoli": ssenariyning 1-kuni Toshkent vaqtiga nisbatan (§14.2). */
export default function DeskPreview({ scenarios }: { scenarios: ShowcaseScenario[] }) {
  const { t } = useTranslation()
  const [index, setIndex] = useState(0)
  const [paused, setPaused] = useState(false)
  const [now, setNow] = useState(() => new Date())

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 30_000)
    return () => clearInterval(id)
  }, [])
  useEffect(() => {
    if (paused || scenarios.length < 2) return
    const id = setInterval(() => setIndex((i) => (i + 1) % scenarios.length), ROTATE_MS)
    return () => clearInterval(id)
  }, [paused, scenarios.length])

  const s = scenarios[index % scenarios.length]
  if (!s) return null
  const art = SECTOR_ART[s.sector]
  const h = tashkentHours(now)
  // ish kunidan keyin (18:00+) hammasi bajarilgan, "hozir" yo'q
  const current = h >= WORKDAY_END ? s.day1.length : s.day1.reduce((acc, slot, i) => (hours(slot.at) <= h ? i : acc), -1)

  return (
    <div className="glass-strong glow-ring relative overflow-hidden rounded-3xl" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}>
      <div className={cn('relative h-24 bg-gradient-to-br transition-colors duration-700', art.glow)}>
        <art.Icon aria-hidden className="absolute -bottom-6 -right-3 h-32 w-32 text-foreground/10" />
        <div className="absolute inset-x-5 top-4 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {t(`catalog.sector.${s.sector}`)} · {t('landing.desk.day1')}
            </p>
            <p className="truncate font-bold">{s.company_name}</p>
          </div>
          <span className="flex shrink-0 items-center gap-1.5 rounded-full border bg-background/70 px-2.5 py-1 text-xs font-semibold tabular-nums">
            <Clock className="h-3.5 w-3.5 text-primary" /> {t('landing.desk.tashkent')} {formatTime(now)}
          </span>
        </div>
      </div>

      <ol className="space-y-1 p-3" aria-label={s.title}>
        {s.day1.map((slot, i) => (
          <Slot key={slot.at + i} slot={slot} state={i < current ? 'done' : i === current ? 'now' : 'next'} />
        ))}
      </ol>

      {s.mentor && (
        <div className="mx-3 mb-3 flex items-start gap-2.5 rounded-2xl border bg-background/60 p-3">
          <span className="bg-brand grid h-8 w-8 shrink-0 place-items-center rounded-full text-xs font-bold text-primary-foreground">
            {s.mentor.name.slice(0, 1)}
          </span>
          <div className="min-w-0 text-sm">
            <p className="text-xs text-muted-foreground"><b className="text-foreground">{s.mentor.name}</b> · {t('landing.desk.mentor')}</p>
            <p>{t('landing.desk.mentorLine')}</p>
          </div>
        </div>
      )}

      {scenarios.length > 1 && (
        <div className="flex justify-center gap-1.5 pb-4" role="tablist" aria-label={t('landing.desk.switch')}>
          {scenarios.map((x, i) => (
            <button key={x.slug} type="button" role="tab" aria-selected={i === index} aria-label={x.title}
              onClick={() => { setIndex(i); setPaused(true) }}
              className={cn('h-1.5 rounded-full transition-all', i === index ? 'w-6 bg-primary' : 'w-1.5 bg-muted-foreground/30 hover:bg-muted-foreground/60')} />
          ))}
        </div>
      )}
    </div>
  )
}

function Slot({ slot, state }: { slot: ShowcaseSlot; state: 'done' | 'now' | 'next' }) {
  const { t } = useTranslation()
  const Icon = state === 'done' ? CheckCircle2 : ICON[slot.type]
  const surprise = slot.type === 'incident' || slot.type === 'decision'
  return (
    <li className={cn(
      'flex items-center gap-3 rounded-xl px-2.5 py-2 text-sm transition-colors',
      state === 'now' && 'bg-primary/10 ring-1 ring-primary/30',
      state === 'done' && 'text-muted-foreground',
    )}>
      <span className="w-11 shrink-0 font-mono text-xs tabular-nums text-muted-foreground">{slot.at}</span>
      <Icon className={cn('h-4 w-4 shrink-0', state === 'done' ? 'text-success' : surprise ? 'text-destructive' : 'text-primary')} />
      <span className={cn('min-w-0 flex-1 truncate', surprise && state !== 'done' && 'italic')}>
        {slot.title ?? t(`landing.slot.${slot.type}`)}
      </span>
      {state === 'now' && (
        <span className="shrink-0 rounded-full bg-primary px-2 py-0.5 text-[10px] font-bold uppercase text-primary-foreground">
          {t('landing.desk.now')}
        </span>
      )}
    </li>
  )
}
