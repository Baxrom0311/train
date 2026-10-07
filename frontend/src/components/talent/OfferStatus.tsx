import { useTranslation } from 'react-i18next'
import { Badge } from '@/pages/Badge'
import type { TalentOffer } from '@/lib/types'

/** Taklif holati: javob bo'lsa — javob (qabul/rad), aks holda yuborildi/ko'rildi (kompaniyaga). */
export default function OfferStatus({ offer, forCandidate = false }: { offer: TalentOffer; forCandidate?: boolean }) {
  const { t } = useTranslation()
  if (offer.response === 'accepted') return <Badge className="bg-success text-white">{t('offers.status.accepted')}</Badge>
  if (offer.response === 'declined') return <Badge variant="secondary">{t('offers.status.declined')}</Badge>
  // talabaga "ko'rildi" emas — javob kutilayotgani muhim
  if (forCandidate) return <Badge>{t('offers.status.awaiting')}</Badge>
  return <Badge variant="outline">{t(`offers.status.${offer.status}`)}</Badge>
}
