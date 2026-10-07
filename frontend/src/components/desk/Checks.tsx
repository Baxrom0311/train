// Yashirin testlar natijasi (CONTRACT.md §19.5): "Avtomatik testlar: 5/7" va yiqilgan test nomlari.
import { useTranslation } from 'react-i18next'
import { CircleCheck, CircleX, FlaskConical } from 'lucide-react'
import type { CheckResults } from '@/lib/types'
import { cn } from '@/lib/utils'

const tone = (c: CheckResults) =>
  c.status === 'ok' && c.passed === c.total ? 'text-success' : c.passed === 0 ? 'text-destructive' : 'text-primary'

/** Topshiriq tafsilotidagi to'liq ko'rinish. */
export function ChecksPanel({ checks }: { checks: CheckResults }) {
  const { t } = useTranslation()
  const pct = checks.total ? (100 * checks.passed) / checks.total : 0
  return (
    <div className="space-y-2 rounded-xl border bg-background/40 p-3">
      <div className="flex items-center gap-2">
        <FlaskConical className={cn('h-4 w-4', tone(checks))} />
        <span className="font-semibold">{t('checks.title')}</span>
        <span className={cn('ml-auto font-bold tabular-nums', tone(checks))}>{checks.passed}/{checks.total}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
        <div className={cn('h-full rounded-full', checks.passed === checks.total ? 'bg-success' : 'bg-brand')} style={{ width: `${pct}%` }} />
      </div>
      {checks.status !== 'ok' && <p className="text-xs text-muted-foreground">{t(`checks.status.${checks.status}`)}</p>}
      {checks.status === 'ok' && checks.failed.length > 0 && (
        <ul className="space-y-1 text-xs">
          {checks.failed.map((name) => (
            <li key={name} className="flex items-center gap-1.5 font-mono text-muted-foreground">
              <CircleX className="h-3.5 w-3.5 shrink-0 text-destructive" /> {name}
            </li>
          ))}
        </ul>
      )}
      {checks.status === 'ok' && checks.failed.length === 0 && (
        <p className="flex items-center gap-1.5 text-xs text-success"><CircleCheck className="h-3.5 w-3.5" /> {t('checks.allPassed')}</p>
      )}
    </div>
  )
}

/** Hisobot jadvalidagi ixcham belgi. */
export function ChecksBadge({ checks }: { checks: CheckResults }) {
  const { t } = useTranslation()
  return (
    <span title={t('checks.title')} className={cn('inline-flex items-center gap-1 text-xs font-semibold tabular-nums', tone(checks))}>
      <FlaskConical className="h-3 w-3" /> {checks.passed}/{checks.total}
    </span>
  )
}
