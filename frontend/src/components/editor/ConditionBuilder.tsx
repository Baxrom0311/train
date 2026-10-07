// `when` sharti (CONTRACT.md §9.3.3): bitta shart yoki "hammasi/birortasi" ro'yxati — konstruktor;
// ichma-ich guruhlar — JSON.
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { AddButton, NumberInput, RemoveButton, SELECT } from './fields'
import { GRADED, type Condition, type Leaf, type NodeDef } from './model'

type Mode = 'none' | 'one' | 'all' | 'any' | 'json'
const KINDS = ['score_lt', 'score_gte', 'missed', 'submitted', 'chose', 'flag'] as const
type Kind = (typeof KINDS)[number]

const isGroup = (c: Condition): c is { all: Condition[] } | { any: Condition[] } => 'all' in c || 'any' in c
const kindOf = (leaf: Leaf): Kind => Object.keys(leaf)[0] as Kind

function modeOf(c: Condition | null): Mode {
  if (!c) return 'none'
  if ('all' in c) return c.all.every((x) => !isGroup(x)) ? 'all' : 'json'
  if ('any' in c) return c.any.every((x) => !isGroup(x)) ? 'any' : 'json'
  return 'one'
}

function blankLeaf(kind: Kind, nodes: NodeDef[]): Leaf {
  const graded = nodes.find((n) => GRADED.includes(n.type))?.id ?? ''
  const decision = nodes.find((n) => n.type === 'decision')
  switch (kind) {
    case 'score_lt': return { score_lt: { node: graded, value: 60 } }
    case 'score_gte': return { score_gte: { node: graded, value: 60 } }
    case 'missed': return { missed: graded }
    case 'submitted': return { submitted: graded }
    case 'chose': return { chose: { node: decision?.id ?? '', option: decision?.options[0]?.key ?? '' } }
    case 'flag': return { flag: '' }
  }
}

export default function ConditionBuilder({ value, onChange, nodes, self }: {
  value: Condition | null
  onChange: (c: Condition | null) => void
  nodes: NodeDef[]
  self: string
}) {
  const { t } = useTranslation()
  const [mode, setMode] = useState<Mode>(() => modeOf(value))
  // boshqa node tanlanganda yoki YAML'dan kelganda — shaklni qiymatdan qayta aniqlash
  useEffect(() => setMode((m) => (m === 'json' ? m : modeOf(value))), [value])

  const others = nodes.filter((n) => n.id !== self)
  const leaves = (value && isGroup(value) ? ('all' in value ? value.all : value.any) : []) as Leaf[]
  const group = (list: Leaf[]) => onChange(mode === 'any' ? { any: list } : { all: list })

  const switchMode = (next: Mode) => {
    setMode(next)
    if (next === 'none') onChange(null)
    else if (next === 'one') onChange(value && !isGroup(value) ? value : leaves[0] ?? blankLeaf('flag', others))
    else if (next === 'all' || next === 'any') {
      const list = value && !isGroup(value) ? [value as Leaf] : leaves.length ? leaves : [blankLeaf('flag', others)]
      onChange(next === 'all' ? { all: list } : { any: list })
    }
  }

  const modes: Mode[] = ['none', 'one', 'all', 'any', 'json']
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-1" role="radiogroup" aria-label={t('editor.when.mode')}>
        {modes.map((m) => (
          <button key={m} type="button" role="radio" aria-checked={mode === m} onClick={() => switchMode(m)}
            className={cn('rounded-full px-3 py-1 text-xs font-semibold transition-colors',
              mode === m ? 'bg-primary/12 text-primary ring-1 ring-primary/40' : 'text-muted-foreground hover:text-foreground')}>
            {t(`editor.when.modes.${m}`)}
          </button>
        ))}
      </div>
      {mode === 'one' && value && !isGroup(value) && <LeafRow leaf={value} nodes={others} all={nodes} onChange={onChange} />}
      {(mode === 'all' || mode === 'any') && (
        <div className="space-y-2">
          {leaves.map((leaf, i) => (
            <div key={i} className="flex items-start gap-2">
              <LeafRow leaf={leaf} nodes={others} all={nodes} onChange={(l) => group(leaves.map((x, j) => (j === i ? l : x)))} />
              <RemoveButton label={t('editor.remove')} onClick={() => (leaves.length > 1 ? group(leaves.filter((_, j) => j !== i)) : switchMode('none'))} />
            </div>
          ))}
          <AddButton onClick={() => group([...leaves, blankLeaf('flag', others)])}>{t('editor.when.add')}</AddButton>
        </div>
      )}
      {mode === 'json' && <JsonCondition value={value} onChange={onChange} />}
      {mode !== 'none' && <p className="text-xs text-muted-foreground">{t('editor.when.hint')}</p>}
    </div>
  )
}

function LeafRow({ leaf, nodes, all, onChange }: {
  leaf: Leaf
  nodes: NodeDef[]
  all: NodeDef[]
  onChange: (l: Leaf) => void
}) {
  const { t } = useTranslation()
  const kind = kindOf(leaf)
  const graded = nodes.filter((n) => GRADED.includes(n.type))
  const decisions = nodes.filter((n) => n.type === 'decision')
  const flags = [...new Set(all.flatMap((n) => n.options.map((o) => o.flag).filter(Boolean) as string[]))]

  const nodeSelect = (value: string, list: NodeDef[], set: (id: string) => void) => (
    <select className={SELECT} value={value} onChange={(e) => set(e.target.value)} aria-label={t('editor.when.node')}>
      {!list.some((n) => n.id === value) && <option value={value}>{value || '—'}</option>}
      {list.map((n) => <option key={n.id} value={n.id}>{n.id}</option>)}
    </select>
  )

  let body = null
  if ('score_lt' in leaf || 'score_gte' in leaf) {
    const ref = 'score_lt' in leaf ? leaf.score_lt : leaf.score_gte
    const set = (patch: Partial<typeof ref>) =>
      onChange('score_lt' in leaf ? { score_lt: { ...ref, ...patch } } : { score_gte: { ...ref, ...patch } })
    body = (
      <>
        {nodeSelect(ref.node, graded, (node) => set({ node }))}
        <NumberInput aria-label={t('editor.when.value')} min={0} max={100} value={ref.value} onChange={(v) => set({ value: v ?? 0 })} />
      </>
    )
  } else if ('missed' in leaf) {
    body = nodeSelect(leaf.missed, graded, (missed) => onChange({ missed }))
  } else if ('submitted' in leaf) {
    body = nodeSelect(leaf.submitted, graded, (submitted) => onChange({ submitted }))
  } else if ('chose' in leaf) {
    const target = decisions.find((n) => n.id === leaf.chose.node)
    body = (
      <>
        {nodeSelect(leaf.chose.node, decisions, (node) => onChange({ chose: { node, option: decisions.find((n) => n.id === node)?.options[0]?.key ?? '' } }))}
        <select className={SELECT} value={leaf.chose.option} aria-label={t('editor.when.option')}
          onChange={(e) => onChange({ chose: { ...leaf.chose, option: e.target.value } })}>
          {!target?.options.some((o) => o.key === leaf.chose.option) && <option value={leaf.chose.option}>{leaf.chose.option || '—'}</option>}
          {target?.options.map((o) => <option key={o.key} value={o.key}>{o.label || o.key}</option>)}
        </select>
      </>
    )
  } else {
    const id = `flags-${all.length}`
    body = (
      <>
        <Input value={leaf.flag} list={id} className="font-mono" aria-label={t('editor.when.flag')} onChange={(e) => onChange({ flag: e.target.value })} />
        <datalist id={id}>{flags.map((f) => <option key={f} value={f} />)}</datalist>
      </>
    )
  }

  return (
    <div className="grid min-w-0 flex-1 gap-2 sm:grid-cols-[minmax(0,13rem)_minmax(0,1fr)_minmax(0,1fr)]">
      <select className={SELECT} value={kind} aria-label={t('editor.when.kind')} onChange={(e) => onChange(blankLeaf(e.target.value as Kind, nodes))}>
        {KINDS.map((k) => <option key={k} value={k}>{t(`editor.when.kinds.${k}`)}</option>)}
      </select>
      {body}
    </div>
  )
}

function JsonCondition({ value, onChange }: { value: Condition | null; onChange: (c: Condition | null) => void }) {
  const { t } = useTranslation()
  const [text, setText] = useState(() => (value ? JSON.stringify(value, null, 2) : ''))
  const [bad, setBad] = useState(false)
  return (
    <div className="space-y-1.5">
      <Textarea rows={6} className={cn('font-mono text-[13px]', bad && 'border-destructive')} value={text} spellCheck={false}
        aria-label={t('editor.when.json')}
        onChange={(e) => {
          setText(e.target.value)
          if (!e.target.value.trim()) {
            setBad(false)
            onChange(null)
            return
          }
          try {
            onChange(JSON.parse(e.target.value))
            setBad(false)
          } catch {
            setBad(true)
          }
        }} />
      <p className={cn('text-xs', bad ? 'text-destructive' : 'text-muted-foreground')}>{bad ? t('editor.when.badJson') : t('editor.when.jsonHint')}</p>
    </div>
  )
}
