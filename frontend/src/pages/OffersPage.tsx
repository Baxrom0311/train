import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Building2, Clock, Eye, EyeOff, Inbox, Loader2, ShieldCheck, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import CandidateProfileView from '@/components/talent/CandidateProfileView'
import OfferStatus from '@/components/talent/OfferStatus'
import { api } from '@/lib/api'
import { formatDateTime } from '@/lib/time'
import type { CandidateProfile, OfferResponse, ReceivedOffer, Visibility } from '@/lib/types'

export default function OffersPage() {
  const { t } = useTranslation()
  const [visibility, setVisibility] = useState<Visibility | null>(null)
  const [profile, setProfile] = useState<CandidateProfile | null | undefined>(undefined)
  const [offers, setOffers] = useState<ReceivedOffer[]>([])
  const [error, setError] = useState<string | null>(null)
  const [preview, setPreview] = useState(false)

  useEffect(() => {
    Promise.all([
      api<Visibility>('/users/me/visibility'),
      api<CandidateProfile | null>('/users/me/talent-profile'),
      api<ReceivedOffer[]>('/talents/offers/my'),
    ])
      .then(([v, p, o]) => {
        setVisibility(v)
        setProfile(p)
        setOffers(o)
        // ochilgan sahifadagi yangi takliflar — "ko'rildi" (kompaniya holatni ko'radi)
        o.filter((x) => x.status === 'sent').forEach((x) => api(`/talents/offers/${x.id}/view`, { method: 'POST' }).catch(() => {}))
      })
      .catch(() => setError(t('common.error')))
  }, [t])

  const saveVisibility = async (next: Visibility) => {
    const prev = visibility
    setVisibility(next)
    try {
      setVisibility(await api<Visibility>('/users/me/visibility', { method: 'PATCH', json: next }))
    } catch {
      setVisibility(prev)
      setError(t('common.error'))
    }
  }

  const companyNames = Object.fromEntries(offers.map((o) => [o.company_id, o.company_name]))

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-8">
      <div className="space-y-2 animate-rise">
        <h1 className="text-4xl font-extrabold tracking-tight">{t('offers.title')}</h1>
        <p className="text-muted-foreground">{t('offers.subtitle')}</p>
      </div>

      {error && <p className="glass rounded-2xl px-4 py-3 text-sm text-destructive">{error}</p>}

      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <Card className="animate-rise">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <ShieldCheck className="h-5 w-5 text-primary" /> {t('offers.visibility.title')}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <label className="flex items-start justify-between gap-4">
              <span className="space-y-1">
                <span className="block font-semibold">{t('offers.visibility.open')}</span>
                <span className="block text-sm text-muted-foreground">{t('offers.visibility.openHint')}</span>
              </span>
              <Switch
                checked={visibility?.is_open_to_work ?? false}
                disabled={!visibility}
                onCheckedChange={(on) => visibility && saveVisibility({ ...visibility, is_open_to_work: on })}
                className="mt-1"
              />
            </label>
            {visibility && visibility.hidden_from_company_ids.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium">{t('offers.visibility.hidden')}</p>
                <div className="flex flex-wrap gap-2">
                  {visibility.hidden_from_company_ids.map((id) => (
                    <span key={id} className="flex items-center gap-1.5 rounded-full border bg-background/60 py-1 pl-3 pr-1 text-sm">
                      <EyeOff className="h-3.5 w-3.5 text-muted-foreground" />
                      {companyNames[id] ?? t('offers.visibility.unknownCompany')}
                      <button type="button" aria-label={t('offers.visibility.unhide')}
                        className="grid h-6 w-6 place-items-center rounded-full hover:bg-accent"
                        onClick={() => saveVisibility({
                          ...visibility,
                          hidden_from_company_ids: visibility.hidden_from_company_ids.filter((x) => x !== id),
                        })}>
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="animate-rise">
          <CardHeader>
            <CardTitle className="text-lg">{t('offers.profile.title')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {profile === undefined && <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />}
            {profile === null && (
              <>
                <p className="text-muted-foreground">{t('offers.profile.empty')}</p>
                <Button size="sm" asChild><Link to="/simulations">{t('dashboard.browseSimulations')}</Link></Button>
              </>
            )}
            {profile && (
              <>
                <p className="text-muted-foreground">{t('offers.profile.hint')}</p>
                <Button size="sm" variant="outline" onClick={() => setPreview(true)}>
                  <Eye className="h-4 w-4" /> {t('offers.profile.preview')}
                </Button>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <section className="space-y-3">
        <h2 className="flex items-center gap-2 text-xl font-bold"><Inbox className="h-5 w-5 text-primary" /> {t('offers.received')}</h2>
        {offers.length === 0 && (
          <p className="glass rounded-2xl px-5 py-10 text-center text-sm text-muted-foreground">{t('offers.none')}</p>
        )}
        {offers.map((o) => (
          <OfferCard key={o.id} offer={o} onAnswered={(updated, hidden) => {
            setOffers((list) => list.map((x) => (x.id === updated.id ? { ...x, ...updated } : x)))
            if (hidden && visibility) {
              setVisibility({ ...visibility, hidden_from_company_ids: [...visibility.hidden_from_company_ids, o.company_id] })
            }
          }} />
        ))}
      </section>

      {profile && (
        <Dialog open={preview} onOpenChange={setPreview}>
          <DialogContent closeLabel={t('common.close')} aria-describedby={undefined}>
            <DialogTitle className="sr-only">{t('offers.profile.preview')}</DialogTitle>
            <div className="overflow-y-auto p-6"><CandidateProfileView profile={profile} /></div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  )
}

function OfferCard({ offer, onAnswered }: { offer: ReceivedOffer; onAnswered: (o: ReceivedOffer, hidden: boolean) => void }) {
  const { t } = useTranslation()
  const [decision, setDecision] = useState<OfferResponse | null>(null)
  const [note, setNote] = useState('')
  const [hide, setHide] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const answered = offer.status === 'responded'

  const send = async () => {
    if (!decision) return
    setBusy(true)
    setError(null)
    try {
      const updated = await api<ReceivedOffer>(`/talents/offers/${offer.id}/respond`, {
        method: 'POST',
        json: { decision, note: note.trim() || null, hide_company: decision === 'declined' && hide },
      })
      onAnswered(updated, decision === 'declined' && hide)
    } catch {
      setError(t('common.error'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card className="animate-rise">
      <CardContent className="space-y-4 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="grid h-11 w-11 place-items-center rounded-2xl bg-primary/12 text-primary">
              <Building2 className="h-5 w-5" />
            </span>
            <div>
              <p className="font-bold">{offer.position_title}</p>
              <p className="text-sm text-muted-foreground">{offer.company_name} · {offer.company_industry}</p>
            </div>
          </div>
          <div className="flex flex-col items-end gap-1">
            <OfferStatus offer={offer} forCandidate />
            {!answered && offer.respond_due_at && (
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" /> {t('offers.dueBy', { date: formatDateTime(offer.respond_due_at) })}
              </span>
            )}
          </div>
        </div>

        <p className="whitespace-pre-wrap text-sm leading-relaxed">{offer.message}</p>

        {answered ? (
          offer.response === 'accepted' && <p className="text-sm text-success">{t('offers.acceptedHint')}</p>
        ) : decision === null ? (
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => setDecision('accepted')}>{t('offers.accept')}</Button>
            <Button variant="outline" onClick={() => setDecision('declined')}>{t('offers.decline')}</Button>
          </div>
        ) : (
          <div className="space-y-3 rounded-2xl border bg-background/60 p-4">
            <p className="text-sm font-semibold">
              {decision === 'accepted' ? t('offers.acceptConfirm', { company: offer.company_name }) : t('offers.declineConfirm')}
            </p>
            <Textarea rows={2} maxLength={500} value={note} onChange={(e) => setNote(e.target.value)}
              placeholder={decision === 'accepted' ? t('offers.notePlaceholderAccept') : t('offers.notePlaceholderDecline')} />
            {decision === 'declined' && (
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={hide} onChange={(e) => setHide(e.target.checked)} className="h-4 w-4 accent-[hsl(var(--primary))]" />
                {t('offers.hideCompany', { company: offer.company_name })}
              </label>
            )}
            {error && <p className="text-sm text-destructive">{error}</p>}
            <div className="flex gap-2">
              <Button size="sm" onClick={send} disabled={busy}>
                {busy && <Loader2 className="h-4 w-4 animate-spin" />} {t('common.confirm')}
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setDecision(null)} disabled={busy}>{t('common.cancel')}</Button>
            </div>
          </div>
        )}
        {offer.response_note && <p className="text-sm italic text-muted-foreground">“{offer.response_note}”</p>}
      </CardContent>
    </Card>
  )
}
