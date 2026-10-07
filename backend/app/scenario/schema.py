"""
Ssenariy YAML'ining Pydantic sxemasi va validatsiyasi (CONTRACT.md §9.3).

Manba: `backend/content/scenarios/<slug>.yaml`. `tools/import_scenario.py`
shu sxema bilan tekshiradi, `ScenarioDefinition.model_dump(mode="json")`
esa `scenario_versions.definition` JSONB'ga yoziladi.

Sxema darajasidagi xatolar → `ValidationError` (import rad etiladi).
Ogohlantirishlar (import qilinadi, lekin muallif ko'rishi kerak) →
`scenario_warnings()`.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import Competency, NodeType, Sector
from app.scenario.clock import WorkCalendar, parse_hhmm
from app.scenario.conditions import (
    Chose,
    Condition,
    iter_leaves,
    referenced_nodes,
    score_nodes,
)

_KEY = r"^[a-z][a-z0-9_]{0,63}$"
_SLUG = r"^[a-z0-9][a-z0-9-]{1,79}$"

# Ish bo'laklari validatsiya uchun — bayramlar bu yerda ahamiyatsiz.
_CALENDAR = WorkCalendar()

GRADED_TYPES = frozenset({NodeType.TASK, NodeType.INCIDENT, NodeType.DECISION, NodeType.DAY_END})
ANSWER_TYPES = frozenset({NodeType.TASK, NodeType.INCIDENT})


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class AnswerType(str, Enum):
    TEXT = "text"
    FILE = "file"
    LINK = "link"
    CODE = "code"


class PersonaKind(str, Enum):
    COLLEAGUE = "colleague"
    MENTOR = "mentor"  # §9.4: javobni aytmaydi, yo'naltiradi; hint beradi


class Persona(_Strict):
    key: str = Field(pattern=_KEY)
    name: str = Field(min_length=1, max_length=80)
    role: str = Field(min_length=1, max_length=120)
    kind: PersonaKind = PersonaKind.COLLEAGUE
    tone: str = ""
    knows: list[str] = []
    secrets: list[str] = []
    # AI ishlamasa yoki limit tugaganda (§9.4)
    busy_reply: str = "Hozir band edim, keyinroq yozing."
    # Anti-spoiler AI javobini bloklaganda (§9.4, 3-qavat)
    deflect_reply: str = "Buni o'zingiz hal qilib ko'ring — brief va hujjatlarni yana bir ko'rib chiqing."


class Document(_Strict):
    """Kompaniya wiki'si, siyosat, ma'lumot — RAG indeksiga kiradi (§9.4)."""
    key: str = Field(pattern=_KEY)
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)


class RubricCriterion(_Strict):
    id: str = Field(pattern=_KEY)
    description: str = Field(min_length=1)
    weight: float = Field(default=1.0, gt=0)


class DecisionOption(_Strict):
    key: str = Field(pattern=_KEY)
    label: str = Field(min_length=1)
    grade: Literal["correct", "acceptable", "wrong"]
    flag: str | None = Field(default=None, pattern=_KEY)


class After(_Strict):
    node: str
    event: Literal["delivered", "submitted"]
    minutes: int = Field(ge=0, le=480 * 5)


class Node(_Strict):
    id: str = Field(pattern=_KEY)
    type: NodeType
    # Vaqt: yoki `day` + `at`, yoki `after` (§9.2)
    day: int | None = Field(default=None, ge=1)
    at: str | None = None
    after: After | None = None
    when: Condition | None = None
    from_: str | None = Field(default=None, alias="from")

    brief: str = ""
    attachments: list[str] = []
    answer_types: list[AnswerType] = []
    due_in_minutes: int | None = Field(default=None, gt=0, le=480 * 5)
    weight: float = Field(default=1.0, gt=0)
    competencies: list[Competency] = []

    # Faqat baholovchi / mentor ko'radi — RAG'ga hech qachon kirmaydi (§9.4)
    rubric: list[RubricCriterion] = []
    checks: dict | None = None
    hints: list[str] = []
    reference_answer: str | None = None

    options: list[DecisionOption] = []
    max_attempts: int = Field(default=3, ge=1, le=10)
    late_penalty: float = Field(default=0.2, ge=0, le=1)
    hint_penalty: float = Field(default=0.1, ge=0, le=1)

    @field_validator("at")
    @classmethod
    def _at_in_work_hours(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not _CALENDAR.is_work_time(parse_hhmm(v)):
            raise ValueError(f"at={v} ish vaqtiga tushmaydi (09:00–13:00, 14:00–18:00)")
        return v

    @model_validator(mode="after")
    def _shape(self) -> Node:
        fixed = self.day is not None or self.at is not None
        if fixed and (self.day is None or self.at is None):
            raise ValueError(f"{self.id}: `day` va `at` birga beriladi")
        if fixed == (self.after is not None):
            raise ValueError(f"{self.id}: vaqt uchun aynan bittasi kerak — `day`+`at` yoki `after`")
        if self.type in ANSWER_TYPES:
            if not self.brief or not self.answer_types or self.due_in_minutes is None:
                raise ValueError(f"{self.id}: task/incident uchun brief, answer_types, due_in_minutes shart")
        elif self.answer_types:
            raise ValueError(f"{self.id}: answer_types faqat task/incident uchun")
        if self.type == NodeType.DECISION:
            if not self.brief or len(self.options) < 2:
                raise ValueError(f"{self.id}: decision uchun brief va kamida 2 variant kerak")
            if len({o.key for o in self.options}) != len(self.options):
                raise ValueError(f"{self.id}: variant kalitlari takrorlanmasin")
        elif self.options:
            raise ValueError(f"{self.id}: options faqat decision uchun")
        if self.type == NodeType.MESSAGE and (not self.brief or self.due_in_minutes is not None):
            raise ValueError(f"{self.id}: message — matn (brief) bor, dedlayn yo'q")
        if self.type == NodeType.DAY_END and self.after is not None:
            raise ValueError(f"{self.id}: day_end faqat `day`+`at` bilan")
        if self.type not in GRADED_TYPES and (self.rubric or self.reference_answer or self.hints):
            raise ValueError(f"{self.id}: rubric/reference_answer/hints faqat baholanadigan node'da")
        if len({c.id for c in self.rubric}) != len(self.rubric):
            raise ValueError(f"{self.id}: rubric mezon id'lari takrorlanmasin")
        return self

    @property
    def is_graded(self) -> bool:
        return self.type in GRADED_TYPES


class ScenarioDefinition(_Strict):
    slug: str = Field(pattern=_SLUG)
    title: str = Field(min_length=1, max_length=200)
    sector: Sector
    company_name: str = Field(min_length=1, max_length=120)  # faqat fictional (AGENTS.md)
    difficulty: Literal["junior", "middle", "senior"] = "junior"
    duration_days: int = Field(ge=1, le=10)
    personas: list[Persona] = Field(min_length=1)
    documents: list[Document] = []
    nodes: list[Node] = Field(min_length=1)

    @model_validator(mode="after")
    def _references(self) -> ScenarioDefinition:
        _unique("persona", [p.key for p in self.personas])
        _unique("document", [d.key for d in self.documents])
        _unique("node", [n.id for n in self.nodes])

        persona_keys = {p.key for p in self.personas}
        doc_keys = {d.key for d in self.documents}
        nodes = {n.id: n for n in self.nodes}

        for p in self.personas:
            if unknown := set(p.knows) - doc_keys:
                raise ValueError(f"persona {p.key}: noma'lum hujjat(lar) {sorted(unknown)}")

        for n in self.nodes:
            if unknown := set(n.attachments) - doc_keys:
                raise ValueError(f"{n.id}: attachments → noma'lum hujjat(lar) {sorted(unknown)}")
            if n.from_ is not None and n.from_ not in persona_keys:
                raise ValueError(f"{n.id}: noma'lum personaj `{n.from_}`")
            if n.day is not None and n.day > self.duration_days:
                raise ValueError(f"{n.id}: day={n.day} > duration_days={self.duration_days}")
            if n.after is not None and n.after.node not in nodes:
                raise ValueError(f"{n.id}: after → noma'lum node `{n.after.node}`")
            if n.after is not None and n.after.event == "submitted" and not nodes[n.after.node].is_graded:
                raise ValueError(f"{n.id}: `{n.after.node}` topshirilmaydi, after.event=submitted bo'lmaydi")
            _check_condition(n, nodes)

        _check_after_cycles(nodes)

        for day in range(1, self.duration_days + 1):
            ends = [n for n in self.nodes if n.type == NodeType.DAY_END and n.day == day]
            if len(ends) != 1:
                raise ValueError(f"{day}-kun uchun aynan bitta day_end kerak (hozir {len(ends)})")
            last = max(_CALENDAR.node_offset(n.day, n.at) for n in self.nodes if n.day == day)
            if _CALENDAR.node_offset(day, ends[0].at) != last:
                raise ValueError(f"{day}-kun: day_end kunning oxirgi fixed node'i bo'lishi kerak")
        return self

    def node(self, node_id: str) -> Node:
        return next(n for n in self.nodes if n.id == node_id)


def _unique(kind: str, keys: list[str]) -> None:
    seen: set[str] = set()
    for k in keys:
        if k in seen:
            raise ValueError(f"{kind} kaliti takrorlangan: `{k}`")
        seen.add(k)


def _check_condition(n: Node, nodes: dict[str, Node]) -> None:
    for ref in referenced_nodes(n.when):
        if ref not in nodes:
            raise ValueError(f"{n.id}: when → noma'lum node `{ref}`")
        if ref == n.id:
            raise ValueError(f"{n.id}: when o'ziga havola qilmasin")
    for ref in score_nodes(n.when):
        if not nodes[ref].is_graded:
            raise ValueError(f"{n.id}: `{ref}` baholanmaydi, score_* sharti bo'lmaydi")
    for leaf in iter_leaves(n.when):
        if isinstance(leaf, Chose):
            target = nodes[leaf.chose.node]
            if target.type != NodeType.DECISION:
                raise ValueError(f"{n.id}: chose → `{target.id}` decision emas")
            if leaf.chose.option not in {o.key for o in target.options}:
                raise ValueError(f"{n.id}: `{target.id}`da `{leaf.chose.option}` varianti yo'q")


def _check_after_cycles(nodes: dict[str, Node]) -> None:
    for start in nodes.values():
        seen: set[str] = set()
        cur = start
        while cur.after is not None:
            if cur.id in seen:
                raise ValueError(f"after zanjirida sikl: `{start.id}`")
            seen.add(cur.id)
            cur = nodes[cur.after.node]


def scenario_warnings(defn: ScenarioDefinition) -> list[str]:
    """
    Import'ni to'xtatmaydigan, lekin muallif ko'rishi kerak bo'lgan holatlar:
    `missed: X` sharti X'ning eng erta dedlaynidan oldin tekshiriladi
    (bunday shart hech qachon true bo'lmaydi).
    """
    warnings: list[str] = []
    nodes = {n.id: n for n in defn.nodes}
    for n in defn.nodes:
        if n.day is None:
            continue
        check_at = _CALENDAR.node_offset(n.day, n.at)
        for leaf in iter_leaves(n.when):
            target_id = getattr(leaf, "missed", None)
            if target_id is None:
                continue
            target = nodes[target_id]
            if target.day is None or target.due_in_minutes is None:
                continue
            earliest_due = _CALENDAR.node_offset(target.day, target.at) + target.due_in_minutes
            if earliest_due >= check_at:
                warnings.append(
                    f"{n.id}: `missed: {target_id}` tekshirilganda {target_id} dedlayni hali o'tmagan bo'ladi"
                )
    return warnings
