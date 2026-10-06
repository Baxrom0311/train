export interface Company {
  id: string;
  name: string;
  logo_url: string;
  industry: string;
  description: string;
  website: string;
  is_verified: boolean;
}

export interface TaskDataset {
  title: string;
  headers: string[];
  rows: string[][];
}

export interface DownloadItem {
  name: string;
  size: string;
  type: string;
}

export interface Supervisor {
  name: string;
  role: string;
  department: string;
  avatar: string;
  audio_duration: string;
}

export interface TaskResourceFiles {
  task_type?: 'code' | 'report' | 'financial' | 'legal_audit';
  supervisor?: Supervisor;
  audio_transcript?: string;
  corporate_context?: string;
  deliverables?: string[];
  dataset?: TaskDataset;
  downloads?: DownloadItem[];
  model_explanation?: string;
}

export interface SimulationTask {
  id: string;
  order: number;
  title: string;
  briefing_text: string;
  instructions: string;
  template_data?: string;
  mentor_persona: string;
  model_answer?: string;
  rubric_criteria: { criterion: string; max_score: number }[];
  resource_files?: TaskResourceFiles;
}

export interface Simulation {
  id: string;
  slug: string;
  title: string;
  category: string;
  difficulty: string;
  estimated_hours: number;
  description: string;
  learning_outcomes: string[];
  company: Company;
  tasks?: SimulationTask[];
  task_count?: number;
}

export interface RubricItemFeedback {
  criterion: string;
  score: number;
  max_score: number;
  comment?: string;
}

export interface AIFeedback {
  total_score: number;
  passed: boolean;
  mentor_name: string;
  mentor_role: string;
  rubric_breakdown?: RubricItemFeedback[];
  rubric_scores?: RubricItemFeedback[];
  strengths?: string[];
  mistakes?: string[];
  best_practices?: string;
}

export interface SubmissionResponse {
  id: string;
  task_id: string;
  status: string;
  score: number;
  ai_feedback: AIFeedback;
  created_at: string;
}

export interface CertificateData {
  id: string;
  cert_uuid: string;
  user_name: string;
  simulation_title: string;
  company_name: string;
  average_score: number;
  issued_at: string;
  hmac_signature: string;
  public_verify_url: string;
}

export interface CaseCup {
  id: string;
  title: string;
  slug: string;
  host_company: string;
  company_logo?: string;
  sponsor_logo?: string;
  prize_pool: string;
  prize_distribution: { rank: string; prize: string }[];
  deadline: string;
  start_date: string;
  participants_count: number;
  status: 'active' | 'upcoming' | 'completed';
  difficulty: 'Junior' | 'Middle' | 'Advanced' | 'Barcha darajalar';
  category: string;
  description: string;
  tasks_count: number;
  rules: string[];
  stages: { stage: number; title: string; date: string }[];
  tags: string[];
}

export interface LeaderboardEntry {
  rank: number;
  user_name: string;
  university: string;
  score: number;
  completed_simulations: number;
  badges: string[];
  avatar_url?: string;
  solved_at?: string;
  category?: string;
  is_verified_talent?: boolean;
}

export interface CandidateProject {
  title: string;
  company: string;
  score: number;
  completed_at: string;
  certificate_uuid?: string;
}

export interface CandidateProfile {
  id: string;
  name: string;
  avatar_url?: string;
  email: string;
  phone: string;
  university: string;
  faculty: string;
  graduation_year: number;
  gpa: number;
  completed_simulations_count: number;
  avg_score: number;
  skills: string[];
  top_projects: CandidateProject[];
  is_open_to_work: boolean;
  is_vip: boolean;
  bio: string;
  location: string;
  preferred_roles: string[];
  badge_titles: string[];
}

export interface TalentOffer {
  id: string;
  candidate_id: string;
  candidate_name: string;
  company_name: string;
  position: string;
  salary_offer: string;
  message: string;
  status: 'sent' | 'viewed' | 'accepted' | 'rejected';
  created_at: string;
}

export interface UniversityMonthlyTrend {
  month: string;
  completions: number;
  avg_score: number;
}

export interface UniversityTopPerformer {
  name: string;
  course: number;
  faculty: string;
  score: number;
  cert_count: number;
  status: string;
}

export interface UniversityDepartmentStat {
  name: string;
  student_count: number;
  completion_rate: number;
  avg_score: number;
}

export interface UniversityStats {
  id: string;
  university_name: string;
  short_name: string;
  logo_url?: string;
  total_students: number;
  active_interns: number;
  completed_simulations: number;
  average_score: number;
  top_department: string;
  hiring_rate_percent: number;
  partner_companies_count: number;
  monthly_trend: UniversityMonthlyTrend[];
  top_performers: UniversityTopPerformer[];
  departments: UniversityDepartmentStat[];
}

