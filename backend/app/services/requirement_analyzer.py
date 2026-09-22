"""
Requirement Analyzer Module.
Extracts structured product categories, materials, voltage ratings, base insulation,
additional property requirements (FRLS, LSZH), safety needs, and testing protocols.
Enforces technical decoupling of FRLS, LSZH, and Halogen-Free.
"""

import json
import logging
from typing import Dict, Any, List
from app.core.llm import llm_service

logger = logging.getLogger(__name__)


def generate_missing_technical_requirements(input_text: str, category: str) -> List[str]:
    """
    Dynamically generates missing technical parameters required for accurate standards matching
    based strictly on product category and user input.
    Contains ONLY technical parameters missing from user input (no standard numbers or verification text).
    """
    text_upper = input_text.upper()
    cat_upper = category.upper() if category else ""
    is_cable = any(w in cat_upper or w in text_upper for w in ["CABLE", "WIRE", "CONDUCTOR"])
    is_gloves = any(w in cat_upper or w in text_upper for w in ["GLOVE", "GLOVES", "HAND PROTECTION"])
    is_thermal = any(w in cat_upper or w in text_upper for w in ["THERMAL", "INSULATION PADDING", "TURBINE"])
    is_pipe = any(w in cat_upper or w in text_upper for w in ["PIPE", "HDPE"])
    is_helmet = any(w in cat_upper or w in text_upper for w in ["HELMET", "HEAD PROTECTION"])

    missing = []

    if is_gloves:
        missing = [
            "Glove material composition (e.g., nitrile, neoprene, latex, PVC, butyl)",
            "Specific chemicals and concentration levels",
            "Required protection duration and chemical breakthrough time",
            "Glove thickness and cuff length specification",
            "Glove size range (e.g., Size 7-11 / S to XXL)",
            "Mechanical performance ratings (abrasion, cut, tear, puncture resistance as per EN 388)",
            "Grip texture and dexterity requirements",
            "Applicable test methods and required certification"
        ]
    elif is_cable:
        if "SHEATH" not in text_upper:
            missing.append("Outer sheath material (e.g., PVC Type ST1/ST2, Polyethylene, Polyolefin)")
            missing.append("Outer sheath fire-performance rating")
        if "SMOKE DENSITY" not in text_upper and "ACID GAS" not in text_upper:
            missing.append("Specific FRLS compound grade and smoke density classification")
        if not any(w in text_upper for w in ["SQ MM", "MM2", "CROSS-SECTION", "CONDUCTOR SIZE", "SQ.MM"]):
            missing.append("Cable size or conductor cross-sectional area (e.g., 1.5 sq mm to 400 sq mm)")
        if not any(w in text_upper for w in ["UNDERGROUND", "DUCT", "TRENCH", "TRAY", "INDOOR", "OUTDOOR", "LAYING", "SUBSTATION"]):
            missing.append("Installation environment and laying conditions")
        missing.append("Required mechanical and additional electrical test parameters")
    elif is_thermal:
        missing = [
            "Insulation material composition (e.g., ceramic fiber, mineral wool, silica fiber)",
            "Maximum operating temperature (°C)",
            "Thermal conductivity (W/m·K) requirement",
            "Thickness and dimensional specifications",
            "Density and compressive strength",
            "Fire or flammability resistance rating"
        ]
    elif is_pipe:
        missing = [
            "HDPE pipe resin grade (PE 63, PE 80, PE 100)",
            "Nominal outer diameter (mm) and wall thickness / PN rating",
            "Fluid transported and maximum working pressure (bar)",
            "Hydrostatic strength and Melt Flow Rate (MFR) requirements"
        ]
    elif is_helmet:
        missing = [
            "Helmet shell material (HDPE, ABS, Fiberglass)",
            "Impact resistance performance level",
            "Electrical insulation voltage rating (if required)",
            "Chin strap strength and retention system specification"
        ]
    else:
        missing = [
            "Specific material grade or composition",
            "Dimensional tolerances and thickness specifications",
            "Operating temperature and environmental exposure limits",
            "Applicable mechanical or physical test requirements",
            "Required certification or purchaser specification"
        ]

    clean_missing = []
    for item in missing:
        item_upper = item.upper()
        if "VERIFICATION REQUIRED" in item_upper or "STANDARD IS " in item_upper or "REVISION" in item_upper:
            continue
        clean_missing.append(item)

    return clean_missing



def extract_procurement_requirements(input_text: str, user_category: str = None, user_purpose: str = None) -> Dict[str, Any]:
    """
    Analyzes raw input specification text and extracts structured requirements.
    Dynamically extracts parameters present in input and preserves specific product_type.
    """
    inferred_cat = user_category or "General Product"
    combined_prompt_text = f"User Product Category Hint: {inferred_cat}\n"
    combined_prompt_text += f"Procurement Purpose: {user_purpose or 'General Procurement'}\n"
    combined_prompt_text += f"Technical Specification Document Text:\n{input_text[:6000]}"

    system_prompt = (
        "You are an expert Indian Government e-Procurement (GeM, CPWD, PSU) technical specification analyst.\n"
        "Analyze the provided procurement document/text and extract technical parameters in strict JSON format.\n\n"
        "CRITICAL RULES:\n"
        "1. Extract ONLY parameters explicitly mentioned in the text. Do NOT invent cable/electrical parameters (such as Conductor, Voltage, FRLS, PVC, Dielectric Test) if the product is not an electrical cable.\n"
        "2. Do NOT conflate FRLS into LSZH.\n"
        "3. Preserve the most specific product type extracted from the input as product_type (e.g., 'Chemical-resistant Protective Gloves', 'PVC Insulated Electric Cables', 'High-Temperature Turbine Insulation Padding').\n"
        "4. Identify missing technical information required for accurate standards matching.\n"
        "5. Do NOT include standard numbers, revision statuses, or standard verification messages in missing_or_ambiguous_specs.\n\n"
        "JSON output format:\n"
        "{\n"
        '  "product_category": "Industrial Safety Gloves",\n'
        '  "product_type": "Chemical-resistant Protective Gloves",\n'
        '  "procurement_summary": "Chemical-resistant protective gloves for laboratory technicians handling industrial cleaning chemicals and corrosive substances.",\n'
        '  "extracted_requirements": [\n'
        '    {"category": "Application", "parameter": "Intended Use", "value_spec": "Handling industrial cleaning chemicals and corrosive substances"}\n'
        '  ],\n'
        '  "missing_or_ambiguous_specs": [\n'
        '    "Glove material composition (e.g., nitrile, neoprene, latex, PVC, butyl)",\n'
        '    "Specific chemicals and concentration levels"\n'
        '  ]\n'
        "}\n\n"
        "Do not include conversational preamble or markdown codeblocks."
    )

    # Infer specific product type heuristically if needed
    text_up = input_text.upper()
    spec_prod_type = None
    if "CHEMICAL-RESISTANT" in text_up or "CHEMICAL RESISTANT" in text_up or "CHEMICAL PROTECTIVE" in text_up:
        spec_prod_type = "Chemical-resistant Protective Gloves"
    elif "TURBINE" in text_up and "INSULATION" in text_up:
        spec_prod_type = "High-Temperature Turbine Insulation Padding"
    elif "PVC" in text_up and "CABLE" in text_up:
        spec_prod_type = "PVC Insulated Electric Cables"
    elif "HDPE" in text_up and "PIPE" in text_up:
        spec_prod_type = "HDPE Water Supply Pipes"
    elif "HELMET" in text_up:
        spec_prod_type = "Industrial Safety Helmets"

    try:
        raw_response = llm_service.generate_response(prompt=combined_prompt_text, system_prompt=system_prompt)
        
        clean_json_str = raw_response.strip()
        if clean_json_str.startswith("```json"):
            clean_json_str = clean_json_str[7:]
        if clean_json_str.startswith("```"):
            clean_json_str = clean_json_str[3:]
        if clean_json_str.endswith("```"):
            clean_json_str = clean_json_str[:-3]
        clean_json_str = clean_json_str.strip()

        parsed = json.loads(clean_json_str)

        if not parsed.get("product_type") and spec_prod_type:
            parsed["product_type"] = spec_prod_type

        # Post-processing safeguard
        extracted_reqs = parsed.get("extracted_requirements", [])
        for req in extracted_reqs:
            val = req.get("value_spec", "")
            if "FRLS" in input_text.upper() and ("LSZH" in val.upper() or "HALOGEN-FREE" in val.upper()) and "LSZH" not in input_text.upper():
                req["value_spec"] = "FRLS"

        # Sanitize missing_or_ambiguous_specs
        cat = parsed.get("product_category") or user_category or "General Product"
        raw_missing = parsed.get("missing_or_ambiguous_specs", [])
        clean_missing = [
            item for item in raw_missing
            if "VERIFICATION REQUIRED" not in item.upper() and "STANDARD IS " not in item.upper() and "IS " not in item
        ]
        if not clean_missing or len(clean_missing) < 2:
            clean_missing = generate_missing_technical_requirements(input_text, cat)

        parsed["missing_or_ambiguous_specs"] = clean_missing
        return parsed
    except Exception as e:
        logger.warning(f"LLM requirement extraction parse failed: {str(e)}. Falling back to deterministic heuristic extraction.")
        
        reqs = []
        is_cable = any(w in input_text.upper() for w in ["CABLE", "CONDUCTOR", "1100V", "1100 V", "FRLS", "DIELECTRIC"])
        
        if is_cable:
            if "COPPER" in input_text.upper() or "ALUMINIUM" in input_text.upper():
                reqs.append({"category": "Conductor", "parameter": "Conductor Material", "value_spec": "Copper / Aluminium"})
            if "SINGLE-CORE" in input_text.upper() or "MULTICORE" in input_text.upper():
                reqs.append({"category": "Cable Type", "parameter": "Core Configuration", "value_spec": "Single-core and Multicore"})
            if "PVC" in input_text.upper():
                reqs.append({"category": "Base Insulation", "parameter": "Insulation Type", "value_spec": "PVC"})
            if "FRLS" in input_text.upper():
                reqs.append({"category": "Additional Insulation Requirement", "parameter": "Flame/Smoke Requirement", "value_spec": "FRLS"})
            if "1100 V" in input_text.upper() or "1100V" in input_text.upper():
                reqs.append({"category": "Voltage Rating", "parameter": "Working Voltage", "value_spec": "1100 V"})
            if "DIELECTRIC" in input_text.upper() or "HIGH VOLTAGE" in input_text.upper():
                reqs.append({"category": "Required Test", "parameter": "Electrical Test", "value_spec": "High Voltage Dielectric Strength Test"})
        else:
            reqs.append({"category": "Application", "parameter": "Intended Use", "value_spec": input_text.strip()[:150]})

        cat = user_category or ("Electrical Wires & Power Cables" if is_cable else "Thermal Insulation Padding")
        missing_tech = generate_missing_technical_requirements(input_text, cat)

        return {
            "product_category": cat,
            "product_type": spec_prod_type or cat,
            "procurement_summary": f"Procurement specification analyzing: {input_text[:200]}...",
            "extracted_requirements": reqs,
            "missing_or_ambiguous_specs": missing_tech
        }

