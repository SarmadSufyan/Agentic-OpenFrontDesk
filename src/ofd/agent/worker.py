"""LiveKit voice agent worker (Phase 2).

Resolves the tenant/agent for the call, loads its config + knowledge, and runs the chained pipeline
(VAD -> turn detection -> STT -> LLM(+tools+RAG) -> TTS) with per-call latency logging.

Run:  ofd-agent dev   (or  ofd-agent start  in production)
Needs the agent extra, LIVEKIT_* env, provider keys (GROQ_API_KEY for the free stack), a running
Kokoro TTS server, and a seeded demo tenant (`python scripts/seed_demo.py`).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from livekit import agents
from livekit.agents import (
    AgentSession,
    JobContext,
    MetricsCollectedEvent,
    RoomInputOptions,
    WorkerOptions,
    cli,
)
from livekit.agents import metrics as lk_metrics

# Import the turn-detector plugin at module load so `ofd-agent download-files` fetches its model
# (baked into the image) and the plugin is registered before jobs run.
from livekit.plugins import (
    silero,
    turn_detector,  # noqa: E402,F401
)

from ofd.agent.frontdesk import FrontDeskAgent
from ofd.agent.metrics import LatencyTracker
from ofd.agent.prompt import build_instructions
from ofd.agent.providers import build_llm, build_stt, build_tts, build_turn_detection
from ofd.core.config import settings
from ofd.core.logging import configure_logging, get_logger
from ofd.db.session import session_scope
from ofd.models.enums import CallDirection, CallOutcome
from ofd.services import calls as calls_svc
from ofd.services import tenants as tenants_svc

logger = get_logger("ofd.agent")


def _extract_transcript(session: object) -> list:
    """Best-effort transcript extraction from the session history (version-tolerant)."""
    out: list = []
    try:
        hist = getattr(session, "history", None)
        items = getattr(hist, "items", None) or []
        for it in items:
            role = getattr(it, "role", None)
            content = (
                getattr(it, "text_content", None)
                or getattr(it, "content", None)
                or getattr(it, "text", None)
            )
            if isinstance(content, (list, tuple)):
                content = " ".join(str(c) for c in content)
            if role and content:
                out.append({"role": str(role), "text": str(content)})
    except Exception:
        pass
    return out


_DAY_NAMES = {
    "mon": "Mon",
    "tue": "Tue",
    "wed": "Wed",
    "thu": "Thu",
    "fri": "Fri",
    "sat": "Sat",
    "sun": "Sun",
}


def _hours_summary(business_hours: dict | None) -> str | None:
    if not business_hours:
        return None
    return ", ".join(
        f"{_DAY_NAMES.get(d, d)} {v[0]}-{v[1]}" for d, v in business_hours.items() if v
    )


async def _resolve_config(metadata: str | None) -> dict:
    """Load tenant/agent config into plain values (safe to use after the session closes)."""
    tid = aid = None
    if metadata:
        try:
            data = json.loads(metadata)
            tid = uuid.UUID(data["tenant_id"]) if data.get("tenant_id") else None
            aid = uuid.UUID(data["agent_id"]) if data.get("agent_id") else None
        except Exception:
            pass

    cfg: dict = {
        "tenant_id": None,
        "agent_id": None,
        "business_name": None,
        "tone": "friendly and professional",
        "timezone": "UTC",
        "greeting": "Thanks for calling! How can I help you today?",
        "hours_summary": None,
        "services_summary": None,
        "slot_minutes": 30,
        "consent_line": None,
    }
    try:
        async with session_scope() as db:
            tenant, agent = await tenants_svc.get_context(db, tenant_id=tid, agent_id=aid)
            if tenant:
                cfg["tenant_id"] = tenant.id
                cfg["business_name"] = tenant.name
                cfg["timezone"] = tenant.timezone or "UTC"
                cfg["hours_summary"] = _hours_summary(tenant.business_hours)
                if settings.RECORDING_ENABLED and tenant.settings:
                    cfg["consent_line"] = tenant.settings.get("record_consent_line")
            if agent:
                cfg["agent_id"] = agent.id
                cfg["tone"] = agent.tone or cfg["tone"]
                cfg["greeting"] = agent.greeting or cfg["greeting"]
                rules = agent.booking_rules or {}
                cfg["slot_minutes"] = int(rules.get("slot_minutes", 30))
                services = rules.get("services")
                if services:
                    cfg["services_summary"] = ", ".join(services)
    except Exception as exc:
        logger.warning("tenant_resolve_failed", error=str(exc))
    return cfg


def prewarm(proc: agents.JobProcess) -> None:
    proc.userdata["vad"] = silero.VAD.load()
    # Pre-import heavy modules during warm-up so the first turn isn't stalled importing them on the
    # event loop (these caused ~0.2-0.8s hot-path stalls that delayed audio/turn handling).
    try:
        import asyncpg  # noqa: F401
        from livekit.plugins import openai as _openai  # noqa: F401
    except Exception:
        pass


async def entrypoint(ctx: JobContext) -> None:
    configure_logging()
    await ctx.connect()

    participant = await ctx.wait_for_participant()
    cfg = await _resolve_config(getattr(participant, "metadata", None))
    tz = cfg["timezone"]
    now_iso = datetime.now(ZoneInfo(tz) if tz else ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M %A")

    logger.info(
        "agent_join",
        room=ctx.room.name,
        tenant=str(cfg["tenant_id"]),
        stt=settings.STT_PROVIDER,
        llm=settings.LLM_PROVIDER,
        tts=settings.TTS_PROVIDER,
    )

    instructions = build_instructions(
        business_name=cfg["business_name"],
        tone=cfg["tone"],
        timezone=tz,
        now_iso=now_iso,
        hours_summary=cfg["hours_summary"],
        services_summary=cfg["services_summary"],
    )

    vad = ctx.proc.userdata.get("vad") or silero.VAD.load()
    session = AgentSession(
        vad=vad,
        stt=build_stt(),
        llm=build_llm(),
        tts=build_tts(),
        turn_detection=build_turn_detection(),
    )

    # Persist a call record (best-effort) so the dashboard shows it.
    call_id = None
    if cfg["tenant_id"]:
        try:
            async with session_scope() as db:
                call = await calls_svc.start_call(
                    db,
                    tenant_id=cfg["tenant_id"],
                    agent_id=cfg["agent_id"],
                    direction=CallDirection.INBOUND,
                )
                call_id = call.id
        except Exception as exc:
            logger.warning("call_start_failed", error=str(exc))

    tracker = LatencyTracker()

    @session.on("metrics_collected")
    def _on_metrics(ev: MetricsCollectedEvent) -> None:
        lk_metrics.log_metrics(ev.metrics)
        tracker.handle(ev.metrics)

    async def _on_shutdown() -> None:
        tracker.summary()
        if call_id and cfg["tenant_id"]:
            try:
                async with session_scope() as db:
                    await calls_svc.finalize_call(
                        db,
                        call_id=call_id,
                        outcome=CallOutcome.ANSWERED,
                        transcript=_extract_transcript(session),
                        latency_ms=tracker.snapshot(),
                    )
            except Exception as exc:
                logger.warning("call_finalize_failed", error=str(exc))

    ctx.add_shutdown_callback(_on_shutdown)

    agent = FrontDeskAgent(
        instructions=instructions,
        tenant_id=cfg["tenant_id"],
        agent_id=cfg["agent_id"],
        call_id=call_id,
        slot_minutes=cfg["slot_minutes"],
    )
    await session.start(agent=agent, room=ctx.room, room_input_options=RoomInputOptions())
    greeting = cfg["greeting"]
    if cfg.get("consent_line"):
        greeting = f"{cfg['consent_line']} {greeting}"
    await session.generate_reply(instructions=f"Greet the caller: {greeting} Keep it brief.")


def run() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
