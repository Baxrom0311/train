import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { CheckCircle2, ChevronDown, Copy, Globe, Loader2, Server, Workflow } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Segmented } from '@/components/ui/segmented'
import { api } from '@/lib/api'
import { formatDateTime } from '@/lib/time'
import type { ErrorGroup, ErrorGroupDetail, ErrorGroupList, ErrorSource, ErrorStatus } from '@/lib/types'
import { cn } from '@/lib/utils'

// §32.5
const SOURCE_ICON = { api: Server, worker: Workflow, frontend: Globe } as const

export default function ErrorGroups({ onOpenTotal }: { onOpenTotal: (n: number) => void }) {
  const { t } = useTranslation()
  const [status, setStatus] = useState<ErrorStatus>('open')
  const [source, setSource] = useState<ErrorSource | 'all'>('all')
  const [items, setItems] = useState<ErrorGroup[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [openId, setOpenId] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    setLoading(true)
    const query = new URLSearchParams({ status, ...(source === 'all' ? {} : { source }) })
    api<ErrorGroupList>(`/admin/errors?${query}`)
      .then((list) => {
        if (!alive) return
        setItems(list.items)
        setError(false)
        onOpenTotal(list.open_total)
      })
      .catch(() => alive && setError(true))
      .finally(() => alive && setLoading(false))
    return () => { alive = false }
  }, [status, source, onOpenTotal])

  const resolved = (group: ErrorGroupDetail) => {
    setItems((list) => list?.filter((g) => g.id !== group.id) ?? null)
    setOpenId(null)
    api<ErrorGroupList>('/admin/errors?limit=1').then((l) => onOpenTotal(l.open_total)).catch(() => {})
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Segmented label={t('errors.status')} value={status} onChange={setStatus} busy={loading}
          options={[{ value: 'open', label: t('errors.open') }, { value: 'resolved', label: t('errors.resolved') }]} />
        <Segmented label={t('errors.source')} value={source} onChange={setSource}
          options={(['all', 'api', 'worker', 'frontend'] as const).map((s) => ({ value: s, label: t(`errors.sources.${s}`) }))} />
      </div>

      {error && <p className="glass rounded-2xl px-4 py-3 text-sm text-destructive">{t('common.error')}</p>}
      {!items && !error && <Loader2 className="mx-auto mt-8 h-6 w-6 animate-spin text-muted-foreground" />}
      {items?.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 p-10 text-center text-muted-foreground">
            <CheckCircle2 className="h-8 w-8 text-emerald-500" />
            <p>{status === 'open' ? t('errors.emptyOpen') : t('errors.emptyResolved')}</p>
          </CardContent>
        </Card>
      )}
      {items && items.length > 0 && (
        <div className="space-y-2">
          {items.map((g) => (
            <GroupCard key={g.id} group={g} open={openId === g.id}
              onToggle={() => setOpenId((id) => (id === g.id ? null : g.id))} onResolved={resolved} />
          ))}
        </div>
      )}
    </div>
  )
}

function GroupCard({ group, open, onToggle, onResolved }: {
  group: ErrorGroup
  open: boolean
  onToggle: () => void
  onResolved: (g: ErrorGroupDetail) => void
}) {
  const { t } = useTranslation()
  const Icon = SOURCE_ICON[group.source]
  return (
    <Card className="animate-rise overflow-hidden">
      <button type="button" onClick={onToggle} aria-expanded={open}
        className="flex w-full items-start gap-3 p-4 text-left transition-colors hover:bg-muted/40">
        <span className={cn('mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl',
          group.status === 'open' ? 'bg-destructive/12 text-destructive' : 'bg-muted text-muted-foreground')}>
          <Icon className="h-4 w-4" />
        </span>
        <span className="min-w-0 flex-1 space-y-1">
          <span className="block break-words font-mono text-sm font-semibold">{group.title}</span>
          <span className="block truncate text-xs text-muted-foreground">
            {t(`errors.sources.${group.source}`)} · {group.location}
          </span>
          <span className="block text-xs text-muted-foreground">
            {t('errors.lastSeen', { date: formatDateTime(group.last_seen) })}
          </span>
        </span>
        <span className="shrink-0 rounded-full bg-primary/12 px-2 py-0.5 text-xs font-bold tabular-nums text-primary"
          title={t('errors.countTitle')}>
          ×{group.count}
        </span>
        <ChevronDown className={cn('mt-1 h-4 w-4 shrink-0 text-muted-foreground transition-transform', open && 'rotate-180')} />
      </button>
      {open && <GroupDetail id={group.id} onResolved={onResolved} />}
    </Card>
  )
}

function GroupDetail({ id, onResolved }: { id: string; onResolved: (g: ErrorGroupDetail) => void }) {
  const { t } = useTranslation()
  const [detail, setDetail] = useState<ErrorGroupDetail | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(false)

  useEffect(() => {
    api<ErrorGroupDetail>(`/admin/errors/${id}`).then(setDetail).catch(() => setError(true))
  }, [id])

  const resolve = async () => {
    setBusy(true)
    try {
      onResolved(await api<ErrorGroupDetail>(`/admin/errors/${id}/resolve`, { method: 'POST' }))
    } catch {
      setError(true)
      setBusy(false)
    }
  }

  if (!detail) {
    return error
      ? <p className="border-t border-border/60 px-4 py-3 text-sm text-destructive">{t('common.error')}</p>
      : <Loader2 className="mx-auto my-4 h-5 w-5 animate-spin text-muted-foreground" />
  }
  return (
    <div className="space-y-3 border-t border-border/60 p-4">
      <dl className="grid gap-x-6 gap-y-1 text-xs sm:grid-cols-2">
        <Row label={t('errors.firstSeen')} value={formatDateTime(detail.first_seen)} />
        <Row label={t('errors.lastSeenLabel')} value={formatDateTime(detail.last_seen)} />
        {detail.last_request_id && <Row label={t('errors.requestId')} value={detail.last_request_id} mono copy />}
        {detail.resolved_at && (
          <Row label={t('errors.resolvedBy')}
            value={`${detail.resolved_by_name ?? '—'} · ${formatDateTime(detail.resolved_at)}`} />
        )}
      </dl>
      <pre className="max-h-96 overflow-auto rounded-xl bg-muted/60 p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap break-words">
        {detail.detail}
      </pre>
      {error && <p className="text-sm text-destructive">{t('common.error')}</p>}
      {detail.status === 'open' && (
        <Button size="sm" onClick={resolve} disabled={busy}>
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
          {t('errors.resolve')}
        </Button>
      )}
    </div>
  )
}

function Row({ label, value, mono = false, copy = false }: { label: string; value: string; mono?: boolean; copy?: boolean }) {
  const { t } = useTranslation()
  return (
    <div className="flex min-w-0 items-center gap-2">
      <dt className="shrink-0 text-muted-foreground">{label}:</dt>
      <dd className={cn('min-w-0 truncate', mono && 'font-mono')}>{value}</dd>
      {copy && (
        <button type="button" aria-label={t('errors.copy')} title={t('errors.copy')}
          onClick={() => navigator.clipboard?.writeText(value).catch(() => {})}
          className="shrink-0 text-muted-foreground hover:text-foreground">
          <Copy className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  )
}
