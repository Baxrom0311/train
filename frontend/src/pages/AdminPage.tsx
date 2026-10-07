import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Building2, CheckCircle2, Hourglass, Loader2, Plus, Receipt, School, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import InvoiceList from '@/components/billing/InvoiceList'
import { Stat } from '@/components/ui/stat'
import { useAuth } from '@/context/AuthContext'
import { api, ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'
import { formatDateTime } from '@/lib/time'
import type { AdminStats, Invoice, InvoiceStatus, Org, OrgList } from '@/lib/types'

type Tab = 'pending' | 'verified' | 'invoices'
const SELECT = 'h-10 rounded-xl border border-input bg-background/60 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring'

const flatten = (list: OrgList) => [...list.companies, ...list.universities]

export default function AdminPage() {
  const { t } = useTranslation()
  const { can } = useAuth()
  const canOrgs = can('approve_companies')
  const canBilling = can('manage_billing')
  const [tab, setTab] = useState<Tab>(canOrgs ? 'pending' : 'invoices')
  const [stats, setStats] = useState<AdminStats | null>(null)

  const loadStats = useCallback(() => {
    api<AdminStats>('/admin/stats').then(setStats).catch(() => {})
  }, [])
  useEffect(loadStats, [loadStats])

  const tabs: { key: Tab; label: string; count?: number; show: boolean }[] = [
    { key: 'pending', label: t('admin.tabs.pending'), count: stats ? stats.pending_companies + stats.pending_universities : undefined, show: canOrgs },
    { key: 'verified', label: t('admin.tabs.verified'), show: canOrgs },
    { key: 'invoices', label: t('admin.tabs.invoices'), count: stats?.invoices_pending, show: canBilling },
  ]

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-8">
      <div className="space-y-2 animate-rise">
        <h1 className="text-4xl font-extrabold tracking-tight">{t('admin.title')}</h1>
        <p className="text-muted-foreground">{t('admin.subtitle')}</p>
      </div>

      {stats && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 animate-rise">
          <Stat Icon={Hourglass} label={t('admin.stats.pending')} value={stats.pending_companies + stats.pending_universities} accent />
          <Stat Icon={Building2} label={t('admin.stats.companies')} value={stats.verified_companies} />
          <Stat Icon={School} label={t('admin.stats.universities')} value={stats.verified_universities} />
          <Stat Icon={Receipt} label={t('admin.stats.invoicesPending')} value={stats.invoices_pending} />
        </div>
      )}

      <nav className="glass flex w-fit gap-1 rounded-2xl p-1">
        {tabs.filter((x) => x.show).map((x) => (
          <button key={x.key} type="button" onClick={() => setTab(x.key)}
            className={cn('flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition-colors',
              tab === x.key ? 'bg-brand text-primary-foreground shadow' : 'text-muted-foreground hover:text-foreground')}>
            {x.label}
            {!!x.count && <span className={cn('rounded-full px-1.5 text-xs', tab === x.key ? 'bg-black/15' : 'bg-primary/15 text-primary')}>{x.count}</span>}
          </button>
        ))}
      </nav>

      {tab === 'pending' && <Applications onChange={loadStats} />}
      {tab === 'verified' && <VerifiedOrgs />}
      {tab === 'invoices' && <Invoices onChange={loadStats} />}
    </div>
  )
}

function OrgIcon({ org }: { org: Org }) {
  const Icon = org.org_type === 'company' ? Building2 : School
  return (
    <span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-primary/12 text-primary">
      <Icon className="h-5 w-5" />
    </span>
  )
}

function Applications({ onChange }: { onChange: () => void }) {
  const { t } = useTranslation()
  const [orgs, setOrgs] = useState<Org[] | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api<OrgList>('/admin/orgs?status=pending').then((l) => setOrgs(flatten(l))).catch(() => setError(t('common.error')))
  }, [t])

  const act = async (org: Org, action: 'approve' | 'reject') => {
    if (action === 'reject' && !window.confirm(t('admin.rejectConfirm', { name: org.name }))) return
    setBusy(org.id)
    setError(null)
    try {
      await api(`/admin/orgs/${org.id}/${action}`, { method: 'POST', json: { org_type: org.org_type } })
      setOrgs((list) => list?.filter((o) => o.id !== org.id) ?? null)
      onChange()
    } catch (err) {
      setError(err instanceof ApiError && err.status === 409 ? t('admin.rejectConflict') : t('common.error'))
    } finally {
      setBusy(null)
    }
  }

  if (!orgs) return error ? <p className="text-sm text-destructive">{error}</p> : <Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />
  if (orgs.length === 0) return <Empty Icon={CheckCircle2} text={t('admin.noPending')} />

  return (
    <div className="space-y-3">
      {error && <p className="glass rounded-2xl px-4 py-3 text-sm text-destructive">{error}</p>}
      {orgs.map((org) => (
        <Card key={org.id} className="animate-rise">
          <CardContent className="flex flex-wrap items-center gap-4 p-5">
            <OrgIcon org={org} />
            <div className="min-w-0 flex-1">
              <p className="font-bold">{org.name}</p>
              <p className="text-sm text-muted-foreground">
                {t(`admin.orgType.${org.org_type}`)} · {org.detail} · {formatDateTime(org.created_at)}
              </p>
              {org.owner_email && (
                <p className="mt-1 text-sm">{org.owner_name} · <a className="text-primary hover:underline" href={`mailto:${org.owner_email}`}>{org.owner_email}</a></p>
              )}
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={() => act(org, 'approve')} disabled={busy === org.id}>
                {busy === org.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                {t('admin.approve')}
              </Button>
              <Button size="sm" variant="ghost" onClick={() => act(org, 'reject')} disabled={busy === org.id}>
                <X className="h-4 w-4" /> {t('admin.reject')}
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function VerifiedOrgs() {
  const { t } = useTranslation()
  const [orgs, setOrgs] = useState<Org[] | null>(null)
  useEffect(() => {
    api<OrgList>('/admin/orgs?status=verified').then((l) => setOrgs(flatten(l))).catch(() => setOrgs([]))
  }, [])
  if (!orgs) return <Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />
  if (orgs.length === 0) return <Empty Icon={Building2} text={t('admin.noVerified')} />
  return (
    <Card>
      <CardContent className="divide-y divide-border/60 p-4">
        {orgs.map((org) => (
          <div key={org.id} className="flex items-center gap-3 py-3">
            <OrgIcon org={org} />
            <div className="min-w-0 flex-1">
              <p className="truncate font-semibold">{org.name}</p>
              <p className="truncate text-xs text-muted-foreground">{t(`admin.orgType.${org.org_type}`)} · {org.detail} · {org.owner_email ?? org.contact_email}</p>
            </div>
            {org.verified_at && <span className="text-xs text-muted-foreground">{t('admin.verifiedAt', { date: formatDateTime(org.verified_at) })}</span>}
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

function Invoices({ onChange }: { onChange: () => void }) {
  const { t } = useTranslation()
  const [invoices, setInvoices] = useState<Invoice[] | null>(null)
  const [status, setStatus] = useState<InvoiceStatus | ''>('')
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    api<Invoice[]>(`/admin/invoices${status ? `?status=${status}` : ''}`).then(setInvoices).catch(() => setError(t('common.error')))
  }, [status, t])
  useEffect(load, [load])

  const act = async (inv: Invoice, action: 'mark-paid' | 'cancel') => {
    if (action === 'cancel' && !window.confirm(t('admin.cancelConfirm'))) return
    try {
      const updated = await api<Invoice>(`/admin/invoices/${inv.id}/${action}`, { method: 'POST' })
      setInvoices((list) => list?.map((i) => (i.id === updated.id ? updated : i)) ?? null)
      onChange()
    } catch {
      setError(t('common.error'))
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <select aria-label={t('admin.filterStatus')} className={SELECT} value={status} onChange={(e) => setStatus(e.target.value as InvoiceStatus | '')}>
          <option value="">{t('admin.allStatuses')}</option>
          {(['pending', 'paid', 'cancelled'] as const).map((s) => <option key={s} value={s}>{t(`billing.status.${s}`)}</option>)}
        </select>
        <Button onClick={() => setCreating(true)}><Plus className="h-4 w-4" /> {t('admin.newInvoice')}</Button>
      </div>
      {error && <p className="glass rounded-2xl px-4 py-3 text-sm text-destructive">{error}</p>}
      {invoices?.length === 0 && <Empty Icon={Receipt} text={t('billing.none')} />}
      {invoices && invoices.length > 0 && (
        <Card>
          <CardContent className="p-4">
            <InvoiceList invoices={invoices} actions={(inv) => inv.status === 'pending' && (
              <>
                <Button size="sm" variant="outline" onClick={() => act(inv, 'mark-paid')}>{t('admin.markPaid')}</Button>
                <Button size="sm" variant="ghost" onClick={() => act(inv, 'cancel')}>{t('admin.cancel')}</Button>
              </>
            )} />
          </CardContent>
        </Card>
      )}
      <NewInvoice open={creating} onClose={() => setCreating(false)} onCreated={() => { setCreating(false); load(); onChange() }} />
    </div>
  )
}

function NewInvoice({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: () => void }) {
  const { t } = useTranslation()
  const [orgs, setOrgs] = useState<Org[]>([])
  const [form, setForm] = useState({ payer: '', amount: '', currency: 'UZS', notes: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open) api<OrgList>('/admin/orgs?status=verified').then((l) => setOrgs(flatten(l))).catch(() => setOrgs([]))
  }, [open])

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const payer = orgs.find((o) => o.id === form.payer)
    if (!payer) return
    setBusy(true)
    setError(null)
    try {
      await api('/admin/invoices', {
        method: 'POST',
        json: { payer_type: payer.org_type, payer_id: payer.id, amount: form.amount, currency: form.currency, notes: form.notes || null },
      })
      setForm({ payer: '', amount: '', currency: 'UZS', notes: '' })
      onCreated()
    } catch {
      setError(t('common.error'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent closeLabel={t('common.close')} aria-describedby={undefined} className="max-w-lg">
        <form onSubmit={submit} className="space-y-4 overflow-y-auto p-6">
          <DialogTitle className="text-xl font-extrabold">{t('admin.newInvoice')}</DialogTitle>
          <div className="space-y-2">
            <Label htmlFor="payer">{t('admin.payer')}</Label>
            <select id="payer" required className={`${SELECT} w-full`} value={form.payer} onChange={(e) => setForm({ ...form, payer: e.target.value })}>
              <option value="" disabled>{t('admin.choosePayer')}</option>
              {orgs.map((o) => <option key={o.id} value={o.id}>{o.name} ({t(`admin.orgType.${o.org_type}`)})</option>)}
            </select>
            {orgs.length === 0 && <p className="text-xs text-muted-foreground">{t('admin.noVerified')}</p>}
          </div>
          <div className="grid grid-cols-[1fr_110px] gap-3">
            <div className="space-y-2">
              <Label htmlFor="amount">{t('admin.amount')}</Label>
              <Input id="amount" required inputMode="decimal" pattern="\d+(\.\d{1,2})?" value={form.amount}
                onChange={(e) => setForm({ ...form, amount: e.target.value })} placeholder="2500000" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="currency">{t('admin.currency')}</Label>
              <select id="currency" className={`${SELECT} w-full`} value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })}>
                <option>UZS</option><option>USD</option>
              </select>
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="notes">{t('admin.notes')}</Label>
            <Textarea id="notes" rows={2} maxLength={1000} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })}
              placeholder={t('admin.notesPlaceholder')} />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" className="w-full" disabled={busy || !form.payer}>
            {busy && <Loader2 className="h-4 w-4 animate-spin" />} {t('admin.issue')}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function Empty({ Icon, text }: { Icon: typeof Building2; text: string }) {
  return (
    <div className="glass flex flex-col items-center gap-2 rounded-2xl px-6 py-14 text-center text-sm text-muted-foreground">
      <Icon className="h-8 w-8" /> {text}
    </div>
  )
}
