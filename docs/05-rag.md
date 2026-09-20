# 05 — Knowledge Base & RAG

Turns a business's documents into grounded answers. Lives in `ofd.rag`. **No model training** — this is
retrieval-augmented generation over pgvector.

## 1. Ingestion pipeline (async job)

```
source (PDF / DOCX / TXT / pasted text / website URL)
  → extract text   (pypdf · python-docx · BeautifulSoup+httpx for crawl)
  → clean/normalize (strip boilerplate, collapse whitespace)
  → chunk          (token-aware ~500 tokens, ~15% overlap, respect headings/sentences)
  → embed          (EmbeddingsProvider: fastembed local / Gemini)
  → upsert         (doc_chunks: text + embedding vector + metadata + source ref)
  → mark knowledge_doc.status = ready
```
- Each `knowledge_doc` → many `doc_chunks`. Re-uploading a doc re-indexes (old chunks replaced).
- Metadata per chunk: `tenant_id`, `doc_id`, `chunk_index`, `source_title`, `source_url/page`.

## 2. Chunking strategy
- Prefer structural splits (headings, sections, FAQ Q/A pairs) before fixed-size.
- Keep chunks self-contained (a chunk should answer a question on its own where possible).
- Overlap preserves context across boundaries.

## 3. Embeddings
- Behind `EmbeddingsProvider` interface (see [07-providers](07-providers.md)).
- **Free/default:** `fastembed` (ONNX, CPU) — e.g. `bge-small`, runs on the VPS, $0.
- **Alt:** Gemini `text-embedding-004` (free tier) — offloads CPU, network dependency.
- Embedding dimension is fixed per deployment (vector column dim must match). Changing models = reindex.

## 4. Retrieval (call time)
```
question → embed → pgvector similarity search (cosine) top-k
        → (optional) hybrid: + keyword/trigram filter for exact terms (prices, names)
        → (optional) rerank
        → assemble grounded context with [source_id] tags
        → LLM answers ONLY from context; returns citations
```
- Default k ≈ 5, tunable per tenant. Similarity threshold filters weak matches.
- Hybrid keyword pass matters for numbers/proper nouns where pure vectors miss.

## 5. Grounding & anti-hallucination (core to trust)
- System rule: **answer only from retrieved context**; if the answer isn't there, say so and
  `take_message`/`transfer` — never guess prices, hours, availability, or policy.
- Responses carry source ids → shown in the test console and stored on the call for auditing.
- Grounding is **scored** in the eval harness; regressions fail CI. [10](10-eval-harness.md).

## 6. Freshness
- Editing a doc or business detail → re-index that doc immediately (seconds). No retraining, no downtime.
- Business hours/pricing can also live as structured tenant config (authoritative) and be injected
  directly, bypassing RAG for the most critical facts.

## 7. Data model
`knowledge_doc(id, tenant_id, title, source_type, source_ref, status, error, created_at)` and
`doc_chunk(id, tenant_id, doc_id, chunk_index, text, embedding vector, metadata)` — see [06](06-data-model.md).

## 8. Limits & guardrails
- Max upload size + page/char caps per tenant (cost/abuse control).
- Poisoned-content mitigation: ingestion is data, never instructions; retrieved text is wrapped as
  quoted context, not executed as prompts.
- PII in documents inherits tenant data-handling policy. [13](13-security-compliance.md).
