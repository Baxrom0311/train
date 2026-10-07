import { cn } from '@/lib/utils'

export default function Initials({ name, className }: { name: string; className?: string }) {
  const letters = name.split(/\s+/).filter(Boolean).map((w) => w[0]).slice(0, 2).join('').toUpperCase()
  return (
    <span className={cn('bg-brand grid h-11 w-11 shrink-0 place-items-center rounded-2xl text-sm font-extrabold text-primary-foreground', className)}>
      {letters || '?'}
    </span>
  )
}
