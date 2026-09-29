"""
Generic regression suite: the same engine, driven only by input text + domain profile + retrieved
catalogue metadata, must give correct buckets for unrelated domains, never leak assumptions between
runs, never invent requirement values, and use no LLM for a recognised domain.

Catalogue rows are verbatim BIS records (catalogue_fixtures.py) in an isolated in-memory database.
"""

import re
import unittest
from pathlib import Path
from unittest.mock import patch

from app.core.llm import llm_service
from app.services import compliance_engine
from app.services.compliance_engine import detect_profile, extract_schema
from app.services.recommendation_service import process_procurement_recommendation
from app.services.recommendation_validator import finalize_recommendation_buckets
from app.test import catalogue_fixtures as fx
from app.test.test_cable_benchmark_regression import BUCKET_KEYS, GOLDEN_INPUT, make_db, _nums

ALL_ROWS = fx.CABLE + fx.GLOVES + fx.HELMET + fx.REBAR + fx.PIPE + fx.PV + fx.OTHER


class GenericEngineBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine, cls.db = make_db(ALL_ROWS)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        cls.engine.dispose()

    def run_case(self, text, hint=None):
        # Count LLM invocations at the boundary (generate_response increments the counter, then get_llm fails).
        with patch("app.core.llm.get_llm", side_effect=RuntimeError("LLM unavailable in test")):
            return process_procurement_recommendation(self.db, "generic-user", input_text=text, product_category=hint)

    def assert_buckets_exclusive(self, rep):
        allnums = [n for k in BUCKET_KEYS for n in _nums(rep[k])]
        self.assertEqual(len(allnums), len(set(allnums)), f"standard in more than one bucket: {allnums}")
        s = rep["recommendation_summary"]
        for key, short in zip(BUCKET_KEYS, ("primary", "secondary_conditional", "related", "test_installation", "excluded")):
            self.assertEqual(s[short], len(rep[key]), short)
        return {k: _nums(rep[k]) for k in BUCKET_KEYS}

    def assert_engine_path(self, rep, profile_id):
        m = rep["processing_metrics"]
        self.assertEqual(m["extraction_path"], f"deterministic_profile:{profile_id}")
        self.assertEqual(m["llm_calls"], 0)


class TestMultiDomain(GenericEngineBase):

    def test_pipes_potable_water_full_spec(self):
        rep = self.run_case("Supply of HDPE PE 100 pipes, 110 mm, PN 10, for municipal potable water supply, laid underground.")
        self.assert_engine_path(rep, "plastic_pipe")
        b = self.assert_buckets_exclusive(rep)
        self.assertEqual(b["recommended_standards"], ["IS 4984:2016"])
        self.assertEqual(b["test_installation_standards"], ["IS 7634 (Part 2):2012"])   # laying codes for other pipe materials are not tied to the request
        live = sum([b[k] for k in BUCKET_KEYS if k != "excluded_standards"], [])
        for other_material in ("IS 3114:1994", "IS 783:1985", "IS 5822:1994", "IS 18910:2024"):
            self.assertNotIn(other_material, live)          # laying codes / coatings for other pipe materials
        ex_gate = {e["standard_number"]: e["gate"] for e in rep["excluded_standards"]}
        self.assertEqual(ex_gate["IS 5822:1994"], "Pipe Material Mismatch")   # steel water-pipe laying code vs polyethylene requirement
        ex = {e["standard_number"]: e for e in rep["excluded_standards"]}
        self.assertEqual(ex["IS 14333:2022"]["gate"], "Intended Use Mismatch")       # sewerage/effluent title vs potable requirement
        self.assertIn("sewerage", ex["IS 14333:2022"]["exclusion_reason"])
        self.assertEqual(ex["IS 14885:2022"]["gate"], "Application Domain Mismatch")  # gaseous fuels
        self.assertEqual(ex["IS 12786:2024"]["gate"], "Application Domain Mismatch")  # irrigation
        values = {r["value_spec"] for r in rep["extracted_requirements"]}
        self.assertTrue({"PE 100", "110 mm", "PN 10"} <= values)

    def test_pipes_missing_inputs_keeps_standard_conditional(self):
        rep = self.run_case("Supply of HDPE water pipes for water distribution and conveyance applications.", "Piping")
        self.assert_engine_path(rep, "plastic_pipe")
        self.assertEqual(rep["product_category"], "Piping")            # user's own category hint preserved
        b = self.assert_buckets_exclusive(rep)
        self.assertEqual(b["recommended_standards"], [])
        self.assertIn("IS 4984:2016", b["potentially_applicable_standards"])
        item = rep["potentially_applicable_standards"][0]
        rows = {m["parameter"]: m for m in item["field_comparison_matrix"]}
        self.assertEqual(rows["Pressure Rating"]["result"], "Missing Input")
        self.assertEqual(rows["Pipe Diameter"]["procurement_requirement"], "Not provided")
        self.assertTrue(any("Pressure rating" in m for m in rep["missing_requirements"]))

    def test_gloves_chemical_no_applicable_standard(self):
        rep = self.run_case("Chemical-resistant nitrile gloves for laboratory technicians handling acids, sizes 7-11.")
        self.assert_engine_path(rep, "safety_gloves")
        b = self.assert_buckets_exclusive(rep)
        self.assertEqual(b["recommended_standards"] + b["potentially_applicable_standards"], [])
        ex = {e["standard_number"]: e for e in rep["excluded_standards"]}
        self.assertEqual(ex["IS 13774:2021"]["gate"], "Hazard Protection Mismatch")      # live-working (electrical) gloves
        self.assertEqual(ex["IS 11230:2023"]["gate"], "Hazard Protection Not Established")
        for num in ("IS 13422:2024", "IS 3785:2023", "IS 3874:1987", "IS 4149:2025", "IS 16874:2018", "IS 18605:2024"):
            self.assertEqual(ex[num]["gate"], "Application Domain Mismatch", num)
        self.assertEqual(ex["IS 10540:1991"]["gate"], "Application Domain Mismatch")   # surgical instrument standard pooled via "Glover's"
        self.assertIn("No", rep["overall_status"])

    def test_gloves_electrical_primary_and_residual_quantity_kept(self):
        rep = self.run_case("Insulating gloves for live working on 1000 V installations")
        b = self.assert_buckets_exclusive(rep)
        self.assertEqual(b["recommended_standards"], ["IS 13774:2021"])
        self.assertIn("1000 V", {r["value_spec"] for r in rep["extracted_requirements"]})

    def test_helmets_industrial(self):
        rep = self.run_case("Industrial safety helmets for head protection against mechanical impact in construction.")
        self.assert_engine_path(rep, "safety_helmet")
        b = self.assert_buckets_exclusive(rep)
        self.assertEqual(b["recommended_standards"], ["IS 2925:1984"])
        self.assertEqual(b["test_installation_standards"], ["IS 7692:2024"])       # headform verifies the requested impact test
        ex = {e["standard_number"]: e["exclusion_reason"] for e in rep["excluded_standards"]}
        for num, dom in (("IS 4151:2015", "motorcycle"), ("IS 18808:2025", "bicycle"), ("IS 11207:1983", "mountaineering"),
                         ("IS 2745:1983", "fire/police"), ("IS 19089:2025", "respiratory"), ("IS 9973:1981", "motorcycle")):
            self.assertIn(dom, ex[num], num)

    def test_reinforcement_steel(self):
        rep = self.run_case("Supply of Fe 500D TMT rebars (high strength deformed steel bars) for RCC construction.")
        self.assert_engine_path(rep, "reinforcement_steel")
        b = self.assert_buckets_exclusive(rep)
        self.assertEqual(b["recommended_standards"], ["IS 1786:2008"])
        for coated in ("IS 13620:1993", "IS 12594:1988", "IS 19068:2025"):
            self.assertIn(coated, b["potentially_applicable_standards"])            # coating variant never requested
        ex = {e["standard_number"]: e["gate"] for e in rep["excluded_standards"]}
        self.assertEqual(ex["IS 18256:2023"], "Bar Material Mismatch")              # GFRP bars vs steel
        self.assertEqual(ex["IS 432 (Part 1):1982"], "Strength Class Mismatch")     # mild steel vs stated high strength
        self.assertIn("IS 16172:2023", b["related_standards"])                      # couplers for steel bars
        self.assertNotIn("IS 2502:1963", sum(b.values(), []))                       # bending code: no installation intent stated
        self.assertIn("IS 16651:2017", b["potentially_applicable_standards"])       # stainless variant never requested
        for not_bars in ("IS 1566:1982", "IS 19464:2025", "IS 13071:2024"):          # wire fabric / hose wire are not reinforcement bars
            self.assertNotIn(not_bars, sum(b.values(), []))

    def test_pv_modules(self):
        rep = self.run_case("Crystalline silicon solar PV modules, 400 Wp, for terrestrial power generation.")
        self.assert_engine_path(rep, "pv_module")
        b = self.assert_buckets_exclusive(rep)
        self.assertEqual(set(b["recommended_standards"]), {"IS 14286:2010 / IEC 61215:2005", "IS 14286 (Part 1):2023"})
        ex = {e["standard_number"]: e["gate"] for e in rep["excluded_standards"]}
        self.assertEqual(ex["IEC 62108:2022"], "Cell Technology Mismatch")          # concentrator PV vs stated crystalline silicon
        for not_modules in ("IEC 62109-1 : 2010", "IS 12762 (Part 13):2020", "IS 12762 (Part 1):2024"):
            self.assertNotIn(not_modules, sum(b.values(), []))                      # converters / measurement procedures
        self.assertNotIn("IS 13129 (Part 1):2023", sum(b.values(), []))             # solar water heating is not a PV module standard
        self.assertIn("400 Wp", {r["value_spec"] for r in rep["extracted_requirements"]})

    def test_cable_still_correct_in_mixed_catalogue(self):
        rep = self.run_case(GOLDEN_INPUT)
        b = self.assert_buckets_exclusive(rep)
        self.assertEqual(b["recommended_standards"], ["IS 1554 (Part 1):1988"])
        self.assertEqual(b["potentially_applicable_standards"], ["IS 694:2010"])
        # nothing from the other domains' fixtures appears anywhere in a cable report
        for n in sum(b.values(), []):
            self.assertFalse(n.startswith(("IS 4984", "IS 2925", "IS 1786", "IS 13774", "IS 14286")), n)


class TestRunIsolation(GenericEngineBase):

    def test_no_assumption_or_result_leaks_between_runs(self):
        cable1 = self.run_case(GOLDEN_INPUT)
        gloves = self.run_case("Live working insulating gloves for 1000 V")
        pipe = self.run_case("HDPE pipes for potable water supply, 63 mm, PN 6")
        cable2 = self.run_case(GOLDEN_INPUT)

        blob = repr([gloves["extracted_requirements"], gloves["requirements_schema"], gloves["product_type"]]).lower()
        for cable_word in ("pvc", "cable", "copper", "frls", "underground", "1100"):
            self.assertNotIn(cable_word, blob)
        pipe_blob = repr([pipe["extracted_requirements"], pipe["requirements_schema"], pipe["product_type"], pipe["missing_requirements"]]).lower()
        for word in ("glove", "1000 v", "pvc insulated", "voltage", "cable", "frls"):
            self.assertNotIn(word, pipe_blob)
        for rep, pid in ((cable1, "power_cable"), (gloves, "safety_gloves"), (pipe, "plastic_pipe"), (cable2, "power_cable")):
            self.assertEqual(rep["requirements_schema"]["profile"], pid)
        strip = lambda r: {k: _nums(r[k]) for k in BUCKET_KEYS}
        self.assertEqual(strip(cable1), strip(cable2))   # same input -> same output regardless of what ran in between

    def test_nothing_invented_or_broadened(self):
        rep = self.run_case("Nitrile gloves for chemical handling")
        attrs = rep["requirements_schema"]["attributes"]
        self.assertEqual(set(attrs), {"hazard", "material"})                    # no size / standard / rating invented
        self.assertTrue(all(not a["derived"] for a in attrs.values()))
        self.assertEqual([r["value_spec"] for r in rep["extracted_requirements"]], ["Chemical", "Nitrile"])


class TestFallbackAndInvariants(GenericEngineBase):

    def test_unknown_domain_uses_llm_path_once(self):
        rep = self.run_case("Procurement of autonomous robotics systems for factory automation.", "Automation & Robotics")
        m = rep["processing_metrics"]
        self.assertEqual(m["extraction_path"], "llm_extraction_hybrid_retrieval")
        self.assertEqual(m["llm_calls"], 1)      # single, only because the domain is genuinely unrecognised
        self.assertIsNone(rep["requirements_schema"])
        self.assert_buckets_exclusive(rep)

    def test_ambiguous_domain_is_not_guessed(self):
        self.assertIsNone(detect_profile("Power cable to be laid through HDPE pipe ducts"))

    def test_unrecognised_quantities_still_preserved_on_fallback_path(self):
        rep = self.run_case("Procurement of autonomous robotics systems, payload 25 kg, reach 1500 mm.", "Automation & Robotics")
        values = {r["value_spec"] for r in rep["extracted_requirements"]}
        self.assertTrue({"25 kg", "1500 mm"} <= values)

    def test_engine_contains_no_domain_specific_vocabulary(self):
        src = Path(compliance_engine.__file__).read_text(encoding="utf-8").lower()
        for banned in ("cable", "pvc", "xlpe", "insulat", "sheath", "hdpe", "glove", "helmet", "rebar", "steel", "pipe", "frls", "conductor"):
            self.assertIsNone(re.search(rf"{banned}s?", src), f"domain word '{banned}' found in the generic engine")

    def test_generic_role_separation_applies_to_legacy_reports(self):
        report = {
            "recommended_standards": [{"standard_number": "IS 1 (Part 1)", "title": "Methods of test for widgets"},
                                      {"standard_number": "IS 2", "title": "Specification for widgets"}],
            "potentially_applicable_standards": [{"standard_number": "IS 3", "title": "Code of practice for widget installation and maintenance"}],
            "related_standards": [], "excluded_standards": [],
        }
        out = finalize_recommendation_buckets(report)
        self.assertEqual(_nums(out["recommended_standards"]), ["IS 2"])
        self.assertEqual(sorted(_nums(out["test_installation_standards"])), ["IS 1 (Part 1)", "IS 3"])
        self.assertEqual(out["recommendation_summary"]["test_installation"], 2)


if __name__ == "__main__":
    unittest.main()
