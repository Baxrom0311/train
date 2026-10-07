import { cn } from '@/lib/utils'
import type { Persona } from '@/lib/types'

export default function Avatar({ persona, active = false, size = 'md' }: { persona: Persona; active?: boolean; size?: 'sm' | 'md' }) {
  const initials = persona.name.split(' ').map((w) => w[0]).slice(0, 2).join('')
  return (
    <span className={cn(
      'grid place-items-center rounded-full font-bold',
      size === 'md' ? 'h-9 w-9 text-xs' : 'h-7 w-7 text-[10px]',
      active || persona.kind === 'mentor' ? 'bg-brand text-primary-foreground' : 'bg-secondary text-secondary-foreground',
      active && 'ring-2 ring-primary/40 ring-offset-2 ring-offset-background',
    )}>
      {initials}
    </span>
  )
}
