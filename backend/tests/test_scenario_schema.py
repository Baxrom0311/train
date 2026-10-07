"""scenario/schema.py — ssenariy YAML validatsiyasi (CONTRACT.md §9.3). DB kerak emas."""
import copy
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.models.enums import NodeType
from app.scenario.schema import ScenarioDefinition, scenario_warnings

FIXTURE = Path(__file__).parent / "fixtures" / "scenarios" / "elon-market-backend-day1.yaml"
RAW = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


def raw() -> dict:
    return copy.deepcopy(RAW)


def node(data: dict, node_id: str) -> dict:
    return next(n for n in data["nodes"] if n["id"] == node_id)


def test_fixture_is_valid():
    defn = ScenarioDefinition.model_validate(RAW)
    assert defn.node("bug_orders").type == NodeType.TASK
    assert defn.node("standup").from_ == "dilnoza"
    assert defn.node("lead_followup").after.event == "submitted"
    assert scenario_warnings(defn) == []


def test_round_trips_through_json():
    defn = ScenarioDefinition.model_validate(RAW)
    dumped = defn.model_dump(mode="json", by_alias=True)
    assert ScenarioDefinition.model_validate(dumped) == defn


def _invalid(mutate, match):
    data = raw()
    mutate(data)
    with pytest.raises(ValidationError, match=match):
        ScenarioDefinition.model_validate(data)


def test_lunch_time_rejected():
    _invalid(lambda d: node(d, "incident_payments").update(at="13:00"), "ish vaqtiga tushmaydi")


def test_after_hours_rejected():
    _invalid(lambda d: node(d, "standup").update(at="18:00"), "ish vaqtiga tushmaydi")


def test_unknown_persona_rejected():
    _invalid(lambda d: node(d, "standup").update(**{"from": "ghost"}), "noma'lum personaj")


def test_unknown_document_in_knows_rejected():
    _invalid(lambda d: d["personas"][0]["knows"].append("doc_secret"), "noma'lum hujjat")


def test_both_fixed_and_after_rejected():
    _invalid(lambda d: node(d, "lead_followup").update(day=1, at="10:00"), "aynan bittasi")


def test_day_beyond_duration_rejected():
    _invalid(lambda d: node(d, "standup").update(day=2), "duration_days")


def test_after_cycle_rejected():
    def mutate(d):
        d["nodes"].append({"id": "loop_a", "type": "message", "brief": "a",
                           "after": {"node": "loop_b", "event": "delivered", "minutes": 5}})
        d["nodes"].append({"id": "loop_b", "type": "message", "brief": "b",
                           "after": {"node": "loop_a", "event": "delivered", "minutes": 5}})
    _invalid(mutate, "sikl")


def test_after_submitted_on_message_rejected():
    _invalid(lambda d: node(d, "lead_followup").update(after={"node": "welcome", "event": "submitted", "minutes": 1}),
             "topshirilmaydi")


def test_missing_day_end_rejected():
    _invalid(lambda d: d["nodes"].remove(node(d, "day1_end")), "day_end")


def test_day_end_must_be_last():
    _invalid(lambda d: node(d, "day1_end").update(at="12:00"), "oxirgi")


def test_unknown_node_in_condition_rejected():
    _invalid(lambda d: node(d, "incident_payments").update(when={"missed": "nope"}), "noma'lum node")


def test_score_on_ungraded_node_rejected():
    _invalid(lambda d: node(d, "incident_payments").update(when={"score_lt": {"node": "welcome", "value": 50}}),
             "baholanmaydi")


def test_chose_unknown_option_rejected():
    def mutate(d):
        d["nodes"].insert(0, {"id": "pick", "type": "decision", "day": 1, "at": "10:00", "brief": "Nima qilasiz?",
                              "options": [{"key": "a", "label": "A", "grade": "correct"},
                                          {"key": "b", "label": "B", "grade": "wrong"}]})
        node(d, "incident_payments")["when"] = {"chose": {"node": "pick", "option": "c"}}
    _invalid(mutate, "varianti yo'q")


def test_task_without_deadline_rejected():
    _invalid(lambda d: node(d, "standup").pop("due_in_minutes"), "due_in_minutes")


def test_rubric_on_message_rejected():
    _invalid(lambda d: node(d, "welcome").update(hints=["x"]), "baholanadigan")


def test_duplicate_node_id_rejected():
    _invalid(lambda d: d["nodes"].append(dict(node(d, "welcome"))), "takrorlangan")


def test_unknown_field_rejected():
    _invalid(lambda d: node(d, "standup").update(deadline="soon"), "Extra inputs")


def test_early_missed_check_warns():
    data = raw()
    node(data, "incident_payments")["at"] = "10:00"   # bug_orders dedlayni 11:30
    defn = ScenarioDefinition.model_validate(data)
    assert any("bug_orders" in w for w in scenario_warnings(defn))
