// Bildirishnoma matni: backend matn saqlamaydi — `kind` + `params`dan interfeys tilida (CONTRACT.md §15.1).
import type { TFunction } from 'i18next'
import {
  AlarmClock, Award, BriefcaseBusiness, CalendarCheck2, CalendarClock, CalendarPlus, CalendarX2, ClipboardList, FileX2, FlaskConical,
  GitBranch, GraduationCap, Handshake, Siren, UserCheck, UserX,
  type LucideIcon,
} from 'lucide-react'
import { formatDateTime, formatTime } from '@/lib/time'
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
    case 'application_received':
      return { Icon: BriefcaseBusiness, title: t('notifications.kind.application_received'), body: `${str('candidate')} — ${str('vacancy')}`, urgent: false }
    case 'application_rejected':
      return { Icon: FileX2, title: t('notifications.kind.application_rejected'), body: `${str('company')} — ${str('vacancy')}`, urgent: false }
    case 'interview_proposed':
      return { Icon: CalendarPlus, title: t('notifications.kind.interview_proposed'), body: `${str('company')} — ${str('vacancy')}`, urgent: false }
    case 'interview_cancelled':
      return { Icon: CalendarX2, title: t('notifications.kind.interview_cancelled'), body: `${str('company')} — ${str('vacancy')}`, urgent: false }
    case 'interview_confirmed':
      return {
        Icon: CalendarCheck2, title: t('notifications.kind.interview_confirmed'), urgent: false,
        body: [`${str('candidate')} — ${str('vacancy')}`, p.starts_at ? formatDateTime(str('starts_at')) : ''].filter(Boolean).join(' · '),
      }
    case 'interview_declined':
      return {
        Icon: CalendarX2, urgent: false,
        title: t(p.withdrawn ? 'notifications.kind.interview_withdrawn' : 'notifications.kind.interview_declined'),
        body: [`${str('candidate')} — ${str('vacancy')}`, str('reason')].filter(Boolean).join(' · '),
      }
    case 'interview_reminder':
      return {
        Icon: CalendarClock, title: t('notifications.kind.interview_reminder', { time: formatTime(str('starts_at')) }), urgent: true,
        body: `${str('vacancy')} · ${str('place')}`,
      }
    case 'assessment_assigned':
      return {
        Icon: FlaskConical, title: t('notifications.kind.assessment_assigned'), urgent: false,
        body: [`${str('company')} — ${str('scenario')}`, p.start_by ? t('notifications.startBy', { time: formatDateTime(str('start_by')) }) : ''].filter(Boolean).join(' · '),
      }
    case 'assessment_completed':
      return {
        Icon: FlaskConical, urgent: false,
        title: t(p.incomplete ? 'notifications.kind.assessment_incomplete' : 'notifications.kind.assessment_completed'),
        body: [`${str('candidate')} — ${str('scenario')}`, p.score == null ? '' : t('notifications.score', { score: Math.round(Number(p.score)) })].filter(Boolean).join(' · '),
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
