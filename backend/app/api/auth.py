from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import uuid
from app.database import get_db
from app.models.user import User
from app.models.rbac import Role
from app.models.billing import Company, University
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from app.core.deps import get_current_active_user
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
    org_name: str = Field(min_length=1)
    industry: Optional[str] = None  # faqat org_type=company uchun
    city: Optional[str] = None      # faqat org_type=university uchun

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.post("/register", response_model=Token)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
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
    await db.commit()
    await db.refresh(new_user)

    access_token = create_access_token(subject=str(new_user.id))
    refresh_token = create_refresh_token(subject=str(new_user.id))

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/register-org", response_model=Token)
async def register_org(user_in: UserCreateOrg, db: AsyncSession = Depends(get_db)):
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

    # Tashkilot shu yerda yaratiladi (is_verified=False) — client'dan
    # mavjud org_id qabul qilinmaydi, shuning uchun soxta/boshqa tashkilot
    # ID'siga ulanib olish mumkin emas.
    if user_in.org_type == OrgType.COMPANY:
        org = Company(
            name=user_in.org_name,
            industry=user_in.industry or "N/A",
            contact_email=user_in.email,
        )
    else:
        org = University(
            name=user_in.org_name,
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
    await db.commit()
    await db.refresh(new_user)

    access_token = create_access_token(subject=str(new_user.id))
    refresh_token = create_refresh_token(subject=str(new_user.id))

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active (pending admin approval or disabled)",
        )

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

    access_token = create_access_token(subject=user_id)
    refresh_token = create_refresh_token(subject=user_id)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@users_router.get("/me")
async def get_me(current_user: User = Depends(get_current_active_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role.name,
        "org_type": current_user.org_type,
        "org_id": current_user.org_id,
        # Frontend menyusi rol nomiga emas, ruxsatlarga qarab quriladi (CONTRACT.md §10.3)
        "permissions": sorted(p.key for p in current_user.role.permissions),
    }
