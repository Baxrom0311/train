import { useTranslation } from 'react-i18next'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { Award, Briefcase, Clapperboard, Globe, GraduationCap, Handshake, LayoutGrid, LogOut, Moon, Receipt, ShieldCheck, Sun, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useTheme } from '@/context/ThemeContext'
import { useAuth } from '@/context/AuthContext'
import { cn } from '@/lib/utils'

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn('flex items-center gap-2', className)}>
      <span className="bg-brand grid h-8 w-8 place-items-center rounded-xl text-sm font-extrabold text-primary-foreground shadow-[0_6px_18px_-6px_hsl(var(--primary)/0.8)]">
        T
      </span>
      <span className="text-lg font-extrabold tracking-tight">
        Try<span className="text-brand">Job</span>
      </span>
    </span>
  )
}

export default function Navbar() {
  const { t, i18n } = useTranslation()
  const { theme, toggleTheme } = useTheme()
  const navigate = useNavigate()
  const { user, logout, can } = useAuth()

  const languages = [
    { code: 'uz', label: t('languages.uz') },
    { code: 'ru', label: t('languages.ru') },
    { code: 'en', label: t('languages.en') },
  ]

  // menyu ruxsatlarga qarab (CONTRACT.md §10.3, §11.4, §12.3, §13.4, §16.3); kompaniya/admin simulyatsiya o'tmaydi
  const student = can('receive_offers')
  const links = [
    ...(student ? [
      { to: '/dashboard', label: t('nav.dashboard'), Icon: LayoutGrid },
      { to: '/simulations', label: t('nav.simulations'), Icon: Briefcase },
    ] : []),
    ...(can('receive_offers') ? [{ to: '/offers', label: t('nav.offers'), Icon: Handshake }] : []),
    ...(can('manage_portfolio') ? [{ to: '/portfolio', label: t('nav.portfolio'), Icon: Award }] : []),
    ...(can('view_candidates') ? [
      { to: '/talents', label: t('nav.talents'), Icon: Users },
      { to: '/talents/offers', label: t('nav.sentOffers'), Icon: Handshake },
    ] : []),
    ...(can('manage_universities') ? [{ to: '/university', label: t('nav.students'), Icon: GraduationCap }] : []),
    ...(can('view_org_invoices') ? [{ to: '/billing', label: t('nav.billing'), Icon: Receipt }] : []),
    ...(can('approve_companies') || can('manage_billing') ? [{ to: '/admin', label: t('nav.admin'), Icon: ShieldCheck }] : []),
    ...(can('manage_simulations') ? [{ to: '/admin/scenarios', label: t('nav.scenarios'), Icon: Clapperboard }] : []),
  ]

  return (
    <header className="sticky top-0 z-40 px-3 pt-3 print:hidden">
      <nav className="glass mx-auto flex h-14 max-w-7xl items-center justify-between gap-2 rounded-2xl px-3 sm:px-4">
        <Link to="/" aria-label="TryJob">
          <Logo />
        </Link>

        <div className="flex items-center gap-1">
          {links.map(({ to, label, Icon }) => (
            <NavLink
              key={to}
              to={to}
              end
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition-colors',
                  isActive ? 'bg-primary/12 text-primary' : 'text-muted-foreground hover:text-foreground',
                )
              }
            >
              <Icon className="h-4 w-4" />
              <span className="hidden md:inline">{label}</span>
            </NavLink>
          ))}
        </div>

        <div className="flex items-center gap-1">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" aria-label={t('nav.language')}>
                <Globe className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {languages.map((lang) => (
                <DropdownMenuItem
                  key={lang.code}
                  onClick={() => i18n.changeLanguage(lang.code)}
                  className={i18n.language === lang.code ? 'bg-accent font-semibold' : ''}
                >
                  {lang.label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          <Button variant="ghost" size="icon" onClick={toggleTheme} aria-label={t('theme.toggle')}>
            {theme === 'dark' ? <Sun className="h-4 w-4 text-primary" /> : <Moon className="h-4 w-4" />}
          </Button>

          {user ? (
            <>
              <span className="ml-1 hidden items-center gap-2 text-sm font-medium lg:flex">
                <span className="bg-brand grid h-7 w-7 place-items-center rounded-full text-xs font-bold text-primary-foreground">
                  {user.full_name.slice(0, 1).toUpperCase()}
                </span>
                {user.full_name}
              </span>
              <Button
                variant="ghost"
                size="icon"
                aria-label={t('nav.logout')}
                title={t('nav.logout')}
                onClick={() => {
                  logout()
                  navigate('/login')
                }}
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" size="sm" className="hidden sm:inline-flex" onClick={() => navigate('/login')}>
                {t('nav.login')}
              </Button>
              <Button size="sm" onClick={() => navigate('/register')}>
                {t('nav.register')}
              </Button>
            </>
          )}
        </div>
      </nav>
    </header>
  )
}
