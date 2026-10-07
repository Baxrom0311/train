// Ssenariy muharriri (CONTRACT.md §16.3): forma ↔ ta'rif, jonli tekshiruv, qoralama va nashr.
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft, CheckCircle2, CircleAlert, FileCode2, FileText, Info, ListTree, Loader2, Rocket, Save, Settings2, Users,
  type LucideIcon,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog'
import NodeEditor from '@/components/editor/NodeEditor'
import NodeTimeline from '@/components/editor/NodeTimeline'
import YamlPanel from '@/components/editor/YamlPanel'
import { DocumentsSection, GeneralSection, PersonasSection, type Located } from '@/components/editor/sections'
import {
  blankNode, locate, normalize, templateScenario, uniqueKey,
  type FieldError, type ScenarioAdmin, type ScenarioDef, type Section, type Validation, type VersionOut,
} from '@/components/editor/model'
import { api, ApiError } from '@/lib/api'
import type { NodeType } from '@/lib/types'
import { cn } from '@/lib/utils'

type Tab = Section | 'yaml'
const TABS: { key: Tab; Icon: LucideIcon }[] = [
  { key: 'general', Icon: Settings2 },
  { key: 'personas', Icon: Users },
  { key: 'documents', Icon: FileText },
  { key: 'nodes', Icon: ListTree },
  { key: 'yaml', Icon: FileCode2 },
]
const VALIDATE_DELAY = 600

const serialize = (d: ScenarioDef) => JSON.stringify(d)

/** 422 javobidagi `{errors: [...]}` (CONTRACT.md §16.2). */
function structuredErrors(e: unknown): FieldError[] | null {
  const detail = e instanceof ApiError ? (e.detail as { errors?: FieldError[] } | undefined) : undefined
  return Array.isArray(detail?.errors) ? detail.errors : null
}

export default function ScenarioEditorPage() {
  const { t } = useTranslation()
  const { id } = useParams()
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const location = useLocation()
  const isNew = !id

  const [defn, setDefn] = useState<ScenarioDef | null>(isNew ? templateScenario() : null)
  const [saved, setSaved] = useState(() => (isNew ? serialize(templateScenario()) : ''))
  const [version, setVersion] = useState<VersionOut | null>(null)
  const [info, setInfo] = useState<ScenarioAdmin | null>(null)
  const [loadError, setLoadError] = useState('')
  const [tab, setTab] = useState<Tab>('general')
  const [selected, setSelected] = useState<number | null>(null)
  const [focus, setFocus] = useState<{ id: string } | null>(null)
  const [validation, setValidation] = useState<Validation | null>(null)
  const [validating, setValidating] = useState(false)
  const [busy, setBusy] = useState<'save' | 'publish' | null>(null)
  // yangi ssenariy saqlangach sahifa `/edit` manziliga o'tadi — xabar shu bilan birga keladi
  const [notice, setNotice] = useState(() => (location.state as { notice?: string } | null)?.notice ?? '')
  const [actionError, setActionError] = useState('')
  const [confirm, setConfirm] = useState(false)

  const dirty = defn !== null && serialize(defn) !== saved
  const update = useCallback((f: (d: ScenarioDef) => ScenarioDef) => setDefn((d) => (d ? f(d) : d)), [])

  // ── Yuklash ─────────────────────────────────────────────────────
  const loadInfo = useCallback(async () => {
    const list = await api<ScenarioAdmin[]>('/admin/scenarios')
    const found = list.find((s) => s.id === id) ?? null
    setInfo(found)
    return found
  }, [id])

  useEffect(() => {
    if (isNew) return
    let cancelled = false
    ;(async () => {
      try {
        const found = await loadInfo()
        if (!found) throw new ApiError(404, t('editor.notFound'))
        const number = Number(params.get('v')) || found.versions[0].version
        const v = await api<VersionOut>(`/admin/scenarios/${id}/versions/${number}`)
        if (cancelled) return
        const d = normalize(v.definition)
        setVersion(v)
        setDefn(d)
        setSaved(serialize(d))
      } catch (e) {
        if (!cancelled) setLoadError((e as Error).message)
      }
    })()
    return () => { cancelled = true }
  }, [id, isNew, params, loadInfo, t])

  // ── Jonli tekshiruv (debounce) ──────────────────────────────────
  useEffect(() => {
    if (!defn) return
    setValidating(true)
    const ctrl = new AbortController()
    const timer = setTimeout(() => {
      api<Validation>('/admin/scenarios/validate', { method: 'POST', json: { definition: defn }, signal: ctrl.signal })
        .then(setValidation)
        .catch(() => {})
        .finally(() => !ctrl.signal.aborted && setValidating(false))
    }, VALIDATE_DELAY)
    return () => { clearTimeout(timer); ctrl.abort() }
  }, [defn])

  // saqlanmagan o'zgarishlar bilan sahifani yopish
  useEffect(() => {
    if (!dirty) return
    const warn = (e: BeforeUnloadEvent) => e.preventDefault()
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty])

  // xato bosilganda — tegishli kartaga aylantirish
  useEffect(() => {
    if (!focus) return
    document.getElementById(focus.id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [focus])

  const located: Located[] = useMemo(
    () => (defn && validation ? validation.errors.map((e) => ({ ...e, ...locate(e, defn) })) : []),
    [validation, defn],
  )
  const bySection = (s: Section) => located.filter((e) => e.section === s)
  const invalidNodes = useMemo(() => new Set(located.filter((e) => e.section === 'nodes' && e.index !== undefined).map((e) => e.index!)), [located])

  const goTo = (e: Located) => {
    setTab(e.section)
    if (e.section === 'nodes' && e.index !== undefined) setSelected(e.index)
    else setFocus({ id: e.index !== undefined ? `${e.section}-${e.index}` : 'editor-top' })
  }

  // ── Saqlash va nashr ────────────────────────────────────────────
  const save = async (): Promise<VersionOut | null> => {
    if (!defn) return null
    setBusy('save')
    setActionError('')
    setNotice('')
    try {
      const v = isNew
        ? await api<VersionOut>('/admin/scenarios', { method: 'POST', json: { definition: defn } })
        : await api<VersionOut>(`/admin/scenarios/${id}/draft`, { method: 'PUT', json: { definition: defn } })
      const d = normalize(v.definition)
      setVersion(v)
      setDefn(d)
      setSaved(serialize(d))
      setNotice(t('editor.saved', { version: v.version }))
      if (isNew) navigate(`/admin/scenarios/${v.scenario_id}/edit`, { replace: true, state: { notice: t('editor.saved', { version: v.version }) } })
      else await loadInfo()
      return v
    } catch (e) {
      const errors = structuredErrors(e)
      if (errors) {
        setValidation({ ok: false, errors, warnings: [], summary: null })
        setActionError(t('editor.fixErrors'))
      } else if (e instanceof ApiError && e.status === 409) {
        setValidation({ ok: false, errors: [{ path: ['slug'], message: t('editor.slugTaken') }], warnings: [], summary: null })
        setTab('general')
        setActionError(t('editor.slugTaken'))
      } else {
        setActionError((e as Error).message)
      }
      return null
    } finally {
      setBusy(null)
    }
  }

  const publish = async () => {
    setConfirm(false)
    const target = dirty || !version ? await save() : version
    if (!target) return
    setBusy('publish')
    try {
      const v = await api<VersionOut>(`/admin/scenarios/${target.scenario_id}/versions/${target.version}/publish`, { method: 'POST' })
      setVersion(v)
      setNotice(t('editor.published', { version: v.version }))
      await loadInfo()
    } catch (e) {
      setActionError(structuredErrors(e) ? t('editor.fixErrors') : (e as Error).message)
    } finally {
      setBusy(null)
    }
  }

  // telefonda forma ro'yxat ostida — tanlangan node formasiga tushirish
  const pickNode = (i: number) => {
    setSelected(i)
    if (window.matchMedia('(max-width: 1023px)').matches) setFocus({ id: 'node-form' })
  }

  const addNode = (type: NodeType, day: number) => {
    if (!defn) return
    const node = blankNode(type, uniqueKey(type, defn.nodes.map((n) => n.id)), day)
    update((d) => ({ ...d, nodes: [...d.nodes, node] }))
    pickNode(defn.nodes.length)
  }

  if (loadError) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-center">
        <p className="text-lg font-semibold">{loadError}</p>
        <Link to="/admin/scenarios" className="mt-4 inline-block text-primary hover:underline">{t('editor.backToList')}</Link>
      </div>
    )
  }
  if (!defn) return <div className="grid place-items-center py-24"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>

  const canPublish = validation?.ok && !validating && (dirty || version?.status === 'draft')
  const editingPublished = version && version.status !== 'draft'
  const nextVersion = editingPublished ? (info?.versions[0]?.version ?? version.version) + 1 : version?.version

  return (
    <div id="editor-top" className="mx-auto max-w-7xl scroll-mt-28 space-y-5 px-4 py-6">
      {/* Sarlavha va amallar */}
      <div className="glass-strong sticky top-[4.75rem] z-30 flex flex-wrap items-center gap-3 rounded-2xl px-4 py-3">
        <Link to="/admin/scenarios" aria-label={t('editor.backToList')} title={t('editor.backToList')}
          className="grid h-9 w-9 shrink-0 place-items-center rounded-xl text-muted-foreground transition-colors hover:bg-accent hover:text-foreground">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-lg font-extrabold tracking-tight">{defn.title || t('editor.untitled')}</h1>
          <p className="flex flex-wrap items-center gap-x-2 text-xs text-muted-foreground">
            {version
              ? <span>v{version.version} · <StatusText status={version.status} /></span>
              : <span>{t('editor.newScenario')}</span>}
            {dirty && <span className="font-semibold text-primary">● {t('editor.unsaved')}</span>}
            {dirty && editingPublished && <span>{t('editor.willBeDraft', { version: nextVersion })}</span>}
          </p>
        </div>
        <Button variant="outline" onClick={save} disabled={!dirty || busy !== null}>
          {busy === 'save' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          {t('editor.saveDraft')}
        </Button>
        <Button onClick={() => setConfirm(true)} disabled={!canPublish || busy !== null}>
          {busy === 'publish' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Rocket className="h-4 w-4" />}
          {t('editor.publish')}
        </Button>
      </div>

      {(notice || actionError) && (
        <p role="status" className={cn('rounded-2xl px-4 py-2.5 text-sm font-medium',
          actionError ? 'bg-destructive/10 text-destructive' : 'bg-success/12 text-success')}>
          {actionError || notice}
        </p>
      )}

      <ValidationBar validation={validation} validating={validating} located={located} onPick={goTo} />

      <nav className="glass flex w-full gap-1 overflow-x-auto rounded-2xl p-1 sm:w-fit" role="tablist">
        {TABS.map(({ key, Icon }) => {
          const count = key === 'yaml' ? 0 : bySection(key).length
          return (
            <button key={key} type="button" role="tab" aria-selected={tab === key} onClick={() => setTab(key)}
              className={cn('flex shrink-0 items-center gap-2 rounded-xl px-3.5 py-2 text-sm font-semibold transition-colors',
                tab === key ? 'bg-brand text-primary-foreground shadow' : 'text-muted-foreground hover:text-foreground')}>
              <Icon className="h-4 w-4" />
              {t(`editor.tabs.${key}`)}
              {count > 0 && <span className={cn('rounded-full px-1.5 text-xs', tab === key ? 'bg-black/15' : 'bg-destructive/15 text-destructive')}>{count}</span>}
            </button>
          )
        })}
      </nav>

      {tab === 'general' && <GeneralSection defn={defn} update={update} errors={bySection('general')} isNew={isNew} />}
      {tab === 'personas' && <PersonasSection defn={defn} update={update} errors={bySection('personas')} isNew={isNew} />}
      {tab === 'documents' && <DocumentsSection defn={defn} update={update} errors={bySection('documents')} isNew={isNew} />}
      {tab === 'yaml' && <YamlPanel defn={defn} onApply={(d) => { setDefn(d); setSelected(null) }} />}
      {tab === 'nodes' && (
        <div className="grid gap-5 lg:grid-cols-[20rem_minmax(0,1fr)]">
          <aside className="glass h-fit min-w-0 rounded-3xl p-3 lg:sticky lg:top-44 lg:max-h-[calc(100dvh-12rem)] lg:overflow-y-auto">
            <NodeTimeline nodes={defn.nodes} days={defn.duration_days} selected={selected} invalid={invalidNodes}
              onSelect={pickNode} onAdd={addNode} />
            {bySection('nodes').some((e) => e.index === undefined) && (
              <ul className="mt-3 space-y-1 border-t pt-3 text-xs text-destructive">
                {bySection('nodes').filter((e) => e.index === undefined).map((e, i) => <li key={i}>{e.message}</li>)}
              </ul>
            )}
          </aside>
          <div id="node-form" className="glass min-w-0 scroll-mt-40 rounded-3xl p-5 sm:p-6">
            {selected !== null && defn.nodes[selected] ? (
              <NodeEditor key={selected} defn={defn} index={selected} update={update} onSelect={setSelected}
                errors={bySection('nodes').filter((e) => e.index === selected)} />
            ) : (
              <div className="grid place-items-center gap-2 py-20 text-center text-muted-foreground">
                <ListTree className="h-8 w-8" />
                <p>{t('editor.nodes.pick')}</p>
              </div>
            )}
          </div>
        </div>
      )}

      <Dialog open={confirm} onOpenChange={setConfirm}>
        <DialogContent closeLabel={t('editor.cancel')} className="max-w-md space-y-4 p-6">
          <DialogTitle className="pr-8 text-lg font-bold">{t('editor.confirm.title')}</DialogTitle>
          <DialogDescription asChild>
            <div className="space-y-2 text-sm text-muted-foreground">
              <p>{t('editor.confirm.body', { title: defn.title })}</p>
              {info?.versions.some((v) => v.status === 'published') && <p>{t('editor.confirm.archive')}</p>}
              {dirty && <p className="font-medium text-foreground">{t('editor.confirm.saveFirst')}</p>}
            </div>
          </DialogDescription>
          {validation?.summary && <SummaryLine summary={validation.summary} />}
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setConfirm(false)}>{t('editor.cancel')}</Button>
            <Button onClick={publish}><Rocket className="h-4 w-4" /> {t('editor.publish')}</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function StatusText({ status }: { status: VersionOut['status'] }) {
  const { t } = useTranslation()
  return <span className={cn('font-semibold', status === 'published' ? 'text-success' : status === 'draft' ? 'text-primary' : '')}>{t(`editor.status.${status}`)}</span>
}

function SummaryLine({ summary }: { summary: NonNullable<Validation['summary']> }) {
  const { t } = useTranslation()
  return (
    <p className="text-sm text-muted-foreground">
      {[
        t('editor.summary.days', { count: summary.days }),
        t('editor.summary.nodes', { count: summary.nodes }),
        t('editor.summary.graded', { count: summary.graded }),
        t('editor.summary.personas', { count: summary.personas }),
        t('editor.summary.documents', { count: summary.documents }),
        summary.mentor ? t('editor.summary.mentor') : t('editor.summary.noMentor'),
      ].join(' · ')}
    </p>
  )
}

function ValidationBar({ validation, validating, located, onPick }: {
  validation: Validation | null
  validating: boolean
  located: Located[]
  onPick: (e: Located) => void
}) {
  const { t } = useTranslation()
  if (!validation) {
    return <div className="glass flex items-center gap-2 rounded-2xl px-4 py-3 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" /> {t('editor.checking')}</div>
  }
  return (
    <div className={cn('glass space-y-2 rounded-2xl px-4 py-3 text-sm transition-opacity', validating && 'opacity-70')} aria-live="polite">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        {validation.ok ? (
          <span className="flex items-center gap-1.5 font-semibold text-success"><CheckCircle2 className="h-4 w-4" /> {t('editor.valid')}</span>
        ) : (
          <span className="flex items-center gap-1.5 font-semibold text-destructive"><CircleAlert className="h-4 w-4" /> {t('editor.errors', { count: located.length })}</span>
        )}
        {validation.summary && <SummaryLine summary={validation.summary} />}
        {validating && <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />}
      </div>
      {located.length > 0 && (
        <ul className="max-h-40 space-y-0.5 overflow-y-auto">
          {located.map((e, i) => (
            <li key={i}>
              <button type="button" onClick={() => onPick(e)} className="w-full rounded-lg px-2 py-1 text-left text-destructive transition-colors hover:bg-destructive/10">
                <span className="mr-2 text-xs font-semibold uppercase text-muted-foreground">{t(`editor.tabs.${e.section}`)}</span>
                {e.path.length > 0 && <span className="mr-1.5 font-mono text-xs">{e.path.join('.')}</span>}
                {e.message}
              </button>
            </li>
          ))}
        </ul>
      )}
      {validation.warnings.map((w, i) => (
        <p key={i} className="flex items-start gap-1.5 text-muted-foreground"><Info className="mt-0.5 h-4 w-4 shrink-0 text-primary" /> {w}</p>
      ))}
    </div>
  )
}
