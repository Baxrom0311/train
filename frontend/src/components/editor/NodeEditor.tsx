// Bitta node formasi: maydonlar turga qarab (CONTRACT.md §9.3, §16.3).
import { useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Copy } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import RichText from '@/components/desk/RichText'
import { COMPETENCIES, type NodeType } from '@/lib/types'
import { cn } from '@/lib/utils'
import ConditionBuilder from './ConditionBuilder'
import { nodeIcon } from './icons'
import { AddButton, Chips, ErrorNote, Field, KeyInput, NumberInput, RemoveButton, SELECT, TextList } from './fields'
import {
  ANSWERED, ANSWER_TYPES, GRADED, NODE_TYPES, renameNode, retypeNode, stripPrefix, uniqueKey,
  type Grade, type NodeDef, type ScenarioDef,
} from './model'
import type { Located } from './sections'

const GRADES: Grade[] = ['correct', 'acceptable', 'wrong']

export default function NodeEditor({ defn, index, update, errors, onSelect }: {
  defn: ScenarioDef
  index: number
  update: (f: (d: ScenarioDef) => ScenarioDef) => void
  errors: Located[]
  onSelect: (i: number | null) => void
}) {
  const { t } = useTranslation()
  const [preview, setPreview] = useState(false)
  const n = defn.nodes[index]
  const set = (patch: Partial<NodeDef>) =>
    update((d) => ({ ...d, nodes: d.nodes.map((x, j) => (j === index ? { ...x, ...patch } : x)) }))
  const err = (field: string) => {
    const e = errors.find((x) => x.field === field)
    return e && stripPrefix(e.message, n.id)
  }
  const loose = errors.filter((e) => !e.field || !FIELDS.has(e.field)).map((e) => stripPrefix(e.message, n.id))

  const graded = GRADED.includes(n.type)
  const answered = ANSWERED.includes(n.type)
  const fixed = !n.after
  const Icon = nodeIcon(n.type)
  const days = Array.from({ length: defn.duration_days }, (_, i) => i + 1)

  const duplicate = () => {
    const copy = { ...n, id: uniqueKey(`${n.id}_copy`, defn.nodes.map((x) => x.id)) }
    update((d) => ({ ...d, nodes: [...d.nodes, copy] }))
    onSelect(defn.nodes.length)
  }
  const remove = () => {
    onSelect(null)
    update((d) => ({ ...d, nodes: d.nodes.filter((_, j) => j !== index) }))
  }

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-center gap-3">
        <span className={cn('grid h-11 w-11 shrink-0 place-items-center rounded-2xl',
          n.type === 'incident' || n.type === 'decision' ? 'bg-destructive/12 text-destructive' : 'bg-primary/12 text-primary')}>
          <Icon className="h-5 w-5" />
        </span>
        <div className="grid min-w-0 flex-1 gap-3 sm:grid-cols-2">
          <Field label={t('editor.nodes.id')} error={err('id')}>
            {(id) => <KeyInput id={id} value={n.id} onCommit={(v) => update((d) => renameNode(d, index, v))} />}
          </Field>
          <Field label={t('editor.nodes.type')} error={err('type')}>
            {(id) => (
              <select id={id} className={SELECT} value={n.type}
                onChange={(e) => update((d) => ({ ...d, nodes: d.nodes.map((x, j) => (j === index ? retypeNode(x, e.target.value as NodeType) : x)) }))}>
                {NODE_TYPES.map((x) => <option key={x} value={x}>{t(`editor.nodeType.${x}`)}</option>)}
              </select>
            )}
          </Field>
        </div>
        <div className="flex gap-1 self-end">
          <button type="button" onClick={duplicate} aria-label={t('editor.nodes.duplicate')} title={t('editor.nodes.duplicate')}
            className="grid h-10 w-10 place-items-center rounded-xl text-muted-foreground transition-colors hover:bg-accent hover:text-foreground">
            <Copy className="h-4 w-4" />
          </button>
          <RemoveButton label={t('editor.remove')} onClick={remove} />
        </div>
      </header>

      <ErrorNote messages={loose} />

      <Group title={t('editor.nodes.timing')}>
        <div className="flex gap-1" role="radiogroup" aria-label={t('editor.nodes.timing')}>
          {(['fixed', 'after'] as const).map((m) => {
            const on = (m === 'fixed') === fixed
            const disabled = m === 'after' && n.type === 'day_end'
            return (
              <button key={m} type="button" role="radio" aria-checked={on} disabled={disabled}
                onClick={() => !on && set(m === 'fixed'
                  ? { after: null, day: 1, at: '10:00' }
                  : { day: null, at: null, after: { node: defn.nodes.find((x) => x.id !== n.id)?.id ?? '', event: 'delivered', minutes: 30 } })}
                className={cn('rounded-full px-3 py-1 text-xs font-semibold transition-colors disabled:opacity-40',
                  on ? 'bg-primary/12 text-primary ring-1 ring-primary/40' : 'text-muted-foreground hover:text-foreground')}>
                {t(`editor.nodes.${m}`)}
              </button>
            )
          })}
        </div>
        {fixed ? (
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label={t('editor.nodes.day')} error={err('day')}>
              {(id) => (
                <select id={id} className={SELECT} value={n.day ?? 1} onChange={(e) => set({ day: Number(e.target.value) })}>
                  {days.map((d) => <option key={d} value={d}>{t('editor.nodes.dayN', { n: d })}</option>)}
                  {n.day != null && n.day > defn.duration_days && <option value={n.day}>{t('editor.nodes.dayN', { n: n.day })}</option>}
                </select>
              )}
            </Field>
            <Field label={t('editor.nodes.at')} error={err('at')} hint={t('editor.nodes.atHint')}>
              {(id) => <Input id={id} type="time" step={300} value={n.at ?? ''} onChange={(e) => set({ at: e.target.value.slice(0, 5) || null })} />}
            </Field>
          </div>
        ) : n.after && (
          <div className="grid gap-3 sm:grid-cols-3">
            <Field label={t('editor.nodes.afterNode')} error={err('after')}>
              {(id) => (
                <select id={id} className={SELECT} value={n.after!.node} onChange={(e) => set({ after: { ...n.after!, node: e.target.value } })}>
                  {!defn.nodes.some((x) => x.id === n.after!.node) && <option value={n.after!.node}>{n.after!.node || '—'}</option>}
                  {defn.nodes.filter((x) => x.id !== n.id).map((x) => <option key={x.id} value={x.id}>{x.id}</option>)}
                </select>
              )}
            </Field>
            <Field label={t('editor.nodes.afterEvent')}>
              {(id) => (
                <select id={id} className={SELECT} value={n.after!.event}
                  onChange={(e) => set({ after: { ...n.after!, event: e.target.value as 'delivered' | 'submitted' } })}>
                  <option value="delivered">{t('editor.nodes.delivered')}</option>
                  <option value="submitted">{t('editor.nodes.submitted')}</option>
                </select>
              )}
            </Field>
            <Field label={t('editor.nodes.afterMinutes')} hint={t('editor.nodes.workMinutes')}>
              {(id) => <NumberInput id={id} min={0} max={2400} value={n.after!.minutes} onChange={(v) => set({ after: { ...n.after!, minutes: v ?? 0 } })} />}
            </Field>
          </div>
        )}
      </Group>

      <Group title={t('editor.nodes.content')}>
        <Field label={t('editor.nodes.from')} error={err('from')}>
          {(id) => (
            <select id={id} className={SELECT} value={n.from ?? ''} onChange={(e) => set({ from: e.target.value || null })}>
              <option value="">{t('editor.nodes.noSender')}</option>
              {!!n.from && !defn.personas.some((p) => p.key === n.from) && <option value={n.from}>{n.from}</option>}
              {defn.personas.map((p) => <option key={p.key} value={p.key}>{p.name || p.key} · {p.role}</option>)}
            </select>
          )}
        </Field>
        <div className="space-y-1.5">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t('editor.nodes.brief')}</span>
            <button type="button" onClick={() => setPreview((p) => !p)} aria-pressed={preview}
              className="text-xs font-semibold text-primary hover:underline">
              {preview ? t('editor.edit') : t('editor.nodes.studentView')}
            </button>
          </div>
          {preview ? (
            <div className="max-h-[28rem] overflow-auto rounded-2xl border bg-background/60 p-4 text-sm">
              {n.brief ? <RichText text={n.brief} /> : <p className="text-muted-foreground">{t('editor.nodes.emptyBrief')}</p>}
            </div>
          ) : (
            <Textarea rows={8} className="font-mono text-[13px]" value={n.brief} aria-label={t('editor.nodes.brief')}
              onChange={(e) => set({ brief: e.target.value })} />
          )}
          {err('brief') ? <p className="text-xs font-medium text-destructive">{err('brief')}</p>
            : <p className="text-xs text-muted-foreground">{t('editor.nodes.briefHint')}</p>}
        </div>
        <Field label={t('editor.nodes.attachments')} error={err('attachments')}>
          {() => <Chips label={t('editor.nodes.attachments')} value={n.attachments} onChange={(attachments) => set({ attachments })}
            options={defn.documents.map((d) => ({ value: d.key, label: d.title || d.key }))} />}
        </Field>
      </Group>

      {(answered || n.type === 'decision') && (
        <Group title={t('editor.nodes.answer')}>
          {answered && (
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label={t('editor.nodes.answerTypes')} error={err('answer_types')}>
                {() => <Chips label={t('editor.nodes.answerTypes')} value={n.answer_types} onChange={(answer_types) => set({ answer_types })}
                  options={ANSWER_TYPES.map((a) => ({ value: a, label: t(`editor.answerType.${a}`) }))} />}
              </Field>
              <Field label={t('editor.nodes.due')} error={err('due_in_minutes')} hint={t('editor.nodes.workMinutes')}>
                {(id) => <NumberInput id={id} min={1} max={2400} value={n.due_in_minutes} onChange={(v) => set({ due_in_minutes: v })} />}
              </Field>
            </div>
          )}
          {n.type === 'decision' && (
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t('editor.nodes.options')}</p>
              {n.options.map((o, i) => {
                const setO = (patch: Partial<typeof o>) => set({ options: n.options.map((x, j) => (j === i ? { ...x, ...patch } : x)) })
                return (
                  <div key={i} className="flex items-start gap-2">
                    <div className="grid min-w-0 flex-1 gap-2 sm:grid-cols-[6rem_minmax(0,1fr)_9rem_9rem]">
                      <Input value={o.key} className="font-mono" aria-label={t('editor.key')} onChange={(e) => setO({ key: e.target.value })} />
                      <Input value={o.label} placeholder={t('editor.nodes.optionLabel')} aria-label={t('editor.nodes.optionLabel')} onChange={(e) => setO({ label: e.target.value })} />
                      <select className={SELECT} value={o.grade} aria-label={t('editor.nodes.grade')} onChange={(e) => setO({ grade: e.target.value as Grade })}>
                        {GRADES.map((g) => <option key={g} value={g}>{t(`editor.grade.${g}`)}</option>)}
                      </select>
                      <Input value={o.flag ?? ''} className="font-mono" placeholder={t('editor.nodes.flag')} aria-label={t('editor.nodes.flag')}
                        onChange={(e) => setO({ flag: e.target.value || null })} />
                    </div>
                    <RemoveButton label={t('editor.remove')} onClick={() => set({ options: n.options.filter((_, j) => j !== i) })} />
                  </div>
                )
              })}
              {err('options') && <p className="text-xs font-medium text-destructive">{err('options')}</p>}
              <AddButton onClick={() => set({ options: [...n.options, { key: uniqueKey('option', n.options.map((o) => o.key)), label: '', grade: 'acceptable', flag: null }] })}>
                {t('editor.nodes.addOption')}
              </AddButton>
              <p className="text-xs text-muted-foreground">{t('editor.nodes.flagHint')}</p>
            </div>
          )}
        </Group>
      )}

      {graded && (
        <Group title={t('editor.nodes.grading')}>
          <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_8rem]">
            <Field label={t('editor.nodes.competencies')} error={err('competencies')}>
              {() => <Chips label={t('editor.nodes.competencies')} value={n.competencies} onChange={(competencies) => set({ competencies })}
                options={COMPETENCIES.map((c) => ({ value: c, label: t(`competency.${c}`) }))} />}
            </Field>
            <Field label={t('editor.nodes.weight')} error={err('weight')}>
              {(id) => <NumberInput id={id} min={0.1} step={0.5} value={n.weight} onChange={(v) => set({ weight: v ?? 1 })} />}
            </Field>
          </div>
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t('editor.nodes.rubric')}</p>
            {n.rubric.map((c, i) => {
              const setC = (patch: Partial<typeof c>) => set({ rubric: n.rubric.map((x, j) => (j === i ? { ...x, ...patch } : x)) })
              return (
                <div key={i} className="flex items-start gap-2">
                  <div className="grid min-w-0 flex-1 gap-2 sm:grid-cols-[10rem_minmax(0,1fr)_6rem]">
                    <Input value={c.id} className="font-mono" aria-label={t('editor.key')} onChange={(e) => setC({ id: e.target.value })} />
                    <Textarea rows={1} value={c.description} placeholder={t('editor.nodes.criterion')} aria-label={t('editor.nodes.criterion')}
                      className="min-h-10" onChange={(e) => setC({ description: e.target.value })} />
                    <NumberInput aria-label={t('editor.nodes.weight')} min={0.1} step={0.5} value={c.weight} onChange={(v) => setC({ weight: v ?? 1 })} />
                  </div>
                  <RemoveButton label={t('editor.remove')} onClick={() => set({ rubric: n.rubric.filter((_, j) => j !== i) })} />
                </div>
              )
            })}
            {err('rubric') && <p className="text-xs font-medium text-destructive">{err('rubric')}</p>}
            <AddButton onClick={() => set({ rubric: [...n.rubric, { id: uniqueKey('criterion', n.rubric.map((c) => c.id)), description: '', weight: 1 }] })}>
              {t('editor.nodes.addCriterion')}
            </AddButton>
          </div>
          {n.type !== 'decision' && (
            <>
              <Field label={t('editor.nodes.hints')} hint={t('editor.nodes.hintsHint')}>
                {() => <TextList value={n.hints} onChange={(hints) => set({ hints })} addLabel={t('editor.nodes.addHint')} multiline />}
              </Field>
              <Field label={t('editor.nodes.reference')} hint={t('editor.nodes.referenceHint')} error={err('reference_answer')}>
                {(id) => <Textarea id={id} rows={5} className="font-mono text-[13px]" value={n.reference_answer ?? ''}
                  onChange={(e) => set({ reference_answer: e.target.value || null })} />}
              </Field>
            </>
          )}
          {answered && (
            <details className="group rounded-2xl border bg-background/40 px-4 py-3">
              <summary className="cursor-pointer text-sm font-semibold text-muted-foreground group-open:text-foreground">{t('editor.nodes.attempts')}</summary>
              <div className="mt-3 grid gap-3 sm:grid-cols-3">
                <Field label={t('editor.nodes.maxAttempts')} error={err('max_attempts')}>
                  {(id) => <NumberInput id={id} min={1} max={10} value={n.max_attempts} onChange={(v) => set({ max_attempts: v ?? 3 })} />}
                </Field>
                <Field label={t('editor.nodes.latePenalty')} error={err('late_penalty')}>
                  {(id) => <NumberInput id={id} min={0} max={1} step={0.05} value={n.late_penalty} onChange={(v) => set({ late_penalty: v ?? 0 })} />}
                </Field>
                <Field label={t('editor.nodes.hintPenalty')} error={err('hint_penalty')}>
                  {(id) => <NumberInput id={id} min={0} max={1} step={0.05} value={n.hint_penalty} onChange={(v) => set({ hint_penalty: v ?? 0 })} />}
                </Field>
              </div>
            </details>
          )}
          {n.checks && <p className="text-xs text-muted-foreground">{t('editor.nodes.checks', { keys: Object.keys(n.checks).join(', ') })}</p>}
        </Group>
      )}

      <Group title={t('editor.nodes.when')}>
        <ConditionBuilder key={index} value={n.when} nodes={defn.nodes} self={n.id} onChange={(when) => set({ when })} />
        {err('when') && <p className="text-xs font-medium text-destructive">{err('when')}</p>}
      </Group>
    </div>
  )
}

// formada alohida ko'rsatiladigan maydonlar — qolgan xatolar tepada
const FIELDS = new Set([
  'id', 'type', 'day', 'at', 'after', 'from', 'brief', 'attachments', 'answer_types', 'due_in_minutes', 'options',
  'competencies', 'weight', 'rubric', 'reference_answer', 'max_attempts', 'late_penalty', 'hint_penalty', 'when',
])

function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-3 rounded-2xl border bg-background/30 p-4">
      <h3 className="text-sm font-bold">{title}</h3>
      {children}
    </section>
  )
}
