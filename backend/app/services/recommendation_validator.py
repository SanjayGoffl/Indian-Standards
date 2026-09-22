"""
Recommendation Validator Module.
Provides deterministic technical compatibility validation, Field Comparison Matrix generation,
explainable score calculation, core/sheath insulation disambiguation, domain category filtering,
dynamic exclusion reason construction, and post-analysis report sanitization.
"""

import re
import logging
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

UNVERIFIED_REVISION_TEXT = (
    "Verification required from the official BIS standard document."
)


def get_safe_cert_explanation(product_category: str = "") -> str:
    """
    Returns product-specific certification guidance text with zero cable terms for non-cable products.
    """
    cat_lower = (product_category or "").lower()
    if any(w in cat_lower for w in ["glove", "gloves", "hand protection"]):
        return (
            "No mandatory BIS certification requirement or Quality Control Order was confirmed from the available local database for this product description.\n\n"
            "This result is not a legal determination. Applicability must be verified using the latest official BIS product scope, applicable Quality Control Orders, tender conditions, and relevant occupational safety requirements."
        )
    elif any(w in cat_lower for w in ["cable", "wire", "conductor", "electrical"]):
        return UNVERIFIED_CERT_TEXT
    elif any(w in cat_lower for w in ["thermal insulation", "insulation padding", "turbine insulation"]):
        return (
            "No mandatory BIS certification requirement or Quality Control Order was confirmed from the available local database for this product description.\n\n"
            "This result is not a legal determination. Applicability must be verified using the latest official BIS product scope, tender conditions, and relevant high-temperature equipment safety specifications."
        )
    elif any(w in cat_lower for w in ["pipe", "hdpe"]):
        return (
            "HDPE pipes for potable water supply are subject to Quality Control Orders (QCO) issued by the Department of Chemicals and Petrochemicals.\n\n"
            "Applicability must be verified against official BIS product scope, pipe pressure rating (PN rating), and municipal water authority standards."
        )
    elif any(w in cat_lower for w in ["helmet"]):
        return (
            "Industrial safety helmets are covered under Personal Protective Equipment (Quality Control) Order. Mandatory BIS ISI mark certification applies.\n\n"
            "Applicability must be verified using the official BIS scope for IS 2925 and purchaser specifications."
        )
    else:
        return (
            "No mandatory BIS certification requirement or Quality Control Order was confirmed from the available local database for this product description.\n\n"
            "This result is not a legal determination. Applicability must be verified using the latest official BIS product scope, applicable Quality Control Orders, tender conditions, and relevant safety requirements."
        )


def build_dynamic_exclusion_reason(candidate_title: str, candidate_category: str, target_category: str) -> str:
    """
    Generates dynamic, accurate product scope mismatch reasons derived from the actual candidate standard title/category
    and the requested procurement product category.
    """
    t_cat = (target_category or "the requested product").strip()
    c_title = (candidate_title or "").strip()
    c_title_lower = c_title.lower()

    if "steel" in c_title_lower or "deformed" in c_title_lower or "reinforcement" in c_title_lower:
        scope_desc = "steel reinforcement bars and wires for concrete structures"
    elif "respiratory" in c_title_lower or "breathing apparatus" in c_title_lower:
        scope_desc = "respiratory protective equipment and breathing apparatus"
    elif "helmet" in c_title_lower or "head protection" in c_title_lower:
        scope_desc = "industrial safety helmets for head protection"
    elif "cable" in c_title_lower or "conductor" in c_title_lower or "electric" in c_title_lower:
        scope_desc = "electrical wires and power cables"
    elif "pipe" in c_title_lower or "hdpe" in c_title_lower:
        scope_desc = "HDPE piping systems for water supplies and effluents"
    elif "photovoltaic" in c_title_lower or "solar" in c_title_lower:
        scope_desc = "terrestrial photovoltaic (PV) solar modules"
    elif "information technology" in c_title_lower or "it equipment" in c_title_lower:
        scope_desc = "information technology equipment safety"
    elif "drinking water" in c_title_lower:
        scope_desc = "drinking water quality specifications"
    elif "concrete" in c_title_lower:
        scope_desc = "plain and reinforced concrete structural design"
    elif c_title:
        scope_desc = c_title
    else:
        scope_desc = candidate_category or "unrelated equipment"

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


def validate_product_category(candidate_category: str, candidate_title: str, target_category: str) -> Tuple[bool, str]:
    """
    Validates whether candidate standard aligns with procurement target domain.
    Enforces strict negative keyword exclusion rules for cross-domain standards.
    """
    if not target_category:
        return True, "Domain scope aligned."

    t_cat = target_category.lower().strip()
    c_cat = (candidate_category or "").lower().strip()
    c_title = (candidate_title or "").lower().strip()

    is_cable_target = any(w in t_cat for w in ["cable", "wire", "conductor", "electrical"])
    is_solar_target = any(w in t_cat for w in ["solar", "photovoltaic", "pv module"])
    is_pipe_target = any(w in t_cat for w in ["pipe", "hdpe", "water supply", "effluent"])
    is_steel_target = any(w in t_cat for w in ["steel", "rebar", "reinforcement", "concrete bar"])
    is_it_target = any(w in t_cat for w in ["it ", "information technology", "computer", "server"])
    is_thermal_target = any(w in t_cat for w in ["thermal insulation", "insulation padding", "turbine insulation", "high-temperature insulation"])
    is_gloves_target = any(w in t_cat for w in ["glove", "gloves", "hand protection"])
    is_helmet_target = any(w in t_cat for w in ["helmet", "head protection"])

    # 1. Gloves Target
    if is_gloves_target:
        if any(w in c_title or w in c_cat for w in ["respiratory", "breathing apparatus", "helmet", "cable", "wire", "conductor", "pipe", "hdpe", "information technology", "steel", "concrete", "photovoltaic", "solar", "drinking water"]):
            reason = build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category)
            return False, reason
        if any(w in c_cat or w in c_title for w in ["glove", "gloves", "hand protection"]):
            return True, "Domain scope aligned with Industrial Safety Gloves."
        return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category)

    # 2. Cable Target
    elif is_cable_target:
        if any(w in c_title or w in c_cat for w in ["photovoltaic", "solar", "pipe", "hdpe", "steel", "rebar", "concrete", "drinking water", "helmet", "respiratory", "information technology"]):
            return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category)
        if any(w in c_cat or w in c_title for w in ["cable", "wire", "electric", "conductor", "power"]):
            return True, "Domain scope aligned with Electrical Cables."
        return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category)

    # 3. Solar Target
    elif is_solar_target:
        if any(w in c_title or w in c_cat for w in ["pipe", "steel", "cable", "helmet", "drinking water", "glove", "respiratory"]):
            return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category)
        if "photovoltaic" in c_cat or "solar" in c_cat or "photovoltaic" in c_title:
            return True, "Domain scope aligned with Solar PV."
        return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category)

    # 4. Pipe Target
    elif is_pipe_target:
        if any(w in c_title or w in c_cat for w in ["solar", "cable", "steel", "helmet", "glove", "respiratory"]):
            return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category)
        if "pipe" in c_cat or "pipe" in c_title or "hdpe" in c_title:
            return True, "Domain scope aligned with Pipes & Water."
        return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category)

    # 5. Steel Target
    elif is_steel_target:
        if any(w in c_title or w in c_cat for w in ["solar", "pipe", "cable", "helmet", "drinking water", "glove", "respiratory"]):
            return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category)
        if "steel" in c_cat or "steel" in c_title or "rebar" in c_title or "reinforcement" in c_title:
            return True, "Domain scope aligned with Reinforcement Steel."
        return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category)

    # 6. IT Target
    elif is_it_target:
        if any(w in c_title or w in c_cat for w in ["pipe", "steel", "cable", "solar", "concrete", "helmet", "glove"]):
            return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category)
        if "it & electronics" in c_cat or "information technology" in c_title:
            return True, "Domain scope aligned with IT Equipment."
        return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category)

    # 7. Thermal Target
    elif is_thermal_target:
        if any(w in c_title or w in c_cat for w in ["cable", "wire", "electric", "solar", "pipe", "steel", "concrete", "helmet", "respiratory", "drinking water", "information technology"]):
            return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category)
        if "thermal insulation" in c_cat or "thermal insulation" in c_title or "insulation padding" in c_title:
            return True, "Domain scope aligned with Thermal Insulation."
        return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category)

    # 8. Helmet Target
    elif is_helmet_target:
        if any(w in c_title or w in c_cat for w in ["cable", "pipe", "steel", "solar", "respiratory", "glove"]):
            return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category)
        if "helmet" in c_title or "head protection" in c_title:
            return True, "Domain scope aligned with Industrial Safety Helmets."
        return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category)

    # General domain fallback
    t_words = [w for w in t_cat.split() if len(w) > 3]
    if t_words:
        if any(w in c_cat or w in c_title for w in t_words):
            return True, "Domain scope aligned."
        else:
            return False, build_dynamic_exclusion_reason(candidate_title, candidate_category, target_category)

    return True, "Domain scope aligned."


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
            return "Match", core_provision, outer_sheath_provision
        elif core_provision == "XLPE":
            return "Mismatch", f"Primary Core Insulation is {core_provision} (Outer Sheath is {outer_sheath_provision})", outer_sheath_provision
        else:
            return "Unknown", core_provision, outer_sheath_provision

    if req_core == "XLPE":
        if core_provision == "XLPE":
            return "Match", core_provision, outer_sheath_provision
        elif core_provision == "PVC":
            return "Mismatch", f"Primary Core Insulation is {core_provision}", outer_sheath_provision

    return "Unknown", core_provision, outer_sheath_provision


def generate_field_comparison_matrix(candidate: IndianStandard, extracted_reqs: List[Dict[str, Any]], target_category: str) -> List[Dict[str, Any]]:
    """
    Generates product-specific Field Comparison Matrix for candidate standard against extracted requirements.
    Matrix items: Parameter, Required Value, Standard Provision, Result (Match / Mismatch / Unknown / Not Applicable / No Match / Not Mentioned)
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
    is_pipe = any(w in t_cat_lower for w in ["pipe", "hdpe"])
    is_helmet = any(w in t_cat_lower for w in ["helmet"])

    # 1. Product Category
    is_domain_match, domain_msg = validate_product_category(c_cat, c_title, target_category)
    matrix.append({
        "parameter": "Product Category",
        "required_value": target_category or "General Procurement",
        "standard_provision": c_cat or c_title[:60],
        "result": "Match" if is_domain_match else "Not Applicable"
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
        mat_res = "Match" if (is_domain_match and mat_prov == "Covered") else "Not Mentioned"
        matrix.append({
            "parameter": "Glove Material",
            "required_value": glove_mat,
            "standard_provision": mat_prov,
            "result": mat_res
        })

        chem_prov = "Chemical resistance specified" if "chemical" in comb_text else "Not Covered"
        chem_res_result = "Match" if (is_domain_match and "chemical" in comb_text) else ("No Match" if chem_res == "Required" else "Not Mentioned")
        matrix.append({
            "parameter": "Chemical Resistance",
            "required_value": chem_res,
            "standard_provision": chem_prov,
            "result": chem_res_result
        })

        reus_prov = "Reusable PPE" if "reusable" in comb_text else "Not Covered"
        reus_result = "Match" if (is_domain_match and "reusable" in comb_text) else "Not Mentioned"
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
                v_res = "Match"
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
            c_res = "Match"
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
            f_res = "Match"
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
            t_res = "Partial Match"
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

    else:
        for req in extracted_reqs[:5]:
            p_name = req.get("parameter") or req.get("category") or "Requirement"
            v_val = req.get("value_spec") or "Required"
            p_lower = p_name.lower()
            res = "Match" if (is_domain_match and p_lower in comb_text) else "Unknown"
            matrix.append({
                "parameter": p_name,
                "required_value": v_val,
                "standard_provision": "Refer to official standard document" if res == "Match" else "Not Covered",
                "result": res
            })
        return matrix


def calculate_technical_match_score(matrix: List[Dict[str, Any]]) -> Tuple[float, str]:
    """
    Calculates explainable score (0.0 to 1.0) and match strength label based on Field Comparison Matrix.
    """
    domain_item = next((item for item in matrix if item["parameter"] == "Product Category"), None)
    if domain_item and domain_item["result"] in ["Mismatch", "Not Applicable"]:
        return 0.0, "Mismatch"

    matches = sum(1 for item in matrix if item["result"] == "Match")
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


def sanitize_and_validate_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Final validation check before displaying or returning report.
    Rejects leaked electrical fields, fixes applicability text, scrubs certification text,
    and adjusts overall status if needed.
    """
    cat = (report.get("product_category") or "").lower()
    is_cable = any(w in cat for w in ["cable", "wire", "conductor"])
    is_gloves = any(w in cat for w in ["glove", "gloves", "hand protection"])

    cable_param_names = {"core insulation", "pvc cable insulation", "voltage rating", "conductor material", "frls requirement", "high voltage test", "cable type", "working voltage"}

    if not is_cable:
        cleaned_reqs = []
        for req in report.get("extracted_requirements", []):
            param = (req.get("parameter") or "").lower()
            if param in cable_param_names:
                continue
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
        title_lower = (item.get("title") or "").lower()
        cat_lower = (item.get("category") or "").lower()
        std_num = item.get("standard_number") or ""

        # Validate domain alignment for non-cable categories
        is_match, reason = validate_product_category(item.get("category", ""), item.get("title", ""), report.get("product_category", ""))
        if not is_match:
            ex_list.append({
                "standard_number": std_num,
                "title": item.get("title"),
                "category": item.get("category") or "Unspecified Category",
                "retrieved_because": "Retrieved via vector similarity search",
                "mismatch_type": "Product Category Mismatch",
                "exclusion_reason": reason,
                "evidence_source": "BIS Standards Catalogue"
            })
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

        if item in rec_list:
            new_rec.append(item)
        else:
            new_pot.append(item)

    report["recommended_standards"] = new_rec
    report["potentially_applicable_standards"] = new_pot

    seen_ex = set()
    clean_ex = []
    for ex in ex_list:
        num = normalize_standard_number(ex.get("standard_number", ""))
        if num not in seen_ex:
            seen_ex.add(num)
            clean_ex.append(ex)
    report["excluded_standards"] = clean_ex

    cert_guidance = report.get("certification_guidance", [])
    safe_explanation = get_safe_cert_explanation(report.get("product_category", ""))
    for cert in cert_guidance:
        exp = cert.get("explanation", "")
        if any(w in exp.lower() for w in ["cable type", "voltage rating", "frls", "conductor"]):
            cert["explanation"] = safe_explanation
            cert["evidence_text"] = safe_explanation

    has_matches = bool(new_rec or new_pot)
    if not has_matches:
        report["overall_status"] = "No Applicable Standard Confirmed"
        report["notice"] = "No potentially applicable Indian Standards were identified from the available standards database for this procurement description."
    elif not new_rec:
        report["overall_status"] = "Analysis Completed – Verification Required"

    return report
