"""Unit tests for the eval harness (pure — no LLM or DB)."""

from __future__ import annotations

from eval.schema import Expected, Scenario, load_scenarios
from eval.scorers import RunResult, captured_contact, no_unsupported_price, task_success


def test_scenarios_load() -> None:
    scenarios = load_scenarios()
    assert len(scenarios) >= 4
    for s in scenarios:
        assert s.id and s.goal


def _sc(outcome: str) -> Scenario:
    return Scenario(id="t", goal="g", expected=Expected(outcome=outcome))


def test_task_success_detects_booking_tool() -> None:
    r = RunResult(tool_calls=[{"name": "book_appointment", "arguments": {}}])
    assert task_success(_sc("booked"), r).passed is True
    r2 = RunResult(tool_calls=[{"name": "search_knowledge", "arguments": {}}])
    assert task_success(_sc("booked"), r2).passed is False


def test_no_unsupported_price_flags_invented_price() -> None:
    invented = RunResult(
        knowledge_empty=1,
        transcript=[{"role": "assistant", "text": "That'll be $250 for whitening."}],
    )
    assert no_unsupported_price(_sc("message_taken"), invented).passed is False

    safe = RunResult(
        knowledge_empty=1,
        transcript=[{"role": "assistant", "text": "I'm not sure — let me take a message."}],
    )
    assert no_unsupported_price(_sc("message_taken"), safe).passed is True


def test_captured_contact_requires_name_and_phone() -> None:
    good = RunResult(
        tool_calls=[
            {"name": "book_appointment", "arguments": {"customer_name": "Jo", "phone": "123"}}
        ]
    )
    assert captured_contact(_sc("booked"), good).passed is True

    bad = RunResult(tool_calls=[{"name": "book_appointment", "arguments": {"service": "cleaning"}}])
    assert captured_contact(_sc("booked"), bad).passed is False
