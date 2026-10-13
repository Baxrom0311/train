import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useLocation } from 'react-router-dom'
import { BadgeCheck, Link2Off, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import AuthShell from '@/components/layout/AuthShell'
import StatusCard from '@/components/account/StatusCard'
import { homeFor, useAuth } from '@/context/AuthContext'
import { verifyEmail, tokenFromHash } from '@/lib/api'

type State = { kind: 'checking' } | { kind: 'done'; email: string } | { kind: 'invalid' } | { kind: 'error' }

// Emaildagi havola: /verify-email#token=… (CONTRACT.md §30.2). Ochilganda o'zi tasdiqlaydi;
// kirish shart emas (tashkilot xodimi admin tasdiqlashini kutayotgan bo'lishi mumkin).
export default function VerifyEmailPage() {
  const { t } = useTranslation()
  const { user, reload } = useAuth()
  const token = tokenFromHash(useLocation().hash)
  const [state, setState] = useState<State>(token ? { kind: 'checking' } : { kind: 'invalid' })
  const sent = useRef(false)

  useEffect(() => {
    // StrictMode'da effekt ikki marta ishlaydi — token bir martalik, so'rov bitta bo'lsin
    if (!token || sent.current) return
    sent.current = true
    verifyEmail(token)
      .then((r) => setState({ kind: 'done', email: r.email }))
      .catch((err) => setState(err?.status === 400 ? { kind: 'invalid' } : { kind: 'error' }))
  }, [token])

  useEffect(() => {
    if (state.kind === 'done' && user && !user.email_verified) reload().catch(() => undefined)
  }, [state.kind, user, reload])

  return (
    <AuthShell>
      {state.kind === 'checking' && (
        <StatusCard Icon={Loader2} spin title={t('account.verify.checking')}>
          <p className="text-sm text-muted-foreground">{t('account.verify.checkingBody')}</p>
        </StatusCard>
      )}
      {state.kind === 'done' && (
        <StatusCard Icon={BadgeCheck} title={t('account.verify.doneTitle')}>
          <p className="text-sm text-muted-foreground">{t('account.verify.doneBody', { email: state.email })}</p>
          <Button asChild>
            <Link to={user ? homeFor(user) : '/login'} replace>
              {t(user ? 'account.verify.continue' : 'account.backToLogin')}
            </Link>
          </Button>
        </StatusCard>
      )}
      {state.kind === 'invalid' && (
        <StatusCard Icon={Link2Off} tone="danger" title={t('account.verify.invalidTitle')}>
          <p className="text-sm text-muted-foreground">
            {t(user && !user.email_verified ? 'account.verify.invalidResend' : 'account.verify.invalidBody')}
          </p>
          <Button asChild variant="outline"><Link to={user ? homeFor(user) : '/login'} replace>
            {t(user ? 'account.verify.continue' : 'account.backToLogin')}
          </Link></Button>
        </StatusCard>
      )}
      {state.kind === 'error' && (
        <StatusCard Icon={Link2Off} tone="danger" title={t('common.error')}>
          <Button onClick={() => window.location.reload()}>{t('common.retry')}</Button>
        </StatusCard>
      )}
    </AuthShell>
  )
}
