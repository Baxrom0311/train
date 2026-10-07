"""
Butun backend bo'ylab ishlatiladigan sobit (fixed) qiymatlar uchun enum'lar.

Qoida: DB ustunlarida `native_enum=False` bilan ishlatiladi (Postgres native
ENUM TYPE emas, oddiy VARCHAR + Python darajasida validatsiya) — shunga ko'ra
kelajakda yangi qiymat qo'shish uchun `ALTER TYPE` kerak bo'lmaydi, oddiy
migratsiya yetarli.

RBAC rollari (`roles.name`) BU YERDA YO'Q — CONTRACT.md §4 bo'yicha rollar
DB'da dinamik (admin kod yozmasdan yangi rol qo'sha oladi), shuning uchun
qattiq enum bilan cheklanmaydi. `DefaultRole` faqat bootstrap/seed kodida
o'qilishi oson bo'lishi uchun konstanta sifatida beriladi, DB constraint emas.
"""
import enum


class OrgType(str, enum.Enum):
    COMPANY = "company"
    UNIVERSITY = "university"


class Sector(str, enum.Enum):
    IT = "IT"
    BANKING = "Banking"


class InvoiceStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"


class TalentOfferStatus(str, enum.Enum):
    SENT = "sent"
    VIEWED = "viewed"
    RESPONDED = "responded"


class AIEvalStatus(str, enum.Enum):
    COMPLETED = "completed"
    QUEUED_RETRY = "queued_retry"
    FAILED_PERMANENT = "failed_permanent"


class DefaultRole(str, enum.Enum):
    """Faqat bootstrap/seed kodi uchun o'qish qulayligi — DB constraint emas."""
    STUDENT = "student"
    COMPANY_HR = "company_hr"
    UNIVERSITY_ADMIN = "university_admin"
    ADMIN = "admin"
