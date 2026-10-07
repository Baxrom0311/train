import { useTranslation } from 'react-i18next'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from './Badge'
import { Clock, Search } from 'lucide-react'

interface SimCard {
  key: string
  titleKey: string
  companyKey: string
  categoryKey: string
  durationKey: string
  difficultyKey: string
  descriptionKey: string
}

const simCards: SimCard[] = [
  {
    key: 'card1',
    titleKey: 'simulations.mockCards.card1.title',
    companyKey: 'simulations.mockCards.card1.company',
    categoryKey: 'simulations.mockCards.card1.category',
    durationKey: 'simulations.mockCards.card1.duration',
    difficultyKey: 'simulations.mockCards.card1.difficulty',
    descriptionKey: 'simulations.mockCards.card1.description',
  },
  {
    key: 'card2',
    titleKey: 'simulations.mockCards.card2.title',
    companyKey: 'simulations.mockCards.card2.company',
    categoryKey: 'simulations.mockCards.card2.category',
    durationKey: 'simulations.mockCards.card2.duration',
    difficultyKey: 'simulations.mockCards.card2.difficulty',
    descriptionKey: 'simulations.mockCards.card2.description',
  },
  {
    key: 'card3',
    titleKey: 'simulations.mockCards.card3.title',
    companyKey: 'simulations.mockCards.card3.company',
    categoryKey: 'simulations.mockCards.card3.category',
    durationKey: 'simulations.mockCards.card3.duration',
    difficultyKey: 'simulations.mockCards.card3.difficulty',
    descriptionKey: 'simulations.mockCards.card3.description',
  },
  {
    key: 'card4',
    titleKey: 'simulations.mockCards.card4.title',
    companyKey: 'simulations.mockCards.card4.company',
    categoryKey: 'simulations.mockCards.card4.category',
    durationKey: 'simulations.mockCards.card4.duration',
    difficultyKey: 'simulations.mockCards.card4.difficulty',
    descriptionKey: 'simulations.mockCards.card4.description',
  },
]

export default function SimulationsPage() {
  const { t } = useTranslation()

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">{t('simulations.title')}</h1>
        <p className="text-muted-foreground mt-2">{t('simulations.subtitle')}</p>
      </div>

      {/* Search */}
      <div className="flex items-center space-x-2 mb-6">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder={t('simulations.search')}
          />
        </div>
      </div>

      {/* Cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-4 gap-4">
        {simCards.map((card) => (
          <Card key={card.key} className="flex flex-col hover:shadow-md transition-shadow">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between gap-2">
                <CardTitle className="text-base leading-snug">{t(card.titleKey)}</CardTitle>
              </div>
              <CardDescription className="text-xs font-medium">
                {t(card.companyKey)}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex-1 space-y-3">
              <p className="text-sm text-muted-foreground">{t(card.descriptionKey)}</p>
              <div className="flex flex-wrap gap-2">
                <Badge variant="secondary">{t(card.categoryKey)}</Badge>
                <Badge variant="outline">{t(card.difficultyKey)}</Badge>
              </div>
              <div className="flex items-center text-xs text-muted-foreground">
                <Clock className="h-3 w-3 mr-1" />
                {t(card.durationKey)}
              </div>
            </CardContent>
            <CardFooter className="pt-3 flex gap-2">
              <Button size="sm" className="flex-1">{t('simulations.startSim')}</Button>
              <Button size="sm" variant="outline" className="flex-1">{t('simulations.viewDetails')}</Button>
            </CardFooter>
          </Card>
        ))}
      </div>
    </div>
  )
}