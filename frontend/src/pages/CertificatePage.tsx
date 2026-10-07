import { useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { BadgeCheck, Loader2, Printer, Search, ShieldX } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import CertificateSheet, { certificateUrl } from '@/components/credentials/CertificateSheet'
import CopyButton from '@/components/credentials/CopyButton'
import { api, ApiError } from '@/lib/api'
import { formatDate } from '@/lib/time'
import type { CertificatePublic } from '@/lib/types'

/** Ochiq tekshiruv sahifasi `/c/:code` (CONTRACT.md §13.4) — login shart emas. */
export default function CertificatePage() {
  const { code = '' } = useParams()
  const { t, i18n } = useTranslation()
  const [cert, setCert] = useState<CertificatePublic | null>(null)
  const [state, setState] = useState<'loading' | 'ok' | 'missing' | 'error'>('loading')

  useEffect(() => {
    setState('loading')
    api<CertificatePublic>(`/certificates/${encodeURIComponent(code)}`)
      .then((c) => {
        setCert(c)
        setState('ok')
      })
      .catch((e) => setState(e instanceof ApiError && e.status === 404 ? 'missing' : 'error'))
  }, [code])

  useEffect(() => {
    if (cert) document.title = `${cert.holder_name} — ${t('cert.title')} · TryJob`
    return () => {
      document.title = 'TryJob'
    }
  }, [cert, t])

  if (state === 'loading') {
    return <p className="flex items-center justify-center gap-2 p-16 text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" /> {t('common.loading')}</p>
  }
  if (state !== 'ok' || !cert) {
    return (
      <div className="mx-auto max-w-lg space-y-6 px-4 py-16 text-center animate-rise">
        <ShieldX className="mx-auto h-12 w-12 text-muted-foreground" />
        <div className="space-y-2">
          <h1 className="text-2xl font-extrabold">{t(state === 'missing' ? 'cert.notFound' : 'common.error')}</h1>
          {state === 'missing' && <p className="text-muted-foreground">{t('cert.notFoundHint', { code })}</p>}
        </div>
        <VerifyForm />
      </div>
    )
  }

  const revoked = cert.status === 'revoked'
  return (
    <div className="mx-auto max-w-5xl space-y-5 px-4 py-8 print:m-0 print:max-w-none print:space-y-0 print:p-0">
      <div className={`glass animate-rise flex flex-wrap items-center justify-between gap-3 rounded-2xl p-4 print:hidden ${revoked ? 'ring-1 ring-destructive/40' : ''}`}>
        <div className="flex items-center gap-3">
          {revoked
            ? <ShieldX className="h-6 w-6 shrink-0 text-destructive" />
            : <BadgeCheck className="h-6 w-6 shrink-0 text-success" />}
          <div className="text-sm">
            <p className="font-semibold">{t(revoked ? 'cert.revokedBanner' : 'cert.validBanner')}</p>
            <p className="text-muted-foreground">
              {revoked
                ? t('cert.revokedReason', { reason: cert.revoked_reason, date: formatDate(cert.revoked_at!, i18n.language) })
                : t('cert.issuedOn', { date: formatDate(cert.issued_at, i18n.language) })}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <CopyButton value={certificateUrl(cert.code)} />
          <Button size="sm" onClick={() => window.print()} disabled={revoked}>
            <Printer className="h-4 w-4" /> {t('cert.print')}
          </Button>
        </div>
      </div>

      <div className="animate-rise" style={{ animationDelay: '80ms' }}>
        <CertificateSheet cert={cert} />
      </div>
      <p className="text-center text-xs text-muted-foreground print:hidden">{t('cert.disclaimer')}</p>
    </div>
  )
}

/** Kod bo'yicha qidirish (QR'siz kelgan tekshiruvchi uchun). */
export function VerifyForm() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [value, setValue] = useState('')
  const submit = (e: FormEvent) => {
    e.preventDefault()
    // "tj hq6w hkt7" → "TJ-HQ6W-HKT7"; boshqa shaklni server o'zi rad etadi
    const raw = value.toUpperCase().replace(/[\s-]+/g, '')
    const code = /^TJ[0-9A-Z]{8}$/.test(raw) ? `TJ-${raw.slice(2, 6)}-${raw.slice(6)}` : value.trim()
    if (code) navigate(`/c/${encodeURIComponent(code)}`)
  }
  return (
    <form onSubmit={submit} className="flex gap-2">
      <Input value={value} onChange={(e) => setValue(e.target.value)} placeholder="TJ-XXXX-XXXX"
        aria-label={t('cert.codeLabel')} className="font-mono uppercase" />
      <Button type="submit"><Search className="h-4 w-4" /> {t('cert.verify')}</Button>
    </form>
  )
}
