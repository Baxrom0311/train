import { CircleHelp, ClipboardList, GitBranch, MessageSquare, Siren, Sunset, type LucideIcon } from 'lucide-react'
import type { NodeType } from '@/lib/types'

const NODE_ICON: Record<NodeType, LucideIcon> = {
  message: MessageSquare,
  task: ClipboardList,
  incident: Siren,
  decision: GitBranch,
  day_end: Sunset,
}

/** YAML'dan noma'lum tur kelsa ham forma yiqilmasin. */
export const nodeIcon = (type: NodeType): LucideIcon => NODE_ICON[type] ?? CircleHelp
