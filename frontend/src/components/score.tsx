import { useTranslation } from 'react-i18next'

/** 0–100 ball: halqa (yashil ≥75, asosiy rang ≥50, qizil <50). */
export function ScoreRing({ value, size = 56 }: { value: number; size?: number }) {
  const r = (size - 6) / 2
  const c = 2 * Math.PI * r
  const tone = value >= 75 ? 'hsl(var(--success))' : value >= 50 ? 'hsl(var(--primary))' : 'hsl(var(--destructive))'
  return (
    <div className="relative grid shrink-0 place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="hsl(var(--muted))" strokeWidth={5} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={tone} strokeWidth={5} strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - Math.min(100, value) / 100)}
          style={{ transition: 'stroke-dashoffset 1s cubic-bezier(0.22, 1, 0.36, 1)' }} />
      </svg>
      <span className="absolute text-sm font-extrabold tabular-nums">{Math.round(value)}</span>
    </div>
  )
}

/** Kompetensiyalar bo'yicha chiziqlar; `compact` — kartalardagi ingichka variant. */
export function CompetencyBars({ scores, compact = false }: { scores: Record<string, number>; compact?: boolean }) {
  const { t } = useTranslation()
  return (
    <div className={compact ? 'space-y-1.5' : 'space-y-2'}>
      {Object.entries(scores).map(([key, value]) => (
        <div key={key} className="space-y-1">
          <div className={`flex justify-between ${compact ? 'text-xs text-muted-foreground' : 'text-sm'}`}>
            <span>{t(`competency.${key}`)}</span>
            <span className="font-medium tabular-nums text-foreground">{Math.round(value)}</span>
          </div>
          <div className={`${compact ? 'h-1.5' : 'h-2.5'} overflow-hidden rounded-full bg-muted`}>
            <div className="bg-brand h-full rounded-full transition-[width] duration-700" style={{ width: `${Math.min(100, value)}%` }} />
          </div>
        </div>
      ))}
    </div>
  )
}
