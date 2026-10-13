import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useLocation } from 'react-router-dom'
import { Loader2, MailCheck } from 'lucide-react'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import AuthShell from '@/components/layout/AuthShell'
import StatusCard from '@/components/account/StatusCard'
import { clock, tooManyText, useCooldown } from '@/components/account/useCooldown'
import { forgotPassword, retryAfter } from '@/lib/api'

// Parolni tiklash havolasini so'rash (CONTRACT.md §30.3): javob har doim bir xil —
// akkaunt bor-yo'qligi oshkor qilinmaydi.
export default function ForgotPasswordPage() {
  const { t } = useTranslation()
  const preset = (useLocation().state as { email?: string } | null)?.email ?? ''
  const [email, setEmail] = useState(preset)
  const [sentTo, setSentTo] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const cooldown = useCooldown()

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await forgotPassword(email.trim())
      setSentTo(email.trim())
    } catch (err) {
      const wait = retryAfter(err)
      if (wait !== null) {
        cooldown.start(wait)
        setError(tooManyText(t, wait))
      } else {
        setError(t('common.error'))
      }
    } finally {
      setBusy(false)
    }
  }

  if (sentTo) {
    return (
      <AuthShell>
        <StatusCard Icon={MailCheck} title={t('account.forgot.sentTitle')}>
          <p className="text-sm text-muted-foreground">{t('account.forgot.sentBody', { email: sentTo })}</p>
          <p className="text-xs text-muted-foreground">{t('account.forgot.sentHint')}</p>
          <div className="flex flex-wrap justify-center gap-2">
            <Button variant="outline" onClick={() => setSentTo(null)}>{t('account.forgot.again')}</Button>
            <Button asChild><Link to="/login">{t('account.backToLogin')}</Link></Button>
          </div>
        </StatusCard>
      </AuthShell>
    )
  }

  return (
    <AuthShell>
      <Card className="glass-strong w-full">
        <form onSubmit={onSubmit}>
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl">{t('account.forgot.title')}</CardTitle>
            <CardDescription>{t('account.forgot.subtitle')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">{t('auth.login.email')}</Label>
              <Input id="email" type="email" required autoComplete="email" autoFocus value={email}
                onChange={(e) => setEmail(e.target.value)} placeholder={t('auth.login.emailPlaceholder')} />
            </div>
            {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
          </CardContent>
          <CardFooter className="flex flex-col space-y-4">
            <Button className="w-full" type="submit" disabled={busy || cooldown.left > 0}>
              {busy && <Loader2 className="h-4 w-4 animate-spin" />}
              {cooldown.left > 0 ? t('account.waitButton', { time: clock(cooldown.left) }) : t('account.forgot.submit')}
            </Button>
            <Link to="/login" className="text-sm font-medium text-muted-foreground hover:text-foreground hover:underline underline-offset-4">
              {t('account.backToLogin')}
            </Link>
          </CardFooter>
        </form>
      </Card>
    </AuthShell>
  )
}
