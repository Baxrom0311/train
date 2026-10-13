from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import uuid
from app.database import get_db
from app.models.user import User
from app.models.rbac import Role
from app.models.billing import Company, University
from app.core import account, throttle
from app.core.account import Purpose
from app.core.security import (
    verify_password, get_password_hash, create_access_token, create_refresh_token, issued_after_password_change,
)
from app.core.deps import get_current_active_user
from app.core.throttle import Limit
from app.models.enums import OrgType, DefaultRole

router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    # Talaba o'z universitetini ko'rsatishi mumkin (ixtiyoriy) — bu
    # register-org orqali yaratiladigan "org_type=university" admin
    # akkauntidan BUTUNLAY ALOHIDA tushuncha (yuqoridagi izohga qarang).
    university_id: Optional[uuid.UUID] = None

class UserCreateOrg(UserCreate):
    """
    Kompaniya/universitet HR/admin ro'yxatdan o'tishi. `org_id` client'dan
    QABUL QILINMAYDI (avval shu yerga tasdiqlanmagan ixtiyoriy UUID
    yuborish mumkin edi — tekshirilmasdan). Buning o'rniga tashkilot
    shu yerda, is_verified=False holatda, yangi yaratiladi.
    """
    org_type: OrgType
    org_name: str = Field(min_length=2, max_length=120)
    industry: Optional[str] = None  # faqat org_type=company uchun
    city: Optional[str] = None      # faqat org_type=university uchun

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class OrgRegistered(BaseModel):
    """Ariza qabul qilindi; token yo'q — akkaunt admin tasdiqlaguncha yopiq (CONTRACT.md §11.1)."""
    status: str = "pending"
    org_type: OrgType
    org_name: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class ForgotPasswordIn(BaseModel):
    email: EmailStr

class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=8, max_length=128)

class VerifyEmailIn(BaseModel):
    token: str = Field(min_length=1, max_length=128)

class VerifyEmailOut(BaseModel):
    email: str
    verified: bool = True

class MailQueued(BaseModel):
    status: str = "sent"


# §30.4 — oynalar soniyada
HOUR = 3600
QUARTER = 15 * 60


def _login_limits(email: str, ip: str) -> list[Limit]:
    """Tartib muhim: birinchi ikkitasi muvaffaqiyatli login'da tozalanadi, IP'niki qoladi."""
    return [
        Limit(f"login:fail:pair:{email}:{ip}", 5, QUARTER),
        Limit(f"login:fail:acct:{email}", 20, QUARTER),
        Limit(f"login:fail:ip:{ip}", 100, QUARTER),
    ]


def _register_limits(request: Request) -> list[Limit]:
    return [Limit(f"register:ip:{throttle.client_ip(request)}", 10, HOUR)]


_dummy_hash: str | None = None


def _check_password(user: User | None, password: str) -> bool:
    """Foydalanuvchi yo'q bo'lsa ham bcrypt ishlaydi — javob vaqti email borligini oshkor qilmaydi."""
    global _dummy_hash
    if user is None:
        _dummy_hash = _dummy_hash or get_password_hash("timing-equaliser-not-a-password")
        verify_password(password, _dummy_hash)
        return False
    return verify_password(password, user.hashed_password)


async def _verification_mail(db: AsyncSession, user: User):
    """Token yoziladi; chaqiruvchi commit qilgach xatni `BackgroundTasks`ga beradi (§30.5) —
    tranzaksiya bekor bo'lsa yaroqsiz havola yuborilmaydi."""
    token = await account.issue(db, user, Purpose.VERIFY_EMAIL)
    return account.compose(user, Purpose.VERIFY_EMAIL, token)

@router.post("/register", response_model=Token)
async def register(
    user_in: UserCreate, request: Request, background: BackgroundTasks, db: AsyncSession = Depends(get_db),
):
    await throttle.consume(_register_limits(request))
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")

    role_result = await db.execute(select(Role).where(Role.name == DefaultRole.STUDENT.value))
    student_role = role_result.scalars().first()
    if not student_role:
        raise HTTPException(status_code=500, detail="Student role not found")

    university_id = None
    if user_in.university_id is not None:
        uni_result = await db.execute(select(University).where(University.id == user_in.university_id))
        if not uni_result.scalars().first():
            raise HTTPException(status_code=400, detail="University not found")
        university_id = user_in.university_id

    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role_id=student_role.id,
        university_id=university_id,
    )
    db.add(new_user)
    await db.flush()
    mail = await _verification_mail(db, new_user)
    await db.commit()
    background.add_task(account.deliver, mail)
    await db.refresh(new_user)

    access_token = create_access_token(subject=str(new_user.id))
    refresh_token = create_refresh_token(subject=str(new_user.id))

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/register-org", response_model=OrgRegistered, status_code=status.HTTP_202_ACCEPTED)
async def register_org(
    user_in: UserCreateOrg, request: Request, background: BackgroundTasks, db: AsyncSession = Depends(get_db),
):
    await throttle.consume(_register_limits(request))
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")

    role_name = (
        DefaultRole.COMPANY_HR.value
        if user_in.org_type == OrgType.COMPANY
        else DefaultRole.UNIVERSITY_ADMIN.value
    )
    role_result = await db.execute(select(Role).where(Role.name == role_name))
    org_role = role_result.scalars().first()
    if not org_role:
        raise HTTPException(status_code=500, detail=f"Role {role_name} not found")

    org_model = Company if user_in.org_type == OrgType.COMPANY else University
    org_name = user_in.org_name.strip()
    taken = await db.execute(select(org_model.id).where(func.lower(org_model.name) == org_name.lower()))
    if taken.first():
        raise HTTPException(status_code=409, detail="Organization with this name already exists")

    # Tashkilot shu yerda yaratiladi (is_verified=False) — client'dan
    # mavjud org_id qabul qilinmaydi, shuning uchun soxta/boshqa tashkilot
    # ID'siga ulanib olish mumkin emas.
    if user_in.org_type == OrgType.COMPANY:
        org = Company(
            name=org_name,
            industry=user_in.industry or "N/A",
            contact_email=user_in.email,
        )
    else:
        org = University(
            name=org_name,
            city=user_in.city or "N/A",
            contact_email=user_in.email,
        )
    db.add(org)
    await db.flush()  # org.id kerak bo'ladi

    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role_id=org_role.id,
        org_type=user_in.org_type,
        org_id=org.id,
        is_active=False,  # admin tasdiqlamaguncha yopiq
    )
    db.add(new_user)
    try:
        await db.flush()
        # kirmasdan ham tasdiqlay oladi — havola ochiq endpointga (§30.2)
        mail = await _verification_mail(db, new_user)
        await db.commit()
    except IntegrityError:  # parallel ariza bilan bir xil nom/email
        await db.rollback()
        raise HTTPException(status_code=409, detail="Organization or email already registered")
    background.add_task(account.deliver, mail)

    return OrgRegistered(org_type=user_in.org_type, org_name=org_name)

@router.post("/login", response_model=Token)
async def login(
    request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db),
):
    limits = _login_limits(form_data.username.strip().lower(), throttle.client_ip(request))
    # §30.4: chegarada parol umuman tekshirilmaydi — to'g'ri parol ham kutadi
    wait = await throttle.retry_after(limits)
    if wait is not None:
        raise throttle.too_many(wait)

    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    if not _check_password(user, form_data.password):
        await throttle.hit(limits)
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active (pending admin approval or disabled)",
        )
    await throttle.clear(limits[:2])

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/refresh", response_model=Token)
async def refresh(req: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    from jose import jwt, JWTError
    from app.config import settings
    try:
        payload = jwt.decode(req.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        token_type: str = payload.get("token_type")
        if token_type != "refresh":
            raise HTTPException(status_code=401, detail="Access token cannot be used as refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Foydalanuvchi hali bazada bor va faolligini tekshirish (o'chirilgan/
    # bloklangan user eski refresh token bilan yangi access token ola
    # olmasligi kerak).
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    # §30.3: parol tiklangach eski sessiyalar yangilanmaydi
    if not issued_after_password_change(payload, user.password_changed_at):
        raise HTTPException(status_code=401, detail="Session expired after password change")

    access_token = create_access_token(subject=user_id)
    refresh_token = create_refresh_token(subject=user_id)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/password/forgot", response_model=MailQueued, status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    body: ForgotPasswordIn, request: Request, background: BackgroundTasks, db: AsyncSession = Depends(get_db),
):
    """Har doim 202 — akkaunt bor-yo'qligi oshkor qilinmaydi; xat javobdan keyin ketadi (§30.3)."""
    email = str(body.email)
    await throttle.consume([
        Limit(f"forgot:email:{email.lower()}", 3, HOUR),
        Limit(f"forgot:ip:{throttle.client_ip(request)}", 10, HOUR),
    ])
    user = (await db.execute(select(User).where(User.email == email))).scalars().first()
    if user is not None and user.is_active:
        token = await account.issue(db, user, Purpose.RESET_PASSWORD)
        await db.commit()
        background.add_task(account.deliver, account.compose(user, Purpose.RESET_PASSWORD, token))
    return MailQueued()


@router.post("/password/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(body: ResetPasswordIn, request: Request, db: AsyncSession = Depends(get_db)):
    ip = throttle.client_ip(request)
    await throttle.consume([Limit(f"reset:ip:{ip}", 20, QUARTER)])
    user = await account.consume(db, body.token, Purpose.RESET_PASSWORD)
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="invalid_token")

    now = datetime.now(timezone.utc)
    user.hashed_password = get_password_hash(body.password)
    user.password_changed_at = now          # eski JWT'lar bekor
    user.email_verified_at = user.email_verified_at or now   # havola email egaligini isbotladi
    await account.drop_unused(db, user.id, Purpose.RESET_PASSWORD)
    await db.commit()
    # bloklangan akkaunt yangi parol bilan darhol kira olsin
    await throttle.clear(_login_limits(user.email.lower(), ip)[:2])
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/verify-email", response_model=VerifyEmailOut)
async def verify_email(body: VerifyEmailIn, request: Request, db: AsyncSession = Depends(get_db)):
    """Ochiq: havola boshqa brauzerda ham ochilishi mumkin; kutilayotgan tashkilot xodimi ham tasdiqlaydi."""
    await throttle.consume([Limit(f"verify:ip:{throttle.client_ip(request)}", 20, QUARTER)])
    user = await account.consume(db, body.token, Purpose.VERIFY_EMAIL)
    if user is None:
        raise HTTPException(status_code=400, detail="invalid_token")
    user.email_verified_at = user.email_verified_at or datetime.now(timezone.utc)
    await db.commit()
    return VerifyEmailOut(email=user.email)


@router.post("/verify-email/resend", response_model=MailQueued, status_code=status.HTTP_202_ACCEPTED)
async def resend_verification(
    background: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.email_verified_at is not None:
        raise HTTPException(status_code=409, detail="already_verified")
    await throttle.consume([Limit(f"verify:resend:{current_user.id}", 3, HOUR)])
    mail = await _verification_mail(db, current_user)
    await db.commit()
    background.add_task(account.deliver, mail)
    return MailQueued()


@users_router.get("/me")
async def get_me(current_user: User = Depends(get_current_active_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "email_verified": current_user.email_verified_at is not None,
        "full_name": current_user.full_name,
        "role": current_user.role.name,
        "org_type": current_user.org_type,
        "org_id": current_user.org_id,
        # Frontend menyusi rol nomiga emas, ruxsatlarga qarab quriladi (CONTRACT.md §10.3)
        "permissions": sorted(p.key for p in current_user.role.permissions),
    }
