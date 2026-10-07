import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { BarChart3, BookOpen } from 'lucide-react'
import { Badge } from './Badge'
import { useAuth } from '@/context/AuthContext'
import { api } from '@/lib/api'
import { formatDateTime } from '@/lib/time'
import type { RunSummary } from '@/lib/types'

export default function DashboardPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [runs, setRuns] = useState<RunSummary[]>([])

  useEffect(() => {
    if (user) api<RunSummary[]>('/runs/my').then(setRuns).catch(() => setRuns([]))
  }, [user])

  const stats = [
    {
      title: t('dashboard.stats.completedSims'),
      value: runs.filter((r) => r.status === 'completed').length,
      icon: <BookOpen className="h-4 w-4 text-muted-foreground" />,
    },
    {
      title: t('dashboard.stats.activeSims'),
      value: runs.filter((r) => r.status === 'active' || r.status === 'scheduled').length,
      icon: <BarChart3 className="h-4 w-4 text-muted-foreground" />,
    },
  ]

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">
          {user ? t('dashboard.welcomeName', { name: user.full_name }) : t('dashboard.welcome')}
        </h1>
        <p className="text-muted-foreground mt-2">{t('dashboard.welcomeSubtitle')}</p>
      </div>

      {user && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
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
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>{t('dashboard.recentActivity')}</CardTitle>
          </CardHeader>
          <CardContent>
            {runs.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <p className="text-muted-foreground text-sm">{t('dashboard.noActivity')}</p>
                <Button variant="link" className="mt-2" onClick={() => navigate('/simulations')}>
                  {t('dashboard.startFirst')}
                </Button>
              </div>
            ) : (
              <ul className="divide-y text-sm">
                {runs.slice(0, 5).map((r) => {
                  const open = r.status === 'active' || r.status === 'scheduled'
                  return (
                    <li key={r.id} className="flex items-center justify-between gap-2 py-2">
                      <Link to={open ? `/runs/${r.id}` : `/runs/${r.id}/report`} className="min-w-0 hover:underline">
                        <p className="truncate font-medium">{r.scenario.title}</p>
                        <p className="text-xs text-muted-foreground">{formatDateTime(r.start_at)}</p>
                      </Link>
                      <Badge variant="outline">{t(`run.status.${r.status}`)}</Badge>
                    </li>
                  )
                })}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t('dashboard.quickActions')}</CardTitle>
            <CardDescription>{t('catalog.subtitle')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button className="w-full" onClick={() => navigate('/simulations')}>
              {t('dashboard.browseSimulations')}
            </Button>
            {!user && (
              <Button variant="outline" className="w-full" onClick={() => navigate('/register')}>
                {t('nav.register')}
              </Button>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
