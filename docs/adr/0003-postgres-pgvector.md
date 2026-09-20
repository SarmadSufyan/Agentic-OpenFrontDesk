# ADR-0003 — Postgres + pgvector as the single datastore

**Status:** Accepted · 2026-09-19

## Context
We need relational data (tenants, calls, bookings) **and** vector search (RAG). Options: a dedicated
vector DB (Pinecone/Weaviate/Chroma) alongside Postgres, or vectors inside Postgres.

## Decision
Use **one Postgres** with the **pgvector** extension for both app data and embeddings.

## Why
- **One system to run, back up, and secure** — big win for a self-hostable, low-cost product.
- Transactional consistency between chunks and their parent docs/tenant.
- pgvector (HNSW/IVFFlat) is more than enough at SMB scale; no extra service, no extra cost.
- Simpler multi-tenant scoping (same `tenant_id` model everywhere).

## Consequences
- At very large scale a specialized vector DB may outperform; we can add one behind the RAG interface if
  ever needed (retrieval is already abstracted).
- Embedding **dimension is fixed per deployment**; changing embedding models requires a reindex.

## Alternatives considered
- Dedicated vector DB — more moving parts, more cost, unnecessary at our scale.
