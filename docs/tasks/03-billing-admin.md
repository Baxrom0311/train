# Task 03 — Billing (Invoice) & Admin Approval

**Bosqich: 2 (Modul 1 tugagandan keyin; Modul 2 bilan parallel ishlaydi)**

## Kontekst

Avval `docs/CONTRACT.md`ni to'liq o'qing, ayniqsa §1 (non-goals) va §7
(API sirtlari). Modul 1 tayyor: `User`, `Company`, `University`
(`is_verified=False` default), `require_permission()` — import qilib
ishlatasiz, o'zgartirmaysiz.

**Juda muhim: bu yerda Click/Payme webhook YOZMAYSIZ.** Eski loyihada
Click/Payme webhook'lari imzosiz, autentifikatsiyasiz edi — har kim
o'ziga bepul VIP bera olardi (audit bu bo'yicha eng kritik topilma deb
baholagan). Kelishilgan yangi model: B2B (universitet/kompaniya) to'lovi
**faqat admin qo'lda boshqaradigan invoice** orqali. Click/Payme bu
loyihada umuman qurilmaydi (kelajakda talaba uchun ixtiyoriy, alohida
qaror — hozir yo'q).

## Siz egalik qiladigan fayllar (faqat shular)

```
backend/app/models/billing.py        # Invoice
backend/app/api/billing.py
backend/app/api/admin.py
backend/app/api/billing_schemas.py
backend/tests/test_billing.py
backend/tests/test_admin_approval.py
```

## Talablar

### 1. `Invoice` modeli

```python
class Invoice(Base):
    id, payer_type ("company" | "university"), payer_id,
    amount, currency (default "UZS"), status ("pending" | "paid" | "cancelled"),
    issued_by_admin_id, paid_marked_at, notes, created_at
```

### 2. Admin endpointlari (`api/admin.py`) — barchasi `require_permission(...)` bilan himoyalangan

```
GET  /admin/organizations/pending       permission: approve_companies (yoki approve_universities)
                                         -> is_verified=False bo'lgan Company+University ro'yxati
POST /admin/organizations/{type}/{id}/approve    permission: approve_companies/approve_universities
                                         -> is_verified=True, verified_at, verified_by_admin_id
POST /admin/organizations/{type}/{id}/reject
```

### 3. Billing endpointlari (`api/billing.py`)

```
POST /admin/invoices                    permission: manage_billing
     body: {payer_type, payer_id, amount, currency, notes}
     -> faqat is_verified=True bo'lgan payer uchun yaratiladi (tasdiqlanmagan orgga invoice yozilmaydi)
POST /admin/invoices/{id}/mark-paid      permission: manage_billing
GET  /billing/invoices                  auth: faqat shu company_hr/university_admin o'z tashkilotining invoice'larini ko'radi
```

### 4. "Pullik funksiya ochiq" qoidasi

Bu modul **o'zi** biror pullik funksiyani ochmaydi (masalan Talent Hunt
ko'rish huquqi) — faqat `Company.is_verified` / `University.is_verified`
bayrog'ini boshqaradi. Modul 4 (Talent Hunt) va Modul 6 (University
Portal) shu bayroqni **o'zlari** tekshiradi. Shuning uchun sizning
vazifangiz faqat: tasdiqlov + invoice holати boshqaruvi, to'g'ri va
ishonchli bo'lsin.

## Qabul qilish mezonlari

- Tasdiqlanmagan (`is_verified=False`) company/university'ga invoice
  yaratishga urinish 400/403 qaytaradi.
- `approve_companies` ruxsatiga ega bo'lmagan user admin endpointga 403 oladi.
- Approve qilingandan keyin `is_verified=True`, `verified_at` to'ldirilgan.
- `grep -rn "click\|payme" backend/app/api/billing.py backend/app/models/billing.py`
  — bo'sh natija (B2B oqimida Click/Payme izi yo'q).
