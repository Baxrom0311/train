import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useLocation } from 'react-router-dom'
import { KeyRound, Link2Off, Loader2 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import AuthShell from '@/components/layout/AuthShell'
import StatusCard from '@/components/account/StatusCard'
import { clock, tooManyText, useCooldown } from '@/components/account/useCooldown'
import { useAuth } from '@/context/AuthContext'
import { ApiError, resetPassword, retryAfter, tokenFromHash } from '@/lib/api'

type State = 'form' | 'done' | 'invalid'

// Emaildagi havola: /reset-password#token=… (CONTRACT.md §30.3). Parol almashgach barcha
// sessiyalar bekor — shu brauzerdagi ham, shuning uchun foydalanuvchi qayta kiradi.
export default function ResetPasswordPage() {
  const { t } = useTranslation()
  const { user, logout } = useAuth()
  const token = tokenFromHash(useLocation().hash)
  const [state, setState] = useState<State>(token ? 'form' : 'invalid')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const cooldown = useCooldown()

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password !== confirm) {
      setError(t('auth.errors.mismatch'))
      return
    }
    setBusy(true)
    setError(null)
    try {
      await resetPassword(token, password)
      if (user) logout()                     // eski sessiya serverda allaqachon bekor
      setState('done')
    } catch (err) {
      const wait = retryAfter(err)
      if (wait !== null) {
        cooldown.start(wait)
        setError(tooManyText(t, wait))
      } else if (err instanceof ApiError && err.status === 400) {
        setState('invalid')
      } else {
        setError(t('common.error'))
      }
    } finally {
      setBusy(false)
    }
  }

  if (state === 'done') {
    return (
      <AuthShell>
        <StatusCard Icon={KeyRound} title={t('account.reset.doneTitle')}>
          <p className="text-sm text-muted-foreground">{t('account.reset.doneBody')}</p>
          <Button asChild><Link to="/login" replace>{t('account.reset.toLogin')}</Link></Button>
        </StatusCard>
      </AuthShell>
    )
  }

  if (state === 'invalid') {
    return (
      <AuthShell>
        <StatusCard Icon={Link2Off} tone="danger" title={t('account.reset.invalidTitle')}>
          <p className="text-sm text-muted-foreground">{t('account.reset.invalidBody')}</p>
          <Button asChild><Link to="/forgot-password" replace>{t('account.reset.requestNew')}</Link></Button>
        </StatusCard>
      </AuthShell>
    )
  }

  return (
    <AuthShell>
      <Card className="glass-strong w-full">
        <form onSubmit={onSubmit}>
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl">{t('account.reset.title')}</CardTitle>
            <CardDescription>{t('account.reset.subtitle')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="password">{t('account.reset.password')}</Label>
              <Input id="password" type="password" required minLength={8} maxLength={128} autoComplete="new-password"
                autoFocus value={password} onChange={(e) => setPassword(e.target.value)}
                placeholder={t('auth.register.passwordPlaceholder')} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">{t('auth.register.confirmPassword')}</Label>
              <Input id="confirmPassword" type="password" required autoComplete="new-password" value={confirm}
                onChange={(e) => setConfirm(e.target.value)} placeholder={t('auth.register.confirmPasswordPlaceholder')} />
            </div>
            <p className="text-xs text-muted-foreground">{t('account.reset.sessionsNote')}</p>
            {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
          </CardContent>
          <CardFooter>
            <Button className="w-full" type="submit" disabled={busy || cooldown.left > 0}>
              {busy && <Loader2 className="h-4 w-4 animate-spin" />}
              {cooldown.left > 0 ? t('account.waitButton', { time: clock(cooldown.left) }) : t('account.reset.submit')}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </AuthShell>
  )
}
