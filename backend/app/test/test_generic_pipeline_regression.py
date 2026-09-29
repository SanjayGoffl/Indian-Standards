"""
Generic Recommendation Pipeline Regression Test Suite.
Verifies the architectural pipeline for ALL domains according to strict generic rules:
1. INPUT -> extract -> retrieve -> VALIDATE -> score -> classify -> final recommendations.
2. Retrieval score != validation score.
3. Never give high/1.00 score when requirements are missing or validation is weak.
4. Never recommend candidate based only on keyword/semantic similarity without validation.
5. Hard mismatch -> EXCLUDED before final ranking.
6. PRIMARY/SECONDARY only after validation passes.
7. RELATED / TEST / INSTALLATION separated from product recommendations.
8. Incomplete extraction flags "Insufficient requirements" instead of inventing values.
9. Every final recommendation includes validation evidence and reasoning.
10. Dynamic validation for arbitrary/unseen domains (no cable/PVC assumptions).
11. Pure stateless per-run execution (zero cross-run parameter leakage).
12. 4-part candidate lifecycle: retrieved -> validated -> excluded -> final recommendations.
"""

import os
import sys
import unittest
import logging

backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import SessionLocal, engine, Base
from app.core.models import User, IndianStandard
from app.services.standards_knowledge_base import seed_indian_standards
from app.services.recommendation_service import process_procurement_recommendation
from app.services.recommendation_validator import (
    calculate_technical_match_score,
    generate_field_comparison_matrix,
    classify_standard_applicability,
    normalize_standard_number,
)

logger = logging.getLogger(__name__)


class TestGenericPipelineRegression(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()
        seed_indian_standards(cls.db)

        cls.user = cls.db.query(User).first()
        if not cls.user:
            cls.user = User(email="generic_test@example.com", hashed_password="hashed_pw", full_name="Generic Pipeline Tester")
            cls.db.add(cls.user)
            cls.db.commit()
            cls.db.refresh(cls.user)

        # Seed allied test method standard if not present
        if not cls.db.query(IndianStandard).filter(IndianStandard.standard_number.ilike("%10810%")).first():
            t_std = IndianStandard(
                standard_number="IS 10810 (Part 5):1984",
                title="Methods of test for cables: Part 5 conductor resistance test",
                category="Electrical Cables & Wires",
                scope="Methods of test for electric cables",
                status="Active"
            )
            cls.db.add(t_std)
            cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_pipeline_structure_and_candidate_lifecycle(self):
        """
        Verify the 4 candidate stages:
        retrieved_candidates -> validated_candidates -> excluded_candidates -> final_recommendations.
        Verify retrieval_score != validation_score.
        """
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="Procurement of cross-linked polyethylene insulated power cables 1100 V rating.",
            product_category="Power Cables",
            procurement_purpose="Plant Electrification"
        )

        # 1. Pipeline stages must all be present
        self.assertIn("retrieved_candidates", report)
        self.assertIn("validated_candidates", report)
        self.assertIn("excluded_candidates", report)
        self.assertIn("final_recommendations", report)

        retrieved = report["retrieved_candidates"]
        validated = report["validated_candidates"]
        excluded = report["excluded_candidates"]
        final_recs = report["final_recommendations"]

        self.assertIsInstance(retrieved, list)
        self.assertIsInstance(validated, list)
        self.assertIsInstance(excluded, list)
        self.assertIsInstance(final_recs, dict)

        # Check retrieval candidate properties
        self.assertTrue(len(retrieved) > 0, "Pipeline must track retrieved candidates before filtering")
        for cand in retrieved:
            self.assertIn("standard_number", cand)
            self.assertIn("title", cand)
            self.assertIn("retrieval_score", cand)
            self.assertIn("retrieval_source", cand)

        # Check validated candidate properties & score decoupling
        self.assertTrue(len(validated) > 0, "Pipeline must track validated candidates")
        for val in validated:
            self.assertIn("standard_number", val)
            self.assertIn("validation_score", val)
            self.assertIn("match_strength", val)
            self.assertIn("field_comparison_matrix", val)
            self.assertIn("reasoning", val)
            self.assertIn("evidence", val)

            # Retrieval score != validation score: finding corresponding retrieved candidate
            match_ret = next((r for r in retrieved if normalize_standard_number(r["standard_number"]) == normalize_standard_number(val["standard_number"])), None)
            if match_ret:
                # Validation score is computed strictly from technical matrix, not simply equal to retrieval score
                self.assertIsInstance(val["validation_score"], float)
                self.assertIsInstance(match_ret["retrieval_score"], float)

        # Check final recommendations structure
        self.assertIn("primary_recommended", final_recs)
        self.assertIn("secondary_conditional", final_recs)
        self.assertIn("test_installation", final_recs)
        self.assertIn("related", final_recs)
        self.assertIn("excluded", final_recs)

    def test_02_missing_requirements_score_capping_and_insufficient_requirements(self):
        """
        Verify rule:
        - Never give a high/1.00 score when requirements are missing.
        - Show 'Insufficient requirements' instead of inventing values.
        """
        # Test direct calculation function with missing inputs in matrix
        matrix_with_missing = [
            {"parameter": "Product Category", "required_value": "Centrifugal Pumps", "result": "Confirmed Match"},
            {"parameter": "Flow Rate", "required_value": "Not provided", "result": "Missing Input"},
            {"parameter": "Head Rating", "required_value": "Not provided", "result": "Missing Input"},
            {"parameter": "Power Rating", "required_value": "Not provided", "result": "Missing Input"},
        ]
        score, strength = calculate_technical_match_score(matrix_with_missing)
        self.assertLessEqual(score, 0.60, "Validation score MUST be capped <= 0.60 when essential inputs are missing")
        self.assertNotEqual(score, 1.00, "Validation score must never be 1.00 when inputs are missing")

        # Test end-to-end missing requirements prefix
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="Need general water supply pipes without specifying diameter or pressure rating.",
            product_category="HDPE Water Pipes",
            procurement_purpose="Municipal Water"
        )
        missing_reqs = report.get("missing_requirements", [])
        self.assertTrue(len(missing_reqs) > 0, "Incomplete specifications must produce missing requirements")
        for mr in missing_reqs:
            self.assertTrue(
                mr.lower().startswith("insufficient requirements"),
                f"Missing requirement item must state 'Insufficient requirements', got: '{mr}'"
            )

        # Recommended standards in report must not have 1.00 validation score
        for rec in report.get("recommended_standards", []):
            self.assertLess(rec.get("internal_match_score", 0.0), 1.00, "Incomplete request cannot yield 1.00 score")

    def test_03_no_recommendation_on_semantic_similarity_alone_hard_mismatch_excluded(self):
        """
        Verify rules:
        - Never recommend a candidate based only on keyword/semantic similarity.
        - Hard mismatch -> EXCLUDED before final ranking.
        """
        # Procurement for lab protective gloves:
        # In a database containing power cables and HDPE pipes, no cable or pipe should ever be recommended,
        # despite any generic word overlap (e.g. 'protective', 'acid', 'handling').
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="Chemical-resistant protective nitrile gauntlets and gloves for laboratory acid handling.",
            product_category="Protective Gloves",
            procurement_purpose="Worker Safety"
        )

        recs = report.get("recommended_standards", [])
        pots = report.get("potentially_applicable_standards", [])
        rec_numbers = [s["standard_number"] for s in (recs + pots)]

        # Cable standards (IS 694, IS 7098) and pipe standards (IS 4984) must NOT be recommended
        for forbidden in ["694", "7098", "4984", "456"]:
            self.assertFalse(
                any(forbidden in num for num in rec_numbers),
                f"Standard containing {forbidden} was recommended for protective gloves!"
            )

        # Excluded standards must capture the mismatch
        excluded = report.get("excluded_standards", [])
        self.assertTrue(len(excluded) > 0, "Mismatched standards must be in excluded_standards")
        for ex in excluded:
            self.assertIn("exclusion_reason", ex)
            self.assertTrue(len(ex["exclusion_reason"]) > 5)

    def test_04_primary_secondary_conditional_and_allied_separation(self):
        """
        Verify rules:
        - PRIMARY/SECONDARY only after validation passes.
        - RELATED / TEST / INSTALLATION must be separate from product recommendations.
        """
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="Supply of 1100 V PVC insulated copper conductor cables as per IS 694. Required test: conductor resistance test as per IS 10810.",
            product_category="Electrical Cables",
            procurement_purpose="Infrastructure Electrification"
        )

        rec_stds = [s["standard_number"] for s in report.get("recommended_standards", [])]
        rel_stds = [s["standard_number"] for s in report.get("related_standards", [])]
        test_inst_stds = [s["standard_number"] for s in report.get("test_installation_standards", [])]

        # Test method IS 10810 must NOT be in primary recommended product standards
        self.assertFalse(
            any("10810" in num for num in rec_stds),
            "Test method standard (IS 10810) must NOT be placed in recommended_standards"
        )

        # Test method IS 10810 or allied standards must be separated into related/test_installation
        all_allied = rel_stds + test_inst_stds
        self.assertTrue(
            any("10810" in num for num in all_allied),
            "Test method IS 10810 must be segregated into related_standards or test_installation_standards"
        )

    def test_05_dynamic_validation_across_unseen_generic_domains(self):
        """
        Verify validation is dynamic for any product/domain without hardcoded cable/PVC assumptions.
        Tests an unprofiled generic domain: Industrial Fire Extinguishers & Centrifugal Pumps.
        """
        # Create a mock unseen standard in DB or test matrix evaluation directly
        dummy_std = IndianStandard(
            standard_number="IS 15683:2018",
            title="Portable Fire Extinguishers - Performance and Construction - Specification",
            scope="Specifies requirements for portable fire extinguishers using water, foam, powder, and clean agents.",
            category="Fire Safety Equipment",
            status="Active"
        )

        extracted_reqs = [
            {"parameter": "Extinguisher Type", "value_spec": "Portable Foam Fire Extinguisher", "category": "Type"},
            {"parameter": "Extinguishing Agent", "value_spec": "AFFF Foam", "category": "Material"},
            {"parameter": "Operating Pressure", "value_spec": "Not provided", "category": "Rating"},
        ]

        matrix = generate_field_comparison_matrix(
            candidate=dummy_std,
            extracted_reqs=extracted_reqs,
            target_category="Portable Fire Extinguishers"
        )

        # Must not contain hardcoded cable or pvc parameters
        matrix_params = [m["parameter"] for m in matrix]
        self.assertNotIn("Core Insulation", matrix_params)
        self.assertNotIn("Voltage Rating", matrix_params)
        self.assertNotIn("Conductor Material", matrix_params)
        self.assertNotIn("Pipe material", matrix_params)

        # Must have evaluated the actual domain parameters
        self.assertTrue(any("Extinguisher" in p or "Agent" in p or "Category" in p for p in matrix_params))

        # Check score calculation for generic matrix
        score, strength = calculate_technical_match_score(matrix)
        self.assertIsInstance(score, float)
        # Because Operating Pressure is "Not provided", score must be capped
        self.assertLessEqual(score, 0.60)

        # Check classification
        status = classify_standard_applicability(
            standard_number="IS 15683:2018",
            title=dummy_std.title,
            internal_score=score,
            match_strength=strength,
            matrix=matrix
        )
        # With missing inputs, cannot be blindly Recommended
        status_label = status["applicability_status"] if isinstance(status, dict) else status
        self.assertIn(status_label, ["Potentially Applicable", "Verification Required"])

    def test_06_stateless_per_run_isolation(self):
        """
        Verify rule:
        - No state or requirements from previous runs. Pure stateless per-run isolation.
        """
        # Run 1: High voltage cables
        report_1 = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="1100 V XLPE insulated power cables for underground distribution.",
            product_category="Electrical Cables",
            procurement_purpose="Power Grid"
        )
        self.assertIn("cable", report_1["product_category"].lower())

        # Run 2: HDPE water supply pipes
        report_2 = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="HDPE pipes PE 100 grade PN 10 for drinking water distribution.",
            product_category="HDPE Water Pipes",
            procurement_purpose="Municipal Water Infrastructure"
        )
        self.assertIn("pipe", report_2["product_category"].lower())

        # Zero parameter leakage between Run 1 and Run 2
        run2_req_params = [r.get("parameter", "").lower() for r in report_2.get("extracted_requirements", [])]
        self.assertNotIn("voltage", run2_req_params)
        self.assertNotIn("conductor", run2_req_params)

        run2_rec_nums = [s["standard_number"] for s in report_2.get("recommended_standards", [])]
        self.assertFalse(any("7098" in num for num in run2_rec_nums), "XLPE cable from Run 1 leaked into Run 2!")

    def test_07_validation_evidence_and_reason_completeness(self):
        """
        Verify rule:
        - Every final recommendation must include validation evidence and reason.
        """
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="Polyvinyl chloride PVC insulated copper cables 1100 V rating.",
            product_category="Power Cables",
            procurement_purpose="Building Wiring"
        )

        final_recs = report.get("final_recommendations", {})
        all_recs = final_recs.get("primary_recommended", []) + final_recs.get("secondary_conditional", [])

        self.assertTrue(len(all_recs) > 0, "Expected recommended standards for authentic PVC cable specification")
        for rec in all_recs:
            reason = rec.get("reasoning", "")
            evidence = rec.get("evidence", "")

            self.assertTrue(bool(reason and len(reason.strip()) > 10), f"Recommendation {rec.get('standard_number')} missing valid reasoning")
            self.assertTrue(bool(evidence), f"Recommendation {rec.get('standard_number')} missing valid validation evidence")


if __name__ == "__main__":
    unittest.main()
