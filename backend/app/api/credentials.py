"""
Sertifikat va portfolio (CONTRACT.md §13). Modul 10 egaligi.

Ochiq endpointlar (`/certificates/{code}`, `/portfolios/{slug}`) faqat
sertifikat suratini va talaba o'zi ochgan portfolioni qaytaradi — email,
javoblar, chat va fayllar hech qachon chiqmaydi.

CV (§28) — talabaning shaxsiy hujjati: ochiq endpointi yo'q.
"""
import re
import uuid
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_permission
from app.credentials.cv import experience, own_run_ids
from app.credentials.issue import normalize_code
from app.credentials.slug import SLUG, from_name
from app.database import get_db
from app.models.billing import University
from app.models.credential import Certificate, CvSettings, Portfolio
from app.models.user import User
from app.talent.profile import load_profile, refresh_profiles

router = APIRouter(prefix="/api/v1", tags=["Credentials"])
users_router = APIRouter(prefix="/api/v1/users", tags=["Credentials - me"])

MAX_LINKS = 3
MAX_LANGUAGES = 5
MAX_HIDDEN_RUNS = 50
PHONE = re.compile(r"^\+?[0-9 ()-]+$")
PHONE_MIN_DIGITS = 7


# ---------------------------------------------------------------------------
# Schemalar
# ---------------------------------------------------------------------------

class CertificatePublic(BaseModel):
    code: str
    status: Literal["valid", "revoked"]
    holder_name: str
    scenario_title: str
    company_name: str
    sector: str
    difficulty: str
    duration_days: int
    completed_at: datetime
    issued_at: datetime
    overall_score: float | None
    competency_scores: dict[str, float]
    revoked_at: datetime | None
    revoked_reason: str | None


class CertificateOut(CertificatePublic):
    run_id: uuid.UUID


class Link(BaseModel):
    label: str = Field(min_length=1, max_length=40)
    url: HttpUrl

    @field_validator("label")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("label bo'sh bo'lmasin")
        return v

    @field_validator("url")
    @classmethod
    def _https(cls, v: HttpUrl) -> HttpUrl:
        if v.scheme != "https" or len(str(v)) > 200:
            raise ValueError("faqat https:// havola, 200 belgigacha")
        return v


class PortfolioIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    slug: str
    is_public: bool
    headline: str = Field(default="", max_length=120)
    about: str = Field(default="", max_length=1000)
    links: list[Link] = Field(default_factory=list, max_length=MAX_LINKS)

    @field_validator("slug")
    @classmethod
    def _slug(cls, v: str) -> str:
        v = v.lower()
        if not SLUG.match(v):
            raise ValueError("slug: 3–40 belgi, lotin kichik harf, raqam va '-'")
        return v


class PortfolioSettings(PortfolioIn):
    exists: bool


class UniversityRef(BaseModel):
    name: str
    city: str


class PortfolioPublic(BaseModel):
    slug: str
    full_name: str
    headline: str
    about: str
    links: list[Link]
    university: UniversityRef | None
    overall_score: float | None
    competencies: dict[str, float]
    sectors: list[str]
    certificates: list[CertificatePublic]


class CvSettingsIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    phone: str | None = Field(default=None, max_length=20)
    city: str | None = Field(default=None, max_length=80)
    languages: list[str] = Field(default_factory=list, max_length=MAX_LANGUAGES)
    hidden_run_ids: list[uuid.UUID] = Field(default_factory=list, max_length=MAX_HIDDEN_RUNS)

    @field_validator("phone", "city")
    @classmethod
    def _blank_is_none(cls, v: str | None) -> str | None:
        v = " ".join((v or "").split())
        return v or None

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        if v and (not PHONE.match(v) or sum(c.isdigit() for c in v) < PHONE_MIN_DIGITS):
            raise ValueError("telefon: raqamlar, '+', bo'shliq, '-', '()'; kamida 7 raqam")
        return v

    @field_validator("languages")
    @classmethod
    def _languages(cls, v: list[str]) -> list[str]:
        out: dict[str, str] = {}
        for raw in v:
            line = " ".join(raw.split())
            if not 1 <= len(line) <= 40:
                raise ValueError("til qatori 1–40 belgi")
            out.setdefault(line.casefold(), line)
        return list(out.values())


class CvSettingsOut(BaseModel):
    phone: str | None
    city: str | None
    languages: list[str]
    hidden_run_ids: list[uuid.UUID]


class CvExperience(BaseModel):
    run_id: uuid.UUID
    scenario_title: str
    company_name: str
    sector: str
    difficulty: str
    duration_days: int
    started_at: datetime
    completed_at: datetime
    overall_score: float | None
    on_time_rate: float | None
    tasks_submitted: int
    tasks_total: int
    top_competencies: dict[str, float]
    strengths: list[str]
    certificate_code: str | None
    hidden: bool


class Cv(BaseModel):
    generated_at: datetime
    full_name: str
    email: str
    headline: str
    about: str
    links: list[Link]
    portfolio_slug: str | None
    university: UniversityRef | None
    overall_score: float | None
    competencies: dict[str, float]
    sectors: list[str]
    experience: list[CvExperience]
    settings: CvSettingsOut


class RevokeIn(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


# ---------------------------------------------------------------------------
# Yordamchilar
# ---------------------------------------------------------------------------

def _public(c: Certificate) -> CertificatePublic:
    return CertificatePublic(
        code=c.code,
        status="revoked" if c.revoked_at else "valid",
        holder_name=c.holder_name,
        scenario_title=c.scenario_title,
        company_name=c.company_name,
        sector=c.sector,
        difficulty=c.difficulty,
        duration_days=c.duration_days,
        completed_at=c.completed_at,
        issued_at=c.issued_at,
        overall_score=c.overall_score,
        competency_scores=c.competency_scores or {},
        revoked_at=c.revoked_at,
        revoked_reason=c.revoked_reason,
    )


def _own(c: Certificate) -> CertificateOut:
    return CertificateOut(**_public(c).model_dump(), run_id=c.run_id)


async def _by_code(db: AsyncSession, raw: str) -> Certificate:
    code = normalize_code(raw)
    cert = await db.scalar(select(Certificate).where(Certificate.code == code)) if code else None
    if cert is None:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return cert


async def _free_slug(db: AsyncSession, base: str, user_id: uuid.UUID) -> str:
    """`base`, band bo'lsa `base-2`, `base-3`, ..."""
    for n in range(1, 100):
        candidate = base if n == 1 else f"{base[:40 - len(str(n)) - 1].rstrip('-')}-{n}"
        owner = await db.scalar(select(Portfolio.user_id).where(Portfolio.slug == candidate))
        if owner is None or owner == user_id:
            return candidate
    return f"{base[:31].rstrip('-')}-{uuid.uuid4().hex[:8]}"


async def _university(db: AsyncSession, user: User) -> UniversityRef | None:
    """Faqat bog'langan va tasdiqlangan universitet (§13.2)."""
    university = await db.get(University, user.university_id) if user.university_id else None
    return UniversityRef(name=university.name, city=university.city) if university and university.is_verified else None


def _settings(p: Portfolio) -> PortfolioSettings:
    return PortfolioSettings(
        slug=p.slug, is_public=p.is_public, headline=p.headline, about=p.about,
        links=[Link(**link) for link in p.links], exists=True,
    )


# ---------------------------------------------------------------------------
# Ochiq
# ---------------------------------------------------------------------------

@router.get("/certificates/{code}", response_model=CertificatePublic)
async def verify_certificate(code: str, db: AsyncSession = Depends(get_db)):
    return _public(await _by_code(db, code))


@router.get("/portfolios/{slug}", response_model=PortfolioPublic)
async def get_portfolio(slug: str, db: AsyncSession = Depends(get_db)):
    portfolio = await db.scalar(
        select(Portfolio).where(Portfolio.slug == slug.lower(), Portfolio.is_public.is_(True))
    )
    user = await db.get(User, portfolio.user_id) if portfolio else None
    if user is None or not user.is_active:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    profile = await load_profile(db, user.id, runs=False)
    certificates = (await db.execute(
        select(Certificate)
        .where(Certificate.user_id == user.id, Certificate.revoked_at.is_(None))
        .order_by(Certificate.completed_at.desc())
    )).scalars().all()
    return PortfolioPublic(
        slug=portfolio.slug,
        full_name=user.full_name,
        headline=portfolio.headline,
        about=portfolio.about,
        links=[Link(**link) for link in portfolio.links],
        university=await _university(db, user),
        overall_score=profile.overall_score if profile else None,
        competencies=profile.competencies if profile else {},
        sectors=profile.sectors if profile else [],
        certificates=[_public(c) for c in certificates],
    )


# ---------------------------------------------------------------------------
# Talaba
# ---------------------------------------------------------------------------

Owner = Annotated[User, Depends(require_permission("manage_portfolio"))]


@users_router.get("/me/certificates", response_model=list[CertificateOut])
async def my_certificates(user: Owner, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Certificate).where(Certificate.user_id == user.id).order_by(Certificate.completed_at.desc())
    )).scalars().all()
    return [_own(c) for c in rows]


@users_router.get("/me/portfolio", response_model=PortfolioSettings)
async def my_portfolio(user: Owner, db: AsyncSession = Depends(get_db)):
    portfolio = await db.get(Portfolio, user.id)
    if portfolio:
        return _settings(portfolio)
    return PortfolioSettings(slug=await _free_slug(db, from_name(user.full_name), user.id), is_public=False, exists=False)


@users_router.put("/me/portfolio", response_model=PortfolioSettings)
async def save_portfolio(data: PortfolioIn, user: Owner, db: AsyncSession = Depends(get_db)):
    taken = await db.scalar(select(Portfolio.user_id).where(Portfolio.slug == data.slug, Portfolio.user_id != user.id))
    if taken:
        raise HTTPException(status_code=409, detail="Slug is taken")
    portfolio = await db.get(Portfolio, user.id) or Portfolio(user_id=user.id)
    portfolio.slug = data.slug
    portfolio.is_public = data.is_public
    portfolio.headline = data.headline
    portfolio.about = data.about
    portfolio.links = [link.model_dump(mode="json") for link in data.links]
    portfolio.updated_at = datetime.now(timezone.utc)
    db.add(portfolio)
    try:
        await db.commit()
    except IntegrityError:
        # parallel so'rov xuddi shu slug'ni oldi
        await db.rollback()
        raise HTTPException(status_code=409, detail="Slug is taken")
    return _settings(portfolio)


async def _cv(db: AsyncSession, user: User) -> Cv:
    portfolio = await db.get(Portfolio, user.id)
    settings = await db.get(CvSettings, user.id)
    hidden = [uuid.UUID(i) for i in settings.hidden_run_ids] if settings else []
    profile = await load_profile(db, user.id)
    entries = await experience(db, profile, set(hidden))
    return Cv(
        generated_at=datetime.now(timezone.utc),
        full_name=user.full_name,
        email=user.email,
        headline=portfolio.headline if portfolio else "",
        about=portfolio.about if portfolio else "",
        links=[Link(**link) for link in portfolio.links] if portfolio else [],
        portfolio_slug=portfolio.slug if portfolio and portfolio.is_public else None,
        university=await _university(db, user),
        overall_score=profile.overall_score if profile else None,
        competencies=dict(sorted(profile.competencies.items(), key=lambda kv: (-kv[1], kv[0]))) if profile else {},
        sectors=profile.sectors if profile else [],
        experience=[CvExperience(**vars(e)) for e in entries],
        settings=CvSettingsOut(
            phone=settings.phone if settings else None,
            city=settings.city if settings else None,
            languages=list(settings.languages) if settings else [],
            hidden_run_ids=hidden,
        ),
    )


@users_router.get("/me/cv", response_model=Cv)
async def my_cv(user: Owner, db: AsyncSession = Depends(get_db)):
    return await _cv(db, user)


@users_router.put("/me/cv/settings", response_model=Cv)
async def save_cv_settings(data: CvSettingsIn, user: Owner, db: AsyncSession = Depends(get_db)):
    settings = await db.get(CvSettings, user.id) or CvSettings(user_id=user.id)
    settings.phone = data.phone
    settings.city = data.city
    settings.languages = data.languages
    settings.hidden_run_ids = [str(i) for i in await own_run_ids(db, user.id, data.hidden_run_ids)]
    settings.updated_at = datetime.now(timezone.utc)
    db.add(settings)
    await db.commit()
    return await _cv(db, user)


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

@router.post("/admin/certificates/{code}/revoke", response_model=CertificateOut)
async def revoke_certificate(
    code: str,
    data: RevokeIn,
    _: Annotated[User, Depends(require_permission("manage_certificates"))],
    db: AsyncSession = Depends(get_db),
):
    cert = await _by_code(db, code)
    if cert.revoked_at:
        raise HTTPException(status_code=409, detail="Certificate is already revoked")
    cert.revoked_at = datetime.now(timezone.utc)
    cert.revoked_reason = data.reason.strip()
    await refresh_profiles(db, [cert.user_id])   # bekor qilingan ish profildan chiqadi (§10.1, §33.2)
    await db.commit()
    return _own(cert)
