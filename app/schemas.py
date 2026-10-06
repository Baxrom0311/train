from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

# ── User & Auth ────────────────────────────────────────────────────────────
class UserRegister(BaseModel):
    email: str = Field(..., min_length=5, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)
    university: Optional[str] = None
    university_id: Optional[str] = None
    role: Optional[str] = "student"

class UserLogin(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    role: str
    university: Optional[str] = None
    university_id: Optional[str] = None
    company_id: Optional[str] = None
    is_vip: bool = False
    vip_expires_at: Optional[datetime] = None
    mastery_level: int = 1
    elo_rating: int = 1000
    xp_points: int = 0
    adaptive_skill_profile: Optional[Dict[str, Any]] = None
    created_at: datetime

class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: UserOut

class RefreshTokenRequest(BaseModel):
    refresh_token: str


# ── University ─────────────────────────────────────────────────────────────
class UniversityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    city: str
    official_code: Optional[str] = None
    total_students: int = 0
    created_at: datetime

class UniversityCreate(BaseModel):
    name: str
    city: str = "Toshkent"
    official_code: Optional[str] = None
    total_students: int = 0

# ── Company ────────────────────────────────────────────────────────────────
class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    logo_url: Optional[str] = None
    industry: str
    description: Optional[str] = None
    website: Optional[str] = None
    is_verified: bool

# ── Tasks ──────────────────────────────────────────────────────────────────
class TaskCreate(BaseModel):
    order: Optional[int] = 1
    title: str = Field(..., min_length=3, max_length=255)
    briefing_text: str = Field(..., min_length=10)
    instructions: str = Field(..., min_length=10)
    resource_files: Optional[Any] = None
    template_data: Optional[str] = None
    rubric_criteria: Optional[List[Dict[str, Any]]] = None
    model_answer: Optional[str] = None
    mentor_persona: Optional[str] = "lead_engineer"

class TaskUpdate(BaseModel):
    order: Optional[int] = None
    title: Optional[str] = None
    briefing_text: Optional[str] = None
    instructions: Optional[str] = None
    resource_files: Optional[Any] = None
    template_data: Optional[str] = None
    rubric_criteria: Optional[List[Dict[str, Any]]] = None
    model_answer: Optional[str] = None
    mentor_persona: Optional[str] = None

class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    order: int
    title: str
    briefing_text: str
    instructions: str
    resource_files: Any = Field(default_factory=dict)
    template_data: Optional[str] = None
    rubric_criteria: List[Dict[str, Any]] = []
    model_answer: Optional[str] = None
    mentor_persona: str

# ── Simulation ─────────────────────────────────────────────────────────────
class SimulationCreate(BaseModel):
    slug: Optional[str] = None
    title: str = Field(..., min_length=3, max_length=255)
    company_id: Optional[str] = None
    category: str = Field(..., min_length=2, max_length=100)
    difficulty: str = "Beginner"
    estimated_hours: float = 4.0
    description: str = Field(..., min_length=10)
    learning_outcomes: List[str] = []
    is_published: bool = True
    is_case_cup: bool = False
    prize_pool: Optional[str] = None
    deadline: Optional[datetime] = None

class SimulationUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    difficulty: Optional[str] = None
    estimated_hours: Optional[float] = None
    description: Optional[str] = None
    learning_outcomes: Optional[List[str]] = None
    is_published: Optional[bool] = None
    is_case_cup: Optional[bool] = None
    prize_pool: Optional[str] = None
    deadline: Optional[datetime] = None

class SimulationListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    title: str
    category: str
    difficulty: str
    estimated_hours: float
    description: str
    learning_outcomes: List[str] = []
    company: CompanyOut
    task_count: int = 0
    is_case_cup: bool = False
    prize_pool: Optional[str] = None
    deadline: Optional[datetime] = None

class SimulationDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    title: str
    category: str
    difficulty: str
    estimated_hours: float
    description: str
    learning_outcomes: List[str] = []
    company: CompanyOut
    tasks: List[TaskOut] = []
    is_case_cup: bool = False
    prize_pool: Optional[str] = None
    deadline: Optional[datetime] = None

# ── Dynamic Adaptive Challenge ─────────────────────────────────────────────
class DynamicChallengeRequest(BaseModel):
    level: Optional[int] = None
    preferred_focus: Optional[str] = None # edge_cases, high_frequency_anomalies, anti_fraud, concurrency, zero_day_bugs, stress_scale, auto
    custom_constraints: Optional[Dict[str, Any]] = None

class DynamicChallengeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    simulation_id: str
    simulation_title: str
    company_name: str
    user_id: str
    level: int
    difficulty_label: str
    challenge_type: str
    title: str
    briefing: str
    instructions: str
    synthetic_dataset: Any = Field(default_factory=dict)
    starter_code: Optional[str] = None
    rubric_criteria: List[Dict[str, Any]] = []
    mentor_persona: str
    status: str
    current_elo: int
    target_elo_gain: int
    created_at: datetime

# ── Submission & AI Evaluation ─────────────────────────────────────────────
class SubmissionCreate(BaseModel):
    task_id: Optional[str] = None
    dynamic_challenge_id: Optional[str] = None
    simulation_id: str
    submitted_text: Optional[str] = None

class FeedbackRubricItem(BaseModel):
    criterion: str
    score: float
    max_score: float
    comment: str

class AIEvaluationFeedback(BaseModel):
    total_score: float
    passed: bool
    mentor_name: str
    mentor_role: str
    rubric_breakdown: List[FeedbackRubricItem] = []
    strengths: List[str] = []
    mistakes: List[str] = []
    best_practices_advice: str
    executive_summary: str
    adaptive_metrics: Optional[Dict[str, Any]] = None

class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: Optional[str] = None
    dynamic_challenge_id: Optional[str] = None
    simulation_id: str
    status: str
    score: float
    elo_change: Optional[int] = 0
    xp_earned: Optional[int] = 0
    new_elo: Optional[int] = None
    new_mastery_level: Optional[int] = None
    submitted_text: Optional[str] = None
    attachment_path: Optional[str] = None
    ai_feedback: Optional[Dict[str, Any]] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None

# ── Certificate ────────────────────────────────────────────────────────────
class CertificateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    cert_uuid: str
    user_name: str
    simulation_title: str
    company_name: str
    average_score: float
    issued_at: datetime
    hmac_signature: str
    public_verify_url: str

class CertificateVerifyOut(BaseModel):
    is_valid: bool
    cert_uuid: str
    student_name: str
    simulation_title: str
    company_name: str
    score: float
    issued_at: str
    verification_status: str
    issuer: str = "TryJob Verified Credential (Uzbekistan)"

# ── Case Cups ──────────────────────────────────────────────────────────────
class CaseCupLeaderboardItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank: int
    user_id: str
    user_name: str
    university: Optional[str] = "TATU"
    total_score: float
    submitted_at: datetime

class CaseCupLeaderboardResponse(BaseModel):
    simulation_id: str
    simulation_title: str
    prize_pool: Optional[str] = None
    deadline: Optional[datetime] = None
    total_participants: int
    leaderboard: List[CaseCupLeaderboardItem] = []

# ── Talent Hunt ────────────────────────────────────────────────────────────
class TalentCandidateOut(BaseModel):
    user_id: str
    full_name: str
    email: str
    university: Optional[str] = None
    completed_simulations: int
    average_score: float
    specialties: List[str] = []
    certificates_count: int
    is_vip: bool
    last_active: Optional[datetime] = None

class TalentOfferCreate(BaseModel):
    candidate_id: str
    simulation_id: Optional[str] = None
    position_title: str = Field(..., min_length=2, max_length=255)
    message: str = Field(..., min_length=5)

class TalentOfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    company_name: Optional[str] = None
    candidate_id: str
    candidate_name: Optional[str] = None
    simulation_id: Optional[str] = None
    position_title: str
    message: str
    status: str
    created_at: datetime

# ── University Portal ──────────────────────────────────────────────────────
class UniversityStudentStat(BaseModel):
    student_id: str
    full_name: str
    email: str
    completed_sims: int
    average_score: float
    has_offer: bool

class UniversityPortalStatsOut(BaseModel):
    university_id: Optional[str] = None
    university_name: str
    total_registered_students: int
    active_learners: int
    completed_simulations_count: int
    overall_average_score: float
    internship_ready_students_count: int # score >= 85
    top_specialties: Dict[str, int] = {}
    top_students: List[UniversityStudentStat] = []

# ── Billing & VIP ──────────────────────────────────────────────────────────
class VIPUpgradeRequest(BaseModel):
    plan_type: str = Field("vip_monthly", description="vip_monthly (99,000 UZS) or vip_yearly (890,000 UZS)")
    provider: str = Field("click", description="click, payme, or demo")
    amount: Optional[float] = None

class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    amount: float
    provider: str
    status: str
    plan_type: str
    created_at: datetime

class ClickWebhookRequest(BaseModel):
    click_trans_id: Any
    service_id: Optional[Any] = None
    click_paydoc_id: Optional[Any] = None
    merchant_trans_id: str # user_id or transaction_id
    amount: float
    action: int = 0
    error: int = 0
    error_note: Optional[str] = ""
    sign_time: Optional[str] = None
    sign_string: Optional[str] = None

class PaymeWebhookRequest(BaseModel):
    method: str
    params: Dict[str, Any]

class PaymentWebhookResponse(BaseModel):
    status: str
    message: str
    transaction_id: Optional[str] = None
    user_vip_status: Optional[bool] = None
