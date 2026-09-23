# QueryNest AI Knowledge Retrieval & Indian Standards Procurement System

QueryNest AI is an AI-powered Knowledge Retrieval and Indian Standards (BIS) Procurement Recommendation System built for Smart Automation and Public/Private Procurement workflows.

---

## 🏛️ Architecture Overview

QueryNest follows an **Offline Ingestion + Indexing + Online Retrieval** pipeline architecture:

```
[BIS Data Source (Local JSON / CSV / Mock)]
             ↓
[Validation & 15-Field Normalization]
             ↓
[SHA-256 Content Hashing & Change Detection]
   ├── New / Modified ──> [PostgreSQL DB Update] ──> [Selective ChromaDB Embedding Update]
   └── Unchanged ────────> [Skip DB & Vector Ops (Zero LLM / Embedding Overhead)]
             ↓
[Online Hybrid Retrieval (Exact IS Regex + SQL Metadata + ChromaDB Vector Search)]
             ↓
[Candidate Reranking & Deduplication (Top 5-10 Standards Selected)]
             ↓
[Small Relevant Context Window (~95% Context Reduction)]
             ↓
[LangGraph Master Recommendation Engine]
```

---

## 🚀 Key Features & Capabilities

1. **Modular Connector Interface**: Extensible `BISConnectorInterface` supporting JSON, CSV, and Mock connectors without inventing BIS data.
2. **Incremental Ingestion & SHA-256 Hashing**: Automatic change detection. Skips unchanged records, logs invalid entries, and updates ChromaDB vector embeddings selectively.
3. **Hybrid Search & Candidate Reranking**: Exact IS number regex lookup (`IS\s*\d+`), SQL metadata filtering, and ChromaDB semantic similarity search. Reranks candidates and sends only top 5–10 standards to the LLM.
4. **Tender Gap Analysis**: Compares tender requirements against standard provisions with explicit status tags (`Match`, `Mismatch`, `Unknown`, `Verification Required`).
5. **Evidence-Backed Relationship Graph**: Connects normative references, test methods, material specs, safety codes, and superseded/superseding standards with clause and evidence citations.
6. **Certification & Revision Safety**: Clearly distinguishes verified catalog data from official gazette QCO requirements with mandatory legal disclaimers.
7. **Ingestion Audit Governance**: Admin API endpoints (`POST /api/standards/sync`, `GET /api/standards/ingest-logs`) protected with JWT authentication, persisting detailed audit records in PostgreSQL (`ingestion_audit_logs`).

---

## 📊 Benchmark Performance & Evaluation Metrics

| Metric | Measured Value | Target Benchmark | Status |
|---|---|---|---|
| **Retrieval Recall@5** | **100.00%** (7/7) | ≥ 85.0% | PASS |
| **Retrieval Recall@10** | **100.00%** (7/7) | ≥ 85.0% | PASS |
| **Cross-Domain Parameter Leakage** | **0.00%** | 0.0% | PASS |
| **Context Window Reduction** | **~95.0%** | ≥ 90.0% | PASS |
| **Test Suite Pass Rate** | **100%** (18/18 Tests) | 100% | PASS |

---

## 🧪 Verification & Testing Commands

### Run 18-Scenario Unit & Ingestion Test Suite:
```bash
pytest backend/app/test/test_bis_ingestion_and_retrieval.py -s
```

### Run 5-Domain Anti-Leakage Test Suite:
```bash
python backend/scratch/test_all_scenarios.py
```

### Start Backend Development Server:
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### Start Frontend Development Server:
```bash
cd frontend
npm run dev
```

---

## 🔒 Administrative Sync APIs

- `POST /api/standards/sync` - Triggers incremental BIS ingestion sync (Requires JWT Bearer Header).
- `GET /api/standards/ingest-logs` - Retrieves history of ingestion runs and change detection logs (Requires JWT Bearer Header).
