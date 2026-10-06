# Task 05 — Case Cup

**Bosqich: 3 (Modul 1, 2 tugagandan keyin; Modul 4, 6 bilan parallel)**

## Kontekst

Avval `docs/CONTRACT.md`ni o'qing. Bu — eng kichik modul: milliy
musobaqalar (bir nechta kompaniya homiyligida, cho'qqi ball bo'yicha
reyting). Modul 1 (`User`) va Modul 2 (`Simulation`, `Submission`)ga
bog'liq, lekin ularning fayllarini **o'zgartirmaysiz** — faqat import
qilib ishlatasiz.

## Siz egalik qiladigan fayllar (faqat shular)

```
backend/app/models/case_cup.py       # CaseCupLeaderboard
backend/app/api/case_cups.py
backend/app/api/case_cups_schemas.py
backend/tests/test_case_cups.py
```

Agar `Simulation` modeliga `is_case_cup` (bool) va `prize_pool`,
`deadline` ustunlari kerak bo'lsa — bu ustunlarni **Modul 2 fayliga
qo'shishni so'ramang**, chunki fayl unga tegishli. O'rniga, shu
ma'lumotlarni sizning `CaseCupLeaderboard`/alohida `CaseCup` jadvalingizda
saqlang va `simulation_id` orqali bog'lang (FK, lekin `Simulation`
jadvalini o'zgartirmaysiz).

## Talablar

### 1. Modellar

```python
class CaseCup(Base):
    id, simulation_id (FK -> simulations.id), title, host_company_name,
    prize_pool, deadline, status ("upcoming" | "active" | "finished"), created_at

class CaseCupLeaderboard(Base):
    id, case_cup_id, user_id, total_score, rank, submitted_at
```

### 2. Endpointlar

```
GET /case-cups                  -> faqat status in ("upcoming","active")
GET /case-cups/{id}/leaderboard -> total_score bo'yicha tartiblangan, rank hisoblangan
```

Rank — `Submission` jadvalidagi (Modul 2) shu simulyatsiya bo'yicha
talabaning eng yuqori balli asosida hisoblanadi (Modul 2'ning
`Submission` modelini faqat **o'qish** uchun import qiling).

## Qabul qilish mezonlari

- Faqat `active`/`upcoming` case cup'lar ro'yxatda chiqadi, `finished` chiqmaydi.
- Leaderboard to'g'ri tartiblangan (eng yuqori ball = rank 1).
- `grep -rn "class Simulation" backend/app/models/case_cup.py` — bo'sh
  natija (Simulation modelini qayta e'lon qilmagansiz, faqat import).
