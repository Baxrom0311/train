import { useTranslation } from 'react-i18next'
import { Clock, MessageSquare, Sparkles } from 'lucide-react'

// Kirish/ro'yxatdan o'tish: chapda platforma va'dasi, o'ngda forma (glass karta).
export default function AuthShell({ children }: { children: React.ReactNode }) {
  const { t } = useTranslation()
  const points = [
    { Icon: Clock, text: t('auth.hero.realTime') },
    { Icon: MessageSquare, text: t('auth.hero.colleagues') },
    { Icon: Sparkles, text: t('auth.hero.feedback') },
  ]
  return (
    <div className="mx-auto grid min-h-[calc(100dvh-5rem)] max-w-6xl items-center gap-10 px-4 py-10 lg:grid-cols-[1.1fr_1fr]">
      <section className="hidden space-y-6 lg:block animate-rise">
        <p className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
          <span className="h-1.5 w-1.5 rounded-full bg-primary animate-glow" /> {t('auth.hero.badge')}
        </p>
        <h1 className="text-5xl font-extrabold leading-[1.05] tracking-tight">
          {t('auth.hero.title1')} <span className="text-brand">{t('auth.hero.title2')}</span>
        </h1>
        <p className="max-w-md text-lg text-muted-foreground">{t('auth.hero.subtitle')}</p>
        <ul className="space-y-3">
          {points.map(({ Icon, text }) => (
            <li key={text} className="glass flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium">
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-primary/12 text-primary">
                <Icon className="h-4 w-4" />
              </span>
              {text}
            </li>
          ))}
        </ul>
      </section>
      <div className="mx-auto w-full max-w-md animate-rise">{children}</div>
    </div>
  )
}
