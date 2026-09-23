"""
Recommendation Validator Module.
Provides deterministic technical compatibility validation, Field Comparison Matrix generation,
explainable score calculation, core/sheath insulation disambiguation, domain category filtering,
dynamic exclusion reason construction, and post-analysis report sanitization.
"""

import re
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from app.core.models import IndianStandard

logger = logging.getLogger(__name__)

OFFICIAL_SCORE_DISCLAIMER = (
    "This score is an internal semantic retrieval indicator. "
    "It does not represent official BIS approval, compliance, certification, legal validity, or applicability."
)

UNVERIFIED_CERT_TEXT = (
    "The product may be subject to BIS product certification or an applicable Quality Control Order. "
    "Exact applicability must be verified against the current official BIS product scope and applicable Gazette notification for the specified cable type, voltage rating, and intended use."
)

UNSUPPORTED_QCO_EXPLANATION = (
    "The applicability of mandatory BIS certification, QCO requirements, "
    "tender conditions, and municipal authority requirements requires verification from current official sources."
)

UNVERIFIED_REVISION_TEXT = (
    "Verification required from the official BIS standard document."
)


def get_safe_cert_explanation(product_category: str = "") -> str:
    """
    Returns unverified certification guidance text adhering strictly to QCO verification requirements.
    Replaces unsupported QCO claims with official verification statement.
    """
    return UNSUPPORTED_QCO_EXPLANATION


DOMAIN_COMPATIBILITY = {
    "Piping": [
        "Piping",
        "Pipes & Water Management",
        "Plumbing",
        "Water Supply",
        "Fluid Transport",
        "Industrial Piping",
        "HDPE Sewage Pipes",
        "Industrial Effluent Piping",
        "HDPE Water Supply Pipes",
        "Water Distribution",
        "Conveyance",
        "Civil & Construction",
        "Building Services"
    ],
    "Pipes & Water Management": [
        "Piping",
        "Pipes & Water Management",
        "Plumbing",
        "Water Supply",
        "Fluid Transport",
        "Industrial Piping",
        "HDPE Sewage Pipes",
        "Industrial Effluent Piping",
        "Water Quality & Environment"
    ],
    "Electrical Wires & Power Cables": [
        "Electrical & Cables",
        "Electrical Wires & Power Cables",
        "Power & Infrastructure",
        "Power & Public Utilities",
        "Electrical Engineering",
        "Cables"
    ],
    "Electrical & Cables": [
        "Electrical & Cables",
        "Electrical Wires & Power Cables",
        "Power & Infrastructure",
        "Power & Public Utilities",
        "Electrical Engineering",
        "Cables"
    ],
    "Civil & Construction": [
        "Civil & Construction",
        "Infrastructure & Buildings",
        "Construction Materials",
        "Building Materials",
        "Reinforcement Steel",
        "Concrete",
        "Pipes & Water Management"
    ],
    "Construction Materials": [
        "Civil & Construction",
        "Infrastructure & Buildings",
        "Construction Materials",
        "Building Materials",
        "Reinforcement Steel",
        "Concrete",
        "Pipes & Water Management"
    ],
    "Automation & Robotics": [
        "Automation & Robotics",
        "Robotics & Automation",
        "Industrial Automation"
    ],
    "Renewable Energy & Solar": [
        "Renewable Energy & Solar",
        "Solar PV",
        "Energy & Sustainability"
    ],
    "Industrial Safety Gloves": [
        "Industrial Safety Gloves",
        "Personal Protective Equipment",
        "Safety & Hand Protection"
    ],
    "Industrial Safety Helmets": [
        "Industrial Safety Helmets",
        "Personal Protective Equipment",
        "Safety & Head Protection"
    ]
}


def build_dynamic_exclusion_reason(candidate_title: str, candidate_category: str, target_category: str, candidate_scope: str = "") -> str:
    """
    Generates dynamic, accurate product scope mismatch reasons derived from the actual candidate standard title/category/scope
    and the requested procurement product category. Prevents self-contradictory exclusion statements.
    """
    t_cat = (target_category or "the requested product").strip()
    t_lower = t_cat.lower()
    c_title = (candidate_title or "").strip()
    c_title_lower = c_title.lower()
    c_cat_lower = (candidate_category or "").lower()
    c_scope_lower = (candidate_scope or "").lower()
    c_all = f"{c_title_lower} {c_cat_lower} {c_scope_lower}"

    # Specific standard & domain exclusion reason generation
    if "10500" in c_title_lower or "drinking water" in c_title_lower:
        if any(w in t_lower for w in ["pipe", "piping", "hdpe", "conveyance", "plumbing"]):
            return f"This standard specifies drinking water quality parameters and testing requirements, but is not the primary product specification for {t_cat}."
        scope_desc = "drinking water quality specifications"
    elif "steel" in c_title_lower or "deformed" in c_title_lower or "reinforcement" in c_title_lower or "rebar" in c_title_lower:
        scope_desc = "steel reinforcement bars and wires for concrete structures"
    elif "respiratory" in c_title_lower or "breathing apparatus" in c_title_lower:
        scope_desc = "respiratory protective equipment and breathing apparatus"
    elif "helmet" in c_title_lower or "head protection" in c_title_lower:
        scope_desc = "industrial safety helmets for head protection"
    elif "cable" in c_title_lower or "conductor" in c_title_lower or "electric" in c_title_lower or "wire" in c_title_lower:
        scope_desc = "electrical wires and power cables"
    elif "pipe" in c_title_lower or "hdpe" in c_title_lower:
        scope_desc = "HDPE piping systems for water supplies and effluents"
    elif "photovoltaic" in c_title_lower or "solar" in c_title_lower:
        scope_desc = "terrestrial photovoltaic (PV) solar modules"
    elif "robot" in c_title_lower or "robotics" in c_title_lower or "automation" in c_title_lower:
        scope_desc = "industrial robotics and automation systems"
    elif "information technology" in c_title_lower or "it equipment" in c_title_lower:
        scope_desc = "information technology equipment safety"
    elif "concrete" in c_title_lower:
        scope_desc = "plain and reinforced concrete structural design"
    elif c_title:
        scope_desc = c_title
    else:
        scope_desc = candidate_category or "unrelated equipment"

    # Anti-hallucination guard: If scope description and target category share domain terms, do not declare a self-contradictory scope mismatch
    if ("pipe" in scope_desc.lower() or "piping" in scope_desc.lower()) and ("pipe" in t_lower or "piping" in t_lower or "plumbing" in t_lower or "conveyance" in t_lower or "hdpe" in t_lower):
        return f"Standard addresses secondary water quality or allied specs, requiring technical confirmation for main {t_cat} procurement."
    if ("cable" in scope_desc.lower() or "wire" in scope_desc.lower()) and ("cable" in t_lower or "wire" in t_lower or "conductor" in t_lower or "electrical" in t_lower):
        return f"Standard addresses secondary electrical specifications, requiring technical confirmation for main {t_cat} procurement."

    return f"Product scope mismatch: This standard addresses {scope_desc}, not {t_cat}."


def normalize_standard_number(std_num: str) -> str:
    """
    Normalizes standard identifiers to prevent duplication caused by formatting variations.
    """
    if not std_num:
        return ""
    s = std_num.strip().upper()
    s = re.sub(r'\s*:\s*', ':', s)
    s = re.sub(r'\bIS\s*-?\s*', 'IS ', s)
    s = re.sub(r'\s+', ' ', s)
    return s


def validate_product_category(candidate_category: str, candidate_title: str, target_category: str, candidate_scope: str = "") -> Tuple[bool, str]:
    """
    Validates whether candidate standard aligns with procurement target domain using multi-signal taxonomy compatibility.
    Enforces strict negative keyword exclusion rules for cross-domain standards.
    """
    if not target_category:
        return True, "Domain scope aligned."

    t_cat = target_category.lower().strip()
    c_cat = (candidate_category or "").lower().strip()
    c_title = (candidate_title or "").lower().strip()
    c_scope = (candidate_scope or "").lower().strip()
    c_all = f"{c_title} {c_cat} {c_scope}"

    is_cable_target = any(w in t_cat for w in ["cable", "wire", "conductor", "electrical"])
    is_solar_target = any(w in t_cat for w in ["solar", "photovoltaic", "pv module"])
    is_pipe_target = any(w in t_cat for w in ["pipe", "pipes", "piping", "hdpe", "water supply", "effluent", "sewage", "conveyance", "plumbing", "fluid transport", "water distribution"])
    is_concrete_target = any(w in t_cat for w in ["concrete", "civil", "construction", "building materials"]) and not any(w in t_cat for w in ["steel rebar", "structural steel", "steel bar"])
    is_steel_target = any(w in t_cat for w in ["steel rebar", "steel bar", "reinforcement steel", "steel reinforcement", "rebar"]) or ("steel" in t_cat and "concrete" not in t_cat)
    is_it_target = any(w in t_cat for w in ["it ", "information technology", "computer", "server"])
    is_thermal_target = any(w in t_cat for w in ["thermal insulation", "insulation padding", "turbine insulation", "high-temperature insulation"])
    is_gloves_target = any(w in t_cat for w in ["glove", "gloves", "hand protection"])
    is_helmet_target = any(w in t_cat for w in ["helmet", "head protection"])
    is_robotics_target = any(w in t_cat for w in ["robot", "robotics", "automation", "autonomous"])
    is_water_quality_target = any(w in t_cat for w in ["water quality", "drinking water", "water testing"]) and not is_pipe_target

    # 1. Gloves Target
    if is_gloves_target:
        if any(w in c_all for w in ["respiratory", "breathing apparatus", "helmet", "cable", "wire", "conductor", "pipe", "hdpe", "information technology", "steel", "concrete", "photovoltaic", "solar", "drinking water"]):
            return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category, candidate_scope)
        if any(w in c_all for w in ["glove", "gloves", "hand protection"]):
            return True, "Domain scope aligned with Industrial Safety Gloves."
        return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category, candidate_scope)

    # 2. Cable Target
    elif is_cable_target:
        if any(w in c_all for w in ["photovoltaic", "solar", "pipe", "hdpe", "steel", "rebar", "concrete", "drinking water", "helmet", "respiratory", "information technology", "robot"]):
            return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category, candidate_scope)
        if any(w in c_all for w in ["cable", "wire", "electric", "conductor", "power"]):
            return True, "Domain scope aligned with Electrical Cables."
        return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category, candidate_scope)

    # 3. Solar Target
    elif is_solar_target:
        if any(w in c_all for w in ["pipe", "steel", "cable", "helmet", "drinking water", "glove", "respiratory", "robot"]):
            return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category, candidate_scope)
        if any(w in c_all for w in ["photovoltaic", "solar", "pv module"]):
            return True, "Domain scope aligned with Solar PV."
        return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category, candidate_scope)

    # 4. Pipe / Piping Target
    elif is_pipe_target:
        if any(w in c_all for w in ["solar", "photovoltaic", "cable", "wire", "conductor", "steel rebar", "helmet", "glove", "respiratory", "robot", "robotics"]):
            return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category, candidate_scope)
        if any(w in c_all for w in ["pipe", "pipes", "piping", "hdpe", "polyethylene", "potable water", "sewage", "effluents", "water supply", "conveyance", "plumbing", "fluid transport"]):
            return True, "Domain scope aligned with Piping & Water Conveyance."
        return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category, candidate_scope)

    # 5. Concrete Target
    elif is_concrete_target:
        if any(w in c_all for w in ["solar", "pipe", "hdpe", "cable", "wire", "helmet", "glove", "respiratory", "robot", "robotics"]):
            return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category, candidate_scope)
        if any(w in c_all for w in ["concrete", "civil", "construction", "aggregate", "cement", "rebar"]):
            return True, "Domain scope aligned with Civil & Concrete."
        return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category, candidate_scope)

    # 6. Steel Target
    elif is_steel_target:
        if any(w in c_all for w in ["solar", "pipe", "cable", "helmet", "drinking water", "glove", "respiratory", "robot"]):
            return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category, candidate_scope)
        if any(w in c_all for w in ["steel", "rebar", "reinforcement"]):
            return True, "Domain scope aligned with Reinforcement Steel."
        return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category, candidate_scope)

    # 7. IT Target
    elif is_it_target:
        if any(w in c_all for w in ["pipe", "steel", "cable", "solar", "concrete", "helmet", "glove"]):
            return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category, candidate_scope)
        if "it & electronics" in c_cat or "information technology" in c_all:
            return True, "Domain scope aligned with IT Equipment."
        return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category, candidate_scope)

    # 8. Thermal Target
    elif is_thermal_target:
        if any(w in c_all for w in ["cable", "wire", "electric", "solar", "pipe", "steel", "concrete", "helmet", "respiratory", "drinking water", "information technology"]):
            return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category, candidate_scope)
        if "thermal insulation" in c_all or "insulation padding" in c_all:
            return True, "Domain scope aligned with Thermal Insulation."
        return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category, candidate_scope)

    # 9. Helmet Target
    elif is_helmet_target:
        if any(w in c_all for w in ["cable", "pipe", "steel", "solar", "respiratory", "glove", "robot"]):
            return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category, candidate_scope)
        if "helmet" in c_all or "head protection" in c_all:
            return True, "Domain scope aligned with Industrial Safety Helmets."
        return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category, candidate_scope)

    # 10. Robotics Target
    elif is_robotics_target:
        if any(w in c_all for w in ["pipe", "hdpe", "cable", "wire", "steel", "concrete", "solar", "helmet", "glove", "drinking water"]):
            return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category, candidate_scope)
        if any(w in c_all for w in ["robot", "robotics", "automation"]):
            return True, "Domain scope aligned with Robotics & Automation."
        return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category, candidate_scope)

    # 11. Water Quality Target
    elif is_water_quality_target:
        if any(w in c_all for w in ["cable", "wire", "steel", "concrete", "solar", "helmet", "glove", "robot"]):
            return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category, candidate_scope)
        if any(w in c_all for w in ["water quality", "drinking water", "10500"]):
            return True, "Domain scope aligned with Water Quality Specifications."
        return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category, candidate_scope)

    # General domain fallback with exact word token matching
    t_words = [w for w in re.findall(r'\b[a-zA-Z]{3,}\b', t_cat) if w not in ["general", "product", "equipment", "item", "procurement", "supply", "system", "materials", "material"]]
    c_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', c_all))
    if t_words and any(w in c_words for w in t_words):
        return True, "Domain scope aligned."

    return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category, candidate_scope)


def validate_insulation_type(candidate_title: str, candidate_scope: str, extracted_reqs: List[Dict[str, Any]]) -> Tuple[str, str, str]:
    """
    Decouples Core Insulation from Outer Sheath.
    Returns: (core_insulation_result: Match/Mismatch/Unknown, core_provision: str, outer_sheath_provision: str)
    """
    req_core = None
    for req in extracted_reqs:
        param = req.get("parameter", "").lower()
        cat = req.get("category", "").lower()
        val = req.get("value_spec", "").upper()
        if "insulation" in param or "insulation" in cat or "pvc" in val or "xlpe" in val:
            if "PVC" in val:
                req_core = "PVC"
            elif "XLPE" in val:
                req_core = "XLPE"

    comb_text = f"{candidate_title} {candidate_scope}".upper()

    core_provision = "Unknown"
    outer_sheath_provision = "Unknown"

    if "XLPE INSULATED" in comb_text or "CROSS-LINKED POLYETHYLENE INSULATED" in comb_text:
        core_provision = "XLPE"
    elif "PVC INSULATED" in comb_text or "POLYVINYL CHLORIDE INSULATED" in comb_text:
        core_provision = "PVC"

    if "PVC SHEATHED" in comb_text or "PVC SHEATH" in comb_text:
        outer_sheath_provision = "PVC"

    if not req_core:
        return "Unknown", core_provision, outer_sheath_provision

    if req_core == "PVC":
        if core_provision == "PVC":
            return "Potential Match", core_provision, outer_sheath_provision
        elif core_provision == "XLPE":
            return "Mismatch", f"Primary Core Insulation is {core_provision} (Outer Sheath is {outer_sheath_provision})", outer_sheath_provision
        else:
            return "Unknown", core_provision, outer_sheath_provision

    if req_core == "XLPE":
        if core_provision == "XLPE":
            return "Potential Match", core_provision, outer_sheath_provision
        elif core_provision == "PVC":
            return "Mismatch", f"Primary Core Insulation is {core_provision}", outer_sheath_provision

    return "Unknown", core_provision, outer_sheath_provision


def generate_field_comparison_matrix(candidate: IndianStandard, extracted_reqs: List[Dict[str, Any]], target_category: str) -> List[Dict[str, Any]]:
    """
    Generates product-specific Field Comparison Matrix for candidate standard against extracted requirements.
    Matrix items: Parameter, Required Value, Standard Provision, Evaluation/Result (Confirmed Match / Potential Match / Mismatch / Unknown / Missing Input / Requires Official Verification)
    """
    matrix = []
    c_title = candidate.title or ""
    c_scope = candidate.scope or ""
    c_cat = candidate.category or ""
    comb_text = f"{c_title} {c_scope}".lower()

    t_cat_lower = (target_category or "").lower()
    is_cable = any(w in t_cat_lower for w in ["cable", "wire", "conductor", "electrical"])
    is_gloves = any(w in t_cat_lower for w in ["glove", "gloves", "hand protection"])
    is_thermal = any(w in t_cat_lower for w in ["thermal insulation", "insulation padding", "turbine insulation"])
    is_pipe = any(w in t_cat_lower for w in ["pipe", "pipes", "piping", "hdpe", "plumbing", "water supply", "conveyance", "effluent", "sewage"]) or "hdpe" in comb_text or "pipe" in comb_text
    is_helmet = any(w in t_cat_lower for w in ["helmet"])

    # 1. Product Category
    is_domain_match, domain_msg = validate_product_category(c_cat, c_title, target_category)
    matrix.append({
        "parameter": "Product Category",
        "required_value": target_category or "General Procurement",
        "standard_provision": c_cat or c_title[:60],
        "result": "Potential Match" if is_domain_match else "Not Applicable"
    })

    if is_gloves:
        glove_mat = "Not Mentioned"
        chem_res = "Required" if any("chem" in str(r).lower() for r in extracted_reqs) else "Not Mentioned"
        reusable = "Reusable" if any("reus" in str(r).lower() for r in extracted_reqs) else "Not Mentioned"
        breakthrough = "Not Mentioned"
        puncture = "Not Mentioned"

        for req in extracted_reqs:
            p_str = (req.get("parameter") or "").lower()
            v_str = req.get("value_spec") or ""
            if "material" in p_str:
                glove_mat = v_str
            if "breakthrough" in p_str:
                breakthrough = v_str
            if "puncture" in p_str:
                puncture = v_str

        mat_prov = "Covered" if "glove" in comb_text and ("latex" in comb_text or "nitrile" in comb_text or "rubber" in comb_text or "pvc" in comb_text) else "Not Covered"
        mat_res = "Potential Match" if (is_domain_match and mat_prov == "Covered") else "Not Mentioned"
        matrix.append({
            "parameter": "Glove Material",
            "required_value": glove_mat,
            "standard_provision": mat_prov,
            "result": mat_res
        })

        chem_prov = "Chemical resistance specified" if "chemical" in comb_text else "Not Covered"
        chem_res_result = "Potential Match" if (is_domain_match and "chemical" in comb_text) else ("No Match" if chem_res == "Required" else "Not Mentioned")
        matrix.append({
            "parameter": "Chemical Resistance",
            "required_value": chem_res,
            "standard_provision": chem_prov,
            "result": chem_res_result
        })

        reus_prov = "Reusable PPE" if "reusable" in comb_text else "Not Covered"
        reus_result = "Potential Match" if (is_domain_match and "reusable" in comb_text) else "Not Mentioned"
        matrix.append({
            "parameter": "Reusability",
            "required_value": reusable,
            "standard_provision": reus_prov,
            "result": reus_result
        })

        matrix.append({
            "parameter": "Breakthrough Time",
            "required_value": breakthrough,
            "standard_provision": "Not Covered",
            "result": "Not Mentioned"
        })

        matrix.append({
            "parameter": "Puncture Resistance",
            "required_value": puncture,
            "standard_provision": "Not Covered",
            "result": "Not Mentioned"
        })

        return matrix

    elif is_cable:
        ins_result, core_prov, sheath_prov = validate_insulation_type(c_title, c_scope, extracted_reqs)
        matrix.append({
            "parameter": "Core Insulation",
            "required_value": "PVC",
            "standard_provision": f"Core: {core_prov} | Outer Sheath: {sheath_prov}",
            "result": ins_result
        })

        target_volts = "Unspecified"
        target_conductor = "Unspecified"
        target_frls = "Unspecified"
        target_test = "Unspecified"

        for req in extracted_reqs:
            param = req.get("parameter", "").lower()
            cat = req.get("category", "").lower()
            val = req.get("value_spec", "")
            if "voltage" in param or "voltage" in cat:
                target_volts = val
            if "conductor" in param or "conductor" in cat:
                target_conductor = val
            if "frls" in val.upper() or "flame" in param or "smoke" in param:
                target_frls = val
            if "test" in param or "test" in cat or "dielectric" in val.lower():
                target_test = val

        if "1100" in target_volts or "1.1 kv" in target_volts.lower():
            if "1100 v" in comb_text or "1100v" in comb_text or "1.1 kv" in comb_text or "up to and including 1100" in comb_text:
                v_res = "Potential Match"
                v_prov = "Working voltages up to and including 1100 V"
            else:
                v_res = "Unknown"
                v_prov = "Voltage bounds require verification in full text"
        else:
            v_res = "Unknown"
            v_prov = "Voltage specification not explicitly detailed in catalog snippet"

        matrix.append({
            "parameter": "Voltage Rating",
            "required_value": target_volts,
            "standard_provision": v_prov,
            "result": v_res
        })

        if "conductor" in comb_text or "copper" in comb_text or "aluminium" in comb_text:
            c_res = "Potential Match"
            c_prov = "Applies to Copper & Aluminium Conductors"
        else:
            c_res = "Unknown"
            c_prov = "Conductor specification requires verification"

        matrix.append({
            "parameter": "Conductor Material",
            "required_value": target_conductor,
            "standard_provision": c_prov,
            "result": c_res
        })

        if "frls" in comb_text and "flame retardant low smoke" in comb_text:
            f_res = "Potential Match"
            f_prov = "Explicit FRLS compound testing specification referenced"
        else:
            f_res = "Unknown"
            f_prov = "FRLS compound grade requirement requires verification against official BIS standard document"

        matrix.append({
            "parameter": "FRLS Requirement",
            "required_value": target_frls,
            "standard_provision": f_prov,
            "result": f_res
        })

        if "dielectric" in comb_text or "high voltage" in comb_text:
            t_res = "Potential Match"
            t_prov = "General dielectric testing procedures referenced; exact clause verification required"
        else:
            t_res = "Unknown"
            t_prov = "Test procedure details require verification from official BIS standard document"

        matrix.append({
            "parameter": "High Voltage Test",
            "required_value": target_test,
            "standard_provision": t_prov,
            "result": t_res
        })

        return matrix

    elif is_pipe:
        pressure_val = "Not provided"
        diameter_val = "Not provided"
        grade_val = "Not provided"
        mat_val = "HDPE"
        use_val = "Water conveyance"

        for req in extracted_reqs:
            p_lower = (req.get("parameter") or "").lower()
            v_val = req.get("value_spec") or ""
            if any(w in p_lower for w in ["pressure", "pn", "bar"]):
                pressure_val = v_val
            if any(w in p_lower for w in ["diameter", "mm", "size", "outer diameter"]):
                diameter_val = v_val
            if any(w in p_lower for w in ["grade", "pe 63", "pe 80", "pe 100", "resin"]):
                grade_val = v_val
            if "material" in p_lower:
                mat_val = v_val
            if "use" in p_lower or "application" in p_lower:
                use_val = v_val

        matrix = [
            {
                "parameter": "Product category",
                "procurement_requirement": target_category or "Piping",
                "required_value": target_category or "Piping",
                "indexed_standard_evidence": "HDPE pipe product scope",
                "standard_provision": "HDPE pipe product scope",
                "evaluation": "Potential Match" if is_domain_match else "Mismatch",
                "result": "Potential Match" if is_domain_match else "Mismatch"
            },
            {
                "parameter": "Pipe material",
                "procurement_requirement": mat_val,
                "required_value": mat_val,
                "indexed_standard_evidence": "HDPE identified in standard record" if ("hdpe" in comb_text or "polyethylene" in comb_text) else "Polyethylene pipe specification",
                "standard_provision": "HDPE identified in standard record" if ("hdpe" in comb_text or "polyethylene" in comb_text) else "Polyethylene pipe specification",
                "evaluation": "Potential Match" if ("hdpe" in comb_text or "polyethylene" in comb_text) else "Not Confirmed",
                "result": "Potential Match" if ("hdpe" in comb_text or "polyethylene" in comb_text) else "Not Confirmed"
            },
            {
                "parameter": "Intended use",
                "procurement_requirement": use_val,
                "required_value": use_val,
                "indexed_standard_evidence": "Water-supply application identified" if any(w in comb_text for w in ["water", "potable", "sewage", "effluent", "conveyance"]) else "Conveyance application requiring verification",
                "standard_provision": "Water-supply application identified" if any(w in comb_text for w in ["water", "potable", "sewage", "effluent", "conveyance"]) else "Conveyance application requiring verification",
                "evaluation": "Potential Match" if any(w in comb_text for w in ["water", "potable", "sewage", "effluent", "conveyance"]) else "Not Confirmed",
                "result": "Potential Match" if any(w in comb_text for w in ["water", "potable", "sewage", "effluent", "conveyance"]) else "Not Confirmed"
            },
            {
                "parameter": "Pressure rating",
                "procurement_requirement": pressure_val,
                "required_value": pressure_val,
                "indexed_standard_evidence": "Exact requirement unverified",
                "standard_provision": "Exact requirement unverified",
                "evaluation": "Missing Input" if pressure_val == "Not provided" else "Requires Official Verification",
                "result": "Missing Input" if pressure_val == "Not provided" else "Requires Official Verification"
            },
            {
                "parameter": "Pipe diameter",
                "procurement_requirement": diameter_val,
                "required_value": diameter_val,
                "indexed_standard_evidence": "Required for detailed comparison",
                "standard_provision": "Required for detailed comparison",
                "evaluation": "Missing Input" if diameter_val == "Not provided" else "Requires Official Verification",
                "result": "Missing Input" if diameter_val == "Not provided" else "Requires Official Verification"
            },
            {
                "parameter": "Material grade",
                "procurement_requirement": grade_val,
                "required_value": grade_val,
                "indexed_standard_evidence": "Requires official document verification",
                "standard_provision": "Requires official document verification",
                "evaluation": "Not Confirmed" if grade_val == "Not provided" else "Requires Official Verification",
                "result": "Not Confirmed" if grade_val == "Not provided" else "Requires Official Verification"
            }
        ]
        return matrix

    else:
        for req in extracted_reqs[:5]:
            p_name = req.get("parameter") or req.get("category") or "Requirement"
            v_val = req.get("value_spec") or "Required"
            p_text = f"{p_name} {v_val}".lower()
            req_words = [w for w in re.findall(r'\b[a-zA-Z]{4,}\b', p_text) if w not in ["procurement", "supply", "request", "requirement", "intended", "used"]]
            word_match = any(w in comb_text for w in req_words) if req_words else False

            if is_domain_match and word_match:
                res = "Potential Match"
            elif is_domain_match:
                res = "Potential Match"
            else:
                res = "Mismatch"

            matrix.append({
                "parameter": p_name,
                "procurement_requirement": v_val,
                "required_value": v_val,
                "indexed_standard_evidence": "Technical provision requires verification against the official standard document." if res == "Potential Match" else "Not Covered",
                "standard_provision": "Technical provision requires verification against the official standard document." if res == "Potential Match" else "Not Covered",
                "evaluation": res,
                "result": res
            })
        return matrix


def calculate_technical_match_score(matrix: List[Dict[str, Any]]) -> Tuple[float, str]:
    """
    Calculates explainable score (0.0 to 1.0) and match strength label based on Field Comparison Matrix.
    """
    domain_item = next((item for item in matrix if item["parameter"] in ["Product Category", "Product category"]), None)
    if domain_item and domain_item["result"] in ["Mismatch", "Not Applicable"]:
        return 0.0, "Mismatch"

    matches = sum(1 for item in matrix if item["result"] in ["Match", "Potential Match", "Confirmed Match"])
    total = len(matrix)

    core_item = next((item for item in matrix if item["parameter"] == "Core Insulation"), None)
    core_mismatch = (core_item and core_item["result"] == "Mismatch")

    if core_mismatch:
        score = 0.45
        strength = "Low"
    else:
        score = round(matches / float(total), 2)
        if score >= 0.75:
            strength = "High"
        elif score >= 0.50:
            strength = "Medium"
        else:
            strength = "Low"

    return score, strength


def filter_unrelated_standards(
    candidate_standards: List[IndianStandard],
    extracted_data: Dict[str, Any]
) -> Tuple[List[IndianStandard], List[Dict[str, Any]]]:
    """
    Filters candidate standards into applicable candidates and excluded standards list with dynamic exclusion reasons.
    """
    target_category = extracted_data.get("product_category", "")
    applicable = []
    excluded = []
    seen_std_nums = set()

    for std in candidate_standards:
        norm_num = normalize_standard_number(std.standard_number)
        if norm_num in seen_std_nums:
            continue
        seen_std_nums.add(norm_num)

        is_match, reason = validate_product_category(
            candidate_category=std.category or "",
            candidate_title=std.title or "",
            target_category=target_category
        )

        if is_match:
            applicable.append(std)
        else:
            excluded.append({
                "standard_number": std.standard_number,
                "title": std.title,
                "category": std.category or "Unspecified",
                "retrieved_because": "Retrieved via vector similarity search",
                "mismatch_type": "Product Category Mismatch",
                "exclusion_reason": reason,
                "evidence_source": std.source_url or "BIS Standards Reference Catalogue"
            })

    return applicable, excluded


def classify_standard_applicability(
    standard_number: str,
    title: str,
    internal_score: float,
    match_strength: str,
    matrix: List[Dict[str, Any]],
    has_verified_qco: bool
) -> Dict[str, Any]:
    """
    Assigns strict applicability status based on field matrix and evidence.
    """
    core_item = next((item for item in matrix if item["parameter"] == "Core Insulation"), None)
    core_mismatch = (core_item and core_item["result"] == "Mismatch")

    if internal_score == 0.0:
        status = "Not Applicable"
    elif core_mismatch:
        status = "Related but Technically Mismatched"
    elif internal_score >= 0.75 and has_verified_qco:
        status = "Recommended"
    elif internal_score >= 0.50:
        status = "Potentially Applicable"
    else:
        status = "Verification Required"

    return {
        "applicability_status": status,
        "internal_match_score": internal_score,
        "match_strength": match_strength
    }


def ensure_item_provenance_and_scope(item: Dict[str, Any], default_ver_status: str = "Verification Required") -> Dict[str, Any]:
    """
    Attaches scope_label and 7-field provenance metadata to a standard recommendation item.
    Ensures source_url label is provided, and unverified scope summaries are properly labelled.
    """
    if not item or not isinstance(item, dict):
        return item
    
    item["scope_label"] = "Scope summary from local catalogue — official document verification required."
    
    ver_status = item.get("verification_status") or default_ver_status
    is_verified = (ver_status in ["Verified", "Verified by Official Gazette"])
    
    raw_src_url = item.get("source_url")
    src_url = raw_src_url if (is_verified and raw_src_url) else None
    url_label = "Official verified document link." if is_verified else ("Official BIS catalogue link for manual verification." if raw_src_url else "No link available")
    
    item["source_url"] = src_url
    item["source_url_label"] = url_label
    
    now_iso = item.get("retrieved_at") or datetime.now(timezone.utc).isoformat()
    src_type = "Official Document Record" if is_verified else "Local Metadata Index"
    
    ev_text = item.get("evidence_text") or item.get("reasoning") or (item["evidence"][0] if item.get("evidence") else "Scope summary from local catalogue — official document verification required.")
    
    prov = item.get("provenance") or {}
    prov["source_type"] = src_type
    prov["source"] = item.get("source") or prov.get("source") or "Local BIS Catalogue"
    prov["source_url"] = src_url
    prov["source_url_label"] = url_label
    prov["source_document"] = item.get("source_document") or prov.get("source_document") or "Local Catalogue Record"
    prov["page_or_clause"] = item.get("page_or_clause") or prov.get("page_or_clause") or "Clause verification required"
    prov["evidence_text"] = ev_text
    prov["retrieved_at"] = now_iso
    prov["verification_status"] = ver_status
    
    item["provenance"] = prov
    item["source_type"] = src_type
    item["source"] = prov["source"]
    item["source_document"] = prov["source_document"]
    item["page_or_clause"] = prov["page_or_clause"]
    item["evidence_text"] = ev_text
    item["retrieved_at"] = prov["retrieved_at"]
    item["verification_status"] = ver_status
    return item


def sanitize_and_validate_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Final validation check before displaying or returning report.
    Rejects leaked electrical fields, fixes applicability text, scrubs certification text,
    enforces 7-field provenance metadata, scope_label, and attaches evidence_summary on report.
    """
    cat = (report.get("product_category") or "").lower()
    is_cable = any(w in cat for w in ["cable", "wire", "conductor"])

    cable_param_names = {"core insulation", "pvc cable insulation", "voltage rating", "conductor material", "frls requirement", "high voltage test", "cable type", "working voltage"}

    if not is_cable:
        cleaned_reqs = []
        for req in report.get("extracted_requirements", []):
            param = (req.get("parameter") or "").lower()
            if param in cable_param_names:
                continue
            req["source_type"] = "User Input Specification"
            req["source"] = "User Procurement Specification"
            req["source_url"] = None
            req["source_url_label"] = "No link available"
            req["source_document"] = "User Input Document"
            req["page_or_clause"] = "Extracted Parameter"
            req["evidence_text"] = f"Extracted requirement parameter: {req.get('parameter')}"
            req["retrieved_at"] = datetime.now(timezone.utc).isoformat()
            req["verification_status"] = "User Provided"
            cleaned_reqs.append(req)
        report["extracted_requirements"] = cleaned_reqs

        cleaned_missing = []
        for m in report.get("missing_requirements", []):
            m_lower = m.lower()
            if any(cp in m_lower for cp in ["core insulation", "voltage rating", "conductor material", "frls", "cable size"]):
                continue
            cleaned_missing.append(m)
        report["missing_requirements"] = cleaned_missing

    rec_list = report.get("recommended_standards", [])
    pot_list = report.get("potentially_applicable_standards", [])
    ex_list = report.get("excluded_standards", [])

    new_rec = []
    new_pot = []

    for item in rec_list + pot_list:
        std_num = item.get("standard_number") or ""

        # Validate domain alignment for non-cable categories
        is_match, reason = validate_product_category(
            item.get("category", ""),
            item.get("title", ""),
            report.get("product_category", ""),
            candidate_scope=item.get("scope", "")
        )
        if not is_match:
            ex_item = {
                "standard_number": std_num,
                "title": item.get("title"),
                "category": item.get("category") or "Unspecified Category",
                "retrieved_because": "Retrieved via vector similarity search",
                "mismatch_type": "Product Category Mismatch",
                "exclusion_reason": reason,
                "evidence_source": "BIS Standards Catalogue"
            }
            ex_list.append(ensure_item_provenance_and_scope(ex_item))
            continue

        if not is_cable:
            matrix = item.get("field_comparison_matrix", [])
            clean_matrix = []
            for m_item in matrix:
                p_name = m_item.get("parameter", "")
                if p_name in ["Core Insulation", "Voltage Rating", "Conductor Material", "FRLS Requirement", "High Voltage Test"]:
                    continue
                clean_matrix.append(m_item)
            item["field_comparison_matrix"] = clean_matrix

        item = ensure_item_provenance_and_scope(item)
        if item in rec_list:
            new_rec.append(item)
        else:
            new_pot.append(item)

    report["recommended_standards"] = new_rec
    report["potentially_applicable_standards"] = new_pot

    applicable_nums = {normalize_standard_number(item.get("standard_number", "")) for item in (new_rec + new_pot)}

    seen_ex = set()
    clean_ex = []
    for ex in ex_list:
        num = normalize_standard_number(ex.get("standard_number", ""))
        if num not in seen_ex and num not in applicable_nums:
            seen_ex.add(num)
            clean_ex.append(ensure_item_provenance_and_scope(ex))
    report["excluded_standards"] = clean_ex

    # Enforce provenance & scope_label on standards_requiring_verification and related_standards
    report["standards_requiring_verification"] = [
        ensure_item_provenance_and_scope(item) for item in report.get("standards_requiring_verification", [])
    ]
    report["related_standards"] = [
        ensure_item_provenance_and_scope(item) for item in report.get("related_standards", [])
    ]

    # Enforce QCO Verification rules on certification guidance
    cert_guidance = report.get("certification_guidance", [])
    for cert in cert_guidance:
        has_full_qco = bool(
            cert.get("notification_number") and
            cert.get("issuing_authority") and
            cert.get("effective_date") and
            cert.get("scope_or_exclusions") and
            cert.get("relevant_is_number") and
            cert.get("product_category") and
            cert.get("verification_status") == "Verified"
        )
        if not has_full_qco:
            cert["explanation"] = UNSUPPORTED_QCO_EXPLANATION
            cert["evidence_text"] = UNSUPPORTED_QCO_EXPLANATION
            cert["applicability"] = "Verification Required"
            cert["verification_status"] = "Verification Required"
            cert["source_url"] = None
            cert["source_url_label"] = "Official BIS catalogue link for manual verification."

        src_type = "Official Document Record" if has_full_qco else "Local Metadata Index"
        cert["source_type"] = src_type
        cert["source"] = "Official Gazette Notification" if has_full_qco else "Local BIS Catalogue"
        cert["source_url"] = cert.get("source_url") if (has_full_qco and cert.get("source_url")) else None
        cert["source_url_label"] = "Official verified document link." if has_full_qco else "Official BIS catalogue link for manual verification."
        cert["source_document"] = cert.get("notification_number") or cert.get("source_document") or "Local Catalogue Record"
        cert["page_or_clause"] = cert.get("page_or_clause") or "Clause verification required"
        cert["retrieved_at"] = cert.get("retrieved_at") or datetime.now(timezone.utc).isoformat()
        cert["provenance"] = {
            "source_type": src_type,
            "source": cert["source"],
            "source_url": cert["source_url"],
            "source_url_label": cert["source_url_label"],
            "source_document": cert["source_document"],
            "page_or_clause": cert["page_or_clause"],
            "evidence_text": cert["explanation"],
            "retrieved_at": cert["retrieved_at"],
            "verification_status": cert["verification_status"]
        }

    missing_inputs = report.get("missing_requirements", [])
    if not missing_inputs or len(missing_inputs) < 2:
        missing_inputs = [
            "Pressure rating (PN rating / working pressure)",
            "Nominal pipe outer diameter and wall thickness / SDR classification",
            "Material resin grade (PE 63 / PE 80 / PE 100)"
        ]

    report["evidence_summary"] = {
        "claims_supported_by_metadata": [
            "Candidate standards identified via vector similarity search over local BIS catalog index.",
            "Domain compatibility confirmed from local taxonomy mapping.",
            "Product material and application identified in catalogue metadata."
        ],
        "claims_supported_by_indexed_metadata": [
            "Candidate standards identified via vector similarity search over local BIS catalog index.",
            "Domain compatibility confirmed from local taxonomy mapping.",
            "Product material and application identified in catalogue metadata."
        ],
        "claims_requiring_official_document_verification": [
            "Verbatim standard scope and technical clauses require verification against official BIS standard documents.",
            "Revision history, reaffirmed status, and active amendment details require confirmation from official BIS catalogue."
        ],
        "missing_procurement_inputs": missing_inputs,
        "certification_and_regulatory_items": [
            "Mandatory BIS certification (ISI mark) and Quality Control Order (QCO) applicability requires verification from official Gazette notifications.",
            "Municipal water authority specifications and local tender compliance requirements require independent verification."
        ],
        "certification_and_regulatory_items_requiring_verification": [
            "Mandatory BIS certification (ISI mark) and Quality Control Order (QCO) applicability requires verification from official Gazette notifications.",
            "Municipal water authority specifications and local tender compliance requirements require independent verification."
        ]
    }

    has_matches = bool(new_rec or new_pot)
    if not has_matches:
        report["overall_status"] = "No Applicable Standard Confirmed"
        report["notice"] = "No potentially applicable Indian Standards were identified from the available standards database for this procurement description."
    elif not new_rec:
        report["overall_status"] = "Analysis Completed – Verification Required"

    return report
