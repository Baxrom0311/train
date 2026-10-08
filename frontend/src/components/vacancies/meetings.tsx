// Suhbat bosqichlari (CONTRACT.md §25.6): kompaniya vaqt taklif qiladi va natijani belgilaydi,
// talaba vaqtni tanlaydi yoki rad etadi. Vaqtlar hamma joyda Toshkent bo'yicha.
import { useState } from 'react'
import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'
import {
  Building2, CalendarCheck2, CalendarPlus, CalendarX2, Check, Clock, Loader2, Plus, Trash2, UserX, Video, X,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Segmented } from '@/components/ui/segmented'
import { Textarea } from '@/components/ui/textarea'
import { api, ApiError } from '@/lib/api'
import { downloadIcs } from '@/lib/ics'
import { formatDate, formatTime, fromTashkentInput, toTashkentInput } from '@/lib/time'
import type {
  HiringInterview, HiringInterviewFormat, HiringInterviewOutcome, HiringInterviewProposal, MyHiringInterview,
} from '@/lib/types'
import { cn } from '@/lib/utils'

const MAX_SLOTS = 3
const DURATIONS = [30, 45, 60, 90]
const HOUR = 60 * 60 * 1000

export const isActive = (m: MyHiringInterview) => m.status === 'proposed' || m.status === 'confirmed'

/** "13-oktabr, 2026 · 13:00" — interfeys tilida, Toshkent vaqti. */
export function useWhen() {
  const { i18n } = useTranslation()
  return (iso: string) => `${formatDate(iso, i18n.language.slice(0, 2))} · ${formatTime(iso)}`
}

/** 409 — holat boshqa oynada o'zgargan, 422 — vaqtlar oynadan tashqarida (§25.1). */
function errorText(err: unknown, t: TFunction): string {
  if (err instanceof ApiError && err.status === 409) return t('meeting.errors.conflict')
  if (err instanceof ApiError && err.status === 422) return t('meeting.errors.invalid')
  return t('common.error')
}

// ── Belgilar ─────────────────────────────────────────────────────────

const TONE = {
  proposed: 'bg-amber-500/15 text-amber-700 dark:text-amber-300',
  confirmed: 'bg-primary/12 text-primary',
  passed: 'bg-success/15 text-success',
  failed: 'bg-destructive/12 text-destructive',
  no_show: 'bg-destructive/12 text-destructive',
  muted: 'bg-muted text-muted-foreground',
}

export function MeetingBadge({ m }: { m: MyHiringInterview }) {
  const { t } = useTranslation()
  const key = m.status === 'completed' && m.outcome ? m.outcome : m.expired ? 'expired' : m.status
  const tone = m.status === 'completed' && m.outcome ? TONE[m.outcome]
    : m.status === 'proposed' && !m.expired ? TONE.proposed
      : m.status === 'confirmed' ? TONE.confirmed : TONE.muted
  return <span className={cn('inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold', tone)}>{t(`meeting.status.${key}`)}</span>
}

export function PlaceLine({ format, place, className }: { format: HiringInterviewFormat; place: string; className?: string }) {
  const { t } = useTranslation()
  const Icon = format === 'online' ? Video : Building2
  const link = /^https?:\/\//i.test(place)
  return (
    <p className={cn('flex min-w-0 items-start gap-1.5 text-sm', className)}>
      <Icon className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
      <span className="min-w-0">
        <span className="text-muted-foreground">{t(`meeting.format.${format}`)}: </span>
        {link
          ? <a href={place} target="_blank" rel="noreferrer noopener" className="break-all font-medium text-primary hover:underline">{place}</a>
          : <span className="break-words font-medium">{place}</span>}
      </span>
    </p>
  )
}

// ── Kompaniya: vaqt taklif qilish ───────────────────────────────────

function defaultSlot(): string {
  // ertangi kun 10:00 (Toshkent)
  return `${toTashkentInput(new Date(Date.now() + 24 * HOUR)).slice(0, 10)}T10:00`
}

export function ScheduleForm({ vacancyId, applicationId, round, onDone }: {
  vacancyId: string
  applicationId: string
  round: number
  onDone: () => void
}) {
  const { t } = useTranslation()
  const [slots, setSlots] = useState<string[]>([defaultSlot()])
  const [duration, setDuration] = useState(45)
  const [format, setFormat] = useState<HiringInterviewFormat>('online')
  const [place, setPlace] = useState('')
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const min = toTashkentInput(new Date(Date.now() + HOUR))

  const filled = slots.filter(Boolean)
  const duplicate = new Set(filled).size !== filled.length
  const valid = filled.length > 0 && !duplicate && filled.every((s) => s >= min) && place.trim().length >= 2

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!valid) return
    setBusy(true)
    setError(null)
    const body: HiringInterviewProposal = {
      slots: filled.map(fromTashkentInput), duration_minutes: duration, format, place: place.trim(), note: note.trim() || null,
    }
    try {
      await api(`/company/vacancies/${vacancyId}/applications/${applicationId}/interviews`, { method: 'POST', json: body })
      onDone()
    } catch (err) {
      setError(errorText(err, t))
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="space-y-2">
        <p className="text-sm font-semibold">{t('meeting.form.slots', { round })}</p>
        {slots.map((value, i) => (
          <div key={i} className="flex items-center gap-2">
            <Input type="datetime-local" required={i === 0} min={min} value={value}
              aria-label={t('meeting.form.slot', { n: i + 1 })}
              aria-invalid={Boolean(value) && value < min}
              onChange={(e) => setSlots(slots.map((s, j) => (j === i ? e.target.value : s)))} />
            {slots.length > 1 && (
              <Button type="button" variant="ghost" size="icon" aria-label={t('common.delete')}
                onClick={() => setSlots(slots.filter((_, j) => j !== i))}>
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        ))}
        <div className="flex flex-wrap items-center justify-between gap-2">
          {slots.length < MAX_SLOTS && (
            <Button type="button" size="sm" variant="outline" onClick={() => setSlots([...slots, ''])}>
              <Plus className="h-4 w-4" /> {t('meeting.form.addSlot')}
            </Button>
          )}
          <p className="text-xs text-muted-foreground">{t('meeting.form.tzHint')}</p>
        </div>
        {duplicate && <p className="text-xs text-destructive">{t('meeting.form.duplicate')}</p>}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <p className="text-sm font-semibold">{t('meeting.form.duration')}</p>
          <Segmented<number> label={t('meeting.form.duration')} value={duration} onChange={setDuration}
            options={DURATIONS.map((d) => ({ value: d, label: t('meeting.minutesShort', { count: d }) }))} />
        </div>
        <div className="space-y-1.5">
          <p className="text-sm font-semibold">{t('meeting.form.format')}</p>
          <Segmented<HiringInterviewFormat> label={t('meeting.form.format')} value={format} onChange={setFormat}
            options={(['online', 'office'] as const).map((f) => ({ value: f, label: t(`meeting.format.${f}`) }))} />
        </div>
      </div>

      <label className="block space-y-1.5">
        <span className="text-sm font-semibold">{t(format === 'online' ? 'meeting.form.link' : 'meeting.form.address')}</span>
        <Input required maxLength={300} value={place} onChange={(e) => setPlace(e.target.value)}
          placeholder={t(format === 'online' ? 'meeting.form.linkPlaceholder' : 'meeting.form.addressPlaceholder')} />
      </label>
      <label className="block space-y-1.5">
        <span className="text-sm font-semibold">{t('meeting.form.note')}</span>
        <Textarea rows={3} maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)}
          placeholder={t('meeting.form.notePlaceholder')} />
      </label>

      {error && <p className="text-sm text-destructive">{error}</p>}
      <Button type="submit" className="w-full" disabled={busy || !valid}>
        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <CalendarPlus className="h-4 w-4" />} {t('meeting.form.send')}
      </Button>
    </form>
  )
}

// ── Kompaniya: ariza ostidagi suhbat holati ─────────────────────────

const OUTCOMES: { value: HiringInterviewOutcome; Icon: typeof Check }[] = [
  { value: 'passed', Icon: Check },
  { value: 'failed', Icon: X },
  { value: 'no_show', Icon: UserX },
]

export function CompanyMeetingPanel({ vacancyId, applicationId, interviews, candidateName, onChange }: {
  vacancyId: string
  applicationId: string
  interviews: HiringInterview[]
  candidateName: string
  onChange: () => void
}) {
  const { t } = useTranslation()
  const when = useWhen()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [outcomeNote, setOutcomeNote] = useState('')
  const latest = interviews[0]
  if (!latest) return null
  const earlier = interviews.slice(1).filter((m) => m.status === 'completed')
  const base = `/company/vacancies/${vacancyId}/applications/${applicationId}/interviews/${latest.id}`
  const started = latest.starts_at !== null && new Date(latest.starts_at).getTime() <= Date.now()

  const post = async (path: string, json?: unknown) => {
    setBusy(true)
    setError(null)
    try {
      await api(`${base}/${path}`, { method: 'POST', ...(json ? { json } : {}) })
      onChange()
    } catch (err) {
      setError(errorText(err, t))
      if (err instanceof ApiError && err.status === 409) onChange()   // eskirgan holatni yangilaymiz
    } finally {
      setBusy(false)
    }
  }

  const cancel = () => {
    if (window.confirm(t('meeting.company.cancelConfirm', { name: candidateName }))) post('cancel')
  }
  const record = (outcome: HiringInterviewOutcome) => {
    if (outcome !== 'passed' && !window.confirm(t('meeting.company.rejectConfirm', { name: candidateName }))) return
    post('outcome', { outcome, note: outcomeNote.trim() || null })
  }

  return (
    <div className="space-y-2.5 rounded-2xl border border-primary/20 bg-primary/5 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <CalendarCheck2 className="h-4 w-4 text-primary" />
        <span className="text-sm font-semibold">{t('meeting.round', { round: latest.round })}</span>
        <MeetingBadge m={latest} />
        <span className="ml-auto text-xs text-muted-foreground">{t('meeting.minutes', { count: latest.duration_minutes })}</span>
      </div>

      {latest.status === 'proposed' && (
        <div className="flex flex-wrap gap-1.5">
          {latest.slots.map((s) => (
            <span key={s} className={cn('rounded-full border px-2.5 py-0.5 text-xs tabular-nums', new Date(s).getTime() <= Date.now() && 'line-through opacity-60')}>{when(s)}</span>
          ))}
        </div>
      )}
      {latest.status === 'proposed' && (
        <p className="text-xs text-muted-foreground">{t(latest.expired ? 'meeting.company.expired' : 'meeting.company.waiting')}</p>
      )}
      {latest.starts_at && latest.status !== 'cancelled' && (
        <p className="flex items-center gap-1.5 text-sm font-semibold"><Clock className="h-4 w-4 text-primary" /> {when(latest.starts_at)}</p>
      )}
      {isActive(latest) && <PlaceLine format={latest.format} place={latest.place} />}
      {latest.status === 'declined' && (
        <p className="text-sm">{t('meeting.company.declined')}{latest.decline_reason && <span className="italic"> “{latest.decline_reason}”</span>}</p>
      )}
      {latest.status === 'cancelled' && <p className="text-sm text-muted-foreground">{t('meeting.company.cancelled')}</p>}
      {latest.outcome_note && <p className="text-sm italic text-muted-foreground">“{latest.outcome_note}”</p>}

      {latest.status === 'confirmed' && started && (
        <div className="space-y-2 border-t border-primary/15 pt-2.5">
          <p className="text-sm font-semibold">{t('meeting.company.outcomeTitle')}</p>
          <Textarea rows={2} maxLength={1000} value={outcomeNote} onChange={(e) => setOutcomeNote(e.target.value)}
            placeholder={t('meeting.company.outcomeNote')} aria-label={t('meeting.company.outcomeNote')} />
          <div className="flex flex-wrap gap-2">
            {OUTCOMES.map(({ value, Icon }) => (
              <Button key={value} size="sm" variant={value === 'passed' ? 'default' : 'outline'} disabled={busy} onClick={() => record(value)}>
                <Icon className="h-4 w-4" /> {t(`meeting.outcome.${value}`)}
              </Button>
            ))}
          </div>
        </div>
      )}
      {isActive(latest) && !(latest.status === 'confirmed' && started) && (
        <Button size="sm" variant="ghost" disabled={busy} onClick={cancel}>
          <CalendarX2 className="h-4 w-4" /> {t('meeting.company.cancel')}
        </Button>
      )}
      {earlier.length > 0 && (
        <p className="text-xs text-muted-foreground">
          {earlier.map((m) => `${t('meeting.round', { round: m.round })}: ${t(`meeting.status.${m.outcome}`)}`).join(' · ')}
        </p>
      )}
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  )
}

// ── Talaba: vakansiya sahifasidagi suhbat kartasi ───────────────────

export function StudentMeetingCard({ vacancyId, vacancyTitle, company, interviews, onChange }: {
  vacancyId: string
  vacancyTitle: string
  company: string
  interviews: MyHiringInterview[]
  onChange: () => void
}) {
  const { t } = useTranslation()
  const when = useWhen()
  const latest = interviews[0]
  const [picked, setPicked] = useState<string | null>(null)
  const [declining, setDeclining] = useState(false)
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  if (!latest) return null

  const now = Date.now()
  const open = latest.slots.filter((s) => new Date(s).getTime() > now)
  const choice = picked ?? (open.length === 1 ? open[0] : null)
  const upcoming = latest.status === 'confirmed' && latest.starts_at !== null && new Date(latest.starts_at).getTime() > now

  const post = async (path: 'confirm' | 'decline', json: unknown) => {
    setBusy(true)
    setError(null)
    try {
      await api(`/vacancies/${vacancyId}/interviews/${latest.id}/${path}`, { method: 'POST', json })
      setDeclining(false)
      onChange()
    } catch (err) {
      setError(errorText(err, t))
      if (err instanceof ApiError && err.status === 409) onChange()   // eskirgan holatni yangilaymiz
    } finally {
      setBusy(false)
    }
  }

  const addToCalendar = () => downloadIcs({
    uid: latest.id,
    start: new Date(latest.starts_at!),
    minutes: latest.duration_minutes,
    title: t('meeting.student.calendarTitle', { vacancy: vacancyTitle, company }),
    description: [latest.note, latest.place].filter(Boolean).join('\n\n'),
    location: latest.place,
    url: /^https?:\/\//i.test(latest.place) ? latest.place : undefined,
  }, `tryjob-interview-${latest.round}.ics`)

  return (
    <section className={cn('space-y-4 rounded-3xl p-5', isActive(latest) && !latest.expired ? 'glass-strong ring-2 ring-primary/30' : 'glass')}>
      <div className="flex items-start gap-3">
        <span className="bg-brand grid h-10 w-10 shrink-0 place-items-center rounded-2xl text-primary-foreground shadow-sm">
          <CalendarCheck2 className="h-5 w-5" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-bold">{t('meeting.student.title', { round: latest.round })}</p>
          <p className="text-xs text-muted-foreground">{t('meeting.minutes', { count: latest.duration_minutes })} · {t(`meeting.format.${latest.format}`)}</p>
        </div>
        <MeetingBadge m={latest} />
      </div>

      {latest.status === 'proposed' && !latest.expired && !declining && (
        <fieldset className="space-y-2">
          <legend className="mb-2 text-sm">{t('meeting.student.pick')}</legend>
          {latest.slots.map((s) => {
            const past = new Date(s).getTime() <= now
            return (
              <label key={s} className={cn(
                'flex cursor-pointer items-center gap-3 rounded-2xl border bg-background/40 px-3 py-2.5 text-sm transition-colors',
                choice === s && 'border-primary bg-primary/10', past && 'cursor-not-allowed opacity-50',
              )}>
                <input type="radio" name={`slot-${latest.id}`} className="h-4 w-4 accent-[hsl(var(--primary))]" disabled={past}
                  checked={choice === s} onChange={() => setPicked(s)} />
                <span className="font-semibold tabular-nums">{when(s)}</span>
              </label>
            )
          })}
          <p className="text-xs text-muted-foreground">{t('meeting.form.tzHint')}</p>
        </fieldset>
      )}
      {latest.status === 'proposed' && latest.expired && <p className="text-sm text-muted-foreground">{t('meeting.student.expired')}</p>}

      {latest.status === 'confirmed' && latest.starts_at && (
        <p className="flex items-center gap-2 text-lg font-extrabold"><Clock className="h-5 w-5 text-primary" /> {when(latest.starts_at)}</p>
      )}
      {isActive(latest) && !latest.expired && <PlaceLine format={latest.format} place={latest.place} />}
      {isActive(latest) && latest.note && <p className="whitespace-pre-line rounded-xl bg-muted/50 px-3 py-2 text-sm">{latest.note}</p>}

      {latest.status === 'declined' && <p className="text-sm text-muted-foreground">{t('meeting.student.declined')}</p>}
      {latest.status === 'cancelled' && <p className="text-sm text-muted-foreground">{t('meeting.student.cancelled')}</p>}
      {latest.status === 'completed' && <p className="text-sm">{t(`meeting.student.outcome.${latest.outcome}`)}</p>}

      {declining ? (
        <div className="space-y-2">
          <Textarea rows={3} maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)}
            placeholder={t('meeting.student.reasonPlaceholder')} aria-label={t('meeting.student.reason')} />
          <div className="flex gap-2">
            <Button variant="destructive" className="flex-1" disabled={busy} onClick={() => post('decline', { reason: reason.trim() || null })}>
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <CalendarX2 className="h-4 w-4" />} {t('meeting.student.declineSend')}
            </Button>
            <Button variant="ghost" disabled={busy} onClick={() => setDeclining(false)}>{t('common.cancel')}</Button>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          {latest.status === 'proposed' && !latest.expired && (
            <Button className="w-full" disabled={busy || !choice} onClick={() => post('confirm', { starts_at: choice })}>
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />} {t('meeting.student.confirm')}
            </Button>
          )}
          {upcoming && (
            <Button className="w-full" variant="outline" onClick={addToCalendar}>
              <CalendarPlus className="h-4 w-4" /> {t('meeting.student.addToCalendar')}
            </Button>
          )}
          {((latest.status === 'proposed' && !latest.expired) || upcoming) && (
            <Button className="w-full" variant="ghost" disabled={busy} onClick={() => setDeclining(true)}>
              <CalendarX2 className="h-4 w-4" /> {t(latest.status === 'proposed' ? 'meeting.student.noneFits' : 'meeting.student.cantAttend')}
            </Button>
          )}
        </div>
      )}
      {error && <p className="text-sm text-destructive">{error}</p>}
    </section>
  )
}
