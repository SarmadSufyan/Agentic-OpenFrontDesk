"""FrontDeskAgent — the LiveKit Agent with function tools that delegate to ofd.services.

Tools open their own short DB sessions (the agent runs outside the API request cycle). Every tool is
defensive: on any failure it returns natural language the LLM can speak, so a caller is never stuck.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from livekit.agents import Agent, RunContext, function_tool

from ofd.core.logging import get_logger
from ofd.db.session import session_scope
from ofd.rag import retrieve
from ofd.services import booking as booking_svc
from ofd.services import knowledge as knowledge_svc
from ofd.services import leads as leads_svc
from ofd.services import tenants as tenants_svc
from ofd.telephony.sms import send_sms

logger = get_logger("ofd.agent.tools")


class FrontDeskAgent(Agent):
    def __init__(
        self,
        *,
        instructions: str,
        tenant_id: uuid.UUID | None = None,
        agent_id: uuid.UUID | None = None,
        call_id: uuid.UUID | None = None,
        slot_minutes: int = 30,
    ) -> None:
        super().__init__(instructions=instructions)
        self.tenant_id = tenant_id
        self.agent_id = agent_id
        self.call_id = call_id
        self.slot_minutes = slot_minutes

    # --- knowledge -----------------------------------------------------------
    @function_tool
    async def search_knowledge(self, context: RunContext, query: str) -> str:
        """Look up answers about services, prices, hours, policies, insurance, or location.
        Always use this before answering a factual question. Returns grounded snippets or NO_RESULTS."""
        if not self.tenant_id:
            return "NO_RESULTS"
        try:
            async with session_scope() as db:
                results = await knowledge_svc.search(db, tenant_id=self.tenant_id, query=query)
            if not results:
                return "NO_RESULTS"
            return retrieve.format_context(results)
        except Exception as exc:
            logger.warning("tool_search_failed", error=str(exc))
            return "LOOKUP_ERROR: could not search right now; offer to take a message."

    # --- scheduling ----------------------------------------------------------
    @function_tool
    async def check_availability(
        self, context: RunContext, service: str | None = None, on_date: str | None = None
    ) -> str:
        """Find open appointment slots. Optionally pass an ISO date (YYYY-MM-DD) to check a specific day."""
        if not self.tenant_id:
            return "No scheduling is configured; offer to take a message."
        try:
            day = datetime.fromisoformat(on_date) if on_date else None
            async with session_scope() as db:
                tenant = await tenants_svc.get_tenant(db, self.tenant_id)
                if not tenant:
                    return "No scheduling is configured; offer to take a message."
                slots = await booking_svc.check_availability(
                    db, tenant, service=service, on_date=day, slot_minutes=self.slot_minutes
                )
            if not slots:
                return "No open slots found in that range; offer to take a message for a callback."
            return "Available slots: " + "; ".join(
                s.start.strftime("%A %b %d at %I:%M %p") for s in slots
            )
        except Exception as exc:
            logger.warning("tool_availability_failed", error=str(exc))
            return "Could not check availability; offer to take a message."

    @function_tool
    async def book_appointment(
        self,
        context: RunContext,
        customer_name: str,
        phone: str,
        start_time: str,
        service: str | None = None,
    ) -> str:
        """Book an appointment. Provide the caller's full name, phone, the service, and an ISO 8601
        start_time (e.g. 2026-09-22T14:30:00). Only call after the caller agreed to a specific time."""
        if not self.tenant_id:
            return "Booking isn't available; take a message instead."
        try:
            start_at = datetime.fromisoformat(start_time)
        except ValueError:
            return "I need a specific date and time. Ask the caller which day and time works."
        try:
            async with session_scope() as db:
                tenant = await tenants_svc.get_tenant(db, self.tenant_id)
                if not tenant:
                    return "Booking isn't available; take a message instead."
                bk = await booking_svc.book(
                    db,
                    tenant,
                    name=customer_name,
                    phone=phone,
                    service=service,
                    start_at=start_at,
                    slot_minutes=self.slot_minutes,
                    agent_id=self.agent_id,
                    call_id=self.call_id,
                )
                when = bk.start_at.strftime("%A %b %d at %I:%M %p")
            return f"BOOKED: {service or 'appointment'} for {customer_name} on {when}. Read this back to confirm."
        except Exception as exc:
            logger.warning("tool_book_failed", error=str(exc))
            return "That time may not be available. Offer another time or take a message."

    # --- messages / escalation ----------------------------------------------
    @function_tool
    async def take_message(self, context: RunContext, name: str, phone: str, message: str) -> str:
        """Capture a message/lead when you can't fully help. Collect name, phone, and the message."""
        return await self._capture(name=name, phone=phone, message=message, intent="message")

    @function_tool
    async def request_callback(
        self, context: RunContext, name: str, phone: str, reason: str | None = None
    ) -> str:
        """Record a callback request (caller wants a human to call them back)."""
        return await self._capture(name=name, phone=phone, message=reason, intent="callback")

    @function_tool
    async def transfer_to_human(self, context: RunContext) -> str:
        """Use when the caller explicitly wants a person or is upset. (Live transfer arrives in Phase 4.)"""
        return (
            "TRANSFER_REQUESTED: tell the caller you'll have a team member call them back shortly, "
            "then collect their name and number with take_message."
        )

    @function_tool
    async def send_sms_confirmation(self, context: RunContext, phone: str, body: str) -> str:
        """Send a short SMS confirmation/follow-up to the caller."""
        try:
            res = await send_sms(phone, body)
            return f"SMS {res.status}."
        except Exception as exc:
            logger.warning("tool_sms_failed", error=str(exc))
            return "SMS could not be sent."

    async def _capture(self, *, name: str, phone: str, message: str | None, intent: str) -> str:
        if not self.tenant_id:
            return "Noted."
        try:
            async with session_scope() as db:
                await leads_svc.capture_lead(
                    db,
                    tenant_id=self.tenant_id,
                    name=name,
                    phone=phone,
                    message=message,
                    intent=intent,
                    call_id=self.call_id,
                )
            return "CAPTURED: confirm to the caller that someone will follow up."
        except Exception as exc:
            logger.warning("tool_capture_failed", error=str(exc))
            return "Noted; a team member will follow up."
