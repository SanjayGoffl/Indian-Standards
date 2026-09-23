"""
HDPE Piping Applicability Regression Test Suite.
Tests all 8 mandatory acceptance cases:
1. "Supply of HDPE water pipes for water distribution." -> IS 4984 retained as potentially applicable.
2. "Procurement of electrical power cables." -> IS 694/7098 retained, IS 4984 excluded.
3. "Procurement of plain and reinforced concrete." -> IS 456 retained, IS 4984 excluded.
4. "Procurement of drinking water quality testing or drinking water specification." -> IS 10500 retained, not primary pipe standard.
5. "Procurement of autonomous robotics systems." -> Piping standards excluded.
6. "Supply of HDPE sewage pipes." -> IS 4984 retained as potentially applicable.
7. "Supply of HDPE industrial effluent pipes." -> IS 4984 retained as potentially applicable.
8. Category mismatch ("Piping" vs "Pipes & Water Management") does NOT cause exclusion.
"""

import sys
import os
import unittest
import logging

backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import SessionLocal, init_db
from app.core.models import User, IndianStandard
from app.services.standards_knowledge_base import seed_indian_standards
from app.services.recommendation_service import process_procurement_recommendation
from app.services.recommendation_validator import validate_product_category, build_dynamic_exclusion_reason

logger = logging.getLogger(__name__)


class TestHDPEPipingApplicability(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.db = SessionLocal()
        seed_indian_standards(cls.db)

        cls.user = cls.db.query(User).first()
        if not cls.user:
            cls.user = User(email="test_hdpe@example.com", hashed_password="hashed_pass", full_name="HDPE Test User")
            cls.db.add(cls.user)
            cls.db.commit()
            cls.db.refresh(cls.user)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_hdpe_water_pipes_procurement(self):
        """TEST 1: Supply of HDPE water pipes for water distribution."""
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="Supply of HDPE water pipes for water distribution and conveyance applications.",
            product_category="Piping"
        )
        rec_and_pot = report.get("recommended_standards", []) + report.get("potentially_applicable_standards", [])
        std_nums = [s["standard_number"] for s in rec_and_pot]
        ex_nums = [s["standard_number"] for s in report.get("excluded_standards", [])]

        self.assertTrue(any("4984" in n for n in std_nums), f"IS 4984 expected in recommended/potentially applicable list! Got std_nums={std_nums}")
        self.assertFalse(any("4984" in n for n in ex_nums), f"IS 4984 must NOT be in excluded standards! Got ex_nums={ex_nums}")

        # Check IS 4984 details
        is_4984_item = next(s for s in rec_and_pot if "4984" in s["standard_number"])
        self.assertEqual(is_4984_item["applicability_status"], "Potentially Applicable")
        self.assertIn("Potentially applicable because the standard addresses HDPE pipes", is_4984_item["reasoning"])
        self.assertEqual(is_4984_item["revision_verification_status"], "Unverified")

    def test_02_electrical_cables_procurement(self):
        """TEST 2: Procurement of electrical power cables."""
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="Procurement of electrical power cables 1100 V working voltage.",
            product_category="Electrical Wires & Power Cables"
        )
        rec_and_pot = report.get("recommended_standards", []) + report.get("potentially_applicable_standards", [])
        std_nums = [s["standard_number"] for s in rec_and_pot]
        self.assertTrue(any("694" in n or "7098" in n for n in std_nums))
        self.assertFalse(any("4984" in n for n in std_nums), "IS 4984 HDPE pipe standard must NOT be recommended for cable queries")

        # Verify domain compatibility rejection for cable query
        is_match, reason = validate_product_category("Pipes & Water Management", "IS 4984:2016 HDPE Pipes", "Electrical Wires & Power Cables")
        self.assertFalse(is_match)

    def test_03_concrete_procurement(self):
        """TEST 3: Procurement of plain and reinforced concrete."""
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="Procurement of plain and reinforced concrete for structural foundation.",
            product_category="Civil & Construction"
        )
        print("\n--- DEBUG TEST 03 ---")
        print("Product Category:", report.get("product_category"))
        print("Recommended:", [s["standard_number"] for s in report.get("recommended_standards", [])])
        print("Potentially Applicable:", [s["standard_number"] for s in report.get("potentially_applicable_standards", [])])
        print("Excluded:", [(s["standard_number"], s.get("exclusion_reason")) for s in report.get("excluded_standards", [])])
        rec_and_pot = report.get("recommended_standards", []) + report.get("potentially_applicable_standards", [])
        std_nums = [s["standard_number"] for s in rec_and_pot]
        self.assertTrue(any("456" in n for n in std_nums), f"IS 456 expected for concrete query! Got std_nums={std_nums}")
        self.assertFalse(any("4984" in n for n in std_nums), "IS 4984 HDPE pipe standard must NOT be recommended for concrete queries")

    def test_04_drinking_water_quality_procurement(self):
        """TEST 4: Drinking water quality testing or drinking water specification."""
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="Procurement of drinking water quality testing and water quality parameter verification.",
            product_category="Water Quality & Environment"
        )
        rec_and_pot = report.get("recommended_standards", []) + report.get("potentially_applicable_standards", [])
        std_nums = [s["standard_number"] for s in rec_and_pot]

        self.assertTrue(any("10500" in n for n in std_nums))

    def test_05_autonomous_robotics_procurement(self):
        """TEST 5: Procurement of autonomous robotics systems."""
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="Procurement of autonomous robotics systems for factory automation.",
            product_category="Automation & Robotics"
        )
        rec_and_pot = report.get("recommended_standards", []) + report.get("potentially_applicable_standards", [])
        std_nums = [s["standard_number"] for s in rec_and_pot]
        self.assertFalse(any("4984" in n for n in std_nums), "Piping standards must NOT be recommended for robotics queries")

        # Verify domain compatibility rejection for robotics query
        is_match, reason = validate_product_category("Pipes & Water Management", "IS 4984:2016 HDPE Pipes", "Automation & Robotics")
        self.assertFalse(is_match)

    def test_06_hdpe_sewage_pipes(self):
        """TEST 6: Supply of HDPE sewage pipes."""
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="Supply of HDPE sewage pipes for municipal underground drainage system.",
            product_category="HDPE Sewage Pipes"
        )
        rec_and_pot = report.get("recommended_standards", []) + report.get("potentially_applicable_standards", [])
        std_nums = [s["standard_number"] for s in rec_and_pot]
        self.assertTrue(any("4984" in n for n in std_nums))

    def test_07_hdpe_industrial_effluent_pipes(self):
        """TEST 7: Supply of HDPE industrial effluent pipes."""
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="Supply of HDPE industrial effluent pipes for chemical plant waste transport.",
            product_category="Industrial Effluent Piping"
        )
        rec_and_pot = report.get("recommended_standards", []) + report.get("potentially_applicable_standards", [])
        std_nums = [s["standard_number"] for s in rec_and_pot]
        self.assertTrue(any("4984" in n for n in std_nums))

    def test_08_exact_category_mismatch_non_exclusion(self):
        """TEST 8: Verify exact category mismatch ('Piping' vs 'Pipes & Water Management') does NOT cause exclusion."""
        is_match, reason = validate_product_category(
            candidate_category="Pipes & Water Management",
            candidate_title="High Density Polyethylene (HDPE) Pipes for Potable Water Supplies, Sewage and Industrial Effluents — Specification",
            target_category="Piping"
        )
        self.assertTrue(is_match, f"Category validation failed! Reason: {reason}")
        self.assertNotIn("not Piping", reason)

    def test_09_unsupported_qco_claims_replaced(self):
        """TEST 9: Unsupported QCO claims are replaced with official verification statement."""
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="Supply of HDPE water pipes for water distribution and conveyance applications.",
            product_category="Piping"
        )
        cert_guidance = report.get("certification_guidance", [])
        self.assertTrue(len(cert_guidance) > 0)
        expected_unsupported_text = (
            "The applicability of mandatory BIS certification, QCO requirements, "
            "tender conditions, and municipal authority requirements requires verification from current official sources."
        )
        for cert in cert_guidance:
            self.assertNotIn("Department of Chemicals and Petrochemicals", cert.get("explanation", ""))
            self.assertEqual(cert.get("explanation"), expected_unsupported_text)
            self.assertIsNone(cert.get("source_url"))

    def test_10_local_scope_summary_labelled_and_provenance(self):
        """TEST 10: Local scope summaries are labelled as unverified and provenance fields are present."""
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="Supply of HDPE water pipes for water distribution and conveyance applications.",
            product_category="Piping"
        )
        rec_and_pot = report.get("recommended_standards", []) + report.get("potentially_applicable_standards", [])
        is_4984_item = next(s for s in rec_and_pot if "4984" in s["standard_number"])
        
        self.assertEqual(
            is_4984_item.get("scope_label"),
            "Scope summary from local catalogue — official document verification required."
        )
        
        # Check all 6 provenance fields
        self.assertIn("source", is_4984_item)
        self.assertIn("source_url", is_4984_item)
        self.assertIn("source_document", is_4984_item)
        self.assertIn("page_or_clause", is_4984_item)
        self.assertIn("retrieved_at", is_4984_item)
        self.assertIn("verification_status", is_4984_item)
        
        # Source link honesty check: unverified items have source_url None
        self.assertIsNone(is_4984_item.get("source_url"))
        self.assertEqual(is_4984_item.get("verification_status"), "Verification Required")

    def test_11_officially_verified_claims_provenance(self):
        """TEST 11: Verified claims display their evidence and valid source_url."""
        from app.services.recommendation_validator import ensure_item_provenance_and_scope
        dummy_verified_item = {
            "standard_number": "IS 4984:2016",
            "title": "HDPE Pipes",
            "source": "Official BIS Gazette",
            "source_url": "https://www.services.bis.gov.in/IS4984",
            "source_document": "Gazette Notification No. 1234",
            "page_or_clause": "Clause 4.1",
            "verification_status": "Verified"
        }
        res = ensure_item_provenance_and_scope(dummy_verified_item, default_ver_status="Verified")
        self.assertEqual(res["source_url"], "https://www.services.bis.gov.in/IS4984")
        self.assertEqual(res["verification_status"], "Verified")

    def test_12_evidence_based_matrix_and_summary(self):
        """TEST 12: Evidence-based evaluation values in comparison matrix and final evidence summary."""
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="Supply of HDPE water pipes for water distribution and conveyance applications.",
            product_category="Piping"
        )
        rec_and_pot = report.get("recommended_standards", []) + report.get("potentially_applicable_standards", [])
        is_4984_item = next(s for s in rec_and_pot if "4984" in s["standard_number"])
        matrix = is_4984_item.get("field_comparison_matrix", [])
        
        # Verify evaluation values
        results = [m.get("result") or m.get("evaluation") for m in matrix]
        self.assertNotIn("Match", results, "'Match' must not be displayed when exact evidence is unverified")
        self.assertIn("Potential Match", results)
        self.assertIn("Missing Input", results)
        
        # Check missing inputs for pressure rating and pipe diameter
        press_item = next(m for m in matrix if "pressure" in m.get("parameter", "").lower())
        diam_item = next(m for m in matrix if "diameter" in m.get("parameter", "").lower())
        
        self.assertEqual(press_item.get("result"), "Missing Input")
        self.assertEqual(press_item.get("procurement_requirement"), "Not provided")
        self.assertEqual(diam_item.get("result"), "Missing Input")
        self.assertEqual(diam_item.get("procurement_requirement"), "Not provided")

        # Check final evidence summary section
        self.assertIn("evidence_summary", report)
        ev_summary = report["evidence_summary"]
        self.assertIn("claims_supported_by_metadata", ev_summary)
        self.assertIn("claims_requiring_official_document_verification", ev_summary)
        self.assertIn("missing_procurement_inputs", ev_summary)
        self.assertIn("certification_and_regulatory_items", ev_summary)


if __name__ == "__main__":
    unittest.main()
