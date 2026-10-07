// Talaba analitikasi grafiklari (CONTRACT.md §17.3): SVG, kutubxonasiz.
import { useEffect, useId, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { formatDayMonth } from '@/lib/time'
import { cn } from '@/lib/utils'

const PAD = { left: 30, right: 14, top: 14, bottom: 26 }
const HEIGHT = 220
const TICKS = [0, 25, 50, 75, 100]
const MAX_LABELS = 8

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(0)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const ro = new ResizeObserver(([entry]) => setWidth(Math.round(entry.contentRect.width)))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  return [ref, width] as const
}

export interface ChartPoint {
  id: string
  title: string
  date: string
  score: number
}

/** Ball chizig'i: har nuqta — tugatilgan Run, bosilsa hisobotiga o'tadi. */
export function ScoreChart({ points, label }: { points: ChartPoint[]; label: string }) {
  const [ref, width] = useWidth<HTMLDivElement>()
  const [active, setActive] = useState<number | null>(null)
  const gradient = useId()

  const innerW = Math.max(0, width - PAD.left - PAD.right)
  const innerH = HEIGHT - PAD.top - PAD.bottom
  const x = (i: number) => PAD.left + (points.length === 1 ? innerW / 2 : (innerW * i) / (points.length - 1))
  const y = (v: number) => PAD.top + innerH * (1 - Math.min(100, Math.max(0, v)) / 100)
  const coords = points.map((p, i) => [x(i), y(p.score)] as const)
  const line = coords.map(([cx, cy], i) => `${i ? 'L' : 'M'}${cx},${cy}`).join(' ')
  const area = coords.length > 1 ? `${line} L${coords[coords.length - 1][0]},${y(0)} L${coords[0][0]},${y(0)} Z` : ''
  // ko'p nuqtada sana yozuvlari ustma-ust tushmasin
  const every = Math.ceil(points.length / MAX_LABELS)
  const shown = active === null ? null : points[active]

  return (
    <div ref={ref} className="relative w-full" onMouseLeave={() => setActive(null)}>
      {width > 0 && (
        <svg width={width} height={HEIGHT} role="img" aria-label={label} className="block overflow-visible">
          <defs>
            <linearGradient id={gradient} x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.35} />
              <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
            </linearGradient>
          </defs>
          {TICKS.map((v) => (
            <g key={v}>
              <line x1={PAD.left} x2={width - PAD.right} y1={y(v)} y2={y(v)}
                stroke="hsl(var(--border))" strokeDasharray={v ? '3 4' : undefined} />
              <text x={PAD.left - 8} y={y(v)} dy="0.32em" textAnchor="end"
                className="fill-muted-foreground text-[10px] tabular-nums">{v}</text>
            </g>
          ))}
          {area && <path d={area} fill={`url(#${gradient})`} />}
          {coords.length > 1 && (
            <path d={line} fill="none" stroke="hsl(var(--primary))" strokeWidth={2.5}
              strokeLinejoin="round" strokeLinecap="round" />
          )}
          {points.map((p, i) => (
            (i % every === 0 || i === points.length - 1) && (
              <text key={`d${p.id}`} x={coords[i][0]} y={HEIGHT - 6} textAnchor="middle"
                className="fill-muted-foreground text-[10px] tabular-nums">{formatDayMonth(p.date)}</text>
            )
          ))}
          {points.map((p, i) => (
            <Link key={p.id} to={`/runs/${p.id}/report`} aria-label={`${p.title}: ${Math.round(p.score)}`}
              onMouseEnter={() => setActive(i)} onFocus={() => setActive(i)} onBlur={() => setActive(null)}
              className="outline-none">
              {/* katta ko'rinmas nishon — barmoq bilan bosish oson bo'lsin */}
              <circle cx={coords[i][0]} cy={coords[i][1]} r={14} fill="transparent" />
              <circle cx={coords[i][0]} cy={coords[i][1]} r={active === i ? 6.5 : 4.5}
                fill="hsl(var(--background))" stroke="hsl(var(--primary))" strokeWidth={2.5}
                className="transition-[r] duration-150" />
            </Link>
          ))}
        </svg>
      )}
      {shown && active !== null && (
        <div role="tooltip"
          className="glass-strong pointer-events-none absolute z-10 w-max max-w-[14rem] -translate-x-1/2 -translate-y-full rounded-xl px-3 py-2 text-xs shadow-lg"
          style={{ left: Math.min(Math.max(coords[active][0], 80), width - 80), top: coords[active][1] - 12 }}>
          <p className="truncate font-semibold">{shown.title}</p>
          <p className="text-muted-foreground">
            {formatDayMonth(shown.date)} · <span className="font-bold text-foreground tabular-nums">{Math.round(shown.score)}</span>
          </p>
        </div>
      )}
    </div>
  )
}

/** Mini-chiziq (0–100): kompetensiya qatorlari uchun. */
export function Sparkline({ values, className }: { values: number[]; className?: string }) {
  const W = 88
  const H = 28
  const pad = 3
  const x = (i: number) => (values.length === 1 ? W / 2 : pad + ((W - 2 * pad) * i) / (values.length - 1))
  const y = (v: number) => pad + (H - 2 * pad) * (1 - Math.min(100, Math.max(0, v)) / 100)
  const d = values.map((v, i) => `${i ? 'L' : 'M'}${x(i)},${y(v)}`).join(' ')
  const last = values.length - 1
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} aria-hidden className={cn('shrink-0', className)}>
      <line x1={0} x2={W} y1={y(50)} y2={y(50)} stroke="hsl(var(--border))" strokeDasharray="2 3" />
      {values.length > 1 && (
        <path d={d} fill="none" stroke="hsl(var(--primary))" strokeWidth={1.75} strokeLinejoin="round" strokeLinecap="round" />
      )}
      <circle cx={x(last)} cy={y(values[last])} r={2.75} fill="hsl(var(--primary))" />
    </svg>
  )
}
