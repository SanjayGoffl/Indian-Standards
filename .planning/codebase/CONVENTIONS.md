# Coding Conventions

**Analysis Date:** 2026-09-27

## Naming Patterns

**Files (backend):**
- `snake_case.py` throughout — `standards_retrieval.py`, `recommendation_service.py`, `bis_connector.py`
- Routers named after resource/domain: `backend/app/api/procurement.py`, `backend/app/api/standards.py`, `backend/app/api/query.py`
- Services suffixed `_service.py`: `backend/app/services/recommendation_service.py`, `backend/app/services/knowledge_base_service.py`
- Test files prefixed `test_`: `backend/app/test/test_procurement_engine.py`, `backend/app/test/test_bis_ingestion_and_retrieval.py`

**Files (frontend):**
- React components `PascalCase.jsx` under `frontend/src/components/`, `frontend/src/pages/`
- Hooks `camelCase.js`/`useX.js` under `frontend/src/hooks/`
- Services `camelCase.js` under `frontend/src/services/`

**Functions:**
- `snake_case` in Python — `extract_is_numbers`, `retrieve_candidate_standards`, `process_procurement_recommendation` (`backend/app/services/standards_retrieval.py`, `backend/app/services/recommendation_service.py`)
- Router handlers describe the action + resource: `analyze_procurement_specification`, `get_user_procurement_requests`, `delete_procurement_request` (`backend/app/api/procurement.py`)

**Variables:**
- `snake_case` for locals (`spec_text`, `extracted_doc_text`, `uploaded_file_path`)
- SQLAlchemy model instances named after the singular entity (`req`, `std`, `user`)

**Types/Classes:**
- `PascalCase` for ORM models and Pydantic schemas — `User`, `IndianStandard`, `ProcurementRequest` (`backend/app/core/models.py`), `ProcurementAnalysisResponse` (`backend/app/models/procurement_schemas.py`)
- Agent/engine classes suffixed by role — `ConversationMemoryAgent` (`backend/app/agents/memory/agent.py`), `MockBISConnector` (`backend/app/services/bis_connector.py`)
- Test classes `TestXxx(unittest.TestCase)`, e.g. `TestProcurementEngine` (`backend/app/test/test_procurement_engine.py`)

## Code Style

**Formatting:**
- No `.flake8`, `black`, or `pyproject.toml` formatter config detected in `backend/` — style is by convention, not enforced tooling
- 4-space indentation, double-quoted strings dominant throughout backend Python
- Frontend uses `oxlint` (`frontend/package.json` → `"lint": "oxlint"`); no Prettier config found

**Linting:**
- No `mypy.ini`/`pyright` config detected — type hints used selectively (e.g. `Generator[Session, None, None]` in `backend/app/core/database.py`) but not enforced project-wide
- Frontend: `oxlint` is the only configured linter; no `.eslintrc*` present

## Import Organization

**Order (backend, observed in `backend/app/api/procurement.py`, `backend/app/test/test_procurement_engine.py`):**
1. Standard library (`os`, `json`, `uuid`, `logging`, `sys`)
2. Third-party (`fastapi`, `sqlalchemy`, `dotenv`)
3. Local `app.*` imports, grouped by layer: `app.core.*` → `app.dependencies.*` → `app.models.*` → `app.rag.*` → `app.services.*`

**Path Aliases:**
- None — all backend imports are absolute from the `app` package root (`from app.core.database import get_db`)
- Test files manually prepend the backend dir to `sys.path` when run standalone (`backend/app/test/test_procurement_engine.py:21-24`)

## Error Handling

**Patterns:**
- API layer converts domain/validation failures to `HTTPException` with explicit `status.HTTP_4xx_*` and a human-readable `detail` string (`backend/app/api/procurement.py:78-81`, `146-150`, `176-180`)
- Ownership checks are always inline `.filter(Model.id == id, Model.user_id == current_user.id).first()` followed by a 404 if `None` — never a bare lookup by ID alone (`backend/app/api/procurement.py:141-150`, `171-180`) — **follow this pattern for any new user-scoped resource** to enforce data isolation
- Best-effort/non-critical failures (e.g. document text extraction, ad-hoc schema migrations) are caught broadly with `except Exception` and logged rather than raised, with a fallback value substituted (`backend/app/api/procurement.py:60-69`, `backend/app/core/database.py:92-97`)
- JSON parsing of stored `result_json` blobs is wrapped in `try/except Exception: pass` when only best-effort summary extraction is needed (`backend/app/api/procurement.py:112-116`)

**Logging:**
- Standard library `logging`, one `logger = logging.getLogger(__name__)` per module (`backend/app/api/procurement.py:23`, `backend/app/core/database.py:48-49`)
- `logger.error(...)` for failures on the request path, `logger.debug(...)` for expected/skippable issues (e.g. migration statement already applied)
- No structured logging or correlation-ID pattern in place

## Comments

**When to Comment:**
- Section-header comments (`# Handle document upload & extraction / OCR`, `# Combine input texts`, `# Process recommendation`) mark logical blocks inside long endpoint functions — used liberally in `backend/app/api/procurement.py`
- Inline comments explain *why*, not *what*, for non-obvious choices (e.g. `# Ensure backend directory is in sys.path` in `backend/app/test/test_procurement_engine.py:21`)

**Module/Function Docstrings:**
- Every router module opens with a triple-quoted module docstring summarizing responsibilities (`backend/app/api/procurement.py:1-6`)
- Every public function/endpoint has a one-to-few-sentence docstring describing behavior and any enforcement rules (e.g. "Strictly verifies user ownership.")
- Test methods use docstrings instead of inline comments to describe intent (`backend/app/test/test_procurement_engine.py`, one line per `test_NN_description` method)

## Function Design

**Size:** Endpoint handlers and service functions are often long (50-150+ lines) and handle multiple responsibilities inline (upload handling, extraction, validation, persistence) rather than being decomposed into smaller private helpers — see `analyze_procurement_specification` (`backend/app/api/procurement.py:31-94`)

**Parameters:** Heavy use of keyword arguments for service calls even when positional would work, improving readability at call sites (`process_procurement_recommendation(db=db, user_id=..., input_text=..., ...)`)

**Return Values:** Endpoints return plain dicts or Pydantic response models; internal services return dicts with well-known string keys (`"recommended_standards"`, `"excluded_standards"`, `"missing_requirements"`, `"overall_status"`) rather than dataclasses — treat these dict shapes as the informal schema when extending `backend/app/services/recommendation_service.py`

## Module Design

**Layering (backend):** `app/api/*` (routers) → `app/services/*` (business logic) → `app/core/*` (db/models/config) — routers depend on services and core, never the reverse
- `app/dependencies/auth.py` supplies `get_current_user` for JWT-based route protection, imported by every user-scoped router
- `app/rag/*` holds document extraction/OCR logic consumed by services and routers (`extract_document` in `backend/app/rag/extractor.py`)

**Exports:** No barrel/`__init__.py` re-export pattern observed beyond package markers — each module is imported directly by its full path

**Numbering convention for tests:** Test methods are numbered (`test_01_...`, `test_02_...`) to encode intended execution order within a `unittest.TestCase`, since ordering affects shared class-level fixtures (`backend/app/test/test_procurement_engine.py`)

---

*Convention analysis: 2026-09-27*
