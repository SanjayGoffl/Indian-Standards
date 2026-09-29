"""
Regression: 1.1 kV copper / PVC insulated / PVC sheathed underground cable benchmark.

Golden expectation
  PRIMARY:              IS 1554 (Part 1)
  SECONDARY/CONDITIONAL IS 694
  RELATED:              IS 5831 (material), IS 3961 (Part 2) (current ratings)
  TEST/INSTALLATION:    IS 10810 (test methods), IS 1255 (installation code of practice)
  EXCLUDED:             IS 7098 (Part 1) + shipboard/offshore standards (IS 10242)

The catalogue is an isolated in-memory SQLite database seeded with verbatim BIS catalogue rows
(catalogue_fixtures.py), so the test is hermetic and never touches querynest.db.
The LLM is stubbed to count invocations.
"""

import time
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.llm import llm_service
from app.core.models import IndianStandard
from app.services.compliance_engine import detect_profile, extract_schema, retrieve_candidates
from app.services.recommendation_service import process_procurement_recommendation
from app.test import catalogue_fixtures as fx

GOLDEN_INPUT = (
    "Tender for supply of 1.1 kV grade copper conductor PVC insulated and PVC sheathed power cables, "
    "single-core and multicore, for underground and outdoor laying. Cables shall be FRLS, provide moisture "
    "resistance and mechanical protection. Tests required: conductor resistance, insulation resistance, "
    "high voltage (withstand) test and dimensional test."
)

CATALOGUE = fx.CABLE + fx.OTHER
BUCKET_KEYS = ("recommended_standards", "potentially_applicable_standards", "related_standards",
               "test_installation_standards", "excluded_standards")


def _nums(items):
    return [i["standard_number"] for i in items]


def _has(nums, prefix):
    return any(n.startswith(prefix) for n in nums)


def _schema(text):
    profile = detect_profile(text)
    return profile, extract_schema(profile, text)


def make_db(rows):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    for num, title, cat, src, scope in rows:
        db.add(IndianStandard(standard_number=num, title=title, category=cat, source=src, scope=scope, status="Active"))
    db.commit()
    return engine, db


class TestCableBenchmarkRegression(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine, cls.db = make_db(CATALOGUE)
        cls.llm_invocations = 0

        def counting_stub(*args, **kwargs):
            TestCableBenchmarkRegression.llm_invocations += 1
            raise RuntimeError("LLM must not be needed for the deterministic path")

        with patch.object(llm_service, "generate_response", side_effect=counting_stub):
            t0 = time.perf_counter()
            cls.report = process_procurement_recommendation(cls.db, user_id="regression-user", input_text=GOLDEN_INPUT)
            cls.wall_ms = (time.perf_counter() - t0) * 1000

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        cls.engine.dispose()

    # 1. deterministic extraction / schema
    def test_01_exact_extraction(self):
        profile, schema = _schema(GOLDEN_INPUT)
        self.assertEqual(profile["id"], "power_cable")
        a = {k: v["values"] for k, v in schema["attributes"].items() if not v["derived"]}
        self.assertEqual(a["conductor"], ["Copper"])
        self.assertEqual(a["insulation"], ["PVC"])
        self.assertEqual(a["sheath"], ["PVC"])
        self.assertEqual(a["voltage"], [1100.0])
        self.assertEqual(a["core_configuration"], ["single-core", "multicore"])
        self.assertEqual(a["installation"], ["underground", "outdoor"])
        self.assertEqual(a["fire"], ["FRLS"])
        self.assertEqual(a["protection"], ["moisture resistance", "mechanical protection"])
        self.assertEqual(a["tests"], ["conductor resistance", "insulation resistance", "high voltage / withstand", "dimensional"])
        self.assertTrue(schema["attributes"]["duty"]["derived"])          # inferred, never presented as a user requirement
        self.assertEqual(schema["attributes"]["voltage"]["source_text"], ["1.1 kV"])  # verbatim user text preserved

    def test_01b_phrasing_variants_extract_same_core_fields(self):
        _, s = _schema("Cu/PVC/PVC power cable rated 1100 V, buried in trench")
        a = s["attributes"]
        self.assertEqual((a["conductor"]["values"], a["insulation"]["values"], a["sheath"]["values"], a["voltage"]["values"]),
                         (["Copper"], ["PVC"], ["PVC"], [1100.0]))
        self.assertIn("underground", a["installation"]["values"])

    def test_01c_xlpe_insulated_pvc_sheathed_not_read_as_pvc_insulation(self):
        _, s = _schema("Copper XLPE insulated PVC sheathed cable 1100 V")
        self.assertEqual(s["attributes"]["insulation"]["values"], ["XLPE"])
        self.assertEqual(s["attributes"]["sheath"]["values"], ["PVC"])

    # 2. hard gates + 4. deterministic exclusion reasons from BIS metadata
    def test_02_incompatibility_gates_and_reasons(self):
        ex = {e["standard_number"]: e for e in self.report["excluded_standards"]}
        for num in ("IS 7098 (Part 1):1988", "IS 7098 (Part 1):2025"):
            self.assertIn(num, ex)
            self.assertEqual(ex[num]["gate"], "Core Insulation Mismatch")
            self.assertIn("XLPE", ex[num]["exclusion_reason"])
            self.assertIn("PVC", ex[num]["exclusion_reason"])
            self.assertIn(ex[num]["title"], ex[num]["exclusion_reason"])   # reason cites the BIS title itself
        ship = [e for n, e in ex.items() if n.startswith("IS 10242")]
        self.assertGreaterEqual(len(ship), 2)
        for e in ship:
            self.assertEqual(e["gate"], "Application Domain Mismatch")
            self.assertIn("shipboard/offshore", e["exclusion_reason"])
        self.assertEqual(ex["IS 1554 (Part 2):1988"]["gate"], "Working Voltage Mismatch")
        self.assertIn("3300 V", ex["IS 1554 (Part 2):1988"]["exclusion_reason"])
        self.assertEqual(ex["IS 9968 (Part 1):2025"]["gate"], "Core Insulation Mismatch")

    def test_02b_gates_run_before_ranking(self):
        excluded = set(_nums(self.report["excluded_standards"]))
        for key in BUCKET_KEYS[:-1]:
            self.assertFalse(excluded & set(_nums(self.report[key])), key)

    def test_02c_inferred_constraint_never_excludes(self):
        """Light-duty rating table conflicts only with an INFERRED duty class: dropped, not excluded on invented grounds."""
        self.assertNotIn("IS 3961 (Part 5):1968", _nums(self.report["excluded_standards"]))
        self.assertNotIn("IS 3961 (Part 5):1968", _nums(self.report["related_standards"]))

    # 3. product vs installation/allied separation + required buckets
    def test_03_primary_secondary_related_test_installation(self):
        self.assertEqual(_nums(self.report["recommended_standards"]), ["IS 1554 (Part 1):1988"])
        self.assertEqual(_nums(self.report["potentially_applicable_standards"]), ["IS 694:2010"])
        related = _nums(self.report["related_standards"])
        self.assertTrue(_has(related, "IS 5831"))
        self.assertTrue(_has(related, "IS 3961 (Part 2)"))
        ti = _nums(self.report["test_installation_standards"])
        self.assertTrue(_has(ti, "IS 10810"))
        self.assertTrue(_has(ti, "IS 1255"))
        types = {r["standard_number"]: r["relationship_type"] for r in self.report["test_installation_standards"]}
        self.assertEqual(types["IS 1255:1983"], "installation")
        self.assertEqual(types["IS 10810 (Part 5):1984"], "test_method")
        allied = related + ti
        product = _nums(self.report["recommended_standards"]) + _nums(self.report["potentially_applicable_standards"])
        self.assertFalse(set(allied) & set(product))

    def test_03b_secondary_reason_is_conditional(self):
        sec = self.report["potentially_applicable_standards"][0]
        self.assertEqual(sec["recommendation_role"], "SECONDARY_CONDITIONAL")
        self.assertIn("heavy duty", sec["reasoning"].lower())
        self.assertIn("conditions:", sec["reasoning"])

    def test_03c_test_methods_map_to_requested_tests_only(self):
        parts = {r["standard_number"]: r["matched_requirement"] for r in self.report["test_installation_standards"]
                 if r["standard_number"].startswith("IS 10810")}
        self.assertIn("conductor resistance", parts["IS 10810 (Part 5):1984"])
        self.assertIn("insulation resistance", parts["IS 10810 (Part 43):1984"])
        self.assertIn("high voltage", parts["IS 10810 (Part 45):1984"])
        self.assertIn("dimensional", parts["IS 10810 (Part 6):1984"])
        self.assertNotIn("IS 10810 (Part 1):1984", parts)    # annealing test: not requested
        self.assertNotIn("IS 10810 (Part 36):1984", parts)   # armour dimensions: not requested

    # 5. consistent buckets/counts
    def test_05_bucket_counts_consistent(self):
        s = self.report["recommendation_summary"]
        self.assertEqual(s["primary"], len(self.report["recommended_standards"]))
        self.assertEqual(s["secondary_conditional"], len(self.report["potentially_applicable_standards"]))
        self.assertEqual(s["related"], len(self.report["related_standards"]))
        self.assertEqual(s["test_installation"], len(self.report["test_installation_standards"]))
        self.assertEqual(s["excluded"], len(self.report["excluded_standards"]))
        self.assertEqual(s["total_evaluated"], sum(len(self.report[k]) for k in BUCKET_KEYS))
        everything = [n for k in BUCKET_KEYS for n in _nums(self.report[k])]
        self.assertEqual(len(everything), len(set(everything)), "a standard appears in more than one bucket")
        self.assertEqual(self.report["overall_status"], "Applicable Standard Confirmed")

    # 6. every explicit requirement preserved
    def test_06_all_requirements_preserved(self):
        values = " | ".join(f"{r['parameter']}={r['value_spec']}" for r in self.report["extracted_requirements"])
        for expected in ("Copper", "PVC", "1100 V", "single-core + multicore", "underground / outdoor", "FRLS",
                         "moisture resistance", "mechanical protection", "conductor resistance", "insulation resistance",
                         "high voltage / withstand", "dimensional"):
            self.assertIn(expected, values)
        self.assertNotIn("Heavy duty", values)  # inferred constraints are not reported as user requirements
        matrix = " | ".join(f"{m['parameter']}={m['required_value']}" for m in self.report["recommended_standards"][0]["field_comparison_matrix"])
        for expected in ("Copper", "PVC", "1100 V", "single-core", "multicore", "underground", "outdoor", "FRLS",
                         "moisture resistance", "mechanical protection", "conductor resistance", "insulation resistance",
                         "high voltage / withstand", "dimensional"):
            self.assertIn(expected, matrix)

    # 7. IS 1554 retrieved and ranked first from product + insulation + voltage + heavy duty
    def test_07_is1554_retrieved_and_ranked_first(self):
        profile, schema = _schema(GOLDEN_INPUT)
        pool = [s.standard_number for s in retrieve_candidates(self.db, profile, schema, GOLDEN_INPUT)]
        self.assertIn("IS 1554 (Part 1):1988", pool)
        self.assertNotIn("IS 456:2000", pool)
        self.assertEqual(self.report["recommended_standards"][0]["standard_number"], "IS 1554 (Part 1):1988")
        self.assertGreater(self.report["recommended_standards"][0]["internal_match_score"],
                           self.report["potentially_applicable_standards"][0]["internal_match_score"])

    def test_07b_gates_are_data_driven_not_hardcoded(self):
        """Ask for XLPE and IS 7098 becomes eligible while PVC-only IS 1554 is gated out."""
        with patch.object(llm_service, "generate_response", side_effect=RuntimeError("no llm")):
            rep = process_procurement_recommendation(self.db, "regression-user", input_text=(
                "Copper XLPE insulated PVC sheathed power cable, 1100 V, underground laying, mechanical protection"))
        self.assertTrue(_has(_nums(rep["recommended_standards"]) + _nums(rep["potentially_applicable_standards"]), "IS 7098 (Part 1)"))
        ex = {e["standard_number"]: e for e in rep["excluded_standards"]}
        self.assertEqual(ex["IS 1554 (Part 1):1988"]["gate"], "Core Insulation Mismatch")

    def test_07c_nothing_invented_when_not_stated(self):
        """No heavy-duty / underground wording => no derived duty class and both PVC product standards stay primary."""
        rep = process_procurement_recommendation(self.db, "regression-user", input_text="Copper PVC insulated cable 1100 V for indoor wiring")
        self.assertNotIn("duty", rep["requirements_schema"]["attributes"])
        self.assertEqual(sorted(_nums(rep["recommended_standards"])), ["IS 1554 (Part 1):1988", "IS 694:2010"])

    # 8. no LLM for a recognised domain
    def test_08_no_llm_calls_and_latency(self):
        self.assertEqual(self.llm_invocations, 0)
        m = self.report["processing_metrics"]
        self.assertEqual(m["llm_calls"], 0)
        self.assertEqual(m["extraction_path"], "deterministic_profile:power_cable")
        self.assertLess(m["latency_ms"], 5000)
        print(f"\n[cable-benchmark] pipeline latency={m['latency_ms']} ms, wall={self.wall_ms:.1f} ms, llm_calls={m['llm_calls']}")


if __name__ == "__main__":
    unittest.main()
