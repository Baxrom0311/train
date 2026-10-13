import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { homeFor, useAuth } from '@/context/AuthContext'
import { ApiError, retryAfter } from '@/lib/api'
import AuthShell from '@/components/layout/AuthShell'
import { clock, tooManyText, useCooldown } from '@/components/account/useCooldown'

export default function LoginPage() {
  const { t } = useTranslation()
  const { login } = useAuth()
  const navigate = useNavigate()
  const from = (useLocation().state as { from?: string } | null)?.from
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const cooldown = useCooldown()

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const me = await login(email, password)
      navigate(from ?? homeFor(me), { replace: true })
    } catch (err) {
      const wait = retryAfter(err)
      if (wait !== null) {
        // §30.4: chegarada to'g'ri parol ham rad etiladi — tugma kutish tugaguncha o'chiq
        cooldown.start(wait)
        setError(tooManyText(t, wait))
      } else if (err instanceof ApiError && err.status === 403) {
        setError(t('auth.errors.inactive'))
      } else if (err instanceof ApiError && err.status === 400) {
        setError(t('auth.errors.invalid'))
      } else {
        setError(t('common.error'))
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthShell>
      <Card className="glass-strong w-full">
        <form onSubmit={onSubmit}>
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl">{t('auth.login.title')}</CardTitle>
            <CardDescription>{t('auth.login.subtitle')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">{t('auth.login.email')}</Label>
              <Input
                id="email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={t('auth.login.emailPlaceholder')}
              />
            </div>
            <div className="space-y-2">
              <div className="flex items-baseline justify-between gap-2">
                <Label htmlFor="password">{t('auth.login.password')}</Label>
                <Link to="/forgot-password" state={{ email }}
                  className="text-xs font-medium text-muted-foreground hover:text-foreground hover:underline underline-offset-4">
                  {t('auth.login.forgotPassword')}
                </Link>
              </div>
              <Input
                id="password"
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={t('auth.login.passwordPlaceholder')}
              />
            </div>
            {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
          </CardContent>
          <CardFooter className="flex flex-col space-y-4">
            <Button className="w-full" type="submit" disabled={busy || cooldown.left > 0}>
              {cooldown.left > 0 ? t('account.waitButton', { time: clock(cooldown.left) }) : t('auth.login.submit')}
            </Button>
            <p className="text-sm text-center text-muted-foreground">
              {t('auth.login.noAccount')}{' '}
              <Link to="/register" className="font-medium text-foreground hover:underline underline-offset-4">
                {t('auth.login.registerLink')}
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </AuthShell>
  )
}
