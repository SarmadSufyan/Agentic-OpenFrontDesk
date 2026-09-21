"""Text-mode eval runner.

Drives a scenario as a text conversation: a synthetic "caller" LLM talks to the agent's brain (our
LLM + the real tools/services), then scorers grade the result. This exercises the LLM + tools + RAG
logic without audio (fast path). The full audio path (real STT/TTS) is added later.

Running requires an LLM provider key (GROQ_API_KEY for the free stack) and a seeded tenant/DB. It uses
our own provider abstraction, so it stays provider-agnostic. Imports are lazy where heavy.
"""

from __future__ import annotations

import time

from eval.schema import Scenario
from eval.scorers import RunResult, score_all

from ofd.agent.prompt import build_instructions
from ofd.providers.base import Message, ToolSpec
from ofd.providers.registry import get_llm

MAX_TURNS = 8

TOOL_SPECS = [
    ToolSpec(
        "search_knowledge",
        "Look up facts about services, prices, hours, policies, location.",
        {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    ),
    ToolSpec(
        "check_availability",
        "Find open appointment slots.",
        {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "on_date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
            },
        },
    ),
    ToolSpec(
        "book_appointment",
        "Book an appointment once the caller agrees to a time.",
        {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "phone": {"type": "string"},
                "start_time": {"type": "string"},
                "service": {"type": "string"},
            },
            "required": ["customer_name", "phone", "start_time"],
        },
    ),
    ToolSpec(
        "take_message",
        "Capture a message when you can't fully help.",
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "phone": {"type": "string"},
                "message": {"type": "string"},
            },
            "required": ["name", "phone", "message"],
        },
    ),
    ToolSpec(
        "transfer_to_human",
        "Use when the caller wants a person or is upset.",
        {"type": "object", "properties": {}},
    ),
]


async def _dispatch(name: str, args: dict, *, tenant, slot_minutes: int, r: RunResult) -> str:
    from datetime import datetime

    from ofd.db.session import session_scope
    from ofd.rag import retrieve
    from ofd.services import booking as booking_svc
    from ofd.services import knowledge as knowledge_svc
    from ofd.services import leads as leads_svc

    r.tool_calls.append({"name": name, "arguments": args})
    try:
        if name == "search_knowledge":
            async with session_scope() as db:
                hits = await knowledge_svc.search(
                    db, tenant_id=tenant.id, query=args.get("query", "")
                )
            if not hits:
                r.knowledge_empty += 1
                return "NO_RESULTS"
            r.knowledge_hits += 1
            return retrieve.format_context(hits)
        if name == "check_availability":
            async with session_scope() as db:
                slots = await booking_svc.check_availability(
                    db, tenant, service=args.get("service"), slot_minutes=slot_minutes
                )
            return "; ".join(s.start.strftime("%A %b %d %I:%M %p") for s in slots) or "No slots"
        if name == "book_appointment":
            start = datetime.fromisoformat(args["start_time"])
            async with session_scope() as db:
                bk = await booking_svc.book(
                    db,
                    tenant,
                    name=args["customer_name"],
                    phone=args["phone"],
                    service=args.get("service"),
                    start_at=start,
                    slot_minutes=slot_minutes,
                )
            return f"BOOKED {bk.service} {bk.start_at.isoformat()}"
        if name == "take_message":
            async with session_scope() as db:
                await leads_svc.capture_lead(
                    db,
                    tenant_id=tenant.id,
                    name=args.get("name"),
                    phone=args.get("phone"),
                    message=args.get("message"),
                    intent="message",
                )
            return "CAPTURED"
        if name == "transfer_to_human":
            return "TRANSFER_REQUESTED"
    except Exception as exc:  # tools must never crash the run
        return f"TOOL_ERROR: {exc}"
    return "UNKNOWN_TOOL"


async def _agent_reply(messages: list[Message], *, with_tools: bool) -> tuple[str, list]:
    llm = get_llm()
    text, tool_calls = "", []
    async for delta in llm.complete(messages, tools=TOOL_SPECS if with_tools else None):
        text += delta.text
        tool_calls.extend(delta.tool_calls)
    return text, tool_calls


async def _caller_says(scenario: Scenario, transcript: list[dict]) -> str:
    convo = "\n".join(f"{t['role']}: {t['text']}" for t in transcript) or "(start of call)"
    sys = (
        f"You are a caller phoning a business. Persona: {scenario.persona or 'a customer'}. "
        f"Your goal: {scenario.goal}. Hints: {', '.join(scenario.script_hints) or 'none'}. "
        "Say ONLY your next short line as the caller. If your goal is met or the call is wrapping up, "
        "say a brief goodbye."
    )
    text, _ = await _agent_reply(
        [
            Message("system", sys),
            Message("user", f"Conversation so far:\n{convo}\n\nYour next line:"),
        ],
        with_tools=False,
    )
    return text.strip() or "Hello?"


async def run_scenario_text(scenario: Scenario, *, tenant, slot_minutes: int = 30) -> RunResult:
    r = RunResult()
    t0 = time.perf_counter()
    instructions = build_instructions(business_name=tenant.name, timezone=tenant.timezone)
    messages: list[Message] = [Message("system", instructions)]
    try:
        for _ in range(MAX_TURNS):
            caller = await _caller_says(scenario, r.transcript)
            r.transcript.append({"role": "user", "text": caller})
            messages.append(Message("user", caller))
            if any(
                w in caller.lower()
                for w in ("goodbye", "bye", "thanks, that's all", "thank you, bye")
            ):
                break

            text, tool_calls = await _agent_reply(messages, with_tools=True)
            if tool_calls:
                summary = []
                for tc in tool_calls:
                    res = await _dispatch(
                        tc.name, tc.arguments, tenant=tenant, slot_minutes=slot_minutes, r=r
                    )
                    summary.append(f"{tc.name} -> {res}")
                messages.append(
                    Message(
                        "system",
                        "Tool results:\n"
                        + "\n".join(summary)
                        + "\nNow reply to the caller in one short line.",
                    )
                )
                text, _ = await _agent_reply(messages, with_tools=False)

            r.transcript.append({"role": "assistant", "text": text})
            messages.append(Message("assistant", text))
    except Exception as exc:
        r.error = str(exc)
    r.latency_p50_ms = round((time.perf_counter() - t0) * 1000, 1)
    return r


async def run_suite(scenarios: list[Scenario], *, tenant_slug: str = "demo") -> int:
    """Run all scenarios against a seeded tenant, print a report, return the number of failures."""
    from ofd.db.session import session_scope
    from ofd.services import tenants as tenants_svc

    async with session_scope() as db:
        tenant = await tenants_svc.get_tenant_by_slug(db, tenant_slug)
        agent = await tenants_svc.get_default_agent(db, tenant.id) if tenant else None
    if tenant is None:
        print(f"Tenant '{tenant_slug}' not found — run scripts/seed_demo.py first.")
        return 1
    slot_minutes = int((agent.booking_rules or {}).get("slot_minutes", 30)) if agent else 30

    failures = 0
    for sc in scenarios:
        r = await run_scenario_text(sc, tenant=tenant, slot_minutes=slot_minutes)
        scores = score_all(sc, r)
        passed = all(s.passed for s in scores)
        failures += 0 if passed else 1
        mark = "PASS" if passed else "FAIL"
        print(f"[{mark}] {sc.id}")
        for s in scores:
            print(f"        {'✓' if s.passed else '✗'} {s.name}: {s.detail}")
        if r.error:
            print(f"        ! error: {r.error}")
    print(f"\n{len(scenarios) - failures}/{len(scenarios)} scenarios passed.")
    return failures
