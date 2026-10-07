import { BarChart3, Code2, HeartHandshake, Landmark, Megaphone, type LucideIcon } from 'lucide-react'
import type { Sector } from '@/lib/types'

/** Soha bo'yicha karta "muqovasi": ikonka va rang (katalog va landing). */
export const SECTOR_ART: Record<Sector, { Icon: LucideIcon; glow: string }> = {
  IT: { Icon: Code2, glow: 'from-emerald-400/50 via-teal-300/30 to-transparent dark:from-violet-500/45 dark:via-indigo-500/25' },
  Banking: { Icon: Landmark, glow: 'from-sky-400/45 via-emerald-300/30 to-transparent dark:from-cyan-400/40 dark:via-indigo-500/25' },
  Marketing: { Icon: Megaphone, glow: 'from-rose-400/40 via-fuchsia-300/25 to-transparent dark:from-fuchsia-500/40 dark:via-violet-500/25' },
  Data: { Icon: BarChart3, glow: 'from-cyan-400/45 via-sky-300/30 to-transparent dark:from-sky-400/40 dark:via-violet-500/25' },
  HR: { Icon: HeartHandshake, glow: 'from-teal-400/45 via-sky-200/30 to-transparent dark:from-teal-400/35 dark:via-indigo-500/25' },
}
