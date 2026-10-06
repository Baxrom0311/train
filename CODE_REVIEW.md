# TryJob kod auditi

Sana: 2026-10-07. Ko‘lam: mavjud lokal loyiha. Audit mahsulot kodini tuzatmaydi; quyida tasdiqlangan xatolar, ularning ta’siri va tuzatish yo‘nalishi berilgan.

## Xulosa

Loyihada ishlaydigan FastAPI API, React interfeys, ORM modellar, AI provider adapterlari va testlar mavjud. Ammo hozirgi holatda uni production uchun tayyor deb hisoblash mumkin emas. Eng jiddiy muammolar: server muhitidan ajratilmagan ochiq kod bajarish endpointi, tasdiqlanmagan to‘lovlar, standart administrator/secretlar va qayta seed qilishda topshiriq tarixining buzilishi. Frontendning bir necha asosiy oqimi backendga ulanmagan.

`README.md` dagi frontend stack va “Zero Critical Vulnerabilities” bayonoti joriy kod hamda audit natijalariga mos emas.

## Tekshiruv natijalari va chegaralari

| Tekshiruv | Natija |
|---|---|
| Izolyatsiyalangan SQLite bazada barcha backend testlari | **34 passed**, 1 ogohlantirish, 1.46 s |
| `frontend`: `npm run build` | **O‘tdi**; Vite 6.4.3; JS 602.85 kB / gzip 165.69 kB |
| Yangi SQLite DB: `alembic upgrade head` | **O‘tdi** |
| Shu DB: `alembic check` | **Muvaffaqiyatsiz**, model va migratsiya orasida 18 indeks farqi |
| Backend web sahifalar | `/`, `/simulations`, `/verify/invalid`: **500**; `/api/health`: 200 |
| Alohida TestClient xavfsizlik va biznes sinovlari | Quyidagi topilmalar amalda takrorlandi |

Testlar vaqtinchalik DB/upload kataloglarida, AI kalitlari bo‘sh holda bajarildi. Mavjud `tryjob.db`, `train.db` va foydalanuvchi uploadlari o‘zgartirilmadi. Sandbox tekshiruvi faqat audit yaratgan zararsiz marker faylini o‘qidi. Frontend build `frontend/dist/` artefaktlarini yangiladi.

PostgreSQL, Docker stack, haqiqiy brauzer oqimlari, tashqi AI va payment providerlari ishga tushirilmadi. Frontend topilmalari source va API shartnomalarini taqqoslashga asoslangan; brauzer E2E natijasi sifatida talqin qilinmasin. Tashqi dependency zaiflik bazasi tekshirilmagan. `scratch/skills_source/` uchinchi tomon materiallari mahsulot auditi doirasiga kiritilmadi.

## Arxitektura

```text
React / Vite :3000
  → Axios /api/v1 → FastAPI :8000
      → SQLAlchemy → SQLite yoki PostgreSQL
      → AIRouter → DeepSeek / Gemini / OpenAI → lokal evristik baholash
      → uploads/ → hozir ochiq StaticFiles
      → Python subprocess → hozir hostdan izolyatsiya qilinmagan

Docker: Nginx → backend → PostgreSQL
                       Redis mavjud, ammo app kodida foydalanilmaydi
```

Production Docker konfiguratsiyasida React build/hosting bosqichi yo‘q. README eski Jinja/Vanilla JS frontendini tasvirlaydi, real interfeys esa `frontend/src/` ichida.

## P0 — tashqi foydalanishdan oldin tuzatish zarur

### 1. Ochiq sandbox host fayllarini o‘qiy oladi — amalda tasdiqlandi

Manba: `app/core/sandbox.py:73`, `app/core/sandbox.py:86`, `app/api/tools.py:33`.

`/tools/sandbox` va `/tools/run-python` autentifikatsiyasiz ishlaydi. AST qora ro‘yxatini import alias bilan chetlab o‘tish mumkin; kod serverning Python jarayoni huquqlari bilan bajariladi. `python -I` fayl tizimi, tarmoq yoki OS huquqlarini izolyatsiya qilmaydi. Sinovda anonim so‘rov audit yaratgan fayldan `AUDIT_MARKER_ONLY` ni o‘qidi va 200 qaytardi.

`timeout_seconds` uchun yuqori chegara yo‘q; xotira, chiqish hajmi va parallel jarayonlar ham cheklanmagan. Faqat timeout xavfsizlik chegarasi bo‘la olmaydi.

Tuzatish: endpointni izolyatsiyalangan runner tayyor bo‘lguncha o‘chirish yoki cheklash; secretsiz muhit, tarmoq/fayl tizimi izolyatsiyasi, CPU/RAM/PID/output limitlari va server belgilagan timeout. AST filtrini xavfsizlikning asosiy vositasi deb qabul qilmaslik.

### 2. VIP to‘lovsiz faollashadi, webhook qayta yuborilishi muddatni uzaytiradi — tasdiqlandi

Manba: `app/api/billing.py:29`, `:67`, `:120`; `app/schemas.py` payment modellari.

`upgrade-vip` foydalanuvchi yuborgan summani olib, to‘lovni tekshirmasdan `completed` tranzaksiya yaratadi. Sinovda 1 birlik summa bilan VIP berildi. Click imzosi tekshirilmaydi; aynan bir hodisani ikki marta yuborish har safar yana 30 kun qo‘shdi. Payme endpointida autentifikatsiya yo‘q, account bo‘lmasa birinchi foydalanuvchi tanlanadi. Provider hodisasi IDsi uchun unique/idempotency yozuvi yo‘q.

Tuzatish: server narxiga asoslangan pending order, provider tasdig‘i, qat’iy summa/valyuta/order mosligi va yagona tranzaksiya holat mashinasi. Bir hodisa faqat bir marta entitlement yaratishi kerak.

### 3. Production seed administratorni ma’lum parol bilan yaratadi — tasdiqlandi

Manba: `app/seed_data.py:197`, `scripts/start.sh:43`.

Startup seed yangi bazada demo administrator va HR hisoblarini yaratadi. Izolyatsiyalangan yangi bazada koddagi standart administrator rekvizitlari bilan login 200 qaytardi. Production startup bu seedni shartsiz chaqiradi.

Tuzatish: demo hisoblarni faqat aniq demo/test rejimida yaratish; production administratorini xavfsiz alohida bootstrap jarayoni orqali yaratish. Oldin deploy qilingan bo‘lsa, ushbu hisoblar va credentiallarni tekshirish.

### 4. JWT va sertifikat secretlari koddagi standart qiymatlarga tushadi — kodda tasdiqlandi

Manba: `app/config.py:23`, `:26`, `docker-compose.yml` backend environment.

Environment qiymati berilmasa hammaga bir xil signing key ishlatiladi, Docker ham shu fallbackni takrorlaydi. Bunday deployda server taniydigan foydalanuvchi IDsi uchun token imzosini tashqarida yasash mumkin. Sertifikat HMAC kaliti ham xuddi shu muammoga ega; HMACni bilishning o‘zi DBda yangi sertifikat yaratmaydi, ammo imzoning maxfiylik kafolatini yo‘qotadi.

Tuzatish: productionda missing/default secret bilan startupni rad etish, tasodifiy mustaqil kalitlar, mavjud tokenlarni almashtirish rejasi.

## P1 — ma’lumot va asosiy mahsulot oqimlari

### 5. Seed restartda task IDlarini yo‘qotadi — tasdiqlandi

Manba: `app/seed_data.py:572`, `:591`; `app/main.py:25`; `scripts/start.sh:43`.

Seed mavjud tasklarni bulk delete qilib yangi UUIDlar bilan qayta yaratadi; leaderboard ham o‘chirilib demo bilan to‘ldiriladi. Takroriy seed sinovida 7 ta eski taskdan **0 ta ID saqlandi**, 6 submission yetim bog‘lanishda qoldi. SQLite `PRAGMA foreign_keys=0`; PostgreSQLdagi `ON DELETE SET NULL` esa eski submission task_idlarini bo‘shatadi. PostgreSQL oqibati schema asosidagi xulosa, alohida PostgreSQL sinovi emas.

Natija: restartdan keyin o‘quvchi tarixi, sertifikat olish sharti va frontendda saqlangan IDlar buziladi. Tuzatish: seedni idempotent upsertga aylantirish, barqaror task kalitlari, destructive resetni oddiy startupdan ajratish.

### 6. Frontend login haqiqiy autentifikatsiya emas — kodda tasdiqlandi

Manba: `frontend/src/context/AuthContext.tsx:36`, `:68`, `:79`; `frontend/src/components/AuthModal.tsx:54`; `frontend/src/api.ts:113`.

Login parolni APIga yubormaydi; role va `mock_jwt_token_*` lokal yaratiladi. Company registration ham faqat localStoragega yozadi. Himoyalangan backend endpointlari bu tokenni qabul qilmaydi. `ensureAuth` avtomatik login uchun seedda yo‘q `student@train.uz` hisobini ishlatadi. Frontendda HR bo‘lib ko‘rinish backend HR ruxsatini bermaydi.

Tuzatish: haqiqiy auth endpointlari, `/auth/me` orqali profil tiklash va backend tasdiqlaydigan kompaniya onboarding oqimi.

### 7. Frontendning HR, OTM va leaderboard API manzillari mos emas — tasdiqlandi

Manba: `frontend/src/api.ts:383`, `:488`, `:646`, `:683`.

| Frontend so‘rovi | Mavjud backend |
|---|---|
| `/talents` | `/talent-hunt/candidates` |
| `/talents/offers` | `/talent-hunt/send-offer` |
| `/university/stats` | `/university-portal/stats` |
| `/leaderboard` | `/case-cups/{slug}/leaderboard` |

GET so‘rovlarida 404 amalda tasdiqlandi. Response va offer payload maydonlari ham farq qiladi: masalan `position` / `position_title`, `id` / `user_id`, `name` / `full_name`. Catch bloklari namuna ma’lumot yoki soxta muvaffaqiyat qaytaradi; foydalanuvchi yuborilgan deb o‘ylagan taklif serverda yaratilmaydi. `/talents/{id}/vip-upgrade` ham mavjud emas.

Tuzatish: backend shartnomasiga mos client/adapters, aniq xato holatlari va frontend-backend integratsion testlar.

### 8. Case Cups javobi UI kutgan maydonlarga ega emas — kod/shartnomada tasdiqlandi

Manba: `app/api/case_cups.py:12`; `frontend/src/api.ts:243`; `frontend/src/pages/CaseCupsPage.tsx:311`, `:334`.

API `SimulationListOut[]` beradi, client uni `CaseCup[]` deb belgilaydi. Javobda `stages`, `tags`, `host_company`, `participants_count` yo‘q. UI `cup.stages.map()` va `cup.tags.map()` ni tekshirmasdan chaqiradi; real nonempty API javobi render xatosiga olib keladi. TypeScript build buni ushlamaydi.

Tuzatish: yagona CaseCup DTO yoki aniq adapter; API javobi bilan render testi.

### 9. Builder va adaptiv frontend vazifalari serverda yaratilmaydi — kodda tasdiqlandi

Manba: `frontend/src/pages/SimulationBuilderPage.tsx:440`; `frontend/src/pages/WorkspacePage.tsx:682`; `frontend/src/api.ts:195`.

Builder simulyatsiyani faqat localStoragega saqlaydi. “Dynamic Mastery” `setTimeout` orqali `task-dynamic-level-*` ID bilan React state ichida task yaratadi. Submission esa shu IDni backendga yuboradi; serverda bunday task/challenge bo‘lmaydi va 404 qaytadi.

Tuzatish: builderni simulation/task CRUDga, adaptiv UI ni mavjud `/simulations/{slug}/dynamic-challenge` endpointiga ulash; backend IDlarini ishlatish.

### 10. Docker/web hosting konfiguratsiyasi interfeysni bermaydi — qisman runtime tasdiqlandi

Manba: `app/main.py:72`; `.dockerignore`; `Dockerfile`; `docker/nginx.conf`.

Backend mavjud bo‘lmagan Jinja templatelarini ochadi: `/`, `/simulations`, `/verify/invalid` 500 qaytardi. `.dockerignore` frontendni chiqarib tashlaydi, Dockerfile React build qilmaydi, Nginx esa `/` ni backendga uzatadi.

Tuzatish: React buildni imagega qo‘shish, Nginx orqali static + SPA fallback, `/api` ni backendga uzatish. Sertifikat linki va deep-link reloadni ham tekshirish.

### 11. HR/OTM ma’lumotlari va takliflar autentifikatsiyasiz ochiq — tasdiqlandi

Manba: `app/api/talent_hunt.py:13`, `:139`; `app/api/university_portal.py:17`.

Anonim so‘rovlar nomzod emaili, ballari, offer matnlari va universitetdagi top talabalar ma’lumotlarini 200 bilan oldi. Universitet/kompaniya bo‘yicha vakolat chegarasi yo‘q. Bu endpointlar kodda HR/dekan portaliga tegishli deb ko‘rsatilgan.

Tuzatish: rol va tenant/ownership nazorati; talabaga faqat o‘z takliflari, HRga o‘z kompaniyasi takliflari; ommaviy profil zarur bo‘lsa alohida rozilik va cheklangan DTO.

### 12. Uploadlar ochiq va baholovchi ularning mazmunini o‘qimaydi — tasdiqlandi

Manba: `app/main.py:56`; `app/api/submissions.py:84`.

Yuklangan fayl URLini bilgan anonim foydalanuvchi uni ola oladi. Sinovda faylning to‘liq mazmuni 200 bilan qaytdi. Faqat fayl yuborilganda AIga haqiqiy mazmun o‘rniga `Yuklangan fayl: /uploads/...` satri uzatiladi. Shu sabab hujjat/kod fayli baholandi degan xulosa asossiz.

Tuzatish: owner tekshiruvchi download endpointi; formatga mos xavfsiz extraction va hajm limitlari; qo‘llanmaydigan formatga aniq javob.

### 13. Submission task va simulation mosligini tekshirmaydi — tasdiqlandi

Manba: `app/api/submissions.py:63`, `:143`.

A simulyatsiya taski bilan B simulyatsiya IDsi yuborilganda 200 qaytdi va B ID saqlandi. Dynamic challenge uchun ham uning simulation_id mosligi tekshirilmaydi. Published holati ham tekshirilmaydi.

Tuzatish: simulation IDni task/challengedan aniqlash yoki ikkisini qat’iy solishtirish, tegishli visibility/ownership qoidalarini qo‘llash.

### 14. Lokal baholash mazmunsiz javobga yuqori ball beradi; AI JSON parseri xatoni muvaffaqiyatga aylantiradi — tasdiqlandi

Manba: `app/ai/router.py:225`, `:243`.

Cloud kalitlarisiz kalit so‘zlardan tuzilgan mazmunsiz matn 92 ball oldi. Lokal baholash asosan AST belgilari va substring mavjudligini tekshiradi, funksional to‘g‘rilikni sinamaydi. `_parse_json_feedback('{}', ...)` esa **85 ball, passed=true** qaytardi. Score chegaralari va passed/score izchilligi schema orqali ta’minlanmagan.

Tuzatish: yetishmayotgan/nomuvofiq provider javobini rad etish; kod uchun izolyatsiyalangan test datasetlari, matn uchun rubrikaga mos tekshiruv; evristik feedbackni ishonchli yakuniy attestatsiya bilan tenglashtirmaslik.

### 15. Bir xil topshiriqni qayta topshirish ELO/XPni cheksiz oshiradi — tasdiqlandi

Manba: `app/api/submissions.py:115`.

Bir xil javobning ketma-ket ikki topshirilishi har safar **+18 ELO va +184 XP** berdi. Completed dynamic challenge ham qayta topshirilishi mumkin. Parallel so‘rovlarda user ko‘rsatkichlari read-modify-write orqali hisoblanadi; lock/atomik yangilanish yo‘qligi yo‘qolgan update xavfini beradi, bu parallel ssenariy alohida sinovdan o‘tkazilmadi.

Tuzatish: retry va mukofot siyosatini ajratish, birinchi completion yoki ball yaxshilanishiga bog‘lash, DB transaction/locking bilan izchillik.

### 16. Adaptive JSON profilidagi keyingi o‘zgarishlar saqlanmaydi — tasdiqlandi

Manba: `app/api/submissions.py:127`; `app/models.py:42`.

Nonempty JSON dict joyida o‘zgartirilib aynan o‘zi qayta biriktiriladi. Oddiy SQLAlchemy JSON bunday ichki mutatsiyani kuzatmaydi. Sinovda umumiy ELO oshdi, ammo `general_domain` eski 1000 qiymatda qoldi.

Tuzatish: yangi dict nusxasini biriktirish yoki `MutableDict`; yangi Session bilan qayta o‘qiydigan persistence testi.

### 17. Case Cup submissionlari leaderboardni yangilamaydi — tasdiqlandi

Manba: `app/api/submissions.py`; `app/api/case_cups.py:39`; `app/seed_data.py:591`.

Leaderboard yozish faqat seed ichida mavjud. Musobaqaga topshiriq yuborgan yangi user leaderboardga kirmadi. Frontend musobaqa registrationi ham localStorage bilan cheklangan.

Tuzatish: musobaqa registration/eligibility va deadline qoidalari, submissionsdan hisoblanadigan leaderboard yoki transaction ichida yangilanadigan aggregate.

### 18. O‘chirilgan foydalanuvchi tizimdan foydalanishda davom etadi — tasdiqlandi

Manba: `app/api/auth.py:19`, `:59` va refresh handler.

`User.is_active=False` qilingandan keyin avvalgi token bilan `/auth/me` 200 qaytardi. Login va refresh ham ushbu flagni tekshirmaydi.

Tuzatish: markaziy active-user nazorati va login/refreshda ham bloklash; disable holatining barcha himoyalangan amallarga tatbiqi.

## P2 — to‘g‘rilik, barqarorlik va xizmat ko‘rsatish

19. **Parol salt umumiy.** `app/core/security.py:13`: barcha parollar bir xil salt va 100000 iteratsiya bilan hashlanadi. Bir xil parol bir xil hash beradi. Har parolga tasodifiy salt va versiyalangan, migratsiya qilinadigan hash formatini qo‘llash kerak.

20. **Refresh navbati osilib qolishi mumkin.** `frontend/src/api.ts:66`: `isRefreshing=true` refresh token yo‘q holatda `false` ga qaytmaydi. Keyingi 401lar hech qachon bo‘shatilmaydigan navbatga tushadi. Har bir exit yo‘lida flag va navbatni yopish; logoutda Axios default Authorization va React auth holatini ham sinxronlash.

21. **Muvaffaqiyatsiz submission UI’da completed bo‘ladi.** `WorkspacePage.tsx:648` har qanday 200 javobni bajarilgan task sifatida yozadi, `revision_needed` ham shular jumlasida. Progress/draft kalitlari user IDni o‘z ichiga olmaydi (`:546`, `:583`), shuning uchun bir brauzerdagi boshqa hisob avvalgi hisobning holatini ko‘radi. Server tasdiqlagan passed holati va userga bog‘liq saqlash kerak.

22. **Sertifikat bahosi barcha urinishlardan olinadi.** `app/api/certificates.py:55`: failed va qayta urinishlar ham o‘rtachaga qo‘shiladi; ko‘p urinish qilingan taskning vazni ko‘payadi. Task bo‘yicha yakuniy/best-passed siyosatini belgilash kerak. `(user_id, simulation_id)` unique constraint yo‘qligi parallel issue so‘rovlari uchun dublikat xavfini ham qoldiradi.

23. **Migratsiya va model farqli.** Yangi DBda `alembic check` 18 ta FK indeksini yetishmayotgan deb topdi. `create_all` asosidagi testlar buni yashiradi. Indekslarni yangi migratsiyada kiritish, CI’da fresh migration + schema drift tekshiruvi kerak.

24. **Etalon javoblar oldindan ommaviy.** `app/schemas.py:109`, `app/api/simulations.py:136`: anonymous detail javobida `model_answer` borligi tasdiqlandi. Ochiq mashq uchun bu mahsulot qarori bo‘lishi mumkin, lekin tanlov va ishonchli skill attestatsiyasi uchun oldindan javobni olish mumkin. Mashq va baholash rejimlarini ajratish zarur.

25. **VIP expiry amalda hisobga olinmaydi.** Talent filter va profil `is_vip`ni o‘qiydi, muddati o‘tgan obunani tugatuvchi tekshiruv yo‘q. `vip_expires_at` asosidagi markaziy entitlement hisoblash kerak.

26. **Saqlash va deploy kamchiliklari.** Compose PostgreSQL, Redis va backend portlarini hostga chiqaradi; backendga to‘g‘ridan-to‘g‘ri kirish Nginx rate limitini chetlab o‘tadi. Redis autentifikatsiyasiz sozlangan. Health endpoint DBni tekshirmaydi. Bu konfiguratsiya topilmalari, amaldagi tarmoq ekspozitsiyasi tekshirilmagan.

27. **Test izolyatsiyasi loyiha ichida avtomatik emas.** Test modullari `app.main`ni to‘g‘ridan-to‘g‘ri import qiladi; alohida DB fixture/conftest yo‘q. Oddiy `pytest` lokal DBni seed qiladi va test yozuvlarini unda qoldiradi. `AGENTS.md`dagi izolatsiyalangan buyruq yoki majburiy test fixtures kerak.

28. **Texnik qarz.** `WorkspacePage.tsx` 1862, `SimulationBuilderPage.tsx` 1390, `LandingPage.tsx` 1060 qator. TS strict rejimi o‘chirilgan, frontend test/lint scriptlari yo‘q, route importlari eager; build 500 kB chunk ogohlantirishini berdi. University stats har talabaga alohida querylar yuboradi, list endpointlarida pagination yo‘q. Talab oshishidan oldin komponentlarni ajratish, lazy routes, shartnoma testlari va query aggregation zarur.

## Tuzatish ketma-ketligi

1. Sandboxni ajratish, billingni tasdiqlashga bog‘lash, production demo auth/secretlarni olib tashlash.
2. Seedni ma’lumotni saqlaydigan qilish va test bazasini majburiy izolyatsiyalash.
3. Haqiqiy frontend auth, API DTO/manzillari, CaseCup renderi, builder va dynamic challenge integratsiyasi.
4. RBAC/tenant va upload maxfiyligi; submission bog‘lanishlari, baholash, mukofot va sertifikat siyosati.
5. React production hosting, migratsiya driftini yopish; PostgreSQL va brauzer E2E tekshiruvlari.

Qabul mezonlari: anonim sandbox host resurslariga kira olmasligi; imzosiz/replay payment VIP yaratmasligi; restart task IDlarini saqlashi; login → task → submission → certificate haqiqiy frontend orqali bajarilishi; noto‘g‘ri rollar va task/simulation juftligi rad etilishi; migration check farqsiz o‘tishi.
