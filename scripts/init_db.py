"""Quick dev DB bootstrap: enable pgvector + create all tables from ORM metadata.

For development convenience only. Production uses Alembic migrations (see migrations/env.py).

    python scripts/init_db.py
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text

from ofd.db.session import get_engine
from ofd.models import Base


async def main() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("✅ DB initialized: pgvector extension enabled, tables created.")


if __name__ == "__main__":
    asyncio.run(main())
