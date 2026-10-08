// Kompaniya hisoboti bo'limlari uchun umumiy kichik yordamchilar (CONTRACT.md §20, §27).
import { useState } from 'react'
import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'
import { Download, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { download } from '@/lib/api'
import { cn } from '@/lib/utils'

export const pct = (v: number | null) => (v === null ? '—' : `${Math.round(v)}%`)

/** Soatlarni o'qiladigan ko'rinishda: "1 soatdan kam", "5 soat", "3 kun". */
export function hours(value: number | null, t: TFunction): string {
  if (value === null) return '—'
  if (value < 1) return t('companyReport.lessThanHour')
  if (value < 48) return t('companyReport.hours', { count: Math.round(value) })
  return t('companyReport.days', { count: Math.round(value / 24) })
}

export function CsvButton({ path, name, label }: { path: string; name: string; label: string }) {
  const { t } = useTranslation()
  const [state, setState] = useState<'idle' | 'busy' | 'error'>('idle')
  const run = () => {
    setState('busy')
    download(path, name).then(() => setState('idle'), () => setState('error'))
  }
  return (
    <Button variant="outline" size="sm" onClick={run} disabled={state === 'busy'} title={state === 'error' ? t('common.error') : undefined}
      className={cn(state === 'error' && 'border-destructive text-destructive')}>
      {state === 'busy' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
      {label}
    </Button>
  )
}
