import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2, Mail, Send } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { DialogDescription } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { api, ApiError } from '@/lib/api'

interface Props {
  candidateId: string
  /** vakansiyadan (§23.3): ariza bergan nomzodga ham yuboriladi, lavozim nomi vakansiyadan */
  vacancyId?: string
  defaultPosition?: string
  onSent?: () => void
}

/** Taklif yuborish formasi (§10.2) — Dialog ichida ishlatiladi. */
export default function OfferForm({ candidateId, vacancyId, defaultPosition = '', onSent }: Props) {
  const { t } = useTranslation()
  const [position, setPosition] = useState(defaultPosition)
  const [message, setMessage] = useState('')
  const [state, setState] = useState<'idle' | 'sending' | 'sent'>('idle')
  const [error, setError] = useState<string | null>(null)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setState('sending')
    setError(null)
    try {
      await api('/talents/offers', {
        method: 'POST',
        json: { candidate_user_id: candidateId, position_title: position, message, vacancy_id: vacancyId ?? null },
      })
      setState('sent')
      onSent?.()
    } catch (err) {
      setError(err instanceof ApiError && err.status === 409 ? t('talent.offer.duplicate') : t('common.error'))
      setState('idle')
    }
  }

  if (state === 'sent') {
    return (
      <p className="rounded-2xl border border-success/30 bg-success/10 px-4 py-3 text-sm">
        {t('talent.offer.sent')}
      </p>
    )
  }

  return (
    <form onSubmit={submit} className="space-y-3 rounded-2xl border bg-background/60 p-4">
      <h3 className="flex items-center gap-2 font-semibold"><Mail className="h-4 w-4 text-primary" /> {t('talent.offer.title')}</h3>
      <DialogDescription className="text-xs text-muted-foreground">{t('talent.offer.privacy')}</DialogDescription>
      <div className="space-y-1.5">
        <Label htmlFor="position">{t('talent.offer.position')}</Label>
        <Input id="position" required minLength={2} maxLength={120} value={position}
          onChange={(e) => setPosition(e.target.value)} placeholder={t('talent.offer.positionPlaceholder')} />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="message">{t('talent.offer.message')}</Label>
        <Textarea id="message" required minLength={10} maxLength={2000} rows={4} value={message}
          onChange={(e) => setMessage(e.target.value)} placeholder={t('talent.offer.messagePlaceholder')} />
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
      <Button type="submit" disabled={state === 'sending'}>
        {state === 'sending' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
        {t('talent.offer.send')}
      </Button>
    </form>
  )
}
