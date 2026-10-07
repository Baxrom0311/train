"""
Sertifikat va portfolio (CONTRACT.md §13). Modul 10 egaligi.

Ochiq endpointlar (`/certificates/{code}`, `/portfolios/{slug}`) faqat
sertifikat suratini va talaba o'zi ochgan portfolioni qaytaradi — email,
javoblar, chat va fayllar hech qachon chiqmaydi.
"""
import uuid
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_permission
from app.credentials.issue import normalize_code
from app.credentials.slug import SLUG, from_name
from app.database import get_db
from app.models.billing import University
from app.models.credential import Certificate, Portfolio
from app.models.user import User
from app.talent.profile import build_profiles

router = APIRouter(prefix="/api/v1", tags=["Credentials"])
users_router = APIRouter(prefix="/api/v1/users", tags=["Credentials - me"])

MAX_LINKS = 3


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

    university = await db.get(University, user.university_id) if user.university_id else None
    profile = (await build_profiles(db, [user.id])).get(user.id)
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
        university=UniversityRef(name=university.name, city=university.city)
        if university and university.is_verified else None,
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
    await db.commit()
    return _own(cert)
