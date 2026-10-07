// Backend API sxemalari (backend/app/api/runs.py, scenarios.py, files.py).

export type Sector = 'IT' | 'Banking'
export type RunStatus = 'scheduled' | 'active' | 'completed' | 'expired' | 'abandoned'
export type NodeType = 'message' | 'task' | 'incident' | 'decision' | 'day_end'
export type EventStatus = 'pending' | 'delivered' | 'submitted' | 'missed' | 'skipped'
export type EvalStatus = 'pending' | 'queued_retry' | 'completed' | 'failed'
export type AnswerType = 'text' | 'code' | 'link' | 'file'

export interface Me {
  id: string
  email: string
  full_name: string
  role: string
}

export interface Persona {
  key: string
  name: string
  role: string
  kind: 'colleague' | 'mentor'
}

export interface Scenario {
  id: string
  slug: string
  title: string
  sector: Sector
  company_name: string
  difficulty: string
  duration_days: number
  version: number
}

export interface ScenarioBrief {
  id: string
  slug: string
  title: string
  sector: Sector
  company_name: string
  duration_days: number
}

export interface RunSummary {
  id: string
  status: RunStatus
  start_at: string
  ends_at: string
  scenario: ScenarioBrief
}

export interface RunEvent {
  node_id: string
  type: NodeType
  from_persona: string | null
  brief: string
  attachments: { key: string; title: string }[]
  answer_types: AnswerType[]
  options: { key: string; label: string }[]
  status: EventStatus
  delivered_at: string | null
  due_at: string | null
  choice: string | null
  attempts_used: number
  max_attempts: number
  last_score: number | null
  last_feedback: string | null
  last_eval_status: EvalStatus | null
}

export interface RunDetail extends RunSummary {
  now: string
  local_time: string
  is_work_time: boolean
  personas: Persona[]
  events: RunEvent[]
}

export interface RunCreated {
  run: RunDetail
  warning: string | null
  day1_ends_at: string
}

export interface SubmissionResult {
  submission_id: string
  attempt: number
  late: boolean
  ai_eval_status: EvalStatus
  score: number | null
  run: RunDetail
}

export interface HintResult {
  hint: string
  hints_used: number
  hints_left: number
  penalty: number
}

export interface ChatMessage {
  id: string
  persona_key: string
  sender: 'student' | 'persona' | 'system'
  content_type: string
  body: string
  file_id: string | null
  link_url: string | null
  generated: boolean
  created_at: string
}

export interface DocumentOut {
  key: string
  title: string
  content: string
}

export interface UploadedFile {
  id: string
  original_name: string
  mime: string
  size_bytes: number
}

export interface TaskResult {
  node_id: string
  type: NodeType
  title: string
  day: number
  status: EventStatus
  score: number | null
  attempts: number
  late: boolean
}

export interface DayReport {
  day: number
  tasks: TaskResult[]
  average_score: number | null
  on_time_rate: number | null
  summary: { strengths: string[]; improvements: string[]; advice: string } | null
}

export interface FinalReport {
  incomplete: boolean
  certificate: boolean
  overall_score: number | null
  on_time_rate: number | null
  competency_scores: Record<string, number>
  tasks: TaskResult[]
  summary: { summary: string; strengths: string[]; improvements: string[] } | null
}

export interface RunReport {
  run_id: string
  status: RunStatus
  days: DayReport[]
  final: FinalReport | null
  competency_scores: Record<string, number> | null
  final_pending: boolean
}
