// Node'lar ro'yxati kunlar bo'yicha vaqt chizig'i sifatida; `after` node'lari langari ostida.
import { useTranslation } from 'react-i18next'
import { CircleAlert, CornerDownRight, Plus } from 'lucide-react'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import type { NodeType } from '@/lib/types'
import { cn } from '@/lib/utils'
import { nodeIcon } from './icons'
import { NODE_TYPES, timeline, type NodeDef, type TimelineRow } from './model'

export default function NodeTimeline({ nodes, days, selected, invalid, onSelect, onAdd }: {
  nodes: NodeDef[]
  days: number
  selected: number | null
  invalid: Set<number>
  onSelect: (i: number) => void
  onAdd: (type: NodeType, day: number) => void
}) {
  const { t } = useTranslation()
  const { days: byDay, loose } = timeline(nodes)
  const dayNumbers = [...new Set([...Array.from({ length: days }, (_, i) => i + 1), ...byDay.keys()])].sort((a, b) => a - b)

  const row = ({ index, depth }: TimelineRow) => {
    const n = nodes[index]
    const Icon = nodeIcon(n.type)
    const surprise = n.type === 'incident' || n.type === 'decision'
    return (
      <li key={index}>
        <button type="button" onClick={() => onSelect(index)} aria-current={selected === index}
          style={{ paddingLeft: `${0.625 + depth * 1.1}rem` }}
          className={cn('flex w-full items-center gap-2.5 rounded-xl py-2 pr-2.5 text-left text-sm transition-colors',
            selected === index ? 'bg-primary/12 ring-1 ring-primary/40' : 'hover:bg-accent/60')}>
          {depth > 0 && <CornerDownRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />}
          <span className="w-12 shrink-0 font-mono text-xs tabular-nums text-muted-foreground">
            {n.after ? `+${n.after.minutes}′` : n.at ?? '—'}
          </span>
          <Icon className={cn('h-4 w-4 shrink-0', surprise ? 'text-destructive' : 'text-primary')} />
          <span className="min-w-0 flex-1">
            <span className="block truncate font-mono text-xs font-semibold">{n.id || '—'}</span>
            <span className="block truncate text-xs text-muted-foreground">{n.brief.split('\n')[0] || t(`editor.nodeType.${n.type}`)}</span>
          </span>
          {n.when && <span className="shrink-0 rounded-full bg-muted px-1.5 text-[10px] font-semibold uppercase text-muted-foreground">{t('editor.nodes.if')}</span>}
          {invalid.has(index) && <CircleAlert aria-label={t('editor.hasErrors')} className="h-4 w-4 shrink-0 text-destructive" />}
        </button>
      </li>
    )
  }

  return (
    <nav aria-label={t('editor.tabs.nodes')} className="space-y-4">
      {dayNumbers.map((day) => (
        <div key={day} className="space-y-1">
          <div className="flex items-center justify-between px-1">
            <h3 className={cn('text-xs font-bold uppercase tracking-wider', day > days ? 'text-destructive' : 'text-muted-foreground')}>
              {t('editor.nodes.dayN', { n: day })}
            </h3>
            <AddMenu label={t('editor.nodes.add')} onAdd={(type) => onAdd(type, day)} />
          </div>
          <ol className="space-y-0.5">{(byDay.get(day) ?? []).map(row)}</ol>
        </div>
      ))}
      {loose.length > 0 && (
        <div className="space-y-1">
          <h3 className="px-1 text-xs font-bold uppercase tracking-wider text-destructive">{t('editor.nodes.loose')}</h3>
          <ol className="space-y-0.5">{loose.map((index) => row({ index, depth: 0 }))}</ol>
        </div>
      )}
    </nav>
  )
}

function AddMenu({ label, onAdd }: { label: string; onAdd: (type: NodeType) => void }) {
  const { t } = useTranslation()
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button type="button" aria-label={label} title={label}
          className="grid h-7 w-7 place-items-center rounded-lg text-primary transition-colors hover:bg-primary/10">
          <Plus className="h-4 w-4" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {NODE_TYPES.map((type) => {
          const Icon = nodeIcon(type)
          return (
            <DropdownMenuItem key={type} onClick={() => onAdd(type)} className="gap-2">
              <Icon className="h-4 w-4" /> {t(`editor.nodeType.${type}`)}
            </DropdownMenuItem>
          )
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
