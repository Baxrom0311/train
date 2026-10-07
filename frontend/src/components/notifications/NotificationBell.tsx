// Navbar qo'ng'iroqchasi (CONTRACT.md §15.5): o'qilmaganlar soni, oxirgi 10 ta, "hammasini o'qildi".
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { Bell, CheckCheck, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { api } from '@/lib/api'
import type { AppNotification, NotificationPage } from '@/lib/types'
import { cn } from '@/lib/utils'
import { ago, describe } from './describe'

const POLL_MS = 60_000
/** Boshqa joyda (masalan, /notifications) o'qilganda qo'ng'iroqcha sonini yangilash uchun. */
export const NOTIFICATIONS_CHANGED = 'tj:notifications-changed'

export async function markRead(body: { ids: string[] } | { all: true }): Promise<number> {
  const r = await api<{ unread: number }>('/users/me/notifications/read', { method: 'POST', json: body })
  window.dispatchEvent(new CustomEvent(NOTIFICATIONS_CHANGED, { detail: r.unread }))
  return r.unread
}

export default function NotificationBell() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [unread, setUnread] = useState(0)
  const [items, setItems] = useState<AppNotification[] | null>(null)

  const refresh = useCallback(() => {
    api<{ unread: number }>('/users/me/notifications/unread').then((r) => setUnread(r.unread)).catch(() => {})
  }, [])

  useEffect(() => {
    refresh()
    const id = setInterval(() => document.visibilityState === 'visible' && refresh(), POLL_MS)
    const changed = (e: Event) => setUnread((e as CustomEvent<number>).detail)
    window.addEventListener('focus', refresh)
    window.addEventListener(NOTIFICATIONS_CHANGED, changed)
    return () => {
      clearInterval(id)
      window.removeEventListener('focus', refresh)
      window.removeEventListener(NOTIFICATIONS_CHANGED, changed)
    }
  }, [refresh])

  const load = () => {
    setItems(null)
    api<NotificationPage>('/users/me/notifications?limit=10')
      .then((r) => { setItems(r.items); setUnread(r.unread) })
      .catch(() => setItems([]))
  }

  const open = async (n: AppNotification) => {
    if (!n.read_at) setUnread(await markRead({ ids: [n.id] }).catch(() => unread))
    navigate(n.link)
  }

  const label = unread ? t('notifications.bellUnread', { count: unread }) : t('notifications.title')
  return (
    <DropdownMenu onOpenChange={(o) => o && load()}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label={label} title={label} className="relative">
          <Bell className="h-4 w-4" />
          {unread > 0 && (
            <span className="bg-brand absolute -right-0.5 -top-0.5 grid h-4 min-w-4 place-items-center rounded-full px-1 text-[10px] font-bold leading-none text-primary-foreground">
              {unread > 99 ? '99+' : unread}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-[min(24rem,calc(100vw-1.5rem))] p-0">
        <div className="flex items-center justify-between gap-2 border-b px-4 py-3">
          <p className="font-bold">{t('notifications.title')}</p>
          {unread > 0 && (
            <button type="button" onClick={async () => { setUnread(await markRead({ all: true })); load() }}
              className="flex items-center gap-1 text-xs font-semibold text-primary hover:underline">
              <CheckCheck className="h-3.5 w-3.5" /> {t('notifications.readAll')}
            </button>
          )}
        </div>
        <div className="max-h-[60vh] overflow-y-auto p-1.5">
          {items === null && <div className="grid place-items-center py-8"><Loader2 className="h-5 w-5 animate-spin text-primary" /></div>}
          {items?.length === 0 && <p className="px-3 py-8 text-center text-sm text-muted-foreground">{t('notifications.empty')}</p>}
          {items?.map((n) => {
            const d = describe(n, t)
            return (
              <DropdownMenuItem key={n.id} onSelect={() => open(n)} className="items-start gap-3 rounded-xl px-2.5 py-2.5">
                <span className={cn('mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-xl',
                  d.urgent ? 'bg-destructive/12 text-destructive' : 'bg-primary/12 text-primary')}>
                  <d.Icon className="h-4 w-4" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className={cn('block text-sm', !n.read_at && 'font-semibold')}>{d.title}</span>
                  {d.body && <span className="block truncate text-xs text-muted-foreground">{d.body}</span>}
                  <span className="block text-[11px] text-muted-foreground">{ago(n.created_at, t)}</span>
                </span>
                {!n.read_at && <span aria-label={t('notifications.unreadMark')} className="mt-2 h-2 w-2 shrink-0 rounded-full bg-primary" />}
              </DropdownMenuItem>
            )
          })}
        </div>
        <DropdownMenuItem asChild className="justify-center rounded-none border-t px-4 py-2.5 text-sm font-semibold text-primary">
          <Link to="/notifications">{t('notifications.all')}</Link>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
