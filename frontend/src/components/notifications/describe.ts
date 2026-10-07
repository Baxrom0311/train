// Bildirishnoma matni: backend matn saqlamaydi — `kind` + `params`dan interfeys tilida (CONTRACT.md §15.1).
import type { TFunction } from 'i18next'
import {
  AlarmClock, Award, ClipboardList, GitBranch, GraduationCap, Handshake, Siren, UserCheck, UserX, type LucideIcon,
} from 'lucide-react'
import { formatTime } from '@/lib/time'
import type { AppNotification } from '@/lib/types'

export interface Described {
  Icon: LucideIcon
  title: string
  body: string
  /** diqqat talab qiladigan (dedlayn, incident) — qizil belgi */
  urgent: boolean
}

const TASK_ICON: Record<string, LucideIcon> = { task: ClipboardList, incident: Siren, decision: GitBranch }

export function describe(n: AppNotification, t: TFunction): Described {
  const p = n.params
  const str = (k: string) => (p[k] == null ? '' : String(p[k]))
  const due = p.due_at ? t('notifications.due', { time: formatTime(str('due_at')) }) : ''
  switch (n.kind) {
    case 'task_delivered': {
      const type = str('type') || 'task'
      return { Icon: TASK_ICON[type] ?? ClipboardList, title: t(`notifications.kind.task_delivered.${type}`), body: [str('title'), due].filter(Boolean).join(' · '), urgent: type === 'incident' }
    }
    case 'deadline_soon':
      return { Icon: AlarmClock, title: t('notifications.kind.deadline_soon'), body: [str('title'), due].filter(Boolean).join(' · '), urgent: true }
    case 'mentor_review':
      return { Icon: GraduationCap, title: t('notifications.kind.mentor_review', { mentor: str('mentor') }), body: str('title'), urgent: false }
    case 'report_ready':
      return {
        Icon: Award, title: t('notifications.kind.report_ready'), urgent: false,
        body: [str('scenario_title'), p.code ? t('notifications.certificate', { code: str('code') }) : ''].filter(Boolean).join(' · '),
      }
    case 'offer_received':
      return { Icon: Handshake, title: t('notifications.kind.offer_received'), body: `${str('company')} — ${str('position')}`, urgent: false }
    case 'offer_responded':
      return {
        Icon: p.accepted ? UserCheck : UserX, urgent: false,
        title: t(p.accepted ? 'notifications.kind.offer_accepted' : 'notifications.kind.offer_declined'),
        body: `${str('candidate')} — ${str('position')}`,
      }
  }
}

/**
 * "5 daqiqa oldin" — tarjima kalitlari bilan: brauzerlarda `uz` uchun
 * `Intl.RelativeTimeFormat` ma'lumoti yo'q ("-6 min", "yesterday" chiqadi).
 */
export function ago(iso: string, t: TFunction, now = Date.now()): string {
  const minutes = Math.max(0, Math.floor((now - new Date(iso).getTime()) / 60_000))
  if (minutes < 1) return t('notifications.ago.now')
  if (minutes < 60) return t('notifications.ago.minutes', { count: minutes })
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return t('notifications.ago.hours', { count: hours })
  return t('notifications.ago.days', { count: Math.floor(hours / 24) })
}
