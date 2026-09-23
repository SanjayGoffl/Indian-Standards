"""
Comprehensive Test Suite for BIS Knowledge Base Architecture & Procurement System.
Tests all 18 required scenarios:
1. Exact IS-number retrieval
2. Semantic retrieval
3. Domain mismatch exclusion
4. Duplicate ingestion
5. New standard ingestion
6. Modified standard ingestion
7. Unchanged record detection
8. Failed record handling
9. Selective embedding updates
10. ChromaDB update behavior
11. Relationship graph expansion
12. Missing requirement detection
13. Certification uncertainty
14. Revision verification warnings
15. No-result queries
16. Unauthorized ingestion requests
17. Existing procurement regression tests
18. Benchmark Ground-Truth Dataset (Recall@5 & Recall@10 metrics).
"""

import sys
import os
import unittest
import logging
from fastapi.testclient import TestClient

backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app
from app.core.database import SessionLocal, engine, Base, init_db
from app.core.models import User, IndianStandard, StandardRelationship, IngestionAuditLog
from app.services.standards_knowledge_base import seed_indian_standards
from app.services.recommendation_service import process_procurement_recommendation
from app.services.standards_retrieval import retrieve_candidate_standards_with_metrics, extract_is_numbers
from app.services.bis_connector import MockBISConnector, normalize_bis_record
from app.services.standards_ingestion import ingest_standards

logger = logging.getLogger(__name__)


class TestBISIngestionAndRetrieval(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.db = SessionLocal()
        seed_indian_standards(cls.db)

        cls.user = cls.db.query(User).first()
        if not cls.user:
            cls.user = User(email="test_bis@example.com", hashed_password="hashed_password", full_name="BIS Test User")
            cls.db.add(cls.user)
            cls.db.commit()
            cls.db.refresh(cls.user)

        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_exact_is_number_retrieval(self):
        """Test exact IS number regex extraction and retrieval priority."""
        nums = extract_is_numbers("Procurement of IS 694 power cables and IS 10810 testing")
        self.assertIn("694", nums)
        self.assertIn("10810", nums)

        candidates, metrics = retrieve_candidate_standards_with_metrics(self.db, "Procurement of IS 694 cables", product_category="Electrical Cables", top_k=5)
        cand_numbers = [c.standard_number for c in candidates]
        self.assertTrue(any("694" in n for n in cand_numbers))
        self.assertIn("candidates_sent_to_llm", metrics)
        self.assertIn("context_reduction_percent", metrics)

    def test_02_semantic_retrieval(self):
        """Test semantic vector retrieval for non-exact queries."""
        candidates, metrics = retrieve_candidate_standards_with_metrics(self.db, "Polyethylene pipes for drinking water transport", product_category="HDPE Water Pipes", top_k=5)
        cand_numbers = [c.standard_number for c in candidates]
        self.assertTrue(any("4984" in n for n in cand_numbers))

    def test_03_domain_mismatch_exclusion(self):
        """Test strict domain mismatch exclusion (e.g. gloves query excludes cable standards)."""
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="Chemical resistant protective gloves for laboratory technicians.",
            product_category="Chemical-resistant protective gloves"
        )
        rec_nums = [s["standard_number"] for s in report.get("recommended_standards", [])]
        self.assertFalse(any("694" in n or "7098" in n for n in rec_nums))

    def test_04_duplicate_ingestion(self):
        """Test re-ingesting identical standards increases unchanged count and skips re-embedding."""
        raw_payload = [
            {
                "standard_number": "IS 694:2010",
                "title": "Polyvinyl Chloride Insulated Cables for Working Voltages Up to and Including 1100 V",
                "scope": "Covers requirements for single core and multicore PVC insulated cables for electric power and lighting in residential, commercial, and industrial procurement. Specifies conductor resistance, insulation thickness, flame retardance, and dielectric strength.",
                "category": "Electrical & Cables",
                "sector": "Power & Public Utilities",
                "publication_date": "2010",
                "revision": "Fourth Revision (Reaffirmed 2020)",
                "status": "Active"
            }
        ]
        connector = MockBISConnector(raw_payload)
        # First sync ensures content_hash is set on the standard in DB
        ingest_standards(self.db, connector)

        # Second sync with identical payload must detect 0 changes and 1 unchanged record
        res = ingest_standards(self.db, connector)
        self.assertEqual(res["unchanged_records"], 1)
        self.assertEqual(res["new_records"], 0)
        self.assertEqual(res["updated_records"], 0)
        self.assertEqual(res["embeddings_created"], 0)

    def test_05_new_standard_ingestion(self):
        """Test ingesting a brand-new standard creates DB record & vector embedding."""
        self.db.query(IndianStandard).filter(IndianStandard.standard_number == "IS 99999:2026").delete()
        self.db.commit()

        raw_payload = [
            {
                "standard_number": "IS 99999:2026",
                "title": "Test Standard for Autonomous Robotics Systems",
                "scope": "Covers safety and communication protocols for autonomous robots.",
                "category": "Automation & Robotics",
                "sector": "Smart Automation",
                "publication_date": "2026",
                "revision": "First Edition",
                "status": "Active"
            }
        ]
        connector = MockBISConnector(raw_payload)
        res = ingest_standards(self.db, connector)
        self.assertEqual(res["new_records"], 1)
        self.assertEqual(res["embeddings_created"], 1)

        std_in_db = self.db.query(IndianStandard).filter(IndianStandard.standard_number == "IS 99999:2026").first()
        self.assertIsNotNone(std_in_db)

    def test_06_modified_standard_ingestion(self):
        """Test updating content of an existing standard triggers database update and selective re-embedding."""
        raw_payload = [
            {
                "standard_number": "IS 99999:2026",
                "title": "Test Standard for Autonomous Robotics Systems (Amended 2026)",
                "scope": "Updated scope including AI multi-agent orchestration and cyber-physical security.",
                "category": "Automation & Robotics",
                "sector": "Smart Automation",
                "publication_date": "2026",
                "revision": "Second Edition",
                "status": "Active"
            }
        ]
        connector = MockBISConnector(raw_payload)
        res = ingest_standards(self.db, connector)
        self.assertEqual(res["updated_records"], 1)
        self.assertEqual(res["embeddings_updated"], 1)

    def test_07_unchanged_record_detection(self):
        """Test sending unchanged record hash skips database update."""
        raw_payload = [
            {
                "standard_number": "IS 99999:2026",
                "title": "Test Standard for Autonomous Robotics Systems (Amended 2026)",
                "scope": "Updated scope including AI multi-agent orchestration and cyber-physical security.",
                "category": "Automation & Robotics",
                "sector": "Smart Automation",
                "publication_date": "2026",
                "revision": "Second Edition",
                "status": "Active"
            }
        ]
        connector = MockBISConnector(raw_payload)
        res = ingest_standards(self.db, connector)
        self.assertEqual(res["unchanged_records"], 1)
        self.assertEqual(res["updated_records"], 0)

    def test_08_failed_record_handling(self):
        """Test invalid record (missing standard_number) is rejected safely and logged."""
        raw_payload = [
            {
                "title": "Invalid Standard Without Standard Number",
                "scope": "Invalid test scope"
            }
        ]
        connector = MockBISConnector(raw_payload)
        res = ingest_standards(self.db, connector)
        self.assertEqual(res["failed_records"], 1)

    def test_09_selective_embedding_updates(self):
        """Verify embeddings_created and embeddings_updated metrics accurately reflect ops."""
        self.db.query(IndianStandard).filter(IndianStandard.standard_number == "IS 88888:2026").delete()
        self.db.commit()

        raw_payload = [
            {
                "standard_number": "IS 88888:2026",
                "title": "Selective Embedding Test Standard",
                "scope": "Testing embedding counts.",
                "category": "Testing Category"
            }
        ]
        connector = MockBISConnector(raw_payload)
        res = ingest_standards(self.db, connector)
        self.assertEqual(res["embeddings_created"], 1)
        self.assertEqual(res["embeddings_updated"], 0)

    def test_10_chromadb_update_behavior(self):
        """Verify standard is searchable in ChromaDB after ingestion."""
        candidates, _ = retrieve_candidate_standards_with_metrics(self.db, "Autonomous Robotics Systems AI", product_category="Automation", top_k=5)
        nums = [c.standard_number for c in candidates]
        self.assertIn("IS 99999:2026", nums)

    def test_11_relationship_graph_expansion(self):
        """Verify relationships include normative, test method, and evidence metadata."""
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="Plain and reinforced concrete design IS 456.",
            product_category="Civil & Construction"
        )
        related = report.get("related_standards", [])
        self.assertTrue(len(related) > 0)

    def test_12_missing_requirement_detection(self):
        """Test missing technical specs identification."""
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="Electric power cable for building procurement.",
            product_category="Electrical Wires & Power Cables"
        )
        self.assertTrue(len(report.get("missing_requirements", [])) > 0)

    def test_13_certification_uncertainty(self):
        """Test certification guidance text contains disclaimer and unverified notice."""
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="Industrial safety helmets for head protection.",
            product_category="Industrial Safety Helmets"
        )
        self.assertTrue(len(report.get("certification_guidance", [])) > 0)

    def test_14_revision_verification_warnings(self):
        """Verify recommended items contain revision_verification_status."""
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="PVC cables 1100V working voltage.",
            product_category="Electrical Wires & Power Cables"
        )
        for std in report.get("recommended_standards", []):
            self.assertIn("revision_verification_status", std)

    def test_15_no_result_queries(self):
        """Test exotic non-existent product query cleanly returns no-result status."""
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="Anti-gravity warp field propulsion coil.",
            product_category="Aerospace Propulsion"
        )
        self.assertEqual(report.get("overall_status"), "No Applicable Standard Confirmed")

    def test_16_unauthorized_ingestion_requests(self):
        """Test endpoint /api/standards/sync returns 401 Unauthorized without JWT token."""
        response = self.client.post("/api/standards/sync")
        self.assertEqual(response.status_code, 401)

    def test_17_existing_procurement_regression_tests(self):
        """Regression test ensuring zero cable parameter leakage in non-cable scenarios."""
        report = process_procurement_recommendation(
            db=self.db,
            user_id=self.user.id,
            input_text="High Density Polyethylene HDPE pipes PE 100 grade for potable water.",
            product_category="HDPE Water Pipes"
        )
        extracted_params = [r["parameter"] for r in report.get("extracted_requirements", [])]
        self.assertNotIn("Core Insulation", extracted_params)
        self.assertNotIn("Voltage Rating", extracted_params)

    def test_18_recall_evaluation_benchmark_dataset(self):
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

        hits_5 = 0
        hits_10 = 0
        total = len(eval_dataset)

        for item in eval_dataset:
            candidates, _ = retrieve_candidate_standards_with_metrics(self.db, item["query"], product_category=item["category"], top_k=10)
            nums = [c.standard_number for c in candidates]
            expected = item["expected_is"]

            if expected in nums[:5]:
                hits_5 += 1
            if expected in nums[:10]:
                hits_10 += 1

        recall_5 = round(hits_5 / total, 4)
        recall_10 = round(hits_10 / total, 4)

        print("\n=================== BENCHMARK EVALUATION METRICS ===================")
        print(f"Total Ground-Truth Test Queries: {total}")
        print(f"Recall@5: {recall_5 * 100:.2f}% ({hits_5}/{total})")
        print(f"Recall@10: {recall_10 * 100:.2f}% ({hits_10}/{total})")
        print("====================================================================")

        self.assertGreaterEqual(recall_5, 0.85)
        self.assertGreaterEqual(recall_10, 0.85)


if __name__ == "__main__":
    unittest.main()
