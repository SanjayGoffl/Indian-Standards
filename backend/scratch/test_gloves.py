import sys
import os
import json

# Add backend directory to sys.path
sys.path.insert(0, r"c:\Users\HP\Downloads\sih rag\ai-knowledge-retrieval-system-main\backend")

from app.core.database import SessionLocal
from app.core.models import User
from app.services.recommendation_service import process_procurement_recommendation

def test_gloves():
    db = SessionLocal()
    try:
        user = db.query(User).first()
        if not user:
            user = User(email="testgloves@example.com", hashed_password="xxx", full_name="Test User")
            db.add(user)
            db.commit()
            db.refresh(user)

        user_id = user.id
        product_category = "Industrial Safety Gloves"
        procurement_purpose = "Safety Equipment & PPE"
        input_text = "Chemical-resistant reusable gloves for laboratory technicians handling cleaning chemicals and corrosive substances."

        report = process_procurement_recommendation(
            db=db,
            user_id=user_id,
            input_text=input_text,
            product_category=product_category,
            procurement_purpose=procurement_purpose
        )

        print("\n=================== GLOVES REPORT VALIDATION RESULTS ===================")
        print(f"Product Category: {report.get('product_category')}")
        print(f"Overall Status: {report.get('overall_status')}")
        print(f"Notice: {report.get('notice')}")

        print("\nExtracted Requirements:")
        print(json.dumps(report.get("extracted_requirements", []), indent=2))

        print("\nMissing Requirements:")
        print(json.dumps(report.get("missing_requirements", []), indent=2))

        print(f"\nRecommended Standards Count: {len(report.get('recommended_standards', []))}")
        print(f"Potentially Applicable Standards Count: {len(report.get('potentially_applicable_standards', []))}")

        print(f"\nExcluded Standards Count: {len(report.get('excluded_standards', []))}")
        for ex in report.get("excluded_standards", []):
            print(f"  - [{ex.get('standard_number')}] {ex.get('title')}: {ex.get('exclusion_reason')}")

        print("\nCertification Guidance:")
        print(json.dumps(report.get("certification_guidance", []), indent=2))

        # Check extracted requirements for cable parameter names
        extracted_param_names = [req.get("parameter") for req in report.get("extracted_requirements", [])]
        for bad_p in ["Core Insulation", "PVC", "Voltage Rating", "Conductor Material", "FRLS Requirement", "High Voltage Test"]:
            assert bad_p not in extracted_param_names, f"LEAKAGE ERROR: '{bad_p}' found in extracted_requirements!"

        print("\n[OK] SUCCESS: Zero electrical cable parameters in extracted_requirements!")

        # Check recommended and potentially applicable standards for comparison matrix fields
        applicable_list = report.get("recommended_standards", []) + report.get("potentially_applicable_standards", [])
        for item in applicable_list:
            matrix_params = [m.get("parameter") for m in item.get("field_comparison_matrix", [])]
            for bad_p in ["Core Insulation", "Voltage Rating", "Conductor Material", "FRLS Requirement", "High Voltage Test"]:
                assert bad_p not in matrix_params, f"LEAKAGE ERROR: '{bad_p}' found in field comparison matrix of {item.get('standard_number')}!"

        print("[OK] SUCCESS: Zero electrical cable parameters in comparison matrices!")

        # Check certification text for cable terms
        for cert in report.get("certification_guidance", []):
            exp = cert.get("explanation", "").lower()
            for bad_term in ["cable type", "voltage rating", "frls", "conductor material"]:
                assert bad_term not in exp, f"LEAKAGE ERROR: Cable term '{bad_term}' found in certification explanation!"

        print("[OK] SUCCESS: Zero electrical cable terms in certification guidance!")

        # E: Respiratory protective devices excluded
        excluded_std_nums = [ex.get("standard_number") for ex in report.get("excluded_standards", [])]
        assert any("10245" in s for s in excluded_std_nums), "ERROR: Respiratory standard IS 10245 was not excluded!"

        print("[OK] SUCCESS: Respiratory protective devices correctly moved to Excluded Standards with category mismatch reason!")

        print("\nALL ACCEPTANCE CRITERIA PASSED SUCCESSFULLY FOR INDUSTRIAL SAFETY GLOVES!")

    finally:
        db.close()

if __name__ == "__main__":
    test_gloves()
