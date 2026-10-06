# Task 04 — Talent Hunt

**Bosqich: 3 (Modul 1, 2, 3 tugagandan keyin; Modul 5, 6 bilan parallel)**

## Kontekst

Avval `docs/CONTRACT.md`ni o'qing. Bu modul kompaniyalarga talaba
nomzodlarni ko'rsatadi — bu B2B daromadning asosiy qismi (oylik obuna +
"intervyu kafolati" SLA).

**Eng muhim qoida — maxfiylik (opt-in, default yopiq):** Eski
muhokamada avtomatik ko'rinish fikri ko'tarilgan edi, lekin keyinroq
LinkedIn-uslubida **talaba o'zi yoqmaguncha hech kim uni ko'rmaydi** deb
qaror qilindi. Buni noto'g'ri qilish — O'zbekistonning shaxsiy
ma'lumotlar qonuniga zid, shuning uchun bu nazoratni **hech qanday
istisnosiz** amalga oshiring.

Bog'liq modullar: Modul 1 (`User`, `require_permission`), Modul 2
(`Submission` — nomzod balli shundan hisoblanadi), Modul 3
(`Company.is_verified`).

## Siz egalik qiladigan fayllar (faqat shular)

```
backend/app/models/talent.py         # CandidateVisibility, TalentOffer
backend/app/api/talent_hunt.py
backend/app/api/talent_hunt_schemas.py
backend/tests/test_talent_hunt.py
```

## Talablar

### 1. Modellar

```python
class CandidateVisibility(Base):
    user_id (PK, FK -> users.id),
    is_open_to_work (bool, default False),   # OPT-IN, default YOPIQ
    hidden_from_company_ids (JSON, default []),
    updated_at

class TalentOffer(Base):
    id, company_id, candidate_user_id, position_title, message,
    status ("sent" | "viewed" | "responded"),
    respond_due_at,   # SLA: yuborilgan vaqtdan +N kun (masalan 5 ish kuni)
    created_at
```

### 2. Endpointlar

```
PATCH /users/me/visibility
    body: {is_open_to_work: bool, hidden_from_company_ids: [str]}
    auth: faqat o'ziniki (current_user.id)

GET  /talents
    auth: require_permission("view_candidates") + current_user.company.is_verified == True
    -> faqat is_open_to_work=True VA so'rov yuboruvchi company
       hidden_from_company_ids ichida bo'lmagan nomzodlar
    -> har nomzod uchun: ism, (agar ko'rsatish kerak bo'lsa) ball/submission
       xulosasi — lekin email/telefon kabi bevosita kontakt ma'lumoti
       FAQAT TalentOffer yuborilgandan keyin company'ga ochiladi (xom
       profil ro'yxatida kontaktni ko'rsatmang)

POST /talents/offers
    auth: require_permission("view_candidates") + company.is_verified
    body: {candidate_user_id, position_title, message}
    -> faqat yuqoridagi ko'rinish shartlariga mos keladigan candidate_user_id uchun
       (aks holda 404 — "topilmadi" qaytaring, "yashiringan" demang —
        bu orqali kompaniyaga "bu user mavjud, lekin yashirilgan" signalini
        bermaslik kerak)
    -> respond_due_at = now + 5 ish kuni
```

### 3. Default-yopiq tekshiruvi — eng muhim test

Yangi ro'yxatdan o'tgan student uchun `CandidateVisibility` yozuvi hali
yaratilmagan bo'lsa ham, `GET /talents` natijasida u **ko'rinmasligi**
kerak (yo'q yozuv = yopiq, default `True` emas — buni ayniqsa ehtiyotkor
tekshiring, SQL default va Python-level default ikkisi ham mos bo'lsin).

## Qabul qilish mezonlari

- Yangi student hech narsa sozlamagan holda `GET /talents`da chiqmaydi.
- `is_open_to_work=True` qilgandan keyin chiqadi.
- O'zini ma'lum kompaniyadan yashirgan (`hidden_from_company_ids`) student
  aynan shu kompaniyaning `/talents` so'rovida chiqmaydi, boshqasida chiqadi.
- Tasdiqlanmagan (`is_verified=False`) kompaniya `/talents`ga umuman kira olmaydi.
- Yashirilgan candidate_user_id'ga offer yuborishga urinish 404 (403 emas).
