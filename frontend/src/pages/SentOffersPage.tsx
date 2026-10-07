import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { ArrowLeft, Clock, Mail, Send } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import Initials from '@/components/talent/Initials'
import OfferStatus from '@/components/talent/OfferStatus'
import { api, ApiError } from '@/lib/api'
import { formatDateTime } from '@/lib/time'
import type { SentOffer } from '@/lib/types'

export default function SentOffersPage() {
  const { t } = useTranslation()
  const [offers, setOffers] = useState<SentOffer[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api<SentOffer[]>('/talents/offers/sent')
      .then(setOffers)
      .catch((err) => setError(err instanceof ApiError && err.status === 403 ? t('talent.notVerified') : t('common.error')))
  }, [t])

  return (
    <div className="mx-auto max-w-4xl space-y-6 px-4 py-8">
      <div className="flex items-center gap-3 animate-rise">
        <Button variant="ghost" size="icon" asChild aria-label={t('talent.title')}>
          <Link to="/talents"><ArrowLeft className="h-4 w-4" /></Link>
        </Button>
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight">{t('talent.sentOffers')}</h1>
          <p className="text-sm text-muted-foreground">{t('talent.sentSubtitle')}</p>
        </div>
      </div>

      {error && <p className="glass rounded-2xl px-4 py-3 text-sm text-destructive">{error}</p>}
      {offers?.length === 0 && (
        <div className="glass flex flex-col items-center gap-2 rounded-2xl px-6 py-16 text-center">
          <Send className="h-8 w-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">{t('talent.noSent')}</p>
        </div>
      )}

      <div className="space-y-3">
        {offers?.map((o) => (
          <Card key={o.id} className="animate-rise">
            <CardContent className="flex flex-wrap items-center gap-4 p-5">
              <Initials name={o.candidate_name} />
              <div className="min-w-0 flex-1">
                <p className="font-bold">{o.candidate_name}</p>
                <p className="text-sm text-muted-foreground">{o.position_title} · {formatDateTime(o.created_at)}</p>
                {o.response_note && <p className="mt-1 text-sm italic">“{o.response_note}”</p>}
              </div>
              <div className="flex flex-col items-end gap-1.5 text-sm">
                <OfferStatus offer={o} />
                {o.candidate_email ? (
                  <a href={`mailto:${o.candidate_email}`} className="flex items-center gap-1 font-medium text-primary hover:underline">
                    <Mail className="h-3.5 w-3.5" /> {o.candidate_email}
                  </a>
                ) : !o.response && o.respond_due_at && (
                  <span className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" /> {t('offers.dueBy', { date: formatDateTime(o.respond_due_at) })}
                  </span>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
