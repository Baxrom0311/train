"""
Node `when` shartlari — v1 cheklangan DSL (CONTRACT.md §9.3.3).

Faqat quyidagi predikatlar, `all`/`any` bilan birlashtiriladi; ixtiyoriy
kod/ifoda yo'q:

    score_lt: {node, value}      score_gte: {node, value}
    missed: node                 submitted: node
    chose: {node, option}        flag: name

Baholash sof funksiya: Run holati `ConditionContext` sifatida beriladi.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Union

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ScoreRef(_Strict):
    node: str
    value: float = Field(ge=0, le=100)


class ChoiceRef(_Strict):
    node: str
    option: str


class ScoreLt(_Strict):
    score_lt: ScoreRef


class ScoreGte(_Strict):
    score_gte: ScoreRef


class Missed(_Strict):
    missed: str


class Submitted(_Strict):
    submitted: str


class Chose(_Strict):
    chose: ChoiceRef


class FlagSet(_Strict):
    flag: str


class AllOf(_Strict):
    all: list[Condition] = Field(min_length=1)


class AnyOf(_Strict):
    any: list[Condition] = Field(min_length=1)


Condition = Union[AllOf, AnyOf, ScoreLt, ScoreGte, Missed, Submitted, Chose, FlagSet]
AllOf.model_rebuild()
AnyOf.model_rebuild()


@dataclass(frozen=True)
class ConditionContext:
    """
    Shart tekshirilayotgan paytdagi Run holati.

    - `submitted` — kamida bir marta topshirilgan node'lar;
    - `missed` — dedlayni o'tgan node'lar (keyin kech topshirilganlari ham);
    - `scores` — oxirgi **baholangan** urinish balli (§9.0 Q11);
    - `awaiting_score` — topshirilgan, lekin baho hali tayyor emas;
    - `choices` — `decision` node'larida tanlangan variant;
    - `flags` — qaror variantlari qo'ygan bayroqlar.
    """
    submitted: frozenset[str] = frozenset()
    missed: frozenset[str] = frozenset()
    scores: Mapping[str, float] = field(default_factory=dict)
    awaiting_score: frozenset[str] = frozenset()
    choices: Mapping[str, str] = field(default_factory=dict)
    flags: frozenset[str] = frozenset()


def evaluate(cond: Condition | None, ctx: ConditionContext) -> bool:
    """Shart yo'q → True. Baho hali yo'q `score_*` predikati → False (§9.3.3)."""
    if cond is None:
        return True
    if isinstance(cond, AllOf):
        return all(evaluate(c, ctx) for c in cond.all)
    if isinstance(cond, AnyOf):
        return any(evaluate(c, ctx) for c in cond.any)
    if isinstance(cond, ScoreLt):
        score = ctx.scores.get(cond.score_lt.node)
        return score is not None and score < cond.score_lt.value
    if isinstance(cond, ScoreGte):
        score = ctx.scores.get(cond.score_gte.node)
        return score is not None and score >= cond.score_gte.value
    if isinstance(cond, Missed):
        return cond.missed in ctx.missed
    if isinstance(cond, Submitted):
        return cond.submitted in ctx.submitted
    if isinstance(cond, Chose):
        return ctx.choices.get(cond.chose.node) == cond.chose.option
    if isinstance(cond, FlagSet):
        return cond.flag in ctx.flags
    raise TypeError(f"noma'lum shart turi: {type(cond).__name__}")


def iter_leaves(cond: Condition | None) -> Iterator[Condition]:
    """`all`/`any` ichidagi barcha predikatlar (validatsiya va kutish uchun)."""
    if cond is None:
        return
    if isinstance(cond, AllOf):
        for c in cond.all:
            yield from iter_leaves(c)
    elif isinstance(cond, AnyOf):
        for c in cond.any:
            yield from iter_leaves(c)
    else:
        yield cond


def referenced_nodes(cond: Condition | None) -> set[str]:
    """Shart havola qiladigan node id'lari (`flag`dan tashqari)."""
    refs: set[str] = set()
    for leaf in iter_leaves(cond):
        if isinstance(leaf, ScoreLt):
            refs.add(leaf.score_lt.node)
        elif isinstance(leaf, ScoreGte):
            refs.add(leaf.score_gte.node)
        elif isinstance(leaf, Missed):
            refs.add(leaf.missed)
        elif isinstance(leaf, Submitted):
            refs.add(leaf.submitted)
        elif isinstance(leaf, Chose):
            refs.add(leaf.chose.node)
    return refs


def score_nodes(cond: Condition | None) -> set[str]:
    """`score_lt`/`score_gte` havola qiladigan node'lar."""
    refs: set[str] = set()
    for leaf in iter_leaves(cond):
        if isinstance(leaf, ScoreLt):
            refs.add(leaf.score_lt.node)
        elif isinstance(leaf, ScoreGte):
            refs.add(leaf.score_gte.node)
    return refs


def pending_scores(cond: Condition | None, ctx: ConditionContext) -> set[str]:
    """
    Hali birorta ham bahosi yo'q, lekin baholanayotgan `score_*` havolalari.
    Bo'sh bo'lmasa dvigatel yetkazishni kechiktiradi (ko'pi bilan 15 daqiqa,
    §9.3.3). Oldingi urinishning bahosi bor bo'lsa kutilmaydi — shart
    o'sha paytdagi oxirgi tayyor ballni ko'radi.
    """
    return (score_nodes(cond) & set(ctx.awaiting_score)) - set(ctx.scores)
