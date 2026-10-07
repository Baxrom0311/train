import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export default function RegisterPage() {
  const { t } = useTranslation()

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-12">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold">{t('auth.register.title')}</CardTitle>
          <CardDescription>{t('auth.register.subtitle')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="fullName">{t('auth.register.fullName')}</Label>
            <Input
              id="fullName"
              type="text"
              placeholder={t('auth.register.fullNamePlaceholder')}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="email">{t('auth.register.email')}</Label>
            <Input
              id="email"
              type="email"
              placeholder={t('auth.register.emailPlaceholder')}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">{t('auth.register.password')}</Label>
            <Input
              id="password"
              type="password"
              placeholder={t('auth.register.passwordPlaceholder')}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirmPassword">{t('auth.register.confirmPassword')}</Label>
            <Input
              id="confirmPassword"
              type="password"
              placeholder={t('auth.register.confirmPasswordPlaceholder')}
            />
          </div>
        </CardContent>
        <CardFooter className="flex flex-col space-y-4">
          <Button className="w-full">{t('auth.register.submit')}</Button>
          <p className="text-sm text-center text-muted-foreground">
            {t('auth.register.hasAccount')}{' '}
            <Link
              to="/login"
              className="font-medium text-foreground hover:underline underline-offset-4"
            >
              {t('auth.register.loginLink')}
            </Link>
          </p>
          <p className="text-xs text-center text-muted-foreground">
            {t('auth.register.terms')}{' '}
            <Link to="#" className="underline underline-offset-4">
              {t('auth.register.termsLink')}
            </Link>
            {t('auth.register.termsEnd') ? ` ${t('auth.register.termsEnd')}` : ''}
          </p>
        </CardFooter>
      </Card>
    </div>
  )
}