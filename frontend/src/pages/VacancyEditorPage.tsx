// /company/vacancies/new va /:id/edit (CONTRACT.md §23.8): vakansiya formasi —
// shartlar, kompetensiya talablari (chegara slayderi) va mashq uchun ssenariylar.
import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Loader2, Save, Send } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { api, ApiError } from '@/lib/api'
import {
  COMPETENCIES, EMPLOYMENTS, SECTORS, WORK_FORMATS,
  type CompanyVacancy, type Competency, type Scenario, type VacancyInput,
} from '@/lib/types'
import { cn } from '@/lib/utils'

const SELECT = 'h-10 w-full rounded-xl border border-input bg-background/60 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring'
const MAX_SCENARIOS = 5
const DEFAULT_REQUIREMENT = 60

const EMPTY: VacancyInput = {
  title: '', description: '', sector: 'IT', employment: 'full_time', work_format: 'office', location: null,
  salary_min: null, salary_max: null, requirements: {}, min_score: null, scenario_ids: [],
}

const toNumber = (v: string) => (v.trim() === '' ? null : Math.max(0, Math.round(Number(v.replace(/\s/g, '')))))

export default function VacancyEditorPage() {
  const { id } = useParams()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [form, setForm] = useState<VacancyInput | null>(id ? null : EMPTY)
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [saving, setSaving] = useState<'draft' | 'open' | 'save' | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api<Scenario[]>('/scenarios').then(setScenarios).catch(() => setScenarios([]))
    if (!id) return
    api<CompanyVacancy>(`/company/vacancies/${id}`)
      .then((v) => setForm({
        title: v.title, description: v.description, sector: v.sector, employment: v.employment, work_format: v.work_format,
        location: v.location, salary_min: v.salary_min, salary_max: v.salary_max, requirements: v.requirements,
        min_score: v.min_score, scenario_ids: v.scenario_ids,
      }))
      .catch(() => setError(t('vacancy.notFound')))
  }, [id, t])

  if (!form) {
    return <div className="grid place-items-center py-24">{error ? <p className="text-destructive">{error}</p> : <Loader2 className="h-6 w-6 animate-spin text-primary" />}</div>
  }

  const set = <K extends keyof VacancyInput>(key: K, value: VacancyInput[K]) => setForm((f) => f && { ...f, [key]: value })
  const toggleRequirement = (c: Competency, on: boolean) => {
    const next = { ...form.requirements }
    if (on) next[c] = DEFAULT_REQUIREMENT
    else delete next[c]
    set('requirements', next)
  }
  const toggleScenario = (sid: string, on: boolean) =>
    set('scenario_ids', on ? [...form.scenario_ids, sid].slice(0, MAX_SCENARIOS) : form.scenario_ids.filter((x) => x !== sid))
  const salaryInvalid = form.salary_min !== null && form.salary_max !== null && form.salary_min > form.salary_max

  const submit = async (mode: 'draft' | 'open' | 'save') => {
    setSaving(mode)
    setError(null)
    try {
      const saved = id
        ? await api<CompanyVacancy>(`/company/vacancies/${id}`, { method: 'PUT', json: form })
        : await api<CompanyVacancy>('/company/vacancies', { method: 'POST', json: { ...form, status: mode } })
      navigate(`/company/vacancies/${saved.id}`)
    } catch (err) {
      setError(err instanceof ApiError && err.status === 409 ? t('vacancy.editor.limit') : err instanceof ApiError ? err.message : t('common.error'))
      setSaving(null)
    }
  }
  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    submit(id ? 'save' : 'open')
  }

  return (
    <form onSubmit={onSubmit} className="mx-auto max-w-4xl space-y-6 px-4 py-8">
      <div className="flex items-center gap-3 animate-rise">
        <Button variant="ghost" size="icon" asChild aria-label={t('common.back')}>
          <Link to={id ? `/company/vacancies/${id}` : '/company/vacancies'}><ArrowLeft className="h-4 w-4" /></Link>
        </Button>
        <h1 className="text-3xl font-extrabold tracking-tight">{t(id ? 'vacancy.editor.editTitle' : 'vacancy.editor.newTitle')}</h1>
      </div>

      <Section title={t('vacancy.editor.basics')}>
        <Field id="title" label={t('vacancy.editor.titleLabel')}>
          <Input id="title" required minLength={2} maxLength={120} value={form.title} onChange={(e) => set('title', e.target.value)}
            placeholder={t('vacancy.editor.titlePlaceholder')} />
        </Field>
        <Field id="description" label={t('vacancy.editor.description')} hint={`${form.description.length}/4000`}>
          <Textarea id="description" required minLength={20} maxLength={4000} rows={6} value={form.description}
            onChange={(e) => set('description', e.target.value)} placeholder={t('vacancy.editor.descriptionPlaceholder')} />
        </Field>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field id="sector" label={t('talent.filter.sector')}>
            <select id="sector" className={SELECT} value={form.sector} onChange={(e) => set('sector', e.target.value as VacancyInput['sector'])}>
              {SECTORS.map((s) => <option key={s} value={s}>{t(`catalog.sector.${s}`)}</option>)}
            </select>
          </Field>
          <Field id="employment" label={t('vacancy.editor.employment')}>
            <select id="employment" className={SELECT} value={form.employment} onChange={(e) => set('employment', e.target.value as VacancyInput['employment'])}>
              {EMPLOYMENTS.map((v) => <option key={v} value={v}>{t(`vacancy.employment.${v}`)}</option>)}
            </select>
          </Field>
          <Field id="format" label={t('vacancy.editor.format')}>
            <select id="format" className={SELECT} value={form.work_format} onChange={(e) => set('work_format', e.target.value as VacancyInput['work_format'])}>
              {WORK_FORMATS.map((v) => <option key={v} value={v}>{t(`vacancy.format.${v}`)}</option>)}
            </select>
          </Field>
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field id="location" label={t('vacancy.editor.location')}>
            <Input id="location" maxLength={120} value={form.location ?? ''} onChange={(e) => set('location', e.target.value || null)}
              placeholder={t('vacancy.editor.locationPlaceholder')} />
          </Field>
          <Field id="salary_min" label={t('vacancy.editor.salaryMin')}>
            <Input id="salary_min" inputMode="numeric" value={form.salary_min ?? ''} onChange={(e) => set('salary_min', toNumber(e.target.value))} />
          </Field>
          <Field id="salary_max" label={t('vacancy.editor.salaryMax')}>
            <Input id="salary_max" inputMode="numeric" value={form.salary_max ?? ''} aria-invalid={salaryInvalid}
              onChange={(e) => set('salary_max', toNumber(e.target.value))} />
          </Field>
        </div>
        {salaryInvalid && <p className="text-sm text-destructive">{t('vacancy.editor.salaryInvalid')}</p>}
      </Section>

      <Section title={t('vacancy.editor.requirements')} hint={t('vacancy.editor.requirementsHint')}>
        <div className="grid gap-2 sm:grid-cols-2">
          {COMPETENCIES.map((c) => {
            const value = form.requirements[c]
            const on = value !== undefined
            return (
              <div key={c} className={cn('rounded-2xl border px-3 py-2.5 transition-colors', on ? 'border-primary/40 bg-primary/5' : 'bg-background/40')}>
                <label className="flex cursor-pointer items-center gap-2.5 text-sm font-medium">
                  <input type="checkbox" className="h-4 w-4 shrink-0 accent-[hsl(var(--primary))]" checked={on} onChange={(e) => toggleRequirement(c, e.target.checked)} />
                  <span className="flex-1">{t(`competency.${c}`)}</span>
                  {on && <span className="font-bold tabular-nums text-primary">≥ {value}</span>}
                </label>
                {on && (
                  <input type="range" min={0} max={100} step={5} value={value} aria-label={t(`competency.${c}`)}
                    onChange={(e) => set('requirements', { ...form.requirements, [c]: Number(e.target.value) })}
                    className="mt-1 block w-full accent-[hsl(var(--primary))]" />
                )}
              </div>
            )
          })}
        </div>
        <label className="flex flex-wrap items-center gap-3 text-sm font-medium">
          <input type="checkbox" className="h-4 w-4 shrink-0 accent-[hsl(var(--primary))]" checked={form.min_score !== null}
            onChange={(e) => set('min_score', e.target.checked ? 60 : null)} />
          {t('vacancy.editor.minScore')}
          {form.min_score !== null && (
            <>
              <input type="range" min={0} max={100} step={5} value={form.min_score} aria-label={t('vacancy.editor.minScore')}
                onChange={(e) => set('min_score', Number(e.target.value))} className="min-w-40 flex-1 accent-[hsl(var(--primary))]" />
              <span className="font-bold tabular-nums text-primary">≥ {form.min_score}</span>
            </>
          )}
        </label>
      </Section>

      <Section title={t('vacancy.editor.scenarios')} hint={t('vacancy.editor.scenariosHint', { count: MAX_SCENARIOS })}>
        <div className="grid gap-2 sm:grid-cols-2">
          {scenarios.map((s) => {
            const on = form.scenario_ids.includes(s.id)
            const full = !on && form.scenario_ids.length >= MAX_SCENARIOS
            return (
              <label key={s.id} className={cn('flex items-start gap-2.5 rounded-2xl border px-3 py-2.5 text-sm',
                on ? 'border-primary/40 bg-primary/5' : 'bg-background/40', full ? 'opacity-50' : 'cursor-pointer')}>
                <input type="checkbox" className="mt-0.5 h-4 w-4 shrink-0 accent-[hsl(var(--primary))]" checked={on} disabled={full}
                  onChange={(e) => toggleScenario(s.id, e.target.checked)} />
                <span className="min-w-0">
                  <span className="block font-medium">{s.title}</span>
                  <span className="text-xs text-muted-foreground">{t(`catalog.sector.${s.sector}`)} · {t('catalog.days', { count: s.duration_days })}</span>
                </span>
              </label>
            )
          })}
        </div>
      </Section>

      {error && <p className="glass rounded-2xl px-4 py-3 text-sm text-destructive" role="alert">{error}</p>}
      <div className="flex flex-wrap justify-end gap-2">
        {id ? (
          <Button type="submit" disabled={saving !== null || salaryInvalid}>
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} {t('vacancy.editor.save')}
          </Button>
        ) : (
          <>
            <Button type="button" variant="outline" disabled={saving !== null || salaryInvalid}
              onClick={(e) => e.currentTarget.form?.reportValidity() && submit('draft')}>
              {saving === 'draft' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} {t('vacancy.editor.saveDraft')}
            </Button>
            <Button type="submit" disabled={saving !== null || salaryInvalid}>
              {saving === 'open' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />} {t('vacancy.editor.publish')}
            </Button>
          </>
        )}
      </div>
    </form>
  )
}

function Section({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <section className="glass space-y-4 rounded-3xl p-5 animate-rise sm:p-6">
      <div>
        <h2 className="font-bold">{title}</h2>
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      </div>
      {children}
    </section>
  )
}

function Field({ id, label, hint, children }: { id: string; label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between">
        <Label htmlFor={id}>{label}</Label>
        {hint && <span className="text-xs tabular-nums text-muted-foreground">{hint}</span>}
      </div>
      {children}
    </div>
  )
}
