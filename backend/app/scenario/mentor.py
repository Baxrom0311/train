"""
Mentor: talabaning ishini ko'radi va o'zi yozadi (CONTRACT.md §9.13).

- `student_work_lines` — mentor chati kontekstiga talabaning topshirgan
  ishlari va baholari (`scenario/persona.py` chaqiradi).
- `post_review` — baholash tugagach mentor chatiga task izohi. Baholash
  job'i ichida chaqiriladi; `chat_messages.submission_id` UNIQUE bo'lgani
  uchun qayta chaqiruv ikkinchi izoh yozmaydi. AI ishlamasa ham izoh
  yoziladi — baholovchining `short_feedback`idan skript matn.

Dedlayn eslatmasi (`nudge`) LLM'siz va dvigatel ichida (`engine.RunState.nudge`).
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.mentor import CriterionView, ReviewContext, mentor_review
from app.ai.persona_chat import PersonaProfile
from app.ai.spoiler import is_spoiler
from app.models.enums import AIEvalStatus, ChatSender, NodeType, RunStatus
from app.models.scenario import CHAT_PURPOSE_REVIEW, ChatMessage, Run, RunEvent, ScenarioVersion
from app.models.simulation import Submission
from app.notifications.run_events import review_posted
from app.scenario.engine import Note, definition_for
from app.scenario.limits import RUN_AI_TOKEN_BUDGET
from app.scenario.reports import task_title
from app.scenario.schema import Node, Persona, ScenarioDefinition, short_title

log = logging.getLogger(__name__)

REVIEWED_TYPES = (NodeType.TASK, NodeType.INCIDENT)
# bundan past ballda (urinish qolgan bo'lsa) qayta topshirish taklif qilinadi
RESUBMIT_BELOW = 80.0
# mentor kontekstidagi talaba javobi parchasi
ANSWER_EXCERPT = 600


def profile(persona: Persona) -> PersonaProfile:
    return PersonaProfile(
        key=persona.key, name=persona.name, role=persona.role, kind=persona.kind.value,
        tone=persona.tone, secrets=tuple(persona.secrets),
    )


def _criteria(node: Node, sub: Submission) -> list[CriterionView]:
    descriptions = {c.id: c.description for c in node.rubric}
    return [
        CriterionView(
            description=descriptions.get(c["id"], "Umumiy bajarilish"),
            score=float(c["score"]),
            evidence=c.get("evidence") or "",
        )
        for c in (sub.rubric_scores or {}).get("criteria", [])
    ]


def can_resubmit(run: Run, node: Node, sub: Submission) -> int:
    """Qayta topshirish taklif qilinadigan urinishlar soni (0 — taklif yo'q)."""
    left = node.max_attempts - sub.attempt
    if run.status != RunStatus.ACTIVE or left <= 0 or (sub.ai_score or 0) >= RESUBMIT_BELOW:
        return 0
    return left


def fallback_review(node: Node, sub: Submission, attempts_left: int) -> str:
    feedback = sub.ai_feedback or "javobingizni ko'rib chiqdim."
    text = f"«{short_title(node.brief)}» bo'yicha qisqa izohim: {feedback}"
    if attempts_left:
        text += f" Yana {attempts_left} ta urinishingiz bor — xohlasangiz tuzatib qayta topshiring."
    return text


def student_work_lines(
    defn: ScenarioDefinition, events: Sequence[RunEvent], submissions: Sequence[Submission]
) -> list[str]:
    """Har task/incident bo'yicha oxirgi urinish: baho, izoh, eng zaif mezon, javob boshi."""
    latest: dict[uuid.UUID, Submission] = {}
    counts: dict[uuid.UUID, int] = {}
    for s in submissions:
        counts[s.run_event_id] = counts.get(s.run_event_id, 0) + 1
        if s.run_event_id not in latest or s.attempt > latest[s.run_event_id].attempt:
            latest[s.run_event_id] = s
    lines = []
    for e in events:
        sub = latest.get(e.id)
        node = defn.node(e.node_id)
        if sub is None or node.type not in REVIEWED_TYPES:
            continue
        parts = [f"«{task_title(node)}»: urinish {counts[e.id]}/{node.max_attempts}"]
        if sub.ai_eval_status == AIEvalStatus.COMPLETED and sub.ai_score is not None:
            parts.append(f"ball {round(sub.ai_score)}")
            if sub.ai_feedback:
                parts.append(f"baholovchi: {sub.ai_feedback}")
            criteria = _criteria(node, sub)
            if criteria:
                weak = min(criteria, key=lambda c: c.score)
                parts.append(f"eng zaif mezon: {weak.description} ({weak.evidence})")
        elif sub.ai_eval_status in (AIEvalStatus.PENDING, AIEvalStatus.QUEUED_RETRY):
            parts.append("hali baholanmoqda")
        if sub.late:
            parts.append("kech topshirilgan")
        excerpt = sub.content[:ANSWER_EXCERPT] + ("…" if len(sub.content) > ANSWER_EXCERPT else "")
        parts.append(f"javob: <data>{excerpt}</data>")
        lines.append("; ".join(parts))
    return lines


async def post_review(
    db: AsyncSession,
    submission_id,
    now: datetime,
    *,
    review_fn=mentor_review,
    spoiler_fn=is_spoiler,
) -> Note | None:
    """Mentor izohini yozadi va commit qiladi; yozilmasa (mentor yo'q, allaqachon bor...) → `None`."""
    sub = await db.get(Submission, submission_id)
    if sub is None or sub.run_event_id is None or sub.ai_eval_status != AIEvalStatus.COMPLETED:
        return None
    if await db.scalar(select(ChatMessage.id).where(ChatMessage.submission_id == sub.id)):
        return None
    event = await db.get(RunEvent, sub.run_event_id)
    run = (await db.execute(
        select(Run).where(Run.id == sub.run_id).options(
            selectinload(Run.scenario_version).selectinload(ScenarioVersion.scenario)
        )
    )).scalars().one()
    defn = definition_for(run.scenario_version)
    mentor = defn.mentor
    node = defn.node(event.node_id)
    if mentor is None or node.type not in REVIEWED_TYPES:
        return None

    attempts_left = can_resubmit(run, node, sub)
    body, generated, tokens = None, False, 0
    if run.ai_tokens_used < RUN_AI_TOKEN_BUDGET:
        ctx = ReviewContext(
            persona=profile(mentor),
            company_name=run.scenario_version.scenario.company_name,
            task_title=task_title(node),
            brief=node.brief,
            answer=sub.content,
            criteria=_criteria(node, sub),
            late=sub.late,
            hints_used=event.hints_used,
            attempts_left=attempts_left,
            hints=tuple(node.hints),
        )
        result = await review_fn(ctx)
        if result is not None:
            tokens = result.tokens
            message = result.data.message.strip()
            references = [n.reference_answer for n in defn.nodes if n.reference_answer]
            if await spoiler_fn(message, references):
                log.info("mentor izohi anti-spoiler'da to'xtadi (submission=%s)", sub.id)
            else:
                body, generated = message, True
    if body is None:
        body = fallback_review(node, sub, attempts_left)

    reply = ChatMessage(
        run_id=run.id, persona_key=mentor.key, sender=ChatSender.PERSONA, body=body,
        generated=generated, created_at=now, purpose=CHAT_PURPOSE_REVIEW, node_id=node.id, submission_id=sub.id,
    )
    db.add(reply)
    await review_posted(db, run, node.id, task_title(node), mentor.name, sub.id, now)   # §15.2
    if tokens:
        await db.execute(update(Run).where(Run.id == run.id).values(ai_tokens_used=Run.ai_tokens_used + tokens))
    try:
        await db.commit()
    except IntegrityError:
        # parallel job allaqachon yozgan
        await db.rollback()
        return None
    return Note(run.id, "chat_message", {"persona_key": mentor.key, "id": str(reply.id)})
