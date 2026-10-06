# Task 01 — Core, Auth & RBAC

**Bosqich: 1 (birinchi, hech narsaga bog'liq emas, boshqa modullar shuni kutadi)**

## Kontekst

Loyiha repo root'ida. Avval `docs/CONTRACT.md` to'liq faylni o'qing — bu
loyihaning yagona haqiqat manbai, barcha biznes qarorlar va modul
chegaralari shunda. Bu task — **Modul 1**, `CONTRACT.md` §6 jadvalidagi
birinchi qator.

Siz **FastAPI ilovaning butun skeletini** va **auth/RBAC** tizimini
noldan qurasiz. Sizdan keyin boshqa agentlar Simulations, Billing, Talent
Hunt kabi modullarni ustiga quradi — shuning uchun bu task'da yozilgan
narsalar **barqaror interfeys** bo'lishi kerak (keyin o'zgartirish qiyin
bo'ladi).

## Siz egalik qiladigan fayllar (faqat shular)

```
backend/app/main.py
backend/app/config.py
backend/app/database.py
backend/app/core/security.py        # JWT (python-jose) + parol (passlib[bcrypt])
backend/app/core/rbac.py            # require_permission() dependency
backend/app/core/rate_limit.py      # Redis-based rate limiter (qayta ishlatiladigan)
backend/app/core/redis_client.py    # Redis + arq connection pool setup
backend/app/models/user.py
backend/app/models/rbac.py          # Role, Permission, RolePermission
backend/app/models/organization.py  # Company, University (is_verified bilan)
backend/app/api/auth.py
backend/app/api/auth_schemas.py
backend/tests/conftest.py
backend/tests/test_auth.py
backend/tests/test_rbac.py
backend/alembic/                    # env.py, migratsiya setup
backend/requirements.txt
backend/pytest.ini
```

Boshqa hech qanday fayl/papkaga tegmang — ular kelgusi modullar uchun.

## Talablar

### 1. `main.py` — auto-discovery router yuklash

`backend/app/api/` papkasidagi **har bir** `.py` faylni skanerlang
(`pkgutil.iter_modules` yoki shunga o'xshash), ichida `router` atributi
bo'lgan modullarni topib, `app.include_router(module.router, prefix="/api/v1")`
qiling. Bu shuning uchun kerak: kelgusi modullar `app/api/`ga yangi fayl
qo'yadi, lekin `main.py`ga **hech qachon** tegmaydi (fayl to'qnashuvini
oldini olish — `CONTRACT.md` §6.1).

CORS: `.env`dagi `CORS_ORIGINS` dan o'qilsin, bo'sh bo'lsa **xatolik
bering** (production'da `*` + `allow_credentials=True` birikmasi xavfli
— shunchaki fallback qilmang).

### 2. `config.py` — xavfsiz sozlamalar

- `SECRET_KEY`, `HMAC_CERT_SECRET`: `.env`dan o'qilsin. **Agar
  `ENVIRONMENT=production` va bu qiymatlar bo'sh/berilmagan bo'lsa —
  ilova ishga tushmasin, aniq xatolik chiqarsin.** Hech qachon kodda
  "haqiqiy ko'rinadigan" fallback secret yozmang (eski loyihada aynan
  shu xato bor edi — audit buni kritik xavf deb topgan).
- `DATABASE_URL`: sqlite (dev) / postgres (prod), eski loyihadagi mantiq
  qayta ishlatilishi mumkin (`postgres://` → `postgresql+psycopg2://`
  almashtirish).
- `REDIS_URL`: `.env`dan, default `redis://localhost:6379/0`.

### 3. Parol va JWT

- Parol: `passlib.hash.bcrypt` — **hech qanday qo'lda yozilgan PBKDF2 yoki
  statik salt yo'q**. `passlib.context.CryptContext(schemes=["bcrypt"])`.
- JWT: `python-jose[cryptography]`, `HS256`. `create_access_token`,
  `create_refresh_token`, `decode_access_token`, `decode_refresh_token`
  funksiyalari — eski API shaklini saqlang (`data: dict`,
  `expires_delta: Optional[timedelta]`), lekin implementatsiya
  `python-jose` orqali bo'lsin. Payload'da `token_type` claim
  (`access`/`refresh`) saqlansin, decode funksiyalari mos turini tekshirsin.

### 4. RBAC modellari va dependency

```python
# models/rbac.py
class Role(Base):      # id, name (unique)
class Permission(Base): # id, key (unique, masalan "manage_billing")
class RolePermission(Base): # role_id, permission_id (composite PK yoki oddiy PK)

# models/user.py
class User(Base):
    # id, email, full_name, hashed_password, role_id -> Role, is_active, created_at
```

Boshlang'ich rollar va ruxsatlar (migratsiya/seed orqali yaratilsin):

| Rol | Ruxsatlar |
|---|---|
| `student` | (hozircha maxsus ruxsat kerak emas) |
| `company_hr` | — (keyingi modullar o'z ruxsatlarini qo'shadi, hozir bo'sh qoldirish mumkin) |
| `university_admin` | — |
| `admin` | `approve_companies`, `approve_universities`, `manage_billing`, `manage_roles` |

`core/rbac.py`:
```python
def require_permission(permission_key: str):
    def dependency(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        # current_user.role.permissions ichida permission_key bor-yo'qligini tekshir
        # yo'q bo'lsa 403
        return current_user
    return dependency
```

**Muhim:** Kodning hech bir joyida `if current_user.role == "admin"` kabi
inline string tekshiruv yozilmasin — faqat `require_permission(...)`
orqali. Bu keyingi barcha modullar uchun majburiy qoida.

### 5. Redis rate limiter (qayta ishlatiladigan)

`core/rate_limit.py`:
```python
def rate_limit(key_prefix: str, max_requests: int, window_seconds: int):
    def dependency(current_user: User = Depends(get_current_user)):
        # Redis key: f"{key_prefix}:{current_user.id}:{bucket}"
        # oshib ketsa HTTPException(429)
        ...
    return dependency
```
Bu keyinroq Modul 2 (sandbox endpoint) tomonidan ishlatiladi — siz hozir
faqat generic mexanizmni qurasiz, ishlatuvchi endpoint yo'q.

### 6. Auth endpointlari (`api/auth.py`)

```
POST /auth/register       body: {email, password, full_name}
                           -> role=student (FIXED, boshqa rol tanlab bo'lmaydi)
POST /auth/register-org   body: {email, password, full_name, org_type(company|university), org_name}
                           -> role=company_hr|university_admin, mos Company/University
                              yozuvi yaratiladi, is_verified=False
POST /auth/login          OAuth2PasswordRequestForm yoki JSON {email, password}
POST /auth/refresh        body: {refresh_token}
GET  /auth/me             auth talab qiladi
```

`register-org` orqali yaratilgan foydalanuvchi **hech qanday pullik
funksiyaga kira olmasligi** kerak — bu keyingi modullarda `is_verified`
tekshiruvi orqali ta'minlanadi (siz shunchaki `is_verified=False` qilib
yozasiz, tekshiruvning o'zi Modul 3'da).

### 7. `Company` / `University` modellari (skeleton)

Faqat RBAC/auth uchun zarur maydonlar bilan boshlang (keyingi modullar
kengaytiradi — shuning uchun bu fayllarga keyin **qo'shimcha ustun
qo'shish** ruxsat, lekin mavjud ustunlarni o'chirish/nomini o'zgartirish
mumkin emas):

```python
class Company(Base):
    id, name, industry, is_verified=False, verified_at, verified_by_admin_id, created_at

class University(Base):
    id, name, is_verified=False, verified_at, verified_by_admin_id, created_at
```

## Qabul qilish mezonlari (testlar)

`backend/tests/test_auth.py`:
- Student ro'yxatdan o'tadi, login qiladi, `/auth/me` to'g'ri qaytadi.
- Noto'g'ri parol bilan login 400/401 qaytaradi.
- `register-org` orqali yaratilgan Company/University `is_verified=False`.
- Refresh token orqali yangi access token olinadi; eskirgan/noto'g'ri
  refresh token 401 qaytaradi.
- Access token refresh endpoint'da ishlamaydi (token_type tekshiruvi).

`backend/tests/test_rbac.py`:
- `admin` ruxsatiga ega bo'lmagan foydalanuvchi `require_permission("approve_companies")`
  bilan himoyalangan dummy endpoint'ga 403 oladi (test uchun shu faylda
  vaqtincha dummy route yaratishingiz mumkin).
- `admin` roli shu ruxsatga ega bo'lsa — 200.

Hammasi `cd backend && pytest -q` bilan o'tishi shart (SQLite, temp DB,
`conftest.py`da sozlanadi).

## Nazorat ro'yxati (topshirishdan oldin)

- [ ] `grep -rn 'role ==' backend/app` — bo'sh natija (inline role check yo'q).
- [ ] `grep -rn 'tryjob_salt\|pbkdf2_hmac' backend/app` — bo'sh natija.
- [ ] Production muhitida bo'sh `SECRET_KEY` bilan ilova ishga tushmaydi (test bilan tasdiqlang).
- [ ] `main.py`da `app/api/`dagi fayllarni qo'lda import qilish yo'q, faqat auto-discovery.
