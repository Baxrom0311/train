"""scenario/conditions.py — `when` DSL (CONTRACT.md §9.3.3). DB kerak emas."""
import pytest
from pydantic import TypeAdapter, ValidationError

from app.scenario.conditions import (
    AnyOf,
    Condition,
    ConditionContext,
    evaluate,
    pending_scores,
    referenced_nodes,
)

parse = TypeAdapter(Condition).validate_python

INCIDENT_WHEN = {"any": [{"missed": "bug_orders"}, {"score_lt": {"node": "bug_orders", "value": 60}}]}


def test_parses_spec_example():
    cond = parse(INCIDENT_WHEN)
    assert isinstance(cond, AnyOf)
    assert referenced_nodes(cond) == {"bug_orders"}


@pytest.mark.parametrize(
    "ctx, expected",
    [
        (ConditionContext(), False),
        (ConditionContext(missed=frozenset({"bug_orders"})), True),
        (ConditionContext(scores={"bug_orders": 59.9}), True),
        (ConditionContext(scores={"bug_orders": 60}), False),
        (ConditionContext(awaiting_score=frozenset({"bug_orders"})), False),
    ],
)
def test_incident_condition(ctx, expected):
    assert evaluate(parse(INCIDENT_WHEN), ctx) is expected


def test_all_and_leaf_predicates():
    cond = parse({"all": [
        {"submitted": "a"},
        {"score_gte": {"node": "a", "value": 80}},
        {"chose": {"node": "d", "option": "escalate"}},
        {"flag": "told_lead"},
    ]})
    ctx = ConditionContext(
        submitted=frozenset({"a"}),
        scores={"a": 80},
        choices={"d": "escalate"},
        flags=frozenset({"told_lead"}),
    )
    assert evaluate(cond, ctx)
    assert not evaluate(cond, ConditionContext(submitted=frozenset({"a"}), scores={"a": 80}))
    assert referenced_nodes(cond) == {"a", "d"}


def test_no_condition_is_true():
    assert evaluate(None, ConditionContext())


def test_pending_scores_waits_only_without_any_score():
    cond = parse(INCIDENT_WHEN)
    waiting = ConditionContext(awaiting_score=frozenset({"bug_orders"}))
    assert pending_scores(cond, waiting) == {"bug_orders"}
    # 2-urinish baholanmoqda, lekin 1-urinishning bahosi bor → kutilmaydi
    resubmitted = ConditionContext(awaiting_score=frozenset({"bug_orders"}), scores={"bug_orders": 40})
    assert pending_scores(cond, resubmitted) == set()


@pytest.mark.parametrize(
    "raw",
    [
        {"missed": "a", "submitted": "b"},          # bitta predikatda ikki kalit
        {"score_lt": {"node": "a", "value": 120}},  # 0..100 dan tashqari
        {"any": []},
        {"eval": "__import__('os')"},               # ixtiyoriy ifoda taqiqlangan
        {"not": {"missed": "a"}},
    ],
)
def test_invalid_conditions_rejected(raw):
    with pytest.raises(ValidationError):
        parse(raw)
