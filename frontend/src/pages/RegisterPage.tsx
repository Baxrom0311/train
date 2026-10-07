import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useAuth } from '@/context/AuthContext'
import { ApiError } from '@/lib/api'
import AuthShell from '@/components/layout/AuthShell'

export default function RegisterPage() {
  const { t } = useTranslation()
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ fullName: '', email: '', password: '', confirm: '' })
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }))

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (form.password !== form.confirm) {
      setError(t('auth.errors.mismatch'))
      return
    }
    setBusy(true)
    setError(null)
    try {
      await register(form.fullName, form.email, form.password)
      navigate('/simulations', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError && err.status === 400 ? t('auth.errors.exists') : t('common.error'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthShell>
      <Card className="glass-strong w-full">
        <form onSubmit={onSubmit}>
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl">{t('auth.register.title')}</CardTitle>
            <CardDescription>{t('auth.register.subtitle')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="fullName">{t('auth.register.fullName')}</Label>
              <Input id="fullName" required value={form.fullName} onChange={set('fullName')}
                placeholder={t('auth.register.fullNamePlaceholder')} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">{t('auth.register.email')}</Label>
              <Input id="email" type="email" required autoComplete="email" value={form.email}
                onChange={set('email')} placeholder={t('auth.register.emailPlaceholder')} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">{t('auth.register.password')}</Label>
              <Input id="password" type="password" required minLength={8} autoComplete="new-password"
                value={form.password} onChange={set('password')} placeholder={t('auth.register.passwordPlaceholder')} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">{t('auth.register.confirmPassword')}</Label>
              <Input id="confirmPassword" type="password" required autoComplete="new-password"
                value={form.confirm} onChange={set('confirm')}
                placeholder={t('auth.register.confirmPasswordPlaceholder')} />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </CardContent>
          <CardFooter className="flex flex-col space-y-4">
            <Button className="w-full" type="submit" disabled={busy}>
              {t('auth.register.submit')}
            </Button>
            <p className="text-sm text-center text-muted-foreground">
              {t('auth.register.hasAccount')}{' '}
              <Link to="/login" className="font-medium text-foreground hover:underline underline-offset-4">
                {t('auth.register.loginLink')}
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </AuthShell>
  )
}
