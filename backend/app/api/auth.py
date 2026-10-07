from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import Optional, List
from app.database import get_db
from app.models.user import User
from app.models.talent import CandidateVisibility
from app.models.rbac import Role
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from app.core.deps import get_current_active_user
from app.models.enums import OrgType, DefaultRole

router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str

class UserCreateOrg(UserCreate):
    org_type: OrgType
    org_id: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class VisibilityUpdate(BaseModel):
    is_open_to_work: Optional[bool] = None
    hidden_from_company_ids: Optional[List[str]] = None

@router.post("/register", response_model=Token)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    role_result = await db.execute(select(Role).where(Role.name == DefaultRole.STUDENT.value))
    student_role = role_result.scalars().first()
    if not student_role:
        raise HTTPException(status_code=500, detail="Student role not found")
        
    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role_id=student_role.id
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
        
    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role_id=org_role.id,
        org_type=user_in.org_type,
        org_id=user_in.org_id,
        is_active=False  # needs verification
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
    
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))
    
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/refresh", response_model=Token)
async def refresh(req: RefreshTokenRequest):
    from jose import jwt, JWTError
    from app.config import settings
    try:
        payload = jwt.decode(req.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        # token_type tekshiruvi: faqat refresh token qabul qilinadi
        token_type: str = payload.get("token_type")
        if token_type != "refresh":
            raise HTTPException(status_code=401, detail="Access token cannot be used as refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

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
        "org_id": current_user.org_id
    }

@users_router.patch("/me/visibility")
async def update_visibility(
    update_data: VisibilityUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(CandidateVisibility).where(CandidateVisibility.user_id == current_user.id))
    visibility = result.scalars().first()
    
    if not visibility:
        visibility = CandidateVisibility(user_id=current_user.id)
        db.add(visibility)
        
    if update_data.is_open_to_work is not None:
        visibility.is_open_to_work = update_data.is_open_to_work
    if update_data.hidden_from_company_ids is not None:
        visibility.hidden_from_company_ids = update_data.hidden_from_company_ids
        
    await db.commit()
    await db.refresh(visibility)
    return {"is_open_to_work": visibility.is_open_to_work, "hidden_from_company_ids": visibility.hidden_from_company_ids}
