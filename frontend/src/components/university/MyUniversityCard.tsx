import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Check, GraduationCap } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'
import type { Affiliation, UniversityRef } from '@/lib/types'

const SELECT = 'h-10 min-w-0 flex-1 rounded-xl border border-input bg-background/60 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring'

/** Talabaning universiteti: ko'rish va o'zgartirish (CONTRACT.md §12.1). */
export default function MyUniversityCard() {
  const { t } = useTranslation()
  const [universities, setUniversities] = useState<UniversityRef[]>([])
  const [current, setCurrent] = useState<string | null | undefined>(undefined)
  const [selected, setSelected] = useState('')
  const [state, setState] = useState<'idle' | 'busy' | 'saved' | 'error'>('idle')

  useEffect(() => {
    Promise.all([api<UniversityRef[]>('/university/list'), api<Affiliation>('/users/me/university')])
      .then(([list, mine]) => {
        setUniversities(list)
        setCurrent(mine.university?.id ?? null)
        setSelected(mine.university?.id ?? '')
      })
      .catch(() => setState('error'))
  }, [])

  const save = async () => {
    setState('busy')
    try {
      const mine = await api<Affiliation>('/users/me/university', { method: 'PATCH', json: { university_id: selected || null } })
      setCurrent(mine.university?.id ?? null)
      setState('saved')
    } catch {
      setState('error')
    }
  }

  if (current === undefined && state !== 'error') return null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><GraduationCap className="h-5 w-5 text-primary" /> {t('dashboard.university.title')}</CardTitle>
        <CardDescription>{t('dashboard.university.hint')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex gap-2">
          <select className={SELECT} value={selected} aria-label={t('dashboard.university.title')}
            onChange={(e) => { setSelected(e.target.value); setState('idle') }}>
            <option value="">{t('dashboard.university.none')}</option>
            {universities.map((u) => <option key={u.id} value={u.id}>{u.name} — {u.city}</option>)}
          </select>
          <Button onClick={save} disabled={state === 'busy' || selected === (current ?? '')}>{t('dashboard.university.save')}</Button>
        </div>
        {state === 'saved' && <p className="flex items-center gap-1 text-sm text-success"><Check className="h-4 w-4" /> {t('dashboard.university.saved')}</p>}
        {state === 'error' && <p className="text-sm text-destructive">{t('common.error')}</p>}
      </CardContent>
    </Card>
  )
}
