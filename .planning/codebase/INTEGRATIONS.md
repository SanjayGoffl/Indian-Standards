# External Integrations

**Analysis Date:** 2026-09-27

## APIs & External Services

**LLM Provider:**
- Groq (Cloud LLM inference) - used for query understanding, clarification, and response generation
  - SDK/Client: `langchain-groq` (`ChatGroq`) in `backend/app/core/llm.py`, also directly referenced in `backend/app/agents/response_generation/llm_call_groq.py`
  - Auth: `GROQ_API_KEY` env var, model selected via `GROQ_MODEL` env var
  - Failure mode: raises `RuntimeError` at call time if either var is missing (`backend/app/core/llm.py:37-47`)

**Speech (browser-native, not a backend integration):**
- Browser Web Speech API - speech-to-text and text-to-speech handled entirely client-side; backend only receives/returns transcript text
  - Backend contract documented in `backend/app/api/voice.py` header comment and implemented via `backend/app/voice/input.py` / `backend/app/voice/output.py`
  - No external speech vendor API key required by the backend

**Indian Standards (BIS) Data Source:**
- No live official BIS API integration detected; `backend/app/services/bis_connector.py` implements a pluggable connector abstraction (`ABC`) supporting local JSON, CSV, mock APIs, or "official BIS data feeds" as adapters, but only local file/mock adapters appear wired in currently — no external network calls or API key for a real BIS endpoint were found
  - Ingestion pipeline: `backend/app/services/standards_ingestion.py`
  - Seed data loader: `backend/app/services/standards_knowledge_base.py` (invoked at FastAPI startup in `backend/app/main.py`)

## Data Storage

**Databases:**
- PostgreSQL (primary relational store)
  - Connection: `DATABASE_URL` env var (e.g. `postgresql+psycopg://postgres:PASSWORD@localhost:5432/querynest`)
  - Client/ORM: SQLAlchemy + `psycopg[binary]` driver, configured in `backend/app/core/database.py`
  - Schema managed by Alembic migrations (`backend/alembic/`) plus defensive `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` statements run at `init_db()` time (`backend/app/core/database.py:52-97`) for standards, certification, and relationship tables
  - Also supports SQLite via `connect_args` branch for `sqlite://` URLs, though default/example config targets Postgres

**Vector Store:**
- ChromaDB (embedded, file-based) - semantic search over ingested standards/document chunks
  - Persisted locally at `chroma_db/` directory (`CHROMA_DB_PATH` in `backend/app/core/config.py`)
  - Populated via ingestion pipeline; queried in `backend/app/agents/retrieval/semantic_search.py`

**File Storage:**
- Local filesystem only
  - Uploaded documents: `uploads/` folder (`UPLOAD_FOLDER` in `backend/app/core/config.py`)
  - Document metadata: `metadata/documents.json` (`METADATA_FOLDER`, `DOCUMENTS_FILE`)
  - No cloud object storage (S3/GCS/Azure Blob) integration detected

**Caching:**
- None detected (no Redis/Memcached config or client library in `backend/requirements.txt`)

## Authentication & Identity

**Auth Provider:**
- Custom (no third-party auth provider such as Auth0/Clerk/Firebase Auth)
  - Implementation: JWT-based auth in `backend/app/core/auth.py` using `python-jose` for token encode/decode and `bcrypt` for password hashing
  - Routes: `backend/app/api/auth.py`
  - Dependency injection guard: `backend/app/dependencies/auth.py`
  - Config: `JWT_SECRET_KEY`, `JWT_ALGORITHM` (default `HS256`), `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (default 60)

## Monitoring & Observability

**Error Tracking:**
- None detected (no Sentry/Datadog/similar SDK in dependencies)

**Logs:**
- Standard Python `logging` module used ad hoc across services (e.g. `backend/app/services/bis_connector.py`, `backend/app/core/database.py`); no centralized log aggregation or structured logging framework configured

## CI/CD & Deployment

**Hosting:**
- Not detected — no deployment manifests, Dockerfiles, or platform-specific config (e.g. Vercel, Render, Railway, Fly.io) found in repo root, `backend/`, or `frontend/`

**CI Pipeline:**
- None detected (no `.github/workflows/`, `.gitlab-ci.yml`, or similar)

## Environment Configuration

**Required env vars (backend, from `backend/.env.example`):**
- `GROQ_API_KEY` - Groq LLM API key
- `GROQ_MODEL` - Groq model identifier
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET_KEY` - JWT signing secret
- `JWT_ALGORITHM` - JWT signing algorithm (default `HS256`)
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` - token TTL (default `60`)
- `FRONTEND_URL` - optional comma-separated list of allowed CORS origins beyond localhost dev ports (`backend/app/core/config.py`)

**Required env vars (frontend, from `frontend/.env.example`):**
- `VITE_API_BASE_URL` - backend API base URL, consumed in `frontend/src/services/api.js`

**Secrets location:**
- `backend/.env` and `frontend/.env` (both present in repo working tree but excluded from reading per secret-file policy; not read/quoted in this analysis)

## Webhooks & Callbacks

**Incoming:**
- None — all API routes are directly invoked by the frontend SPA (`backend/app/api/*.py` routers registered in `backend/app/main.py`); no webhook receiver endpoints detected

**Outgoing:**
- None detected — no outbound webhook dispatch code found; the only outbound network calls are to the Groq LLM API via `langchain-groq`

---

*Integration audit: 2026-09-27*
