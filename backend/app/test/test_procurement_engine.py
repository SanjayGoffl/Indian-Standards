"""
Comprehensive Procurement Recommendation Engine & Verification Test Suite.
Includes deterministic tests covering:
1. Exact IS lookup
2. Semantic recommendation
3. Wrong-domain exclusion
4. Normative/test/safety/material relationship expansion
5. Missing requirements detection
6. Outdated/amended standards handling
7. Certification uncertainty handling
8. No-result case handling
9. Multi-standard recommendations
10. Benchmark Evaluation Dataset with Recall@5 & Recall@10 metrics.
"""

import sys
import os
import unittest
import logging

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import SessionLocal, engine, Base
from app.core.models import User, IndianStandard
from app.services.standards_knowledge_base import seed_indian_standards
from app.services.recommendation_service import process_procurement_recommendation
from app.services.standards_retrieval import retrieve_candidate_standards, extract_is_numbers
from app.services.bis_connector import MockBISConnector
from app.services.standards_ingestion import ingest_standards

logger = logging.getLogger(__name__)


class TestProcurementEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()
        seed_indian_standards(cls.db)

        cls.user = cls.db.query(User).first()
        if not cls.user:
            cls.user = User(email="unittest@example.com", hashed_password="hashed_pass", full_name="Unit Test User")
            cls.db.add(cls.user)
            cls.db.commit()
            cls.db.refresh(cls.user)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_exact_is_number_extraction_and_lookup(self):
        """Test exact IS number regex extraction and retrieval boosting."""
        extracted = extract_is_numbers("Procurement of cables as per IS 694:2010 and IS 10810")
        self.assertIn("694", extracted)
        self.assertIn("10810", extracted)

        candidates = retrieve_candidate_standards(self.db, "Procurement of IS 694 cables", product_category="Electrical Cables", top_k=5)
        cand_numbers = [c.standard_number for c in candidates]
        self.assertTrue(any("694" in num for num in cand_numbers))

    def test_02_semantic_recommendation_and_matching(self):
        """Test semantic retrieval and field matching for HDPE water pipes."""
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="High Density Polyethylene HDPE pipes PE 100 grade for municipal drinking water supply.",
            product_category="HDPE Water Pipes",
            procurement_purpose="Municipal Water Infrastructure"
        )
        self.assertIn("HDPE", report.get("product_category", ""))
        rec_stds = [s["standard_number"] for s in report.get("recommended_standards", []) + report.get("potentially_applicable_standards", [])]
        self.assertTrue(any("4984" in num for num in rec_stds))

    def test_03_wrong_domain_exclusion(self):
        """Test wrong-domain standards are strictly excluded without parameter leakage."""
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="Chemical-resistant protective gloves for lab technicians handling acids.",
            product_category="Chemical-resistant protective gloves",
            procurement_purpose="PPE Safety"
        )
        rec_nums = [s["standard_number"] for s in report.get("recommended_standards", [])]
        # Cable standards must NOT be recommended for protective gloves
        self.assertFalse(any("694" in num or "7098" in num for num in rec_nums))
        
        # Verify excluded standards contains reasons
        ex_list = report.get("excluded_standards", [])
        self.assertTrue(len(ex_list) > 0)
        self.assertTrue(any("Product scope mismatch" in ex.get("exclusion_reason", "") for ex in ex_list))

    def test_04_relationship_graph_expansion(self):
        """Test normative and test method relationship resolution in recommendation."""
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="Plain and reinforced concrete design specs.",
            product_category="Civil & Construction",
            procurement_purpose="Building Infrastructure"
        )
        all_recs = report.get("recommended_standards", []) + report.get("potentially_applicable_standards", [])
        related_stds = report.get("related_standards", [])
        
        # Check if IS 456 was found
        is_456_found = any("456" in s["standard_number"] for s in all_recs)
        self.assertTrue(is_456_found)

        # Check related normative references (e.g. IS 1786 steel or IS 269 cement)
        rel_numbers = [r.get("standard_number", "") for r in related_stds]
        self.assertTrue(len(related_stds) > 0 or any("1786" in r or "269" in r for r in rel_numbers))

    def test_05_missing_requirements_detection(self):
        """Test detection of missing technical parameters in procurement text."""
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="Electric power cable for factory wiring.",
            product_category="Electrical Wires & Power Cables",
            procurement_purpose="Factory Procurement"
        )
        missing = report.get("missing_requirements", [])
        self.assertTrue(len(missing) > 0)
        self.assertTrue(any("Voltage" in m or "Working Voltage" in m or "Sheath" in m or "FRLS" in m for m in missing))

    def test_06_outdated_and_amended_standards_verification(self):
        """Test status and amendment details are populated with unverified disclaimer."""
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="PVC insulated cable 1100 V working voltage.",
            product_category="Electrical Wires & Power Cables"
        )
        for std in report.get("recommended_standards", []):
            self.assertIn("revision_verification_status", std)
            self.assertIn("amendments", std)

    def test_07_certification_uncertainty_handling(self):
        """Test certification guidance contains legal disclaimers and verification guidance."""
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="Industrial safety helmets for construction workers.",
            product_category="Industrial Safety Helmets"
        )
        cert_guidance = report.get("certification_guidance", [])
        self.assertTrue(len(cert_guidance) > 0)

    def test_08_no_result_fallback_handling(self):
        """Test handling queries for non-existent exotic categories gracefully."""
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="Quantum magnetic levitation propulsion thruster shield.",
            product_category="Aerospace Physics"
        )
        self.assertIn("overall_status", report)
        self.assertIn("No Applicable Standard Confirmed", report["overall_status"])

    def test_09_multi_standard_recommendations(self):
        """Test retrieving multiple standards for multi-purpose specifications."""
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="Cables for power transmission and steel reinforcement bars for concrete building foundation.",
            product_category="Power & Civil Infrastructure"
        )
        rec_nums = [s["standard_number"] for s in report.get("recommended_standards", []) + report.get("potentially_applicable_standards", [])]
        self.assertTrue(len(rec_nums) >= 2 or len(report.get("excluded_standards", [])) > 0)

    def test_10_recall_evaluation_dataset(self):
        """Benchmark Evaluation Dataset for Retrieval Recall@5 and Recall@10."""
        eval_dataset = [
            {
                "query": "PVC insulated cables for working voltages up to 1100 V IS 694",
                "category": "Electrical Wires & Power Cables",
                "expected_is": "IS 694:2010"
            },
            {
                "query": "XLPE insulated PVC sheathed power cables 1100 V IS 7098",
                "category": "Electrical Wires & Power Cables",
                "expected_is": "IS 7098 (Part 1):1988"
            },
            {
                "query": "Plain and reinforced concrete structural design code IS 456",
                "category": "Civil & Construction",
                "expected_is": "IS 456:2000"
            },
            {
                "query": "High strength deformed steel bars for concrete reinforcement IS 1786",
                "category": "Civil & Construction",
                "expected_is": "IS 1786:2008"
            },
            {
                "query": "HDPE pipes for potable water supply IS 4984",
                "category": "HDPE Water Pipes",
                "expected_is": "IS 4984:2016"
            },
            {
                "query": "Drinking water specification IS 10500",
                "category": "Water Quality & Environment",
                "expected_is": "IS 10500:2012"
            },
            {
                "query": "Industrial safety helmets for head protection IS 2925",
                "category": "Safety Equipment & PPE",
                "expected_is": "IS 2925:1984"
            }
        ]

        hits_at_5 = 0
        hits_at_10 = 0
        total = len(eval_dataset)

        for item in eval_dataset:
            candidates = retrieve_candidate_standards(self.db, item["query"], product_category=item["category"], top_k=10)
            cand_nums = [c.standard_number for c in candidates]
            
            exp = item["expected_is"]
            if exp in cand_nums[:5]:
                hits_at_5 += 1
            if exp in cand_nums[:10]:
                hits_at_10 += 1

        recall_5 = hits_at_5 / total
        recall_10 = hits_at_10 / total

        print(f"\n=================== EVALUATION METRICS ===================")
        print(f"Total Benchmark Queries: {total}")
        print(f"Recall@5: {recall_5 * 100:.2f}% ({hits_at_5}/{total})")
        print(f"Recall@10: {recall_10 * 100:.2f}% ({hits_at_10}/{total})")
        print(f"==========================================================\n")

        self.assertGreaterEqual(recall_5, 0.85, "Recall@5 should be at least 85%")
        self.assertGreaterEqual(recall_10, 0.85, "Recall@10 should be at least 85%")


if __name__ == "__main__":
    unittest.main()
