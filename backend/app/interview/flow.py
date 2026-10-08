"""
Sinov suhbati oqimi (CONTRACT.md §24.2–24.4, Modul 14).

LLM chaqiruvi bir necha soniya davom etadi, shuning uchun har amal ikki
bosqichda (Run chati kabi, §9.4): avval qulfsiz tekshiruv va kontekst,
so'ng LLM, so'ng qisqa tranzaksiyada holat qayta tekshirilib yoziladi.
Holat o'zgarib ulgurgan bo'lsa (ikki marta yuborilgan javob) — `Conflict`;
ikki bosqich orasida hech narsa yozilmaydi, shuning uchun suhbat "yarim
yo'lda" qolmaydi.

AI ishlamasa suhbat to'xtamaydi: savollar `bank.py`dan, reaksiya va
aniqlashtiruvchi savolsiz davom etadi; faqat yakuniy baho LLM talab qiladi.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, time, timedelta
from statistics import fmean

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import interviewer as ai
from app.ai.llm import chat
from app.interview import bank
from app.models.enums import InterviewMessageKind as Kind, InterviewRole as Role, InterviewStatus as Status
from app.models.interview import Interview, InterviewMessage
from app.models.user import User
from app.scenario.clock import TASHKENT
from app.talent import vacancies as matching
from app.talent.profile import Profile, build_profiles

log = logging.getLogger(__name__)

DAILY_LIMIT = 3
TOKEN_BUDGET = 40_000
MAX_FOLLOW_UPS = 2
MAX_FOCUS = 3
STALE_ACTIVE = timedelta(hours=24)
# fokus 3 tadan kam bo'lsa xulq-atvor savollari shu tartibda to'ldiriladi
PADDING = ("prioritization", "stress_handling", "initiative", "communication", "time_management")
LANGS = ("uz", "ru", "en")


class InterviewError(Exception):
    status_code = 400

    def __init__(self, detail: str | dict):
        super().__init__(detail)
        self.detail = detail


class NotFound(InterviewError):
    status_code = 404


class Conflict(InterviewError):
    status_code = 409


class TooMany(InterviewError):
    status_code = 429


# ── Reja ─────────────────────────────────────────────────────────────


def focus_for(requirements: dict[str, int], gap_keys: list[str]) -> list[str]:
    """§24.2: avval yetishmayotganlar (talab tartibida), so'ng qolgan talablar; bo'sh — muloqot."""
    ordered = [k for k in requirements if k in gap_keys] + [k for k in requirements if k not in gap_keys]
    return ordered[:MAX_FOCUS] or ["communication"]


def slots_for(focus: list[str]) -> list[ai.Slot]:
    middle = list(focus) + [c for c in PADDING if c not in focus]
    return [
        ai.Slot("communication", "intro"),
        *(ai.Slot(c, "behavioral") for c in middle[:3]),
        ai.Slot("technical", "situational"),
    ]


def setting_for(interview: Interview, description: str = "") -> ai.InterviewSetting:
    return ai.InterviewSetting(
        position=interview.position, company_name=interview.company_name, sector=interview.sector.value,
        lang=interview.lang, description=description, requirements=interview.requirements,
    )


def _day_start(now: datetime) -> datetime:
    local = now.astimezone(TASHKENT)
    return datetime.combine(local.date(), time.min, tzinfo=TASHKENT)


async def _expire_stale(db: AsyncSession, user_id: uuid.UUID, now: datetime) -> None:
    await db.execute(
        update(Interview)
        .where(Interview.user_id == user_id, Interview.status == Status.ACTIVE, Interview.created_at < now - STALE_ACTIVE)
        .values(status=Status.ABANDONED, finished_at=now)
    )


async def _check_can_start(db: AsyncSession, user_id: uuid.UUID, now: datetime) -> None:
    active = await db.scalar(
        select(Interview.id).where(Interview.user_id == user_id, Interview.status == Status.ACTIVE)
    )
    if active is not None:
        raise Conflict({"message": "Active interview exists", "interview_id": str(active)})
    started = await db.scalar(
        select(func.count()).select_from(Interview)
        .where(Interview.user_id == user_id, Interview.created_at >= _day_start(now))
    )
    if started >= DAILY_LIMIT:
        raise TooMany(f"Daily limit: {DAILY_LIMIT} interviews")


def _message(interview: Interview, seq: int, role: Role, kind: Kind, body: str, *, generated: bool, now: datetime) -> InterviewMessage:
    return InterviewMessage(
        interview_id=interview.id, seq=seq, role=role, kind=kind, question_index=interview.current,
        body=body, generated=generated, created_at=now,
    )


# ── Boshlash ─────────────────────────────────────────────────────────


async def start(
    db: AsyncSession, user: User, vacancy_id: uuid.UUID, lang: str, now: datetime, *, chat_fn=None,
) -> Interview:
    found = await matching.student_vacancy(db, user.id, vacancy_id)
    if found is None:
        raise NotFound("Vacancy not found")
    vacancy, company = found
    await _expire_stale(db, user.id, now)
    await _check_can_start(db, user.id, now)
    profile = (await build_profiles(db, [user.id])).get(user.id) or Profile(user.id)
    gaps = [g.competency for g in matching.fit(profile, vacancy).gaps]
    requirements = dict(vacancy.requirements or {})
    interview = Interview(
        id=uuid.uuid4(), user_id=user.id, vacancy_id=vacancy.id, position=vacancy.title,
        company_name=company.name, sector=vacancy.sector, requirements=requirements,
        focus=focus_for(requirements, gaps), lang=lang, current=0, follow_ups=0,
        status=Status.ACTIVE, tokens_used=0, eval_attempts=0, created_at=now,
    )
    description = vacancy.description
    await db.commit()          # eskirganlar `abandoned` — LLM'dan oldin

    slots = slots_for(interview.focus)
    planned = await ai.plan_questions(setting_for(interview, description), slots, chat_fn=chat_fn or chat)
    if planned is None:
        texts, generated = bank.fallback_questions(
            slots, sector=interview.sector.value, position=interview.position, lang=lang, seed=str(interview.id),
        ), False
    else:
        texts, result = planned
        generated = True
        interview.tokens_used = result.tokens
    interview.plan = [{"competency": s.competency, "text": t} for s, t in zip(slots, texts)]

    # parallel boshlash va kunlik limit — foydalanuvchi qatori bo'yicha ketma-ket
    await db.execute(select(User.id).where(User.id == user.id).with_for_update())
    await _expire_stale(db, user.id, now)
    await _check_can_start(db, user.id, now)
    greeting = bank.GREETING[lang].format(company=interview.company_name, position=interview.position, total=len(slots))
    db.add(interview)
    await db.flush()
    db.add(_message(interview, 0, Role.INTERVIEWER, Kind.QUESTION, f"{greeting}\n\n{texts[0]}", generated=generated, now=now))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise Conflict("Active interview exists")
    return interview


# ── Javob ────────────────────────────────────────────────────────────


async def owned(db: AsyncSession, user: User, interview_id: uuid.UUID, *, lock: bool = False) -> Interview:
    # sessiya commit'da eskirmaydi (expire_on_commit=False) — har doim DB'dagi holat o'qilsin
    q = select(Interview).where(Interview.id == interview_id, Interview.user_id == user.id).execution_options(
        populate_existing=True
    )
    if lock:
        q = q.with_for_update()
    interview = await db.scalar(q)
    if interview is None:
        raise NotFound("Interview not found")
    return interview


async def messages(db: AsyncSession, interview_id: uuid.UUID) -> list[InterviewMessage]:
    return list((await db.execute(
        select(InterviewMessage).where(InterviewMessage.interview_id == interview_id).order_by(InterviewMessage.seq)
    )).scalars())


async def answer(
    db: AsyncSession, user: User, interview_id: uuid.UUID, text: str, now: datetime, *, chat_fn=None,
) -> bool:
    """Javobni yozadi va suhbatni bir qadam suradi. `True` — suhbat tugadi, baholash navbatga qo'yilsin."""
    interview = await owned(db, user, interview_id)
    if interview.status != Status.ACTIVE:
        raise Conflict("Interview is not active")
    history = await messages(db, interview.id)
    last = history[-1]
    if last.role != Role.INTERVIEWER:
        raise Conflict("Answer already sent")
    observed = (len(history), interview.current, interview.follow_ups)
    after_follow_up = last.kind == Kind.FOLLOW_UP
    may_follow_up = not after_follow_up and interview.follow_ups < MAX_FOLLOW_UPS
    is_last = interview.current >= len(interview.plan) - 1
    slot = interview.plan[interview.current]
    question = last.body if after_follow_up else slot["text"]
    setting = setting_for(interview)
    budget_left = interview.tokens_used < TOKEN_BUDGET
    await db.commit()

    turn, tokens = None, 0
    # oxirgi savolning aniqlashtiruvchi javobidan keyin aytadigan gap yo'q — faqat yakun
    if budget_left and not (is_last and not may_follow_up):
        got = await ai.interviewer_turn(
            setting, slot["competency"], question, text, may_follow_up=may_follow_up, chat_fn=chat_fn or chat,
        )
        if got is not None:
            turn, result = got
            tokens = result.tokens

    interview = await owned(db, user, interview_id, lock=True)
    seq = await db.scalar(select(func.count()).select_from(InterviewMessage).where(InterviewMessage.interview_id == interview.id))
    if interview.status != Status.ACTIVE or (seq, interview.current, interview.follow_ups) != observed:
        await db.rollback()
        raise Conflict("Answer already sent")

    db.add(_message(interview, seq, Role.CANDIDATE, Kind.ANSWER, text, generated=False, now=now))
    ack = f"{turn.ack}\n\n" if turn and turn.ack else ""
    # tartib aniq bo'lsin — javob va savol bir xil `now`da
    reply_at = now + timedelta(microseconds=1)
    finished = False
    if turn and turn.follow_up and may_follow_up:
        interview.follow_ups += 1
        db.add(_message(interview, seq + 1, Role.INTERVIEWER, Kind.FOLLOW_UP, ack + turn.follow_up, generated=True, now=reply_at))
    elif not is_last:
        interview.current += 1
        nxt = interview.plan[interview.current]["text"]
        db.add(_message(interview, seq + 1, Role.INTERVIEWER, Kind.QUESTION, ack + nxt, generated=bool(ack), now=reply_at))
    else:
        db.add(_message(interview, seq + 1, Role.INTERVIEWER, Kind.CLOSING, ack + bank.CLOSING[interview.lang],
                        generated=bool(ack), now=reply_at))
        interview.status = Status.EVALUATING
        interview.finished_at = now
        finished = True
    interview.tokens_used += tokens
    await db.commit()
    return finished


async def abandon(db: AsyncSession, user: User, interview_id: uuid.UUID, now: datetime) -> None:
    interview = await owned(db, user, interview_id, lock=True)
    if interview.status != Status.ACTIVE:
        raise Conflict("Interview is not active")
    interview.status = Status.ABANDONED
    interview.finished_at = now
    await db.commit()


async def retry(db: AsyncSession, user: User, interview_id: uuid.UUID) -> None:
    interview = await owned(db, user, interview_id, lock=True)
    if interview.status != Status.FAILED:
        raise Conflict("Interview evaluation has not failed")
    interview.status = Status.EVALUATING
    interview.eval_attempts = 0
    await db.commit()


# ── Baholash ─────────────────────────────────────────────────────────


def exchanges(interview: Interview, history: list[InterviewMessage]) -> list[ai.Exchange]:
    """Har asosiy savolga: birinchi javob, aniqlashtiruvchi savol va unga javob (bo'lsa)."""
    out = []
    for index, slot in enumerate(interview.plan):
        own = [m for m in history if m.question_index == index]
        answers = [m.body for m in own if m.kind == Kind.ANSWER]
        follow_up = next((m.body for m in own if m.kind == Kind.FOLLOW_UP), None)
        out.append(ai.Exchange(
            competency=slot["competency"], question=slot["text"], answer=answers[0] if answers else "",
            follow_up=follow_up, follow_up_answer=answers[1] if follow_up and len(answers) > 1 else None,
        ))
    return out


def aggregate(interview: Interview, review: ai.EvaluationOut) -> tuple[float, dict[str, float], dict]:
    """§24.4: ballar server hisobida — umumiy va kompetensiyalar bo'yicha o'rtacha."""
    scores = [a.score for a in review.answers]
    by_competency: dict[str, list[int]] = {}
    for slot, a in zip(interview.plan, review.answers):
        by_competency.setdefault(slot["competency"], []).append(a.score)
    feedback = {
        "summary": review.summary.strip(),
        "strengths": [s.strip() for s in review.strengths if s.strip()],
        "improvements": [s.strip() for s in review.improvements if s.strip()],
        "answers": [
            {"index": i, "competency": slot["competency"], "score": a.score,
             "comment": a.comment.strip(), "better": a.better.strip()}
            for i, (slot, a) in enumerate(zip(interview.plan, review.answers))
        ],
    }
    return (
        round(fmean(scores), 1),
        {k: round(fmean(v), 1) for k, v in by_competency.items()},
        feedback,
    )


async def evaluate(db: AsyncSession, interview_id: uuid.UUID, now: datetime, *, chat_fn=None) -> bool:
    """`True` — baholandi yoki baholash kerak emas; `False` — AI ishlamadi (qayta urinish mumkin)."""
    interview = await db.get(Interview, interview_id, populate_existing=True)
    if interview is None or interview.status != Status.EVALUATING:
        return True
    pairs = exchanges(interview, await messages(db, interview.id))
    setting = setting_for(interview)
    await db.commit()

    got = await ai.evaluate_interview(setting, pairs, chat_fn=chat_fn or chat)

    interview = await db.scalar(
        select(Interview).where(Interview.id == interview_id).with_for_update().execution_options(populate_existing=True)
    )
    if interview is None or interview.status != Status.EVALUATING:
        await db.rollback()
        return True
    if got is None:
        interview.eval_attempts += 1
        await db.commit()
        return False
    review, result = got
    interview.score, interview.competency_scores, interview.feedback = aggregate(interview, review)
    interview.status = Status.COMPLETED
    interview.evaluated_at = now
    interview.tokens_used += result.tokens
    await db.commit()
    return True


async def mark_failed(db: AsyncSession, interview_id: uuid.UUID) -> None:
    await db.execute(
        update(Interview).where(Interview.id == interview_id, Interview.status == Status.EVALUATING)
        .values(status=Status.FAILED)
    )
    await db.commit()
