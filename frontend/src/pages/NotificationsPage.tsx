// /notifications (CONTRACT.md §15.5, §22.4): to'liq ro'yxat, push va email sozlamalari.
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Bell, BellOff, BellRing, CheckCheck, Download, Loader2, Mail, Smartphone, type LucideIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { describe, ago } from '@/components/notifications/describe'
import { NOTIFICATIONS_CHANGED, markRead } from '@/components/notifications/NotificationBell'
import { api } from '@/lib/api'
import { disablePush, enablePush, pushState, useInstallPrompt, type PushState } from '@/lib/pwa'
import { formatDateTime } from '@/lib/time'
import type { AppNotification, NotificationKind, NotificationPage, NotificationSettings } from '@/lib/types'
import { cn } from '@/lib/utils'

const PAGE = 20

export default function NotificationsPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [items, setItems] = useState<AppNotification[] | null>(null)
  const [unread, setUnread] = useState(0)
  const [more, setMore] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const fetchPage = async (before?: string) => {
    setLoading(true)
    try {
      const q = new URLSearchParams({ limit: String(PAGE), ...(before ? { before } : {}) })
      const r = await api<NotificationPage>(`/users/me/notifications?${q}`)
      setItems((list) => (before ? [...(list ?? []), ...r.items] : r.items))
      setUnread(r.unread)
      setMore(r.items.length === PAGE)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { fetchPage() }, [])
  // qo'ng'iroqchada o'qilganda ro'yxat ham yangilansin
  useEffect(() => {
    const changed = (e: Event) => setUnread((e as CustomEvent<number>).detail)
    window.addEventListener(NOTIFICATIONS_CHANGED, changed)
    return () => window.removeEventListener(NOTIFICATIONS_CHANGED, changed)
  }, [])

  const readAll = async () => {
    await markRead({ all: true })
    const now = new Date().toISOString()
    setItems((list) => list?.map((n) => ({ ...n, read_at: n.read_at ?? now })) ?? null)
  }

  const open = async (n: AppNotification) => {
    if (!n.read_at) await markRead({ ids: [n.id] }).catch(() => {})
    navigate(n.link)
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-8">
      <div className="flex flex-wrap items-end justify-between gap-4 animate-rise">
        <div className="space-y-2">
          <h1 className="text-4xl font-extrabold tracking-tight">{t('notifications.title')}</h1>
          <p className="text-muted-foreground">{unread ? t('notifications.unreadCount', { count: unread }) : t('notifications.allRead')}</p>
        </div>
        {unread > 0 && (
          <Button variant="outline" onClick={readAll}><CheckCheck className="h-4 w-4" /> {t('notifications.readAll')}</Button>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <section className="min-w-0 space-y-2">
          {error && <p className="rounded-2xl bg-destructive/10 px-4 py-2.5 text-sm font-medium text-destructive">{error}</p>}
          {items === null && !error && <div className="grid place-items-center py-16"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>}
          {items?.length === 0 && (
            <div className="glass grid place-items-center gap-3 rounded-3xl py-16 text-center text-muted-foreground">
              <Bell className="h-8 w-8" />
              <p className="max-w-sm">{t('notifications.emptyLong')}</p>
            </div>
          )}
          <ul className="space-y-2">
            {items?.map((n) => {
              const d = describe(n, t)
              return (
                <li key={n.id}>
                  <button type="button" onClick={() => open(n)}
                    className={cn('glass flex w-full items-start gap-3 rounded-2xl p-4 text-left transition-colors hover:bg-accent/40',
                      !n.read_at && 'ring-1 ring-primary/30')}>
                    <span className={cn('grid h-10 w-10 shrink-0 place-items-center rounded-2xl',
                      d.urgent ? 'bg-destructive/12 text-destructive' : 'bg-primary/12 text-primary')}>
                      <d.Icon className="h-5 w-5" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className={cn('block', !n.read_at && 'font-semibold')}>{d.title}</span>
                      {d.body && <span className="block break-words text-sm text-muted-foreground">{d.body}</span>}
                      <span className="block text-xs text-muted-foreground" title={formatDateTime(n.created_at)}>{ago(n.created_at, t)}</span>
                    </span>
                    {!n.read_at && <span aria-label={t('notifications.unreadMark')} className="mt-2 h-2.5 w-2.5 shrink-0 rounded-full bg-primary" />}
                  </button>
                </li>
              )
            })}
          </ul>
          {more && (
            <div className="flex justify-center pt-2">
              <Button variant="ghost" disabled={loading} onClick={() => items && fetchPage(items[items.length - 1].created_at)}>
                {loading && <Loader2 className="h-4 w-4 animate-spin" />} {t('notifications.more')}
              </Button>
            </div>
          )}
        </section>
        <Settings />
      </div>
    </div>
  )
}

/** Sozlamalar ustuni: push (§22.2) va email (§15.4) — bitta `notification-settings` holati. */
function Settings() {
  const { t } = useTranslation()
  const [s, setS] = useState<NotificationSettings | null>(null)
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState<'saved' | 'error' | null>(null)

  useEffect(() => {
    api<NotificationSettings>('/users/me/notification-settings').then(setS).catch(() => setStatus('error'))
  }, [])

  // har o'zgarish darhol saqlanadi — alohida "Saqlash" tugmasi yo'q
  const save = async (next: NotificationSettings) => {
    const prev = s
    setS(next)
    setSaving(true)
    setStatus(null)
    try {
      setS(await api<NotificationSettings>('/users/me/notification-settings', {
        method: 'PUT',
        json: { email_enabled: next.email_enabled, email_kinds: next.email_kinds, push_enabled: next.push_enabled },
      }))
      setStatus('saved')
    } catch {
      setS(prev)
      setStatus('error')
    } finally {
      setSaving(false)
    }
  }

  if (!s) return <aside className="glass h-fit rounded-3xl p-5">{status === 'error' ? t('notifications.settingsError') : <Loader2 className="h-5 w-5 animate-spin text-primary" />}</aside>

  return (
    <aside className="h-fit space-y-4 lg:sticky lg:top-24">
      <PushSettings settings={s} saving={saving} onSave={save} />
      {s.available.length > 0 && <EmailSettings settings={s} saving={saving} onSave={save} />}
      <p className={cn('h-4 px-2 text-xs', status === 'error' ? 'text-destructive' : 'text-success')} role="status">
        {status === 'saved' && t('notifications.email.saved')}
        {status === 'error' && t('notifications.settingsError')}
      </p>
    </aside>
  )
}

interface SettingsProps {
  settings: NotificationSettings
  saving: boolean
  onSave: (next: NotificationSettings) => Promise<void>
}

function CardHead({ Icon, title, hint }: { Icon: LucideIcon; title: string; hint: string }) {
  return (
    <div className="flex items-start gap-3">
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-2xl bg-primary/12 text-primary"><Icon className="h-5 w-5" /></span>
      <div className="min-w-0 flex-1">
        <p className="font-bold">{title}</p>
        <p className="text-xs text-muted-foreground">{hint}</p>
      </div>
    </div>
  )
}

/**
 * Push: hisob kaliti (`push_enabled`, hamma qurilmalar) va shu qurilma obunasi.
 * Server push'siz sozlangan bo'lsa (VAPID yo'q) — karta ko'rsatilmaydi.
 */
function PushSettings({ settings: s, saving, onSave }: SettingsProps) {
  const { t } = useTranslation()
  const install = useInstallPrompt()
  const [state, setState] = useState<PushState | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(false)

  useEffect(() => {
    pushState().then(setState).catch(() => setState('unsupported'))
  }, [])

  const toggleDevice = async (on: boolean) => {
    setBusy(true)
    setError(false)
    try {
      setState(await (on ? enablePush() : disablePush()))
      if (on && !s.push_enabled) await onSave({ ...s, push_enabled: true })
    } catch (err) {
      console.warn('push', err)
      setError(true)
    } finally {
      setBusy(false)
    }
  }

  if (state === 'server-off') return null
  const ready = state === 'on' || state === 'off'

  return (
    <section className="glass space-y-4 rounded-3xl p-5">
      <CardHead Icon={Smartphone} title={t('pwa.push.title')} hint={t('pwa.push.hint')} />
      {state === null && <Loader2 className="h-5 w-5 animate-spin text-primary" />}
      {ready && (
        <>
          <label className="flex items-center justify-between gap-3 rounded-2xl border bg-background/40 px-3 py-2.5 text-sm font-semibold">
            {t('pwa.push.account')}
            <Switch checked={s.push_enabled} disabled={saving} onCheckedChange={(v) => onSave({ ...s, push_enabled: v })} />
          </label>
          <div className={cn('flex items-center justify-between gap-3 rounded-2xl px-3 py-1 text-sm', !s.push_enabled && 'opacity-50')}>
            <span className="flex items-center gap-2">
              {state === 'on' ? <BellRing className="h-4 w-4 text-primary" /> : <BellOff className="h-4 w-4 text-muted-foreground" />}
              {t(state === 'on' ? 'pwa.push.deviceOn' : 'pwa.push.deviceOff')}
            </span>
            <Button size="sm" variant={state === 'on' ? 'ghost' : 'default'} disabled={busy || !s.push_enabled}
              onClick={() => toggleDevice(state !== 'on')}>
              {busy && <Loader2 className="h-4 w-4 animate-spin" />}
              {t(state === 'on' ? 'pwa.push.disconnect' : 'pwa.push.connect')}
            </Button>
          </div>
        </>
      )}
      {state && !ready && (
        <p className="rounded-2xl bg-muted/60 px-3 py-2.5 text-sm text-muted-foreground">{t(`pwa.push.${state}`)}</p>
      )}
      {error && <p className="text-xs text-destructive">{t('pwa.push.error')}</p>}
      {install && (
        <Button variant="outline" size="sm" className="w-full" onClick={install}>
          <Download className="h-4 w-4" /> {t('pwa.install')}
        </Button>
      )}
    </section>
  )
}

function EmailSettings({ settings: s, saving, onSave }: SettingsProps) {
  const { t } = useTranslation()
  const toggleKind = (k: NotificationKind, on: boolean) =>
    onSave({ ...s, email_kinds: on ? [...s.email_kinds, k] : s.email_kinds.filter((x) => x !== k) })

  return (
    <section className="glass space-y-4 rounded-3xl p-5">
      <CardHead Icon={Mail} title={t('notifications.email.title')} hint={t('notifications.email.hint')} />
      <label className="flex items-center justify-between gap-3 rounded-2xl border bg-background/40 px-3 py-2.5 text-sm font-semibold">
        {t('notifications.email.enabled')}
        <Switch checked={s.email_enabled} disabled={saving} onCheckedChange={(v) => onSave({ ...s, email_enabled: v })} />
      </label>
      <fieldset disabled={!s.email_enabled || saving} className={cn('space-y-1', !s.email_enabled && 'opacity-50')}>
        <legend className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{t('notifications.email.kinds')}</legend>
        {s.available.map((k) => (
          <label key={k} className="flex cursor-pointer items-center gap-2.5 rounded-xl px-2 py-1.5 text-sm hover:bg-accent/50">
            <input type="checkbox" className="h-4 w-4 accent-[hsl(var(--primary))]" checked={s.email_kinds.includes(k)}
              onChange={(e) => toggleKind(k, e.target.checked)} />
            {t(`notifications.setting.${k}`)}
          </label>
        ))}
      </fieldset>
    </section>
  )
}
