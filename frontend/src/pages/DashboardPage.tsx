import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { BarChart3, BookOpen, Star, Trophy } from 'lucide-react'

export default function DashboardPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const stats = [
    {
      title: t('dashboard.stats.completedSims'),
      value: '0',
      icon: <BookOpen className="h-4 w-4 text-muted-foreground" />,
    },
    {
      title: t('dashboard.stats.activeSims'),
      value: '0',
      icon: <BarChart3 className="h-4 w-4 text-muted-foreground" />,
    },
    {
      title: t('dashboard.stats.totalScore'),
      value: '0',
      icon: <Star className="h-4 w-4 text-muted-foreground" />,
    },
    {
      title: t('dashboard.stats.rank'),
      value: '—',
      icon: <Trophy className="h-4 w-4 text-muted-foreground" />,
    },
  ]

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">{t('dashboard.welcome')}</h1>
        <p className="text-muted-foreground mt-2">{t('dashboard.welcomeSubtitle')}</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {stats.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
              {stat.icon}
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent activity */}
        <Card>
          <CardHeader>
            <CardTitle>{t('dashboard.recentActivity')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <p className="text-muted-foreground text-sm">{t('dashboard.noActivity')}</p>
              <Button
                variant="link"
                className="mt-2"
                onClick={() => navigate('/simulations')}
              >
                {t('dashboard.startFirst')}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Quick actions */}
        <Card>
          <CardHeader>
            <CardTitle>{t('dashboard.quickActions')}</CardTitle>
            <CardDescription>{t('dashboard.welcomeSubtitle')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button
              className="w-full"
              onClick={() => navigate('/simulations')}
            >
              {t('dashboard.browseSimulations')}
            </Button>
            <Button
              variant="outline"
              className="w-full"
              onClick={() => navigate('/profile')}
            >
              {t('dashboard.viewProfile')}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}