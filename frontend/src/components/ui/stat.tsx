import type { LucideIcon } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'

/** Statistika kartasi: ikon, katta raqam, izoh; `accent` — qiymat > 0 bo'lsa porlaydi. */
export function Stat({ Icon, label, value, accent = false }: {
  Icon: LucideIcon
  label: string
  value: number | string
  accent?: boolean
}) {
  return (
    <Card className={cn(accent && typeof value === 'number' && value > 0 && 'glow-ring')}>
      <CardContent className="flex items-center gap-3 p-4">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary/12 text-primary"><Icon className="h-5 w-5" /></span>
        <div className="min-w-0">
          <p className="text-2xl font-extrabold tabular-nums">{value}</p>
          <p className="text-xs text-muted-foreground">{label}</p>
        </div>
      </CardContent>
    </Card>
  )
}
