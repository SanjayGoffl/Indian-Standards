# Testing Patterns

**Analysis Date:** 2026-09-27

## Test Framework

**Runner:**
- Python built-in `unittest` (no `pytest`, no `pytest.ini`/`pyproject.toml` test config detected in `backend/`)
- Tests live in `backend/app/test/` and are runnable individually as scripts (each ends with `if __name__ == "__main__": unittest.main()`)

**Assertion Library:**
- `unittest.TestCase` assertion methods (`assertIn`, `assertTrue`, `assertFalse`, `assertGreaterEqual`, `assertEqual`)

**Run Commands:**
```bash
# From backend/ (venv activated)
python -m unittest app.test.test_procurement_engine -v
python -m unittest discover -s app/test -p "test_*.py" -v

# Or run a single file directly (test files manipulate sys.path themselves)
python app/test/test_procurement_engine.py
```
No coverage tool, CI workflow, or npm test script was found for the frontend (`frontend/package.json` has no `"test"` script).

## Test File Organization

**Location:**
- All backend tests are centralized in `backend/app/test/` (not co-located with source modules)
- Files present: `test_bis_ingestion_and_retrieval.py`, `test_hdpe_piping_applicability.py`, `test_memory.py`, `test_new_improvements_and_security.py`, `test_procurement_engine.py`

**Naming:**
- `test_<feature_area>.py` — named after the subsystem under test (e.g. `test_procurement_engine.py`, `test_bis_ingestion_and_retrieval.py`), not after a single source file 1:1

**Structure:**
```
backend/app/test/
├── test_bis_ingestion_and_retrieval.py
├── test_hdpe_piping_applicability.py
├── test_memory.py                       # manual smoke-test script, not unittest-based
├── test_new_improvements_and_security.py
└── test_procurement_engine.py
```

## Test Structure

**Suite Organization (from `backend/app/test/test_procurement_engine.py`):**
```python
class TestProcurementEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()
        seed_indian_standards(cls.db)
        cls.user = cls.db.query(User).first()
        if not cls.user:
            cls.user = User(email="unittest@example.com", ...)
            cls.db.add(cls.user)
            cls.db.commit()
            cls.db.refresh(cls.user)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_exact_is_number_extraction_and_lookup(self):
        """Test exact IS number regex extraction and retrieval boosting."""
        ...
```

**Patterns:**
- Setup is class-scoped (`setUpClass`/`tearDownClass`), not per-test — a single real DB session and a seeded dataset are shared across all test methods in a class, so tests are not fully isolated from each other
- Test methods are numbered (`test_01_`, `test_02_`, ...) to signal intended read order and to align with the numbered scenario list in the module docstring
- Each test has a one-line docstring describing the scenario, doubling as the spec for that behavior
- Assertions favor `assertTrue(any(... for ... in ...))` style checks against lists of dicts returned by service calls, since exact ordering/content of recommendations is not guaranteed

## Mocking

**Framework:** No `unittest.mock`/`pytest-mock` usage found in the test files reviewed — the suite favors **real integration over mocks**.

**Patterns:**
- External BIS lookups are stubbed via a dedicated fake implementation class rather than `Mock()`: `MockBISConnector` in `backend/app/services/bis_connector.py`, imported directly into tests (`backend/app/test/test_procurement_engine.py:31`)
- Database is real (SQLite/Postgres via `SessionLocal`/`engine` from `backend/app/core/database.py`), created fresh with `Base.metadata.create_all(bind=engine)` and seeded via `seed_indian_standards(db)` (`backend/app/services/standards_knowledge_base.py`) rather than mocked

**What to Mock:**
- External/third-party network calls to the real BIS system — use `MockBISConnector`-style fake classes, not `unittest.mock.patch`, to stay consistent with existing style

**What NOT to Mock:**
- Database session and ORM models — tests run against a real (test) database via `SessionLocal`
- Core service/recommendation logic — tests call `process_procurement_recommendation` and `retrieve_candidate_standards` directly, exercising the real pipeline end-to-end

## Fixtures and Factories

**Test Data:**
```python
# Seeded once per class via a real service call, not fixture files
Base.metadata.create_all(bind=engine)
cls.db = SessionLocal()
seed_indian_standards(cls.db)   # backend/app/services/standards_knowledge_base.py

cls.user = cls.db.query(User).first()
if not cls.user:
    cls.user = User(email="unittest@example.com", hashed_password="hashed_pass", full_name="Unit Test User")
    cls.db.add(cls.user); cls.db.commit(); cls.db.refresh(cls.user)
```
- Benchmark/evaluation datasets are declared inline as a list of dicts within the test method itself (`eval_dataset = [...]` in `test_10_recall_evaluation_dataset`, `backend/app/test/test_procurement_engine.py:177-213`) rather than externalized to a fixtures file

**Location:**
- No dedicated `fixtures/` or `factories/` directory — seed data comes from production seeding functions (`seed_indian_standards`) reused as test fixtures, and ad-hoc data is inlined per test

## Coverage

**Requirements:** None enforced — no coverage tool, threshold, or CI gate detected.

**View Coverage:**
```bash
# Not configured; would need manual setup, e.g.:
pip install coverage
coverage run -m unittest discover -s backend/app/test
coverage report
```

## Test Types

**Unit Tests:** Not strictly unit-isolated — most "unit" tests in `backend/app/test/test_procurement_engine.py` exercise multiple layers (retrieval + recommendation + DB) together.

**Integration Tests:** The dominant style. Tests hit the real service layer (`process_procurement_recommendation`) and real database, covering scenarios like exact IS lookup, semantic recommendation, wrong-domain exclusion, missing-requirement detection, and outdated-standard handling end-to-end (`backend/app/test/test_procurement_engine.py`).

**Benchmark/Evaluation Tests:** A distinct pattern — `test_10_recall_evaluation_dataset` computes Recall@5/Recall@10 metrics over a hand-written evaluation dataset and asserts a minimum recall threshold (`self.assertGreaterEqual(recall_5, 0.85, ...)`), printing a formatted metrics block to stdout for visibility (`backend/app/test/test_procurement_engine.py:215-239`). Use this pattern for any new retrieval/ranking feature that needs quality regression protection.

**Manual smoke scripts:** `backend/app/test/test_memory.py` is not a `unittest` suite — it is a `main()` script that exercises `ConversationMemoryAgent` and prints results for manual inspection. Follow the `unittest.TestCase` pattern instead for new automated tests; reserve script-style files only for manual/interactive debugging.

**E2E Tests:** Not used. No frontend test framework, Cypress/Playwright config, or `frontend/**/*.test.*` files were found.

## Common Patterns

**Multi-condition existence checks:**
```python
self.assertTrue(any("456" in s["standard_number"] for s in all_recs))
```

**Negative/exclusion assertions:**
```python
self.assertFalse(any("694" in num or "7098" in num for num in rec_nums))
self.assertTrue(any("Product scope mismatch" in ex.get("exclusion_reason", "") for ex in ex_list))
```

**Fallback/graceful-degradation testing:**
```python
report = process_procurement_recommendation(db=self.db, user_id=self.user.id,
    input_text="Quantum magnetic levitation propulsion thruster shield.",
    product_category="Aerospace Physics")
self.assertIn("overall_status", report)
self.assertIn("No Applicable Standard Confirmed", report["overall_status"])
```

---

*Testing analysis: 2026-09-27*
