# Backend qurish rejasi — agent tasklari

Har bir fayl — alohida AI agentga **to'liq, mustaqil** beriladigan prompt
(agent avval `docs/CONTRACT.md`ni o'qib chiqishi kerak). Frontend bu
bosqichda yo'q — Stitch'da UI tayyor bo'lgandan keyin alohida yoziladi.

## Ishga tushirish tartibi (bosqichlar)

```
Bosqich 1 (yolg'iz, hech kim kutmaydi):
  └── 01-core-auth-rbac.md

Bosqich 2 (01 tugagandan keyin, bir-biriga tegmaydi — PARALLEL):
  ├── 02-simulations-ai-mentor.md
  └── 03-billing-admin.md

Bosqich 3 (01+02+03 tugagandan keyin, bir-biriga tegmaydi — PARALLEL):
  ├── 04-talent-hunt.md
  ├── 05-case-cup.md
  └── 06-university-portal.md
```

**Muhim:** Bosqich 2 va 3'dagi agentlarni bosqich tugamaguncha
ishga tushirmang — ular Modul 1 (yoki 1+2+3) yozgan fayllarni import
qilib ishlatadi; o'zlari yo'q bo'lsa, import xatoligi bo'ladi.

Bosqich ichidagi agentlar bir-birining faylini o'zgartirmaydi (har
task faylida "Siz egalik qiladigan fayllar" ro'yxati bor) — shuning
uchun bitta bosqich ichida xavfsiz parallel ishlashi mumkin.

## Har bosqichdan keyin tekshirish

Keyingi bosqichni boshlashdan oldin:

```bash
cd backend && pytest -q
```

Hammasi o'tishi shart. O'tmasa — keyingi bosqich fundamentga suyanadi,
oldin tuzating.

## Frontend

Hozircha yozilmaydi. Foydalanuvchi Stitch orqali UI chiqargandan keyin,
backend API tayyor bo'lgan modullar asosida alohida task yoziladi.
