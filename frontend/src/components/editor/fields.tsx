// Muharrir formalari uchun kichik maydonlar: yorliq + xato, select, chiplar, ro'yxat.
import { useEffect, useId, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Plus, Trash2 } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'

export const SELECT =
  'h-10 w-full rounded-xl border border-input bg-background/60 px-3 text-sm focus:outline-none focus-visible:border-primary/60 focus-visible:ring-4 focus-visible:ring-ring/15'

export function Field({ label, hint, error, children, className }: {
  label: string
  hint?: string
  error?: string
  children: (id: string) => ReactNode
  className?: string
}) {
  const id = useId()
  return (
    <div className={cn('min-w-0 space-y-1.5', className)}>
      <label htmlFor={id} className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</label>
      {children(id)}
      {error ? <p className="text-xs font-medium text-destructive">{error}</p> : hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  )
}

/** Raqam maydoni: bo'sh — `null` (ixtiyoriy maydonlar uchun). */
export function NumberInput({ value, onChange, min, max, step, ...rest }: {
  value: number | null
  onChange: (v: number | null) => void
  min?: number
  max?: number
  step?: number
  id?: string
  placeholder?: string
  'aria-label'?: string
}) {
  return (
    <Input type="number" inputMode="decimal" min={min} max={max} step={step} value={value ?? ''} {...rest}
      onChange={(e) => onChange(e.target.value === '' ? null : Number(e.target.value))} />
  )
}

/** Ko'p tanlov chiplari (hujjatlar, kompetensiyalar, javob turlari). */
export function Chips<T extends string>({ options, value, onChange, label }: {
  options: { value: T; label: string }[]
  value: T[]
  onChange: (v: T[]) => void
  label: string
}) {
  const { t } = useTranslation()
  if (!options.length) return <p className="text-sm text-muted-foreground">{t('editor.none')}</p>
  return (
    <div className="flex flex-wrap gap-1.5" role="group" aria-label={label}>
      {options.map((o) => {
        const on = value.includes(o.value)
        return (
          <button key={o.value} type="button" aria-pressed={on}
            onClick={() => onChange(on ? value.filter((v) => v !== o.value) : [...value, o.value])}
            className={cn('rounded-full border px-3 py-1 text-xs font-semibold transition-colors',
              on ? 'border-primary/50 bg-primary/12 text-primary' : 'border-border text-muted-foreground hover:text-foreground')}>
            {o.label}
          </button>
        )
      })}
    </div>
  )
}

/** Matnlar ro'yxati (hintlar, sirlar). */
export function TextList({ value, onChange, addLabel, placeholder, multiline = false }: {
  value: string[]
  onChange: (v: string[]) => void
  addLabel: string
  placeholder?: string
  multiline?: boolean
}) {
  const { t } = useTranslation()
  const set = (i: number, text: string) => onChange(value.map((v, j) => (j === i ? text : v)))
  return (
    <div className="space-y-2">
      {value.map((v, i) => (
        <div key={i} className="flex items-start gap-2">
          {multiline
            ? <Textarea rows={2} value={v} placeholder={placeholder} onChange={(e) => set(i, e.target.value)} aria-label={`${addLabel} ${i + 1}`} />
            : <Input value={v} placeholder={placeholder} onChange={(e) => set(i, e.target.value)} aria-label={`${addLabel} ${i + 1}`} />}
          <RemoveButton label={t('editor.remove')} onClick={() => onChange(value.filter((_, j) => j !== i))} />
        </div>
      ))}
      <AddButton onClick={() => onChange([...value, ''])}>{addLabel}</AddButton>
    </div>
  )
}

export function AddButton({ onClick, children }: { onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" onClick={onClick}
      className="flex items-center gap-1.5 rounded-xl border border-dashed border-primary/40 px-3 py-1.5 text-sm font-semibold text-primary transition-colors hover:bg-primary/8">
      <Plus className="h-4 w-4" /> {children}
    </button>
  )
}

export function RemoveButton({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button type="button" onClick={onClick} aria-label={label} title={label}
      className="grid h-10 w-10 shrink-0 place-items-center rounded-xl text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive">
      <Trash2 className="h-4 w-4" />
    </button>
  )
}

/** Bo'lim ichidagi xatolar (maydonga bog'lanmaganlari). */
export function ErrorNote({ messages }: { messages: string[] }) {
  if (!messages.length) return null
  return (
    <ul className="space-y-1 rounded-xl border border-destructive/30 bg-destructive/8 px-3 py-2 text-sm text-destructive">
      {messages.map((m, i) => <li key={i}>{m}</li>)}
    </ul>
  )
}

/**
 * Kalit/id maydoni: o'zgarish maydondan chiqqanda (yoki Enter) qo'llanadi — qayta nomlashda
 * havolalar yangilanadi, oraliq qiymat boshqa kalit bilan to'qnashib ularni aralashtirmasin.
 */
export function KeyInput({ value, onCommit, id, ...rest }: {
  value: string
  onCommit: (v: string) => void
  id?: string
  placeholder?: string
  'aria-label'?: string
}) {
  const [draft, setDraft] = useState(value)
  useEffect(() => setDraft(value), [value])
  const commit = () => {
    const v = draft.trim()
    if (v !== value) onCommit(v)
  }
  return (
    <Input id={id} value={draft} spellCheck={false} autoComplete="off" className="font-mono" {...rest}
      onChange={(e) => setDraft(e.target.value)} onBlur={commit}
      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); commit() } }} />
  )
}
