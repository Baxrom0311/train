import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

/** Bir nechta variantdan bittasini tanlash (davr tanlovi va h.k.); `busy` — yuklanish belgisi. */
export function Segmented<T extends string | number | null>({ options, value, onChange, label, busy = false }: {
  options: { value: T; label: string }[]
  value: T
  onChange: (value: T) => void
  label: string
  busy?: boolean
}) {
  return (
    <div role="radiogroup" aria-label={label} className="glass flex items-center gap-1 rounded-xl p-1">
      {options.map((o) => (
        <button key={String(o.value)} type="button" role="radio" aria-checked={value === o.value} onClick={() => onChange(o.value)}
          className={cn(
            'rounded-lg px-3 py-1.5 text-sm font-medium transition-colors',
            value === o.value ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:bg-muted/60',
          )}>
          {o.label}
        </button>
      ))}
      <Loader2 className={cn('mx-1 h-4 w-4 animate-spin text-muted-foreground', !busy && 'invisible')} />
    </div>
  )
}
