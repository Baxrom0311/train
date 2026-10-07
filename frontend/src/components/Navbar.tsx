import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { Moon, Sun, Globe } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useTheme } from '@/context/ThemeContext'
import { useAuth } from '@/context/AuthContext'

export default function Navbar() {
  const { t, i18n } = useTranslation()
  const { theme, toggleTheme } = useTheme()
  const navigate = useNavigate()
  const { user, logout } = useAuth()

  const languages = [
    { code: 'uz', label: t('languages.uz') },
    { code: 'ru', label: t('languages.ru') },
    { code: 'en', label: t('languages.en') },
  ]

  const changeLanguage = (lng: string) => {
    i18n.changeLanguage(lng)
  }

  return (
    <nav className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
        <Link to="/" className="flex items-center space-x-2">
          <span className="text-xl font-bold tracking-tight">{t('common.appName')}</span>
        </Link>

        <div className="hidden md:flex items-center space-x-6">
          <Link
            to="/dashboard"
            className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            {t('nav.dashboard')}
          </Link>
          <Link
            to="/simulations"
            className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            {t('nav.simulations')}
          </Link>
        </div>

        <div className="flex items-center space-x-2">
          {/* Language switcher */}
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
                  onClick={() => changeLanguage(lang.code)}
                  className={i18n.language === lang.code ? 'bg-accent' : ''}
                >
                  {lang.label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Theme toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            aria-label={t('theme.toggle')}
          >
            {theme === 'dark' ? (
              <Sun className="h-4 w-4" />
            ) : (
              <Moon className="h-4 w-4" />
            )}
          </Button>

          {user ? (
            <>
              <span className="hidden text-sm text-muted-foreground sm:inline">{user.full_name}</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  logout()
                  navigate('/login')
                }}
              >
                {t('nav.logout')}
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" size="sm" onClick={() => navigate('/login')}>
                {t('nav.login')}
              </Button>
              <Button size="sm" onClick={() => navigate('/register')}>
                {t('nav.register')}
              </Button>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}