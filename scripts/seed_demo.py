"""Seed a demo tenant (a dental clinic) with an agent config + knowledge base.

Run after the DB is up and migrated/initialized:
    python scripts/init_db.py        # or: alembic upgrade head
    python scripts/seed_demo.py

Requires the RAG extra (fastembed) for embeddings: pip install -e '.[rag]'
Idempotent: safe to run repeatedly (won't duplicate the tenant/agent or re-ingest knowledge).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from ofd.core.security import hash_password
from ofd.db.session import get_engine, session_scope
from ofd.models.agent import Agent
from ofd.models.booking import Booking
from ofd.models.call import Call
from ofd.models.enums import BookingStatus, CallDirection, CallOutcome, CallStatus, Role
from ofd.models.knowledge import KnowledgeDoc
from ofd.models.lead import Lead
from ofd.models.tenant import Membership, Tenant
from ofd.models.user import User
from ofd.services import knowledge as knowledge_svc

DEMO_SLUG = "demo"

BUSINESS_HOURS = {
    "mon": ["09:00", "17:00"],
    "tue": ["09:00", "17:00"],
    "wed": ["09:00", "17:00"],
    "thu": ["09:00", "17:00"],
    "fri": ["09:00", "16:00"],
    "sat": ["09:00", "13:00"],
}

SERVICES = ["Check-up", "Cleaning", "Teeth whitening", "Filling", "Emergency visit"]

KNOWLEDGE = """\
Bright Smile Dental — Frequently Asked Information

About us
Bright Smile Dental is a family dental clinic at 128 Oak Street, Springfield. We welcome new patients.

Hours
Monday to Thursday 9:00 AM to 5:00 PM, Friday 9:00 AM to 4:00 PM, Saturday 9:00 AM to 1:00 PM.
Closed Sundays and public holidays.

Services and prices
- New patient check-up and consultation: 60 dollars.
- Routine cleaning (scale and polish): 90 dollars.
- Teeth whitening: 250 dollars.
- Fillings: from 120 dollars depending on size.
- Emergency visit (toothache, broken tooth): same-day where possible, 80 dollars assessment.

Appointments
Standard appointments are 30 minutes. Check-ups and cleanings can usually be booked within a week.
Please arrive 10 minutes early if you are a new patient to complete a short form.

Insurance and payment
We accept most major dental insurance plans and direct-bill where possible. We also accept cash, all
major credit cards, and offer interest-free payment plans for treatments over 300 dollars.

Policies
Please give at least 24 hours notice to cancel or reschedule to avoid a 25 dollar late-cancellation fee.
For dental emergencies outside opening hours, please call and follow the voicemail instructions.
"""


async def main() -> None:
    async with session_scope() as db:
        tenant = (
            await db.execute(select(Tenant).where(Tenant.slug == DEMO_SLUG))
        ).scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(
                name="Bright Smile Dental",
                slug=DEMO_SLUG,
                vertical="dental",
                timezone="America/Chicago",
                business_hours=BUSINESS_HOURS,
                address={"line1": "128 Oak Street", "city": "Springfield"},
                settings={},
                plan="free",
            )
            db.add(tenant)
            await db.flush()
            print(f"Created tenant {tenant.id} (Bright Smile Dental)")
        else:
            print(f"Tenant already exists: {tenant.id}")

        agent = (
            await db.execute(select(Agent).where(Agent.tenant_id == tenant.id))
        ).scalar_one_or_none()
        if agent is None:
            agent = Agent(
                tenant_id=tenant.id,
                name="Bright Smile Front Desk",
                voice="af_heart",
                greeting="Thanks for calling Bright Smile Dental! How can I help you today?",
                tone="warm and professional",
                booking_rules={"slot_minutes": 30, "services": SERVICES},
            )
            db.add(agent)
            await db.flush()
            print(f"Created agent {agent.id}")
        else:
            print(f"Agent already exists: {agent.id}")

        existing_docs = (
            await db.execute(select(KnowledgeDoc.id).where(KnowledgeDoc.tenant_id == tenant.id))
        ).first()
        if existing_docs is None:
            print("Ingesting knowledge base (embeddings may download a small model on first run)…")
            doc = await knowledge_svc.create_and_ingest(
                db,
                tenant_id=tenant.id,
                title="Bright Smile Dental — Clinic Info",
                source_type="text",
                text=KNOWLEDGE,
            )
            print(f"Ingested knowledge doc {doc.id} ({doc.chunk_count} chunks)")
        else:
            print("Knowledge already ingested; skipping.")

        # --- demo login (so you can sign in to the dashboard) ---
        demo_email = "demo@openfrontdesk.local"
        user = (
            await db.execute(select(User).where(User.email == demo_email))
        ).scalar_one_or_none()
        if user is None:
            user = User(
                email=demo_email, password_hash=hash_password("demodemo12"), name="Demo Owner"
            )
            db.add(user)
            await db.flush()
            db.add(Membership(tenant_id=tenant.id, user_id=user.id, role=Role.OWNER))
            print(f"Created demo login  ->  {demo_email} / demodemo12")
        else:
            print(f"Demo login exists   ->  {demo_email} / demodemo12")

        # --- sample records (so the dashboard isn't empty) ---
        has_data = (
            await db.execute(select(Booking.id).where(Booking.tenant_id == tenant.id))
        ).first()
        if has_data is None:
            now = datetime.now(timezone.utc)
            db.add(
                Booking(
                    tenant_id=tenant.id,
                    customer_name="Jane Smith",
                    customer_phone="+15551234567",
                    service="Cleaning",
                    start_at=now + timedelta(days=1, hours=2),
                    end_at=now + timedelta(days=1, hours=2, minutes=30),
                    status=BookingStatus.CONFIRMED,
                )
            )
            db.add(
                Lead(
                    tenant_id=tenant.id,
                    name="Bob Lee",
                    phone="+15559876543",
                    intent="callback",
                    message="Wants a quote for whitening.",
                )
            )
            db.add(
                Call(
                    tenant_id=tenant.id,
                    direction=CallDirection.INBOUND,
                    status=CallStatus.COMPLETED,
                    outcome=CallOutcome.BOOKED,
                    caller_number="+15551234567",
                    started_at=now - timedelta(minutes=5),
                    ended_at=now - timedelta(minutes=3),
                    duration_seconds=120,
                    transcript=[
                        {"role": "assistant", "text": "Thanks for calling Bright Smile Dental!"},
                        {"role": "user", "text": "I'd like to book a cleaning."},
                        {"role": "assistant", "text": "Booked you for tomorrow afternoon at 2:30."},
                    ],
                    summary="Caller booked a cleaning for tomorrow afternoon.",
                    latency_ms={"p50": 620, "p95": 940},
                )
            )
            await db.flush()
            print("Added sample booking, lead, and call.")
        else:
            print("Sample data already present; skipping.")

    await get_engine().dispose()
    print("\n✅ Demo seeded. Token endpoint defaults to tenant 'demo'. Try /test or the knowledge API.")


if __name__ == "__main__":
    asyncio.run(main())
