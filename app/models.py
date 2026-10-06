import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def get_utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class University(Base):
    __tablename__ = "universities"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    name = Column(String(255), nullable=False, unique=True)
    city = Column(String(100), default="Toshkent")
    official_code = Column(String(50), unique=True, nullable=True)
    total_students = Column(Integer, default=0)
    created_at = Column(DateTime, default=get_utc_now)

    students = relationship("User", back_populates="university_rel")

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="student") # student, company_hr, university_dean, admin, superadmin
    university = Column(String(255), nullable=True) # Text name for quick display
    university_id = Column(String(36), ForeignKey("universities.id", ondelete="SET NULL"), nullable=True, index=True)
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    is_vip = Column(Boolean, default=False)
    vip_expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    mastery_level = Column(Integer, default=1)
    elo_rating = Column(Integer, default=1000)
    xp_points = Column(Integer, default=0)
    adaptive_skill_profile = Column(JSON, default=dict) # e.g. {"algorithms": 1000, "security": 1000, "concurrency": 1000, "edge_cases": 1000}
    created_at = Column(DateTime, default=get_utc_now)

    university_rel = relationship("University", back_populates="students")
    company_rel = relationship("Company", back_populates="employees")
    submissions = relationship("Submission", back_populates="user", cascade="all, delete-orphan")
    certificates = relationship("Certificate", back_populates="user", cascade="all, delete-orphan")
    case_cup_entries = relationship("CaseCupLeaderboard", back_populates="user", cascade="all, delete-orphan")
    received_offers = relationship("TalentOffer", foreign_keys="TalentOffer.candidate_id", back_populates="candidate", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    dynamic_challenges = relationship("DynamicChallenge", back_populates="user", cascade="all, delete-orphan")

class Company(Base):
    __tablename__ = "companies"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    name = Column(String(255), nullable=False, unique=True)
    logo_url = Column(String(500), nullable=True)
    industry = Column(String(100), nullable=False) # Banking, Fintech, IT, Consulting, Telecom
    description = Column(Text, nullable=True)
    website = Column(String(255), nullable=True)
    is_verified = Column(Boolean, default=True)
    created_at = Column(DateTime, default=get_utc_now)

    simulations = relationship("Simulation", back_populates="company", cascade="all, delete-orphan")
    employees = relationship("User", back_populates="company_rel")
    talent_offers = relationship("TalentOffer", back_populates="company", cascade="all, delete-orphan")

class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(100), nullable=False) # Engineering, Finance, Analytics, Legal, Cybersecurity
    difficulty = Column(String(50), default="Beginner") # Beginner, Intermediate, Advanced, Adaptive
    estimated_hours = Column(Float, default=4.0)
    description = Column(Text, nullable=False)
    learning_outcomes = Column(JSON, default=list) # ["Credit scoring analysis", "Risk modeling"]
    is_published = Column(Boolean, default=True)
    is_case_cup = Column(Boolean, default=False)
    prize_pool = Column(String(255), nullable=True, default=None)
    deadline = Column(DateTime, nullable=True, default=None)
    created_at = Column(DateTime, default=get_utc_now)

    company = relationship("Company", back_populates="simulations")
    tasks = relationship("SimulationTask", back_populates="simulation", order_by="SimulationTask.order", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="simulation", cascade="all, delete-orphan")
    certificates = relationship("Certificate", back_populates="simulation", cascade="all, delete-orphan")
    case_cup_leaderboard = relationship("CaseCupLeaderboard", back_populates="simulation", cascade="all, delete-orphan")
    talent_offers = relationship("TalentOffer", back_populates="simulation")
    dynamic_challenges = relationship("DynamicChallenge", back_populates="simulation", cascade="all, delete-orphan")

class SimulationTask(Base):
    __tablename__ = "simulation_tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    simulation_id = Column(String(36), ForeignKey("simulations.id", ondelete="CASCADE"), nullable=False, index=True)
    order = Column(Integer, nullable=False, default=1)
    title = Column(String(255), nullable=False)
    briefing_text = Column(Text, nullable=False) # Kompaniya nomidan ish vazifasi brifingi
    instructions = Column(Text, nullable=False)  # Qadam-baqadam yo'riqnoma
    resource_files = Column(JSON, default=list) # [{"name": "credit_data.xlsx", "url": "/static/templates/..."}]
    template_data = Column(Text, nullable=True) # Boshlang'ich kod yoki hujjat matni
    rubric_criteria = Column(JSON, default=list) # [{"criterion": "Xavfsizlik", "max_score": 30}]
    model_answer = Column(Text, nullable=True) # Ekspert namunaviy javobi
    mentor_persona = Column(String(50), default="lead_engineer") # lead_engineer, chief_financial_officer, legal_counsel, hr_lead
    created_at = Column(DateTime, default=get_utc_now)

    simulation = relationship("Simulation", back_populates="tasks")
    submissions = relationship("Submission", back_populates="task", cascade="all, delete-orphan")

class DynamicChallenge(Base):
    __tablename__ = "dynamic_challenges"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    simulation_id = Column(String(36), ForeignKey("simulations.id", ondelete="CASCADE"), nullable=False, index=True)
    level = Column(Integer, default=1)
    challenge_type = Column(String(100), default="edge_cases") # edge_cases, high_frequency_anomalies, anti_fraud, concurrency, zero_day_bugs, stress_scale
    title = Column(String(255), nullable=False)
    difficulty_label = Column(String(50), default="Level 1 - Foundation")
    briefing = Column(Text, nullable=False)
    instructions = Column(Text, nullable=False)
    synthetic_dataset = Column(JSON, default=dict)
    starter_code = Column(Text, nullable=True)
    rubric_criteria = Column(JSON, default=list)
    model_answer = Column(Text, nullable=True)
    mentor_persona = Column(String(50), default="lead_engineer")
    status = Column(String(50), default="active") # active, completed, failed
    score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=get_utc_now)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="dynamic_challenges")
    simulation = relationship("Simulation", back_populates="dynamic_challenges")
    submissions = relationship("Submission", back_populates="dynamic_challenge", cascade="all, delete-orphan")

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    simulation_id = Column(String(36), ForeignKey("simulations.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(String(36), ForeignKey("simulation_tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    dynamic_challenge_id = Column(String(36), ForeignKey("dynamic_challenges.id", ondelete="SET NULL"), nullable=True, index=True)
    submitted_text = Column(Text, nullable=True)
    attachment_path = Column(String(500), nullable=True)
    status = Column(String(50), default="submitted") # submitted, evaluated, passed, revision_needed
    score = Column(Float, default=0.0) # 0.0 - 100.0
    elo_change = Column(Integer, default=0)
    xp_earned = Column(Integer, default=0)
    ai_feedback = Column(JSON, nullable=True) # {"rubric": ..., "strengths": ..., "mistakes": ..., "best_practices": ...}
    created_at = Column(DateTime, default=get_utc_now)
    reviewed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="submissions")
    simulation = relationship("Simulation", back_populates="submissions")
    task = relationship("SimulationTask", back_populates="submissions")
    dynamic_challenge = relationship("DynamicChallenge", back_populates="submissions")

class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    cert_uuid = Column(String(64), unique=True, index=True, nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    simulation_id = Column(String(36), ForeignKey("simulations.id", ondelete="CASCADE"), nullable=False, index=True)
    average_score = Column(Float, default=100.0)
    issued_at = Column(DateTime, default=get_utc_now)
    hmac_signature = Column(String(128), nullable=False)
    qr_code_url = Column(String(500), nullable=True)
    public_verify_url = Column(String(500), nullable=True)

    user = relationship("User", back_populates="certificates")
    simulation = relationship("Simulation", back_populates="certificates")

class CaseCupLeaderboard(Base):
    __tablename__ = "case_cup_leaderboard"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    simulation_id = Column(String(36), ForeignKey("simulations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    total_score = Column(Float, default=0.0)
    rank = Column(Integer, default=1)
    submitted_at = Column(DateTime, default=get_utc_now)
    created_at = Column(DateTime, default=get_utc_now)

    simulation = relationship("Simulation", back_populates="case_cup_leaderboard")
    user = relationship("User", back_populates="case_cup_entries")

class TalentOffer(Base):
    __tablename__ = "talent_offers"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    simulation_id = Column(String(36), ForeignKey("simulations.id", ondelete="SET NULL"), nullable=True, index=True)
    position_title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(50), default="sent") # sent, accepted, declined
    created_at = Column(DateTime, default=get_utc_now)

    company = relationship("Company", back_populates="talent_offers")
    candidate = relationship("User", foreign_keys=[candidate_id], back_populates="received_offers")
    simulation = relationship("Simulation", back_populates="talent_offers")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Float, nullable=False) # e.g. 99000.0 UZS
    provider = Column(String(50), nullable=False) # click, payme, stripe, demo
    status = Column(String(50), default="pending") # pending, completed, failed, cancelled
    plan_type = Column(String(50), default="vip_monthly") # vip_monthly, vip_yearly, case_cup_pro
    created_at = Column(DateTime, default=get_utc_now)

    user = relationship("User", back_populates="transactions")

