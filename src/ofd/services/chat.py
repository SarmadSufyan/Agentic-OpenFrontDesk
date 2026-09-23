"""Text-chat brain for the embeddable widget.

Grounded RAG + tools over an OpenAI-compatible chat API (Groq / Gemini / OpenAI) via httpx, so the API
image needs no vendor SDKs. Reuses the same tools/services as the voice agent, so widget chats produce
the same leads/bookings in the dashboard. Text is cheap, so this is not concurrency-gated.
"""

from __future__ import annotations

import json
from datetime import datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from ofd.core.config import settings
from ofd.core.exceptions import ProviderError
from ofd.models.agent import Agent
from ofd.models.tenant import Tenant
from ofd.rag import retrieve
from ofd.services import booking as booking_svc
from ofd.services import knowledge as knowledge_svc
from ofd.services import leads as leads_svc

MAX_HISTORY = 8
MAX_TOOL_ROUNDS = 4

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "Look up facts about services, prices, hours, policies, or location. Use for ANY factual question.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Find open appointment slots.",
            "parameters": {
                "type": "object",
                "properties": {"service": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Book an appointment once the visitor agrees to a time. Collect their name first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "phone": {"type": "string"},
                    "start_time": {
                        "type": "string",
                        "description": "ISO 8601, e.g. 2026-09-24T14:30:00",
                    },
                    "service": {"type": "string"},
                },
                "required": ["customer_name", "start_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "take_message",
            "description": "Capture the visitor's message/contact when you can't fully help.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["message"],
            },
        },
    },
]


def _llm_config() -> tuple[str, str, str]:
    """Return (base_url, api_key, model) for the OpenAI-compatible endpoint of the configured provider."""
    p = settings.LLM_PROVIDER.lower()
    if p == "gemini":
        return (
            "https://generativelanguage.googleapis.com/v1beta/openai",
            settings.GEMINI_API_KEY,
            settings.GEMINI_LLM_MODEL,
        )
    if p == "openai":
        return ("https://api.openai.com/v1", settings.OPENAI_API_KEY, "gpt-4o-mini")
    return ("https://api.groq.com/openai/v1", settings.GROQ_API_KEY, settings.GROQ_LLM_MODEL)


async def _llm(messages: list[dict], tools: list | None = None) -> dict:
    base, key, model = _llm_config()
    if not key:
        raise ProviderError("LLM API key not configured for widget chat")
    payload: dict = {"model": model, "messages": messages, "max_tokens": 700, "temperature": 0.3}
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json=payload,
        )
    if resp.status_code != 200:
        raise ProviderError(f"LLM error {resp.status_code}: {resp.text[:200]}")
    return resp.json()["choices"][0]["message"]


def _system_prompt(tenant: Tenant, agent: Agent | None) -> str:
    name = tenant.name
    return (
        f"You are the website assistant for {name}. You are friendly and concise.\n"
        "Rules:\n"
        "- Answer ONLY using facts from search_knowledge. If it returns NO_RESULTS, say you're not sure "
        "and offer to take a message. NEVER invent prices, hours, availability, or policy.\n"
        "- Use check_availability then book_appointment to schedule; collect the visitor's name (and "
        "phone if booking).\n"
        "- Keep replies short and helpful. This is a website chat."
    )


async def _run_tool(
    db: AsyncSession, name: str, args: dict, *, tenant: Tenant, agent: Agent | None, sources: set
) -> str:
    slot = int((agent.booking_rules or {}).get("slot_minutes", 30)) if agent else 30
    try:
        if name == "search_knowledge":
            hits = await knowledge_svc.search(db, tenant_id=tenant.id, query=args.get("query", ""))
            for h in hits:
                if h.source_title:
                    sources.add(h.source_title)
            return retrieve.format_context(hits) if hits else "NO_RESULTS"
        if name == "check_availability":
            slots = await booking_svc.check_availability(
                db, tenant, service=args.get("service"), slot_minutes=slot
            )
            return (
                "; ".join(s.start.strftime("%A %b %d %I:%M %p") for s in slots) or "No open slots"
            )
        if name == "book_appointment":
            start = datetime.fromisoformat(args["start_time"])
            bk = await booking_svc.book(
                db,
                tenant,
                name=args.get("customer_name", "Website visitor"),
                phone=args.get("phone", ""),
                service=args.get("service"),
                start_at=start,
                slot_minutes=slot,
            )
            return f"BOOKED {bk.service or 'appointment'} at {bk.start_at.isoformat()}"
        if name == "take_message":
            await leads_svc.capture_lead(
                db,
                tenant_id=tenant.id,
                name=args.get("name"),
                phone=args.get("phone"),
                email=args.get("email"),
                message=args.get("message"),
                intent="widget",
            )
            return "CAPTURED"
    except Exception as exc:  # tools must never crash the chat
        return f"TOOL_ERROR: {exc}"
    return "UNKNOWN_TOOL"


async def chat(
    db: AsyncSession,
    *,
    tenant: Tenant,
    agent: Agent | None,
    message: str,
    history: list[dict] | None = None,
) -> dict:
    """Run one grounded chat turn. Returns {reply, sources}."""
    messages: list[dict] = [{"role": "system", "content": _system_prompt(tenant, agent)}]
    for h in (history or [])[-MAX_HISTORY:]:
        role, content = h.get("role"), h.get("content")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": str(content)[:2000]})
    messages.append({"role": "user", "content": message[:2000]})

    sources: set[str] = set()
    for _ in range(MAX_TOOL_ROUNDS):
        m = await _llm(messages, tools=_TOOLS)
        tool_calls = m.get("tool_calls")
        if tool_calls:
            # keep only the fields the API expects when echoing the assistant turn back
            messages.append(
                {"role": "assistant", "content": m.get("content") or "", "tool_calls": tool_calls}
            )
            for tc in tool_calls:
                fn = tc.get("function", {})
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = await _run_tool(
                    db, fn.get("name", ""), args, tenant=tenant, agent=agent, sources=sources
                )
                messages.append({"role": "tool", "tool_call_id": tc.get("id"), "content": result})
            continue
        reply = (m.get("content") or "").strip()
        return {"reply": reply or "Sorry, could you rephrase that?", "sources": sorted(sources)}
    return {"reply": "Let me have a team member follow up with you.", "sources": sorted(sources)}
