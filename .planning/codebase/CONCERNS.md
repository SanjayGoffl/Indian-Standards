# Codebase Concerns

**Analysis Date:** 2026-09-27

## Tech Debt

**Dual/conflicting database migration strategy:**
- Issue: `backend/main.py` header comment states "Database schema changes are managed by Alembic migrations," yet `backend/app/core/database.py` runs its own imperative `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` list (35+ statements) inside `init_db()` on every startup, independent of the 6 Alembic revisions in `backend/alembic/versions/`. `database.py` currently has uncommitted working-tree changes (see `git status`), indicating this drift is actively being introduced/modified.
- Files: `backend/app/core/database.py`, `backend/alembic/versions/`, `backend/main.py`
- Impact: Two sources of truth for schema state. `IF NOT EXISTS` syntax is Postgres-specific and will silently no-op or fail differently on SQLite (used in tests per `conftest.py`), risking schema drift between test and prod databases. Alembic history becomes unreliable as a record of actual schema state, making rollbacks and audits unsafe.
- Fix approach: Consolidate all schema changes into Alembic revisions only; remove the manual `ALTER TABLE` loop from `database.py`, or clearly document why it exists (e.g., a hotfix path) with a ticket to migrate it into a proper revision.

**Extremely large, monolithic modules:**
- Issue: Several files exceed 700-2200 lines, mixing multiple responsibilities (extraction, parsing, validation, orchestration) in a single module.
- Files: `backend/app/rag/extractor.py` (2202 lines), `backend/app/agents/retrieval/agent.py` (1207 lines), `backend/app/orchestration/nodes.py` (1132 lines), `backend/app/services/recommendation_validator.py` (979 lines), `backend/app/agents/retrieval/reranker.py` (950 lines), `backend/app/core/models.py` (888 lines)
- Impact: High cognitive load for changes, higher risk of regressions, difficult to unit-test in isolation, merge-conflict prone in a multi-agent/parallel development workflow.
- Fix approach: Split by responsibility (e.g., `extractor.py` into format-specific extractors + a coordinator; `nodes.py` into per-stage orchestration node files).

**Widespread silent exception swallowing:**
- Issue: Numerous `except Exception: pass` blocks discard errors without logging, especially in OCR and extraction paths.
- Files: `backend/app/services/ocr_service.py` (lines 15-16, 18-19, 23-24, 40-41, 83-84), `backend/app/rag/extractor.py` (lines 2038-2039, 2047-2048, 2056-2057, 2072-2073), `backend/app/rag/chromadb_service.py` (lines 56-57), `backend/app/services/knowledge_base_service.py` (lines 163-164), `backend/app/api/analytics.py` (lines 63-64), `backend/app/api/procurement.py` (lines 115-116)
- Impact: Failures in OCR, embedding, and ingestion pipelines fail silently, producing incomplete or corrupt data with no operator visibility. Debugging production issues (e.g., "why is this standard missing embeddings") becomes guesswork. There are 80+ total `except Exception` blocks across the backend, many of which likely follow this same pattern.
- Fix approach: Replace bare `except Exception: pass` with logged exceptions (`logger.warning`/`logger.exception`) at minimum; use narrower exception types where the failure mode is known.

**`print()` used instead of structured logging in app lifecycle code:**
- Issue: Application startup failure handling uses `print()` rather than the `logging` module.
- Files: `backend/main.py` (line ~43: `except Exception as e: print(f"Lifespan initialization warning: {e}")`), plus 25 files across `backend/app` containing `print(` calls.
- Impact: Startup seeding failures are not captured by log aggregation/monitoring in production, making outages harder to diagnose from deployed logs.
- Fix approach: Route all diagnostic output through a configured `logging.Logger`, and reserve `print()` for CLI/dev scripts only.

**No automated frontend tests:**
- Issue: `frontend/package.json` has no test runner, no test dependency (no Jest/Vitest/Testing Library), and no `*.test.*`/`*.spec.*` files exist anywhere under `frontend/`.
- Files: `frontend/package.json`, `frontend/src/`
- Impact: All UI regressions (query flows, auth, admin panels) are caught only by manual testing. Refactors of `frontend/src/components`, `frontend/src/pages`, `frontend/src/services` carry high regression risk.
- Fix approach: Introduce Vitest + React Testing Library, starting with the query submission flow and auth context.

## Known Bugs

**No explicit bug reports found in code comments (no TODO/FIXME/HACK/XXX markers exist in `backend/`).** This itself is a minor flag: either the codebase is unusually clean, or issues are being fixed immediately without tracking markers, or debt is undocumented. Given the volume of `except: pass` blocks found above, the latter is more likely — issues are probably being silently absorbed rather than tracked.

## Security Considerations

**Broad CORS configuration:**
- Risk: `backend/app/main.py` configures `CORSMiddleware` with `allow_methods=["*"]`, `allow_headers=["*"]`, and `allow_credentials=True`, while `allow_origins` is sourced from `CORS_ALLOW_ORIGINS` in `backend/app/core/config.py`.
- Files: `backend/app/main.py` (lines 56-62), `backend/app/core/config.py`
- Current mitigation: Origins are at least externalized to config rather than hardcoded to `*`.
- Recommendations: Verify `CORS_ALLOW_ORIGINS` is a strict allowlist (not `*`) in all deployed environments — combining `allow_credentials=True` with a wildcard origin is invalid/dangerous. Audit `backend/app/core/config.py` and deployment env vars to confirm this.

**JWT secret and API keys required via environment, good pattern but unverified rotation/storage:**
- Risk: `backend/app/core/auth.py` correctly fails fast if `JWT_SECRET_KEY` is unset, and `backend/app/core/llm.py` does the same for `GROQ_API_KEY`. No hardcoded secrets were found in source.
- Files: `backend/app/core/auth.py` (line 22), `backend/app/core/llm.py` (line 34)
- Current mitigation: Fail-fast on missing secrets; `.env.example` files present in both `backend/` and `frontend/` document required vars without leaking real values.
- Recommendations: Confirm secret rotation policy and that `.env` (actual, not `.env.example`) is git-ignored; no `.env` file was found in the working tree at time of analysis, which is good, but should be explicitly verified in CI (e.g., a pre-commit secret scanner).

**Silent failure paths in OCR/extraction could mask malicious or malformed uploads:**
- Risk: Because `backend/app/services/ocr_service.py` and `backend/app/rag/extractor.py` swallow exceptions broadly, a malformed or adversarial uploaded document (PDF/image) could cause partial/incorrect extraction without raising any error, potentially bypassing validation logic in `backend/app/services/upload_service.py` (784 lines) and `backend/app/services/recommendation_validator.py`.
- Files: `backend/app/services/ocr_service.py`, `backend/app/rag/extractor.py`, `backend/app/services/upload_service.py`
- Current mitigation: None identified beyond the try/except itself.
- Recommendations: Add explicit validation checkpoints after extraction (e.g., assert non-empty/expected structure) rather than relying on the absence of an exception as a success signal.

## Performance Bottlenecks

**Large single-file RAG extraction pipeline:**
- Problem: `backend/app/rag/extractor.py` at 2202 lines handles multiple document formats and extraction strategies in one module; combined with `paddleocr`/`pymupdf` dependencies (heavyweight, CPU/GPU-bound OCR), ingestion of large PDFs is likely synchronous and blocking.
- Files: `backend/app/rag/extractor.py`, `backend/app/services/ocr_service.py`
- Cause: No evidence of background task queuing (e.g., Celery/RQ) for OCR/extraction; FastAPI's `lifespan` and routers appear to call services directly.
- Improvement path: Move OCR/extraction/embedding for large documents to a background worker or async task queue so upload requests don't block on CPU-heavy OCR.

**Reranker and retrieval agent size suggests potential redundant computation:**
- Problem: `backend/app/agents/retrieval/reranker.py` (950 lines) and `backend/app/agents/retrieval/agent.py` (1207 lines) are large enough to warrant checking for repeated embedding calls or redundant DB round-trips per query.
- Files: `backend/app/agents/retrieval/reranker.py`, `backend/app/agents/retrieval/agent.py`, `backend/app/agents/retrieval/semantic_search.py`
- Cause: Not fully profiled in this pass; flagged due to file size and central role in the query hot path (`backend/app/api/query.py`, `backend/app/services/query_service.py`).
- Improvement path: Profile the query request path end-to-end; look for repeated ChromaDB queries or LLM calls per retrieval cycle.

## Fragile Areas

**`backend/app/core/database.py` (uncommitted, currently mid-edit):**
- Files: `backend/app/core/database.py`
- Why fragile: Actively modified working-tree file combining ORM setup with imperative schema patching; Postgres-only SQL (`ADD COLUMN IF NOT EXISTS`) run against a codebase that also supports SQLite in tests (`backend/app/test/conftest.py`), meaning behavior differs by environment in an untested way.
- Safe modification: Do not add more ad-hoc `ALTER TABLE` statements; route any new column requirements through Alembic (`backend/alembic/versions/`) instead.
- Test coverage: No test file directly exercises `init_db()`'s migration loop.

**`backend/app/rag/extractor.py`:**
- Files: `backend/app/rag/extractor.py`
- Why fragile: 2202 lines, multiple bare `except Exception: pass` blocks (lines 2038-2073), central to ingestion correctness.
- Safe modification: Add unit tests around specific extraction functions before refactoring; avoid changing exception handling without adding logging first (to detect if suppressed cases are actually being hit in practice).
- Test coverage: `backend/app/test/test_bis_ingestion_and_retrieval.py` and `test_hdpe_piping_applicability.py` cover ingestion/retrieval scenarios but do not appear to target extractor internals directly.

**`backend/app/services/ocr_service.py`:**
- Files: `backend/app/services/ocr_service.py`
- Why fragile: 5 separate `except Exception: pass` sites in 84 lines — over half the file's exception paths are silent, including module-level import guards (lines 23-24, 40-41) that could mask missing OCR dependencies (`paddleocr`, `paddlepaddle`) rather than failing clearly at startup.
- Safe modification: Add explicit logging when optional OCR dependencies fail to import, so operators know OCR is degraded rather than discovering it via missing extracted text.
- Test coverage: No dedicated OCR test file found under `backend/app/test/`.

## Scaling Limits

**Not assessed in this pass** — no load/capacity data, connection pool sizing, or infrastructure config (beyond `pool_pre_ping=True` in `backend/app/core/database.py`) was found to evaluate concrete scaling thresholds. `SessionLocal`/`engine` use SQLAlchemy defaults; default pool size (5) may be insufficient under concurrent load given the app also runs synchronous OCR/extraction on the request path.

## Dependencies at Risk

**Unpinned core dependencies:**
- Risk: `backend/requirements.txt` pins some packages exactly (`langchain==1.3.14`, `fastapi==0.141.1`, `chromadb==1.5.9`) but leaves others fully unpinned (`pypdf`, `python-docx`, `pandas`, `pymupdf`, `paddlepaddle`, `paddleocr`, `Pillow`, `python-dotenv`, `SQLAlchemy`, `psycopg[binary]`, `alembic`, `bcrypt`, `email-validator`).
- Impact: Non-reproducible builds; a future `pip install` can pull breaking major versions of SQLAlchemy or pandas without warning, especially risky for `alembic`/`SQLAlchemy` given the manual migration logic already present in `database.py`.
- Migration plan: Pin all dependencies (or use a lockfile via `pip-compile`/`poetry`/`uv`) and add a CI job that fails on dependency drift.

**Heavy OCR stack (`paddlepaddle`, `paddleocr`) as unpinned, large native dependencies:**
- Risk: These are large binary packages with platform-specific wheels; unpinned versions increase the chance of environment-specific install failures or behavior changes in OCR output quality.
- Impact: Ingestion pipeline reliability depends on an OCR engine whose version can silently drift between developer machines, CI, and production.
- Migration plan: Pin exact versions and document supported OS/Python combinations.

## Missing Critical Features

**No visible background job/queue system:**
- Problem: Document upload, OCR, and embedding generation (`backend/app/services/upload_service.py`, `backend/app/services/ocr_service.py`, `backend/app/rag/chromadb_service.py`) appear to run inline with API requests rather than via an async worker.
- Blocks: Reliable handling of large document uploads without request timeouts; retry/backoff for failed embedding jobs; horizontal scaling of ingestion independent of API traffic.

## Test Coverage Gaps

**Frontend has zero test coverage:**
- What's not tested: All of `frontend/src/components`, `frontend/src/pages`, `frontend/src/services`, `frontend/src/context`, `frontend/src/hooks`.
- Files: `frontend/` (entire tree)
- Risk: UI regressions in auth flows, query submission, and admin views ship undetected.
- Priority: High

**No dedicated tests for extraction/OCR internals:**
- What's not tested: `backend/app/rag/extractor.py` (2202 lines) and `backend/app/services/ocr_service.py` have no matching test files under `backend/app/test/` (existing tests target BIS ingestion/retrieval and HDPE applicability end-to-end, not extractor/OCR unit behavior).
- Files: `backend/app/rag/extractor.py`, `backend/app/services/ocr_service.py`
- Risk: The most fragile, exception-swallowing code in the repo is also the least directly tested; extraction bugs surface only as downstream data-quality issues.
- Priority: High

**No test for `database.py` migration/init logic:**
- What's not tested: `init_db()`'s manual `ALTER TABLE` loop and its interaction with Alembic-managed schema.
- Files: `backend/app/core/database.py`
- Risk: Schema drift between SQLite test DB and Postgres production DB could go unnoticed until a production deploy.
- Priority: Medium

---

*Concerns audit: 2026-09-27*
