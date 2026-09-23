"""Import all ORM models so ``Base.metadata`` is fully populated (Alembic, create_all)."""

from ofd.db.base import Base
from ofd.models.access import AllowlistEntry
from ofd.models.agent import Agent, PhoneNumber
from ofd.models.audit import AuditLog
from ofd.models.automation import ApiKey, WebhookDelivery, WebhookEndpoint
from ofd.models.booking import Booking
from ofd.models.call import Call, CallEvent
from ofd.models.contact import ContactRequest
from ofd.models.integration import Integration
from ofd.models.knowledge import DocChunk, KnowledgeDoc
from ofd.models.lead import Lead
from ofd.models.tenant import Membership, Tenant
from ofd.models.usage import UsageEvent
from ofd.models.user import User

__all__ = [
    "Base",
    "Tenant",
    "Membership",
    "User",
    "Agent",
    "PhoneNumber",
    "AuditLog",
    "AllowlistEntry",
    "WebhookEndpoint",
    "WebhookDelivery",
    "ApiKey",
    "ContactRequest",
    "KnowledgeDoc",
    "DocChunk",
    "Call",
    "CallEvent",
    "Booking",
    "Lead",
    "Integration",
    "UsageEvent",
]
