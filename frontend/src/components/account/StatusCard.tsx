import type { LucideIcon } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'

// Hisob sahifalarining yakuniy holati (yuborildi, tasdiqlandi, havola yaroqsiz) — bitta ko'rinish.
export default function StatusCard({ Icon, tone = 'brand', spin = false, title, children }: {
  Icon: LucideIcon
  tone?: 'brand' | 'danger'
  spin?: boolean
  title: string
  children: React.ReactNode
}) {
  return (
    <Card className="glass-strong w-full animate-rise">
      <CardContent role="status" className="flex flex-col items-center gap-4 p-8 text-center">
        <span className={cn('grid h-14 w-14 place-items-center rounded-2xl',
          tone === 'brand' ? 'bg-brand text-primary-foreground' : 'bg-destructive/12 text-destructive')}>
          <Icon className={cn('h-6 w-6', spin && 'animate-spin')} />
        </span>
        <h2 className="text-2xl font-extrabold">{title}</h2>
        {children}
      </CardContent>
    </Card>
  )
}
