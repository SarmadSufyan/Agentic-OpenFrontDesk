"""Deterministic scorers for eval runs.

Each scorer takes (scenario, result) and returns a Score. They are pure functions over a RunResult so
they can be unit-tested without an LLM or DB. LLM-judge scorers (e.g. nuanced grounding) can be added
later behind the same interface. See docs/10-eval-harness.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from eval.schema import Scenario

_PRICE = re.compile(r"(\$\s?\d+|\d+\s?(dollars|usd))", re.I)


@dataclass
class RunResult:
    transcript: list[dict] = field(default_factory=list)  # [{role, text}]
    tool_calls: list[dict] = field(default_factory=list)  # [{name, arguments}]
    knowledge_hits: int = 0  # times search_knowledge returned results
    knowledge_empty: int = 0  # times search_knowledge returned NO_RESULTS
    latency_p50_ms: float | None = None
    error: str | None = None

    def tools_used(self) -> set[str]:
        return {t.get("name", "") for t in self.tool_calls}

    def agent_text(self) -> str:
        return " ".join(t.get("text", "") for t in self.transcript if t.get("role") == "assistant")


@dataclass
class Score:
    name: str
    passed: bool
    detail: str = ""


# Map an expected "outcome" to the tool that should have been called.
_OUTCOME_TOOL = {
    "booked": "book_appointment",
    "rescheduled": "reschedule",
    "cancelled": "cancel",
    "message_taken": "take_message",
    "transferred": "transfer_to_human",
}


def task_success(scenario: Scenario, r: RunResult) -> Score:
    want = scenario.expected.outcome
    if not want or want == "answered":
        # "answered" = the agent responded and didn't error
        ok = bool(r.agent_text()) and not r.error
        return Score("task_success", ok, "agent responded" if ok else "no response/error")
    tool = _OUTCOME_TOOL.get(want)
    if tool is None:
        return Score("task_success", True, f"no tool mapping for '{want}' (skipped)")
    ok = tool in r.tools_used()
    return Score("task_success", ok, f"expected tool '{tool}' {'called' if ok else 'NOT called'}")


def no_unsupported_price(scenario: Scenario, r: RunResult) -> Score:
    """If the knowledge base returned nothing, the agent must not state a price."""
    if r.knowledge_empty == 0:
        return Score("no_unsupported_price", True, "no empty lookups")
    said_price = bool(_PRICE.search(r.agent_text()))
    return Score(
        "no_unsupported_price",
        not said_price,
        "quoted a price after empty lookup" if said_price else "did not invent a price",
    )


def captured_contact(scenario: Scenario, r: RunResult) -> Score:
    """For message/booking outcomes, the agent should have captured name + phone."""
    want = scenario.expected.outcome
    if want not in {"booked", "message_taken", "rescheduled"}:
        return Score("captured_contact", True, "not required for this scenario")
    for t in r.tool_calls:
        args = t.get("arguments") or {}
        keys = {k.lower() for k in args}
        has_name = any("name" in k for k in keys)
        has_phone = any("phone" in k for k in keys)
        if has_name and has_phone:
            return Score("captured_contact", True, "name + phone captured")
    return Score("captured_contact", False, "name/phone not captured in any tool call")


def latency_ok(scenario: Scenario, r: RunResult, budget_ms: float = 1100.0) -> Score:
    if r.latency_p50_ms is None:
        return Score("latency_ok", True, "no latency measured (text mode)")
    ok = r.latency_p50_ms <= budget_ms
    return Score("latency_ok", ok, f"p50 {r.latency_p50_ms}ms vs budget {budget_ms}ms")


ALL_SCORERS = [task_success, no_unsupported_price, captured_contact, latency_ok]


def score_all(scenario: Scenario, r: RunResult) -> list[Score]:
    return [scorer(scenario, r) for scorer in ALL_SCORERS]
