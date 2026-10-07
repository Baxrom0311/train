// Backend API sxemalari (backend/app/api/runs.py, scenarios.py, files.py).

// backend/app/models/enums.py Sector bilan bir xil tartibda
export const SECTORS = ['IT', 'Banking', 'Marketing', 'Data', 'HR'] as const
export type Sector = (typeof SECTORS)[number]
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
  org_type: 'company' | 'university' | null
  org_id: string | null
  permissions: string[]
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
  last_checks: CheckResults | null
}

/** Yashirin testlar natijasi (CONTRACT.md §19.4) — test kodi emas, faqat nomlar. */
export interface CheckResults {
  status: 'ok' | 'error' | 'timeout' | 'no_code'
  passed: number
  total: number
  failed: string[]
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
  // mentorning o'zi boshlagan xabari (CONTRACT.md §9.13)
  purpose: 'review' | 'nudge' | null
  node_id: string | null
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
  checks?: CheckResults | null
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

// Talent Hunt (backend/app/api/talent_hunt.py, CONTRACT.md §10)

export type Competency =
  | 'technical' | 'communication' | 'prioritization' | 'time_management' | 'stress_handling' | 'initiative'
export const COMPETENCIES: Competency[] = [
  'technical', 'communication', 'prioritization', 'time_management', 'stress_handling', 'initiative',
]

export interface Visibility {
  is_open_to_work: boolean
  hidden_from_company_ids: string[]
}

export interface CandidateCard {
  id: string
  full_name: string
  overall_score: number | null
  runs_completed: number
  sectors: Sector[]
  top_competencies: Record<string, number>
  last_completed_at: string | null
}

export interface CandidateRun {
  scenario_title: string
  company_name: string
  sector: Sector
  completed_at: string
  overall_score: number | null
  competency_scores: Record<string, number>
  strengths: string[]
}

export interface CandidateProfile extends CandidateCard {
  competencies: Record<string, number>
  runs: CandidateRun[]
}

export interface CandidatePage {
  items: CandidateCard[]
  total: number
}

export type OfferStatus = 'sent' | 'viewed' | 'responded'
export type OfferResponse = 'accepted' | 'declined'

export interface TalentOffer {
  id: string
  company_id: string
  candidate_user_id: string
  position_title: string
  message: string
  status: OfferStatus
  response: OfferResponse | null
  response_note: string | null
  respond_due_at: string | null
  responded_at: string | null
  created_at: string
}

export interface SentOffer extends TalentOffer {
  candidate_name: string
  candidate_email: string | null
}

export interface ReceivedOffer extends TalentOffer {
  company_name: string
  company_industry: string
}

// Admin va invoice'lar (backend/app/api/admin.py, billing.py, CONTRACT.md §11)

export type OrgType = 'company' | 'university'
export type InvoiceStatus = 'pending' | 'paid' | 'cancelled'

export interface Org {
  id: string
  org_type: OrgType
  name: string
  detail: string
  contact_email: string
  is_verified: boolean
  verified_at: string | null
  created_at: string
  owner_name: string | null
  owner_email: string | null
}

export interface OrgList {
  companies: Org[]
  universities: Org[]
}

export interface AdminStats {
  pending_companies: number
  pending_universities: number
  verified_companies: number
  verified_universities: number
  invoices_pending: number
}

export interface Invoice {
  id: string
  payer_type: OrgType
  payer_id: string
  payer_name: string | null
  /** Decimal — JSON'da satr ("2500000.50") */
  amount: string
  currency: 'UZS' | 'USD'
  status: InvoiceStatus
  paid_marked_at: string | null
  notes: string | null
  created_at: string
}

// Universitet portali (backend/app/api/university_portal.py, CONTRACT.md §12)

export interface UniversityRef {
  id: string
  name: string
  city: string
}

export interface StudentRow extends CandidateCard {
  email: string
  joined_at: string | null
  runs_in_progress: number
}

export interface InProgressRun {
  scenario_title: string
  sector: Sector
  status: RunStatus
  ends_at: string
}

export interface StudentDetail extends StudentRow {
  competencies: Record<string, number>
  runs: CandidateRun[]
  in_progress: InProgressRun[]
}

export interface StudentPage {
  items: StudentRow[]
  total: number
}

export interface SectorStat {
  sector: Sector
  students: number
  avg_score: number | null
}

export interface UniversityOverview {
  university: UniversityRef
  students_total: number
  students_with_results: number
  runs_completed: number
  runs_in_progress: number
  avg_score: number | null
  sectors: SectorStat[]
  competencies: Record<string, number>
  top_students: StudentRow[]
}

export interface Affiliation {
  university: UniversityRef | null
}

// Sertifikat va portfolio (backend/app/api/credentials.py, CONTRACT.md §13)

export interface CertificatePublic {
  code: string
  status: 'valid' | 'revoked'
  holder_name: string
  scenario_title: string
  company_name: string
  sector: Sector
  difficulty: string
  duration_days: number
  completed_at: string
  issued_at: string
  overall_score: number | null
  competency_scores: Record<string, number>
  revoked_at: string | null
  revoked_reason: string | null
}

export interface Certificate extends CertificatePublic {
  run_id: string
}

export interface PortfolioLink {
  label: string
  url: string
}

export interface PortfolioSettings {
  slug: string
  is_public: boolean
  headline: string
  about: string
  links: PortfolioLink[]
  exists: boolean
}

export interface PortfolioPublic {
  slug: string
  full_name: string
  headline: string
  about: string
  links: PortfolioLink[]
  university: { name: string; city: string } | null
  overall_score: number | null
  competencies: Record<string, number>
  sectors: Sector[]
  certificates: CertificatePublic[]
}

export interface ShowcaseSlot {
  at: string
  type: NodeType
  title: string | null
}

export interface ShowcaseScenario {
  slug: string
  title: string
  sector: Sector
  company_name: string
  difficulty: string
  duration_days: number
  tasks: number
  mentor: { name: string; role: string } | null
  day1: ShowcaseSlot[]
}

export interface Showcase {
  stats: { scenarios: number; sectors: number; completed_runs: number }
  scenarios: ShowcaseScenario[]
}

// Bildirishnomalar (backend/app/api/notifications.py, CONTRACT.md §15)

export type NotificationKind =
  | 'task_delivered' | 'deadline_soon' | 'mentor_review' | 'report_ready' | 'offer_received' | 'offer_responded'

export interface AppNotification {
  id: string
  kind: NotificationKind
  params: Record<string, string | number | boolean | null>
  link: string
  created_at: string
  read_at: string | null
}

export interface NotificationPage {
  items: AppNotification[]
  unread: number
}

export interface NotificationSettings {
  email_enabled: boolean
  email_kinds: NotificationKind[]
  available: NotificationKind[]
}

// Talaba analitikasi (backend/app/api/analytics.py, CONTRACT.md §17)

export type Trend = 'up' | 'down' | 'flat' | 'new'

export interface AnalyticsPoint {
  run_id: string
  scenario_title: string
  sector: Sector
  completed_at: string
  overall_score: number | null
  on_time_rate: number | null
  competency_scores: Partial<Record<Competency, number>>
}

export interface CompetencyTrend {
  key: Competency
  current: number
  first: number
  delta: number | null
  trend: Trend
  values: number[]
}

export interface Recommendation {
  scenario_id: string
  title: string
  sector: Sector
  company_name: string
  duration_days: number
  difficulty: string
  practices: Partial<Record<Competency, number>>
}

export interface StudentAnalytics {
  summary: {
    completed: number
    in_progress: number
    avg_score: number | null
    best_score: number | null
    on_time_rate: number | null
    certificates: number
  }
  timeline: AnalyticsPoint[]
  competencies: CompetencyTrend[]
  sectors: { sector: Sector; runs: number; avg_score: number | null }[]
  focus: { key: Competency; current: number; trend: Trend }[]
  improvements: string[]
  recommendations: Recommendation[]
}
