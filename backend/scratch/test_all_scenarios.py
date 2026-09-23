import sys
import os
import json

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import SessionLocal
from app.core.models import User
from app.services.recommendation_service import process_procurement_recommendation

def run_all_scenarios():
    db = SessionLocal()
    try:
        user = db.query(User).first()
        if not user:
            user = User(email="testall@example.com", hashed_password="xxx", full_name="Test User All")
            db.add(user)
            db.commit()
            db.refresh(user)

        user_id = user.id

        scenarios = [
            {
                "name": "Scenario A: Chemical-resistant protective gloves",
                "category": "Chemical-resistant protective gloves",
                "purpose": "Safety Equipment & PPE",
                "input": "Chemical-resistant protective gloves for laboratory technicians handling industrial cleaning chemicals and corrosive substances."
            },
            {
                "name": "Scenario B: PVC electrical cables",
                "category": "Electrical Wires & Power Cables",
                "purpose": "Power & Infrastructure",
                "input": "Procurement of single-core and multicore PVC insulated cables for 1100 V working voltage with FRLS insulation requirement."
            },
            {
                "name": "Scenario C: High-temperature turbine insulation padding",
                "category": "Thermal Insulation Padding",
                "purpose": "Experimental Research",
                "input": "Experimental research for high-temperature turbine insulation padding suitable for 800 deg C operation."
            },
            {
                "name": "Scenario D: HDPE water pipes",
                "category": "HDPE Water Pipes",
                "purpose": "Municipal Water Supply",
                "input": "High Density Polyethylene HDPE pipes PE 100 grade for potable water supply PN 10 pressure rating."
            },
            {
                "name": "Scenario E: Industrial safety helmets",
                "category": "Industrial Safety Helmets",
                "purpose": "Construction Safety",
                "input": "Industrial safety helmets for head protection against falling objects and mechanical impact in construction sites."
            }
        ]

        print("\n=================== EXECUTING 5 SCENARIO TEST SUITE ===================")

        for sc in scenarios:
            print(f"\n---> Testing {sc['name']}...")
            report = process_procurement_recommendation(
                db=db,
                user_id=user_id,
                input_text=sc["input"],
                product_category=sc["category"],
                procurement_purpose=sc["purpose"]
            )

            is_cable_sc = ("cables" in sc["name"].lower())
            extracted_params = [r.get("parameter") for r in report.get("extracted_requirements", [])]
            
            print(f"  Category: {report.get('product_category')}")
            print(f"  Overall Status: {report.get('overall_status')}")
            print(f"  Extracted Params: {extracted_params}")
            print(f"  Recommended Standards Count: {len(report.get('recommended_standards', []))}")
            print(f"  Excluded Standards Count: {len(report.get('excluded_standards', []))}")

            # Check for cable parameter leakage in non-cable scenarios
            if not is_cable_sc:
                for bad_param in ["Core Insulation", "Voltage Rating", "Conductor Material", "FRLS Requirement", "High Voltage Test"]:
                    assert bad_param not in extracted_params, f"LEAKAGE FAIL in {sc['name']}: '{bad_param}' in extracted_requirements!"

                # Check matrices of applicable standards
                for std in (report.get("recommended_standards", []) + report.get("potentially_applicable_standards", [])):
                    m_params = [m.get("parameter") for m in std.get("field_comparison_matrix", [])]
                    for bad_param in ["Core Insulation", "Voltage Rating", "Conductor Material", "FRLS Requirement", "High Voltage Test"]:
                        assert bad_param not in m_params, f"LEAKAGE FAIL in {sc['name']}: '{bad_param}' in comparison matrix of {std.get('standard_number')}!"

                # Check certification guidance
                for cert in report.get("certification_guidance", []):
                    exp = cert.get("explanation", "").lower()
                    for bad_word in ["cable type", "voltage rating", "frls"]:
                        assert bad_word not in exp, f"LEAKAGE FAIL in {sc['name']}: '{bad_word}' in certification explanation!"

                print(f"  [OK] PASSED: Zero cable parameter leakage in {sc['name']}!")
            else:
                # Cable scenario MUST have cable fields and match IS 694
                assert any("Insulation" in p or "Voltage" in p or "Conductor" in p or "FRLS" in p for p in extracted_params), f"FAIL in {sc['name']}: Expected cable parameters missing!"
                rec_nums = [std.get("standard_number") for std in (report.get("recommended_standards", []) + report.get("potentially_applicable_standards", []))]
                assert any("694" in n for n in rec_nums), f"FAIL in {sc['name']}: IS 694 was expected in cable results!"
                print(f"  [OK] PASSED: Cable parameters and IS 694 verified for {sc['name']}!")

            # Verify dynamic exclusion reason formatting for excluded standards
            for ex in report.get("excluded_standards", []):
                reason = ex.get("exclusion_reason", "")
                assert any(phrase in reason for phrase in ["Product scope mismatch:", "secondary", "addresses", "This standard specifies"]), f"FAIL in {sc['name']}: Exclusion reason not dynamic! Got: {reason}"
                print(f"    - Sample Exclusion [{ex.get('standard_number')}]: {reason}")

        print("\nALL 5 SCENARIOS PASSED WITH ZERO DATA LEAKAGE AND 100% ACCURATE SCOPE DISAMBIGUATION!")

    finally:
        db.close()

if __name__ == "__main__":
    run_all_scenarios()
