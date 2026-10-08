// Muharrir bo'limlari: umumiy ma'lumot, personajlar, hujjatlar (CONTRACT.md §16.3).
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Eye, GraduationCap, Pencil, UserRound } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import RichText from '@/components/desk/RichText'
import { SECTORS } from '@/lib/types'
import { cn } from '@/lib/utils'
import { AddButton, Chips, ErrorNote, Field, KeyInput, NumberInput, RemoveButton, SELECT, TextList } from './fields'
import {
  DIFFICULTIES, blankPersona, renameDocument, renamePersona, uniqueKey,
  type ErrorTarget, type FieldError, type ScenarioDef,
} from './model'
import { useEditorScope } from './scope'

export type Located = FieldError & ErrorTarget
type Update = (f: (d: ScenarioDef) => ScenarioDef) => void

interface SectionProps {
  defn: ScenarioDef
  update: Update
  errors: Located[]
  isNew: boolean
}

const fieldError = (errors: Located[], field: string, index?: number) =>
  errors.find((e) => e.field === field && e.index === index)?.message
const loose = (errors: Located[], index?: number) =>
  errors.filter((e) => !e.field && e.index === index).map((e) => e.message)

export function GeneralSection({ defn, update, errors, isNew }: SectionProps) {
  const { t } = useTranslation()
  const scope = useEditorScope()
  const set = <K extends keyof ScenarioDef>(key: K, value: ScenarioDef[K]) => update((d) => ({ ...d, [key]: value }))
  return (
    <div className="glass space-y-5 rounded-3xl p-5 sm:p-6">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label={t('editor.general.title')} error={fieldError(errors, 'title')} className="sm:col-span-2">
          {(id) => <Input id={id} value={defn.title} maxLength={200} onChange={(e) => set('title', e.target.value)} />}
        </Field>
        <Field label={t('editor.general.slug')} error={fieldError(errors, 'slug')}
          hint={isNew ? t('editor.general.slugHint') : t('editor.general.slugLocked')}>
          {(id) => (
            <Input id={id} value={defn.slug} disabled={!isNew} spellCheck={false} className="font-mono"
              placeholder="kompaniya-lavozim-day1" onChange={(e) => set('slug', e.target.value.toLowerCase())} />
          )}
        </Field>
        <Field label={t('editor.general.company')} error={fieldError(errors, 'company_name')}
          hint={t(scope.company ? 'editor.general.companyOwn' : 'editor.general.companyHint')}>
          {(id) => scope.company
            ? <Input id={id} value={defn.company_name} disabled placeholder={t('editor.general.companyAuto')} />
            : <Input id={id} value={defn.company_name} maxLength={120} onChange={(e) => set('company_name', e.target.value)} />}
        </Field>
        <Field label={t('editor.general.sector')} error={fieldError(errors, 'sector')}>
          {(id) => (
            <select id={id} className={SELECT} value={defn.sector} onChange={(e) => set('sector', e.target.value as ScenarioDef['sector'])}>
              {SECTORS.map((s) => <option key={s} value={s}>{t(`catalog.sector.${s}`)}</option>)}
            </select>
          )}
        </Field>
        <Field label={t('editor.general.difficulty')} error={fieldError(errors, 'difficulty')}>
          {(id) => (
            <select id={id} className={SELECT} value={defn.difficulty} onChange={(e) => set('difficulty', e.target.value as ScenarioDef['difficulty'])}>
              {DIFFICULTIES.map((x) => <option key={x} value={x}>{t(`editor.difficulty.${x}`)}</option>)}
            </select>
          )}
        </Field>
        <Field label={t('editor.general.days')} error={fieldError(errors, 'duration_days')} hint={t(scope.company ? 'editor.general.daysHintCompany' : 'editor.general.daysHint', { count: scope.maxDays })}>
          {(id) => <NumberInput id={id} min={1} max={scope.maxDays} value={defn.duration_days} onChange={(v) => set('duration_days', v ?? 1)} />}
        </Field>
      </div>
      <ErrorNote messages={loose(errors)} />
    </div>
  )
}

export function PersonasSection({ defn, update, errors }: SectionProps) {
  const { t } = useTranslation()
  const docs = defn.documents.map((d) => ({ value: d.key, label: d.title || d.key }))
  const set = (i: number, patch: Partial<ScenarioDef['personas'][number]>) =>
    update((d) => ({ ...d, personas: d.personas.map((p, j) => (j === i ? { ...p, ...patch } : p)) }))
  const used = (key: string) => defn.nodes.filter((n) => n.from === key).length

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">{t('editor.personas.intro')}</p>
      <ErrorNote messages={loose(errors)} />
      {defn.personas.map((p, i) => {
        const mentor = p.kind === 'mentor'
        const Icon = mentor ? GraduationCap : UserRound
        return (
          <section key={i} id={`personas-${i}`} className="glass scroll-mt-28 space-y-4 rounded-3xl p-5">
            <header className="flex items-center gap-3">
              <span className={cn('grid h-10 w-10 shrink-0 place-items-center rounded-2xl', mentor ? 'bg-brand text-primary-foreground' : 'bg-primary/12 text-primary')}>
                <Icon className="h-5 w-5" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate font-bold">{p.name || t('editor.personas.unnamed')}</p>
                <p className="truncate text-xs text-muted-foreground">
                  {mentor ? t('editor.personas.mentor') : t('editor.personas.colleague')} · {t('editor.personas.used', { count: used(p.key) })}
                </p>
              </div>
              <RemoveButton label={t('editor.remove')} onClick={() => update((d) => ({ ...d, personas: d.personas.filter((_, j) => j !== i) }))} />
            </header>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Field label={t('editor.key')} error={fieldError(errors, 'key', i)}>
                {(id) => <KeyInput id={id} value={p.key} onCommit={(v) => update((d) => renamePersona(d, i, v))} />}
              </Field>
              <Field label={t('editor.personas.name')} error={fieldError(errors, 'name', i)}>
                {(id) => <Input id={id} value={p.name} maxLength={80} onChange={(e) => set(i, { name: e.target.value })} />}
              </Field>
              <Field label={t('editor.personas.role')} error={fieldError(errors, 'role', i)}>
                {(id) => <Input id={id} value={p.role} maxLength={120} onChange={(e) => set(i, { role: e.target.value })} />}
              </Field>
              <Field label={t('editor.personas.kind')}>
                {(id) => (
                  <select id={id} className={SELECT} value={p.kind} onChange={(e) => set(i, { kind: e.target.value as 'colleague' | 'mentor' })}>
                    <option value="colleague">{t('editor.personas.colleague')}</option>
                    <option value="mentor">{t('editor.personas.mentor')}</option>
                  </select>
                )}
              </Field>
            </div>
            <Field label={t('editor.personas.tone')} hint={t('editor.personas.toneHint')}>
              {(id) => <Input id={id} value={p.tone} onChange={(e) => set(i, { tone: e.target.value })} />}
            </Field>
            <Field label={t('editor.personas.knows')} hint={t('editor.personas.knowsHint')}>
              {() => <Chips label={t('editor.personas.knows')} options={docs} value={p.knows} onChange={(knows) => set(i, { knows })} />}
            </Field>
            <Field label={t('editor.personas.secrets')} hint={t('editor.personas.secretsHint')}>
              {() => <TextList value={p.secrets} onChange={(secrets) => set(i, { secrets })} addLabel={t('editor.personas.addSecret')} />}
            </Field>
            <details className="group rounded-2xl border bg-background/40 px-4 py-3">
              <summary className="cursor-pointer text-sm font-semibold text-muted-foreground group-open:text-foreground">{t('editor.personas.replies')}</summary>
              <div className="mt-3 grid gap-4">
                <Field label={t('editor.personas.busy')} error={fieldError(errors, 'busy_reply', i)}>
                  {(id) => <Textarea id={id} rows={2} value={p.busy_reply ?? ''} onChange={(e) => set(i, { busy_reply: e.target.value })} />}
                </Field>
                <Field label={t('editor.personas.deflect')} error={fieldError(errors, 'deflect_reply', i)}>
                  {(id) => <Textarea id={id} rows={2} value={p.deflect_reply ?? ''} onChange={(e) => set(i, { deflect_reply: e.target.value })} />}
                </Field>
                {mentor && (
                  <Field label={t('editor.personas.nudge')} hint={t('editor.personas.nudgeHint')} error={fieldError(errors, 'nudge_reply', i)}>
                    {(id) => <Textarea id={id} rows={2} value={p.nudge_reply ?? ''} onChange={(e) => set(i, { nudge_reply: e.target.value })} />}
                  </Field>
                )}
              </div>
            </details>
            <ErrorNote messages={loose(errors, i)} />
          </section>
        )
      })}
      <AddButton onClick={() => update((d) => ({ ...d, personas: [...d.personas, blankPersona(uniqueKey('persona', d.personas.map((p) => p.key)))] }))}>
        {t('editor.personas.add')}
      </AddButton>
    </div>
  )
}

export function DocumentsSection({ defn, update, errors }: SectionProps) {
  const { t } = useTranslation()
  const [preview, setPreview] = useState<number | null>(null)
  const set = (i: number, patch: Partial<ScenarioDef['documents'][number]>) =>
    update((d) => ({ ...d, documents: d.documents.map((x, j) => (j === i ? { ...x, ...patch } : x)) }))
  const used = (key: string) => defn.nodes.filter((n) => n.attachments.includes(key)).length + defn.personas.filter((p) => p.knows.includes(key)).length

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">{t('editor.documents.intro')}</p>
      <ErrorNote messages={loose(errors)} />
      {defn.documents.map((doc, i) => (
        <section key={i} id={`documents-${i}`} className="glass scroll-mt-28 space-y-4 rounded-3xl p-5">
          <div className="grid gap-4 sm:grid-cols-[minmax(0,14rem)_minmax(0,1fr)_auto] sm:items-end">
            <Field label={t('editor.key')} error={fieldError(errors, 'key', i)}>
              {(id) => <KeyInput id={id} value={doc.key} onCommit={(v) => update((d) => renameDocument(d, i, v))} />}
            </Field>
            <Field label={t('editor.documents.title')} error={fieldError(errors, 'title', i)}>
              {(id) => <Input id={id} value={doc.title} onChange={(e) => set(i, { title: e.target.value })} />}
            </Field>
            <div className="flex items-center gap-1">
              <button type="button" onClick={() => setPreview(preview === i ? null : i)} aria-pressed={preview === i}
                className="flex h-10 items-center gap-1.5 rounded-xl px-3 text-sm font-semibold text-muted-foreground transition-colors hover:bg-accent hover:text-foreground">
                {preview === i ? <Pencil className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                {preview === i ? t('editor.edit') : t('editor.preview')}
              </button>
              <RemoveButton label={t('editor.remove')} onClick={() => update((d) => ({ ...d, documents: d.documents.filter((_, j) => j !== i) }))} />
            </div>
          </div>
          {preview === i ? (
            <div className="max-h-[32rem] overflow-auto rounded-2xl border bg-background/60 p-4 text-sm"><RichText text={doc.content} /></div>
          ) : (
            <Field label={t('editor.documents.content')} error={fieldError(errors, 'content', i)} hint={t('editor.documents.contentHint')}>
              {(id) => <Textarea id={id} rows={10} className="font-mono text-[13px]" value={doc.content} onChange={(e) => set(i, { content: e.target.value })} />}
            </Field>
          )}
          <p className="text-xs text-muted-foreground">{t('editor.documents.used', { count: used(doc.key) })}</p>
          <ErrorNote messages={loose(errors, i)} />
        </section>
      ))}
      <AddButton onClick={() => update((d) => ({
        ...d, documents: [...d.documents, { key: uniqueKey('doc', d.documents.map((x) => x.key)), title: '', content: '' }],
      }))}>
        {t('editor.documents.add')}
      </AddButton>
    </div>
  )
}
