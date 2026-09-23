# QueryNest AI Knowledge Retrieval & Indian Standards Procurement System

QueryNest AI is an advanced AI-powered Knowledge Retrieval and Indian Standards (BIS) Procurement Recommendation System built for e-Procurement (GeM, CPWD, PSUs), public tenders, and municipal utility workflows.

---

## 🏛️ System Architecture

QueryNest follows a strict **Offline Ingestion + Incremental Hashing + Online Hybrid Retrieval** pipeline architecture:

```
[BIS Data Connectors (Local JSON / CSV / Mock)]
             ↓
[Input Validation & Canonical Standard Normalization]
             ↓
[SHA-256 Content Hashing & Change Detection]
   ├── New / Modified ──> [PostgreSQL Relational DB] ──> [ChromaDB Vector Upsert]
   │                                                             │
   │                                                    Success: embedding_status = "indexed"
   │                                                    Failure: embedding_status = "failed", needs_reindex = True
   └── Unchanged ────────> [Skip Vector Operations (Zero Embedding Overhead)]
             ↓
[Online Hybrid Retrieval (Exact IS Regex + SQL Metadata + ChromaDB Semantic Vector Search)]
             ↓
[Deterministic Candidate Re-ranking & Deduplication (Top 5-10 Standards Selected)]
             ↓
[Applicability Engine & Field Comparison Matrix Evaluation]
             ↓
[Evidence-Based Report Generation & Legal Safety Disclaimers]
```

---

## 📋 Data Schema & Canonical Normalization

The system normalizes standard identifiers to prevent duplicates caused by formatting differences (e.g. `IS 4984`, `IS4984`, `IS 4984:2016`, `IS 7098 (Part 1):1988`):

- `standard_number`: Raw display standard identifier.
- `canonical_standard_number`: Standardized canonical identifier (e.g., `IS 7098 (Part 1):1988`).
- `base_standard_number`: Base standard identifier (e.g., `IS 7098`).
- `part_number`: Part number details (e.g., `Part 1`).
- `revision_year`: Publication / reaffirmation revision year (e.g., `2016`).
- `content_hash`: Deterministic SHA-256 content hash across standardized fields.

---

## 🔍 Source Provenance & Verification Model

Every technical standard entry and relationship carries explicit provenance metadata:

1. `source_type`: Category of data source (`Official Document Record`, `Local Metadata Index`).
2. `source`: Source provider or file (`Local BIS Catalogue`, `Official Gazette`).
3. `source_url`: URL for official standard reference or manual catalogue lookup.
4. `source_url_label`: Explanatory label distinguishing verified links from manual lookup links.
5. `source_document`: Source document reference.
6. `page_or_clause`: Specific page or clause reference.
7. `verification_status`: Status label (`Unverified`, `Verification Required`, `Verified`, `Verified by Official Gazette`).

---

## 🔄 Incremental Sync & ChromaDB Synchronization Safety

- **Incremental Change Detection**: Standards are hashed using SHA-256. Unchanged records bypass ChromaDB re-embedding to eliminate redundant vector operations.
- **Transactional Sync Tracking**: Database records track `embedding_status` (`pending`, `indexed`, `failed`), `indexed_content_hash`, `last_embedded_at`, `needs_reindex`, and `embedding_error`.
- **Failure Resilience & Retry API**: In case of vector store failures during ingestion, records are marked with `embedding_status = "failed"` and `needs_reindex = True`. Administrators can trigger `POST /api/standards/reindex-failed` to retry pending embeddings.
- **Soft Deletion**: Records missing from source updates are marked as `source_missing` or `inactive_pending_review` rather than deleted.

---

## ⚖️ Applicability Validation & HDPE Piping Regression Fix

Candidate standards are evaluated against extracted procurement requirements using domain compatibility rules and a 6-parameter Field Comparison Matrix.

- **HDPE Water Pipes (`IS 4984:2016`)**: Correctly classified as **Potentially Applicable** under "Recommended & Potentially Applicable Standards" for water distribution and conveyance queries.
- **Cross-Domain Exclusion**: Valid exclusions are maintained for unrelated domains (Electrical Cables, Concrete, Solar PV, Helmets, Robotics).
- **Evidence-Based Evaluation Labels**:
  - `Confirmed Match`
  - `Potential Match`
  - `Not Confirmed`
  - `Mismatch`
  - `Missing Input`
  - `Requires Official Verification`

---

## 🛡️ Certification & QCO Legal Safety

Quality Control Orders (QCOs) and mandatory BIS product certification claims require full authoritative evidence:
- Notification Number
- Issuing Authority
- Notification Date
- Effective Date
- Product Scope
- Official Gazette URL

In the absence of complete gazette evidence, the system safely outputs standard verification notices:
> *"Applicability of mandatory BIS certification, QCO requirements, tender conditions, and municipal authority requirements requires verification from current official sources."*

---

## 🔒 API Security & Role-Based Authorization

All administrative standards endpoints require active accounts (`is_active == True`) and administrative privileges (`role == "Admin"`):

- `POST /api/standards/seed` — Seeds default Indian Standards catalog (Admin only, HTTP 403 for non-admins).
- `POST /api/standards/sync` — Triggers incremental ingestion sync (Admin only, HTTP 403 for non-admins).
- `GET /api/standards/ingest-logs` — Retrieves execution audit logs (Admin only, HTTP 403 for non-admins).
- `POST /api/standards/reindex-failed` — Retries failed ChromaDB vector embeddings (Admin only, HTTP 403 for non-admins).

---

## 🛠️ Setup & Migration Instructions

### 1. Install Dependencies:
```bash
cd backend
pip install -r requirements.txt
```

### 2. Run Database Migrations:
```bash
cd backend
alembic upgrade head
```

### 3. Start Backend Server:
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 4. Start Frontend Application:
```bash
cd frontend
npm run dev
```

---

## 🧪 Automated Test Commands

### Run Full Pytest Suite (40 Tests):
```bash
pytest backend/app/test/ -s
```

### Run Specific Test Modules:
```bash
pytest backend/app/test/test_bis_ingestion_and_retrieval.py -s
pytest backend/app/test/test_hdpe_piping_applicability.py -s
```

### Run 5-Domain Scenario Anti-Leakage Test:
```bash
python backend/scratch/test_all_scenarios.py
```

---

## 📊 Prototype Benchmark Methodology

> **Disclaimer**: *Performance metrics reported below are measured on the local prototype benchmark dataset v1.0.*

| Metric | Measured Value | Evaluation Scope |
|---|---|---|
| **Retrieval Recall@5** | **100.00%** | Measured on the local prototype benchmark dataset |
| **Retrieval Recall@10** | **100.00%** | Measured on the local prototype benchmark dataset |
| **Precision@5** | **100.00%** | Measured on the local prototype benchmark dataset |
| **Mean Reciprocal Rank (MRR)** | **1.0000** | Measured on the local prototype benchmark dataset |
| **NDCG@5** | **1.0000** | Measured on the local prototype benchmark dataset |
| **Cross-Domain Parameter Leakage** | **0.00%** | Measured on 5 distinct procurement domains |
| **False Positive Rate** | **0.00%** | Measured against disallowed cross-domain standards |
| **Test Suite Pass Rate** | **100% (40/40 Tests)** | Automated pytest execution |

---

## ⚠️ Important Legal & Technical Disclaimer

> **Official Disclaimer**:
> The QueryNest system provides AI-assisted standards discovery and preliminary technical applicability validation. It does not independently establish official BIS compliance, certification, legal validity, or QCO applicability. All procurement specifications, standard versions, active amendments, and mandatory certification requirements must be verified against current official publications from the Bureau of Indian Standards (BIS) and official Gazette notifications prior to tender publication or commercial procurement execution.
