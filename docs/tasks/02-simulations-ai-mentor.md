# Task 02 — Simulations, Submissions & AI Mentor

**Bosqich: 2 (Modul 1 tugagandan keyin; Modul 3 bilan parallel ishlaydi)**

## Kontekst

Avval `docs/CONTRACT.md`ni to'liq o'qing. Modul 1 (Core/Auth/RBAC) allaqachon
qurilgan: `User`, `require_permission()`, `rate_limit()`, JWT auth
(`get_current_user` dependency `backend/app/api/auth.py`da) tayyor —
import qilib ishlatasiz, **o'zgartirmaysiz**.

Siz bu platformaning **yuragi**ni qurasiz: talabalar simulyatsiya
topshiriqlarini yuboradi, AI mentor baholaydi. V1 kontenti faqat **IT/
Dasturlash va Bank/Moliya** sohalari bilan cheklangan (`CONTRACT.md` §1).

## Siz egalik qiladigan fayllar (faqat shular)

```
backend/app/models/simulation.py     # Simulation, SimulationTask, Submission
backend/app/api/simulations.py
backend/app/api/submissions.py
backend/app/api/simulations_schemas.py
backend/app/ai/router.py             # AIRouter — Cloud-only
backend/app/ai/guardrail.py          # prompt injection filtri
backend/app/ai/personas.py           # 4 mentor persona
backend/app/ai/retry_worker.py       # arq job: queued_retry submissionlarni qayta baholash
backend/app/core/sandbox.py          # Python sandbox (AST + subprocess)
backend/app/core/file_validator.py   # fayl yuklash xavfsizligi
backend/tests/test_submissions.py
backend/tests/test_sandbox.py
backend/tests/test_ai_router.py
```

`backend/app/main.py`, `config.py`, `database.py`, `conftest.py`ga
**tegmang** — ular Modul 1'ga tegishli (`CONTRACT.md` §6.1).

## Talablar

### 1. Modellar

```python
class Simulation(Base):
    id, slug, title, company_id (fictional kompaniya, hozircha oddiy
    string "company_name" ustuni ham qo'ying — alohida Company jadvaliga
    FK shart emas bu bosqichda), category ("IT" | "Finance" — FAQAT shu
    ikkisi v1'da), difficulty, description, is_published, created_at

class SimulationTask(Base):
    id, simulation_id, order, title, briefing_text, instructions,
    rubric_criteria (JSON), model_answer, mentor_persona, created_at

class Submission(Base):
    id, user_id, simulation_id, task_id, submitted_text, attachment_path,
    status, score, ai_feedback (JSON), ai_eval_status
      # "completed" | "queued_retry" | "failed_permanent"
    retry_count (default 0), created_at, reviewed_at
```

### 2. AI Router — **faqat Cloud AI, keyword-engine YO'Q**

Eski loyihada `_evaluate_deep_domain` deb nomlangan katta keyword-matching
fallback bor edi — **buni butunlay qurmang**. Zanjir:

```
DeepSeek (agar DEEPSEEK_API_KEY bor) 
  -> muvaffaqiyatsiz bo'lsa Gemini (agar GEMINI_API_KEY bor)
  -> muvaffaqiyatsiz bo'lsa OpenAI (agar OPENAI_API_KEY bor)
  -> barchasi muvaffaqiyatsiz -> submission.ai_eval_status = "queued_retry"
     + arq job navbatga qo'yiladi, HTTP 202 bilan javob qaytadi
     (talabaga: "baholanmoqda, bir ozdan keyin natija keladi")
```

Prompt injection himoyasi (`guardrail.py`) — talaba submission matnini AI
promptiga yuborishdan oldin tekshiring (asosiy shablonlarni aniqlash:
"ignore previous instructions", system prompt'ni ochib berishga urinish
va h.k.), xavfli topilsa darhol 0 ball + xavfsizlik mezoni bilan
qaytaring (AI chaqirilmaydi).

### 3. Retry worker (`arq`)

```python
# ai/retry_worker.py
async def retry_ai_evaluation(ctx, submission_id: str):
    # submissionni oching, qayta AI chaqiring
    # muvaffaqiyatli -> ai_eval_status="completed", ball yozilsin
    # muvaffaqiyatsiz va retry_count >= 3 -> "failed_permanent"
    # aks holda retry_count += 1, qayta navbatga qo'yilsin (backoff: 2^retry_count daqiqa)
```
`WorkerSettings` klassini shu faylda e'lon qiling (`arq.worker.run_worker`
bilan ishga tushiriladigan), lekin **worker'ni ishga tushirish buyrug'i**
(masalan `Procfile`/skript) Modul 8 (deploy) uchun qoldiring — faqat
kodni yozing.

### 4. Sandbox endpoint — xavfsizlik MAJBURIY

Eski loyihada bu endpoint **autentifikatsiyasiz** va `timeout_seconds`
cheksiz edi — audit buni kritik DoS xavfi deb topgan. Endi:

```python
@router.post("/tools/sandbox")
def run_python_code(
    data: PythonRunRequest,
    current_user: User = Depends(get_current_user),      # MAJBURIY auth
    _rl = Depends(rate_limit("sandbox", max_requests=10, window_seconds=60)),  # Modul 1'dan
):
    timeout = min(data.timeout_seconds or 2.0, 3.0)  # SERVER tomonda qattiq cheklov, client qiymatiga ishonilmaydi
    ...
```

AST blacklist mantiqi (`BANNED_MODULES`, `BANNED_CALLS`, `BANNED_ATTRS`)
eski loyihadan qayta ishlatilishi mumkin — **lekin** `BANNED_MODULES`
ro'yxatida haqiqiy modul nomi `"builtins"` (ko'plik bilan) yozilsin, eski
loyihadagi `"builtin"` (xato, yakka son) yozilishini takrorlamang.

### 5. Fayl yuklash

Eski `file_validator.py` mantiqi (magic bytes + extension + streamed
size cap + `sanitize_filename` path-traversal himoyasi) **yaxshi
yozilgan edi** — xuddi shu mantiqni qayta ishlatishingiz mumkin, faqat
yangi joyga ko'chiring va `settings` importini yangi `config.py`ga
moslang.

### 6. Submission endpoint

`POST /submissions` — `current_user` talab qiladi (auth), `simulation_id`
va `task_id` DB'da **mavjudligini tekshiring** (eski loyihada bu
tekshiruv yo'q edi — ixtiyoriy string qabul qilinardi). IDOR himoyasi:
`GET /submissions/{id}` faqat egasi yoki `admin` ruxsatiga ega bo'lgan
ko'radi (eski loyihadagi mantiq to'g'ri edi, qayta ishlatilsin).

## Qabul qilish mezonlari

- `test_sandbox.py`: auth'siz so'rov 401; rate-limit 11-so'rovda 429;
  `timeout_seconds=9999` yuborilsa ham serverda haqiqiy timeout ≤3s.
- `test_ai_router.py`: barcha AI key'lar bo'sh bo'lganda submission
  `queued_retry` holatiga o'tadi (keyword-fallback natija QAYTARMAYDI).
- `test_submissions.py`: boshqa userning submission'ini ko'rishga urinish 403.
- Kodda `has_dti`, `has_aml_structuring` kabi keyword-heuristic funksiyalar
  **mavjud emas** — `grep -rn "_evaluate_deep_domain" backend/app` bo'sh natija.
