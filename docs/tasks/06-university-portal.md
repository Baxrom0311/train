# Task 06 — University Portal

**Bosqich: 3 (Modul 1, 2, 3 tugagandan keyin; Modul 4, 5 bilan parallel)**

## Kontekst

Avval `docs/CONTRACT.md`ni o'qing. Universitet dekani/admini o'z
talabalarining statistikasini ko'radigan dashboard API'si. Bu —
universitetning yillik litsenziya to'lovi evaziga olgan asosiy qiymati,
shuning uchun **ma'lumot faqat o'z universitetiga tegishli bo'lishi**
nihoyatda muhim (boshqa universitet ma'lumotini ko'rsatish — jiddiy
ishonch va maxfiylik buzilishi).

Bog'liq: Modul 1 (`User`, `University.is_verified`), Modul 2
(`Submission`, `Simulation`), Modul 3 (tasdiqlov holati). Hammasini
faqat import qilib ishlatasiz, o'zgartirmaysiz.

## Siz egalik qiladigan fayllar (faqat shular)

```
backend/app/api/university_portal.py
backend/app/api/university_portal_schemas.py
backend/tests/test_university_portal.py
```

`University` modeliga yangi ustun kerak bo'lsa (masalan talabalar sonini
cache qilish uchun) — Modul 1'dan so'rang / shartnomaga qo'shimcha
qiling, o'zingiz `models/organization.py`ga tegmang.

`User` modelida talabaning qaysi universitetga tegishli ekanligini
bildiruvchi `university_id` ustuni bo'lishi kerak — bu Modul 1'da
allaqachon bor deb faraz qiling (agar yo'q bo'lsa, bu "shartnoma to'liq
emas" holati — ishni to'xtatib, shartnomani yangilashni so'rang, o'zingiz
boshqa modul faylini o'zgartirmang).

## Talablar

### Endpointlar

```
GET /university/stats
    auth: require_permission bilan himoyalangan (yangi permission:
          "view_university_stats", `university_admin` roliga biriktirilgan)
    + current_user.university.is_verified == True bo'lishi shart
    -> faqat current_user.university_id ga tegishli statistika:
       jami talaba soni, o'rtacha ball, tugatilgan simulyatsiyalar soni,
       top-performerlar (faqat shu universitet talabalari)
```

**Xavfsizlik talabi:** `university_id` so'rov parametri sifatida
qabul qilinmaydi — statistika **har doim** `current_user.university_id`
dan olinadi, hech qachon client yuborgan ID'dan emas (aks holda bir
universitet admini boshqasining ma'lumotini so'rab ko'rishi mumkin
bo'lib qoladi — IDOR).

Tasdiqlanmagan (`is_verified=False`) universitet admini bu endpointga
kira olmaydi (403, "universitetingiz hali tasdiqlanmagan" xabari bilan).

## Qabul qilish mezonlari

- Universitet A admini faqat A universiteti statistikasini ko'radi,
  B universitetiga tegishli hech qanday ma'lumot (hatto umumiy
  agregatda ham) sizmaydi.
- `is_verified=False` universitet admini 403 oladi.
- Endpoint imzosida `university_id` so'rov parametri **yo'q** —
  faqat `current_user` orqali aniqlanadi.
