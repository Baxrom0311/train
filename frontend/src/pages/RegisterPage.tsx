import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { Building2, GraduationCap, Hourglass, School } from 'lucide-react'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useAuth } from '@/context/AuthContext'
import { api, ApiError, registerOrg } from '@/lib/api'
import { cn } from '@/lib/utils'
import AuthShell from '@/components/layout/AuthShell'

type Kind = 'student' | 'company' | 'university'
interface University { id: string; name: string; city: string }

const KINDS: { kind: Kind; Icon: typeof GraduationCap }[] = [
  { kind: 'student', Icon: GraduationCap },
  { kind: 'company', Icon: Building2 },
  { kind: 'university', Icon: School },
]
const SELECT = 'h-10 w-full rounded-xl border border-input bg-background/60 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring'

export default function RegisterPage() {
  const { t } = useTranslation()
  const { register } = useAuth()
  const navigate = useNavigate()
  const [kind, setKind] = useState<Kind>('student')
  const [form, setForm] = useState({ fullName: '', email: '', password: '', confirm: '', orgName: '', detail: '', universityId: '' })
  const [universities, setUniversities] = useState<University[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [pending, setPending] = useState<string | null>(null)

  useEffect(() => {
    api<University[]>('/university/list').then(setUniversities).catch(() => setUniversities([]))
  }, [])

  const set = (key: keyof typeof form) => (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }))

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (form.password !== form.confirm) {
      setError(t('auth.errors.mismatch'))
      return
    }
    setBusy(true)
    setError(null)
    const base = { full_name: form.fullName.trim(), email: form.email.trim(), password: form.password }
    try {
      if (kind === 'student') {
        await register({ ...base, university_id: form.universityId || null })
        navigate('/simulations', { replace: true })
      } else {
        await registerOrg({
          ...base,
          org_type: kind,
          org_name: form.orgName.trim(),
          ...(kind === 'company' ? { industry: form.detail.trim() } : { city: form.detail.trim() }),
        })
        setPending(form.orgName.trim())
      }
    } catch (err) {
      const status = err instanceof ApiError ? err.status : 0
      setError(status === 400 ? t('auth.errors.exists') : status === 409 ? t('auth.errors.orgExists') : t('common.error'))
    } finally {
      setBusy(false)
    }
  }

  if (pending) {
    return (
      <AuthShell>
        <Card className="glass-strong w-full animate-rise">
          <CardContent className="flex flex-col items-center gap-4 p-8 text-center">
            <span className="bg-brand grid h-14 w-14 place-items-center rounded-2xl text-primary-foreground">
              <Hourglass className="h-6 w-6" />
            </span>
            <h2 className="text-2xl font-extrabold">{t('auth.pending.title')}</h2>
            <p className="text-sm text-muted-foreground">{t('auth.pending.body', { org: pending })}</p>
            <Button asChild variant="outline"><Link to="/login">{t('auth.register.loginLink')}</Link></Button>
          </CardContent>
        </Card>
      </AuthShell>
    )
  }

  const isOrg = kind !== 'student'

  return (
    <AuthShell>
      <Card className="glass-strong w-full">
        <form onSubmit={onSubmit}>
          <CardHeader className="space-y-3">
            <div className="space-y-1">
              <CardTitle className="text-2xl">{t('auth.register.title')}</CardTitle>
              <CardDescription>{t(`auth.register.subtitle_${kind}`)}</CardDescription>
            </div>
            <div role="radiogroup" aria-label={t('auth.register.accountType')} className="grid grid-cols-3 gap-1 rounded-2xl bg-muted/70 p-1">
              {KINDS.map(({ kind: k, Icon }) => (
                <button key={k} type="button" role="radio" aria-checked={kind === k} onClick={() => setKind(k)}
                  className={cn('flex items-center justify-center gap-1.5 rounded-xl py-2 text-xs font-semibold transition-all sm:text-sm',
                    kind === k ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground')}>
                  <Icon className="h-4 w-4" /> {t(`auth.register.kind.${k}`)}
                </button>
              ))}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {isOrg && (
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="orgName">{t(`auth.register.orgName_${kind}`)}</Label>
                  <Input id="orgName" required minLength={2} maxLength={120} value={form.orgName} onChange={set('orgName')} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="detail">{t(kind === 'company' ? 'auth.register.industry' : 'auth.register.city')}</Label>
                  <Input id="detail" required value={form.detail} onChange={set('detail')}
                    placeholder={t(kind === 'company' ? 'auth.register.industryPlaceholder' : 'auth.register.cityPlaceholder')} />
                </div>
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="fullName">{t(isOrg ? 'auth.register.contactName' : 'auth.register.fullName')}</Label>
              <Input id="fullName" required value={form.fullName} onChange={set('fullName')}
                placeholder={t('auth.register.fullNamePlaceholder')} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">{t(isOrg ? 'auth.register.workEmail' : 'auth.register.email')}</Label>
              <Input id="email" type="email" required autoComplete="email" value={form.email}
                onChange={set('email')} placeholder={t('auth.register.emailPlaceholder')} />
            </div>
            {kind === 'student' && universities.length > 0 && (
              <div className="space-y-2">
                <Label htmlFor="university">{t('auth.register.university')}</Label>
                <select id="university" className={SELECT} value={form.universityId} onChange={set('universityId')}>
                  <option value="">{t('auth.register.noUniversity')}</option>
                  {universities.map((u) => <option key={u.id} value={u.id}>{u.name} — {u.city}</option>)}
                </select>
                {form.universityId && <p className="text-xs text-muted-foreground">{t('auth.register.universityHint')}</p>}
              </div>
            )}
            <div className="grid gap-4 sm:grid-cols-2">
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
            </div>
            {isOrg && <p className="text-xs text-muted-foreground">{t('auth.register.orgNote')}</p>}
            {error && <p className="text-sm text-destructive">{error}</p>}
          </CardContent>
          <CardFooter className="flex flex-col space-y-4">
            <Button className="w-full" type="submit" disabled={busy}>
              {t(isOrg ? 'auth.register.submitOrg' : 'auth.register.submit')}
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
