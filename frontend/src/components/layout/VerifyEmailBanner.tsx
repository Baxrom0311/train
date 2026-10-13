// Tasdiqlanmagan email eslatmasi (CONTRACT.md §30.8): navbar ostida, sessiya davomida yopiladi.
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation } from 'react-router-dom'
import { Check, Loader2, MailWarning, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/context/AuthContext'
import { ApiError, resendVerification, retryAfter } from '@/lib/api'
import { tooManyText } from '@/components/account/useCooldown'

const DISMISSED = 'tj_verify_banner_dismissed'

function readDismissed(): string | null {
  try {
    return sessionStorage.getItem(DISMISSED)
  } catch {
    return null
  }
}

export default function VerifyEmailBanner() {
  const { t } = useTranslation()
  const { user, reload } = useAuth()
  const { pathname } = useLocation()
  const [dismissed, setDismissed] = useState(readDismissed)
  const [state, setState] = useState<'idle' | 'busy' | 'sent'>('idle')
  const [error, setError] = useState<string | null>(null)
  const unverified = Boolean(user && !user.email_verified)

  // havola boshqa oynada ochilgan bo'lsa — qaytganda yo'lak yo'qolsin
  useEffect(() => {
    if (!unverified) return
    const onFocus = () => void reload().catch(() => undefined)
    window.addEventListener('focus', onFocus)
    return () => window.removeEventListener('focus', onFocus)
  }, [unverified, reload])

  if (!user || !unverified || dismissed === user.id || pathname === '/verify-email') return null

  const resend = async () => {
    setState('busy')
    setError(null)
    try {
      await resendVerification()
      setState('sent')
    } catch (err) {
      setState('idle')
      const wait = retryAfter(err)
      if (wait !== null) setError(tooManyText(t, wait))
      else if (err instanceof ApiError && err.status === 409) void reload()
      else setError(t('common.error'))
    }
  }

  const dismiss = () => {
    try {
      sessionStorage.setItem(DISMISSED, user.id)
    } catch {
      // saqlab bo'lmasa ham shu sahifada yopiladi
    }
    setDismissed(user.id)
  }

  return (
    <div role="status" className="mx-3 mt-2 print:hidden">
      <div className="glass mx-auto flex max-w-7xl items-start gap-3 rounded-2xl border-primary/30 px-4 py-2.5 text-sm sm:items-center">
        <MailWarning className="mt-0.5 h-4 w-4 shrink-0 text-primary sm:mt-0" />
        <div className="min-w-0 flex-1 sm:flex sm:items-center sm:gap-3">
          <p className="min-w-0 flex-1">
            <span className="font-semibold">{t('account.banner.title')}</span>{' '}
            <span className="text-muted-foreground">{t('account.banner.body', { email: user.email })}</span>
            {error && <span className="block text-destructive">{error}</span>}
          </p>
          <div className="mt-2 shrink-0 sm:mt-0">
            {state === 'sent' ? (
              <span className="inline-flex items-center gap-1 text-xs font-semibold text-primary">
                <Check className="h-3.5 w-3.5" /> {t('account.banner.sent')}
              </span>
            ) : (
              <Button size="sm" variant="outline" onClick={resend} disabled={state === 'busy'}>
                {state === 'busy' && <Loader2 className="h-3.5 w-3.5 animate-spin" />} {t('account.banner.resend')}
              </Button>
            )}
          </div>
        </div>
        <button type="button" onClick={dismiss} aria-label={t('common.close')}
          className="-mr-1 rounded-lg p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground">
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
