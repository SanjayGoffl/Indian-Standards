"""
Domain-agnostic compliance engine.

Every run is stateless and derives everything from (a) the current input text, (b) a declarative
domain profile (domain_profiles.py) and (c) BIS catalogue metadata retrieved for this run:

  detect_profile -> extract_schema -> retrieve_candidates -> evaluate_candidates
     (understand)     (ALL explicit      (requirement-aware     (hard gates BEFORE ranking,
                       requirements)       SQL pool)              role separation, buckets)

Buckets are mutually exclusive: PRIMARY, SECONDARY_CONDITIONAL, RELATED, TEST_INSTALLATION, EXCLUDED.
Exclusion reasons are composed only from the candidate's own catalogue title and the requirement
it violates. No LLM is used anywhere in this module.
"""

import re
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.models import IndianStandard
from app.services.domain_profiles import PROFILES

logger = logging.getLogger(__name__)

ROLE_PRIMARY = "PRIMARY"
ROLE_SECONDARY = "SECONDARY_CONDITIONAL"
ROLE_RELATED = "RELATED"
ROLE_TEST_INSTALLATION = "TEST_INSTALLATION"
ROLE_EXCLUDED = "EXCLUDED"

_F = re.I
_VERIFY = "Not stated in BIS catalogue record; official document verification required"

# Document-role patterns valid for every domain; profiles add domain-specific ones.
_GENERIC_ROLES = [
    ("test_method", r"methods?\s+(?:of|for)\s+(?:the\s+)?(?:tests?|testing)|test\s+methods?|\btest\s+of\b|\bfor\s+testing\b"),
    # A "code of practice" is an installation document only when it says so; in other domains
    # (e.g. structural design) a code of practice IS the primary specification.
    ("installation_code", r"installation\s+and\s+maintenance|selection,?\s+handling|\blaying\b|"
                          r"(?:code\s+of\s+practice|guide(?:lines)?)\b.*\b(?:installation|handling|storage|erection)\b|"
                          r"\b(?:installation|handling|storage|erection)\b.*\b(?:code\s+of\s+practice|guide(?:lines)?)\b"),
]
_INSTALL_INTENT = r"install|laying|\blaid\b|buried|underground|erect|commission|fixing|storage|handling"
_ALLIED_POOL_TERMS = ["methods of test", "method of test", "code of practice", "installation and maintenance"]

_QUANTITY = re.compile(
    r"(?<![\w.])(\d+(?:\.\d+)?)\s*(kv|v|volts?|mm2|mm²|sq\.?\s*mm|mm|cm|km|m|kg|bar|mpa|kpa|psi|°\s?c|deg(?:rees?)?\s?c|%|hz|khz|kw|mw|wp|w|ah|mah|amps?|µm|micron|hrs?|hours?|years?|days?|nos|pcs|units?|litres?|liters?|ml)(?![\w])",
    _F)
_IS_REF = re.compile(r"\bIS\s*\d+(?:\s*\(\s*Part\s*[\w/]+\s*\))?(?:\s*:\s*\d{4})?", _F)


def _merge_digit_groups(text: str) -> str:
    """BIS prints large quantities with a thousands space ('1 100 V'); join them before parsing."""
    return re.sub(r"(?<=\d)\s(?=\d{3}\s*(?:kv|v|volts?|mm|cm|m|kg|bar|mpa)\b)", "", text or "", flags=_F)


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _key(s: str) -> str:
    return re.sub(r"[\s-]+", "", s).lower()


def _title_pat(v: Dict[str, Any]) -> str:
    return v.get("title") or v["user"]


# --------------------------------------------------------------------------------------
# understand: profile detection
# --------------------------------------------------------------------------------------

def detect_profile(text: str, hint: str = "") -> Optional[Dict[str, Any]]:
    """Best-scoring profile for THIS input, or None when nothing matches or the top score is tied."""
    blob = f"{text or ''} {hint or ''}"
    scored = []
    for p in PROFILES:
        s = sum(w for pat, w in p["detect"] if re.search(pat, blob, _F))
        if s >= 3:
            scored.append((s, p))
    if not scored:
        return None
    scored.sort(key=lambda x: -x[0])
    if len(scored) > 1 and scored[0][0] - scored[1][0] <= 1:
        return None   # two domains almost equally plausible: genuine ambiguity, do not guess
    return scored[0][1]


def generic_role(title: str) -> Optional[str]:
    """Domain-neutral document role of a catalogue title (test method / installation code)."""
    t = title or ""
    return next((role for role, pat in _GENERIC_ROLES if re.search(pat, t, _F)), None)


# --------------------------------------------------------------------------------------
# extract: ALL explicit requirements
# --------------------------------------------------------------------------------------

def residual_requirements(text: str, taken_spans: Optional[List[Tuple[int, int]]] = None) -> List[Dict[str, str]]:
    """Quantities and cited IS numbers in the input that no attribute captured, kept verbatim."""
    t = _merge_digit_groups(text)
    taken = taken_spans or []
    out = []

    def free(span):
        return not any(span[0] < e and s < span[1] for s, e in taken)

    for m in _QUANTITY.finditer(t):
        if free(m.span()):
            out.append({"category": "Other Specification", "parameter": "Stated Value",
                        "value_spec": _clean(m.group(0)), "source_text": _clean(m.group(0))})
    for m in _IS_REF.finditer(t):
        out.append({"category": "Referenced Standard", "parameter": "Cited Standard",
                    "value_spec": _clean(m.group(0)), "source_text": _clean(m.group(0))})
    return out


def _numeric_values(spec: Dict[str, Any], text: str) -> List[Tuple[float, str, Tuple[int, int]]]:
    found = []
    for m in re.finditer(rf"(\d+(?:\.\d+)?)\s*({spec['unit_re']})\b", text, _F):
        v = float(m.group(1)) * spec.get("scale", {}).get(m.group(2).lower(), 1)
        if spec.get("min", 0) <= v <= spec.get("max", float("inf")):
            found.append((v, m.group(0), m.span()))
    return found


def extract_schema(profile: Dict[str, Any], text: str) -> Dict[str, Any]:
    """Dynamic requirement schema for this input: explicit values with their verbatim source text."""
    t = _merge_digit_groups(text)
    spans: List[Tuple[int, int]] = []
    attrs: Dict[str, Dict[str, Any]] = {}

    for spec in profile["attributes"]:
        kind = spec["kind"]
        if kind in ("enum", "multi"):
            vals, srcs = [], []
            for name, v in spec["values"].items():
                m = re.search(v["user"], t, _F)
                if m:
                    vals.append(name)
                    srcs.append(_clean(m.group(0)))
                    spans.append(m.span())
            if vals:
                attrs[spec["key"]] = {"values": vals, "source_text": srcs, "derived": False}
        elif kind == "token":
            m = re.search(spec["user"], t, _F)
            if m:
                attrs[spec["key"]] = {"values": [_clean(m.group(0))], "source_text": [_clean(m.group(0))], "derived": False}
                spans.append(m.span())
        elif kind == "numeric":
            nums = _numeric_values(spec, t)
            if nums:
                pick = max(nums, key=lambda x: x[0]) if spec.get("pick") == "max" else nums[0]
                attrs[spec["key"]] = {"values": [pick[0]], "source_text": [_clean(pick[1])], "derived": False}
                spans.extend(n[2] for n in nums)

    # Soft constraints derived from explicit ones (never gating, never listed as user requirements).
    for spec in profile["attributes"]:
        if spec["key"] in attrs or not spec.get("infer"):
            continue
        for rule in spec["infer"]:
            src = attrs.get(rule["attr"])
            if src and not src["derived"] and re.search(rule["match"], " | ".join(map(str, src["values"] + src["source_text"])), _F):
                basis = ", ".join(f"{_label(profile, rule['attr'])} '{v}'" for v in src["values"])
                prev = attrs.get(spec["key"])
                attrs[spec["key"]] = {"values": [rule["value"]], "source_text": [], "derived": True,
                                      "basis": f"{prev['basis']}; {basis}" if prev else f"inferred from {basis}"}

    atoms = _atoms(profile, attrs)
    atoms += residual_requirements(text, spans)

    missing = [s["missing_prompt"] for s in profile["attributes"]
               if (s.get("essential") or s.get("ask")) and s["key"] not in attrs and s.get("missing_prompt")]

    return {
        "profile": profile["id"],
        "label": profile["label"],
        "product_type": _product_type(profile, attrs),
        "attributes": attrs,
        "atoms": atoms,
        "missing": missing,
        "requested_domains": [d for d, pat in profile["domains"].items() if re.search(pat, t, _F)],
        "installation_intent": bool(re.search(_INSTALL_INTENT, t, _F)),
    }


def _label(profile: Dict[str, Any], key: str) -> str:
    return next(s["label"] for s in profile["attributes"] if s["key"] == key)


def _atoms(profile: Dict[str, Any], attrs: Dict[str, Dict[str, Any]]) -> List[Dict[str, str]]:
    atoms = []
    for spec in profile["attributes"]:
        a = attrs.get(spec["key"])
        if not a or a["derived"]:
            continue
        vals = [f"{v:g} {spec['canon']}" if spec["kind"] == "numeric" else str(v) for v in a["values"]]
        srcs = a["source_text"]
        if spec.get("join") and len(vals) > 1:
            atoms.append({"category": spec["category"], "parameter": spec["label"],
                          "value_spec": spec["join"].join(vals), "source_text": ", ".join(srcs)})
        else:
            for v, s in zip(vals, srcs):
                atoms.append({"category": spec["category"], "parameter": spec["label"], "value_spec": v, "source_text": s})
    return atoms


def _product_type(profile: Dict[str, Any], attrs: Dict[str, Dict[str, Any]]) -> str:
    """Product phrase built from the user's own explicit words (verbatim source text where declared)."""
    parts = []
    for spec in profile["attributes"]:
        a = attrs.get(spec["key"])
        if a and not a["derived"] and spec.get("type_fmt"):
            if spec.get("type_verbatim"):
                vals = a["source_text"]
            else:
                vals = [f"{v:g}" if spec["kind"] == "numeric" else str(v) for v in a["values"]]
            parts.append(spec["type_fmt"].format(" / ".join(vals)))
    return _clean(" ".join(parts + [profile["label"]]))


def schema_to_extracted_data(profile: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy-compatible extraction dict (same keys the LLM extraction path returns)."""
    product_type = schema["product_type"]
    listed = [f"{a['parameter']}: {a['value_spec']}" for a in schema["atoms"][:8]]
    return {
        "product_category": profile["category"],
        "product_type": product_type,
        "procurement_summary": f"Procurement of {product_type}." + (f" Explicit requirements: {'; '.join(listed)}." if listed else ""),
        "extracted_requirements": schema["atoms"],
        "missing_or_ambiguous_specs": schema["missing"],
    }


# --------------------------------------------------------------------------------------
# retrieve: requirement-aware candidate pool
# --------------------------------------------------------------------------------------

def _user_keywords(text: str) -> List[str]:
    return list({w.lower() for w in re.findall(r"[A-Za-z]{5,}", text or "")})[:12]


def retrieve_candidates(db: Session, profile: Dict[str, Any], schema: Dict[str, Any], text: str) -> List[IndianStandard]:
    """
    Pool = catalogue family (profile nouns) narrowed by the requested attribute values (and, for
    attributes flagged pool_alternatives, their alternatives so near-misses get explicit
    exclusions), plus domain near-misses, allied documents and any IS number the user cited.
    Withdrawn standards are never candidates.
    """
    title = IndianStandard.title
    nouns = or_(*[title.ilike(f"%{n}%") for n in profile["pool_nouns"]])
    base = [IndianStandard.status != "Withdrawn", nouns]

    context: List[str] = []
    for spec in profile["attributes"]:
        if spec["kind"] != "enum":
            continue
        req = schema["attributes"].get(spec["key"])
        if spec.get("pool_alternatives"):
            wanted = list(spec["values"])
        else:
            wanted = req["values"] if req and not req["derived"] else []
        for name in wanted:
            context.extend(spec["values"].get(name, {}).get("pool", []))
    context += profile.get("pool_near_miss", [])

    if profile.get("pool_context_required") and context:
        conds = [title.ilike(f"%{c}%") for c in context] + [title.ilike(f"%{a}%") for a in _ALLIED_POOL_TERMS]
        rows = db.query(IndianStandard).filter(and_(*base, or_(*conds))).all()
    else:
        rows = db.query(IndianStandard).filter(and_(*base)).limit(500).all()
        if profile.get("pool_context_required"):
            kws = _user_keywords(text)
            rows.sort(key=lambda s: -sum(k in (s.title or "").lower() for k in kws))
            rows = rows[:60]

    by_id = {s.id: s for s in rows}
    for num in {m.group(1) for m in re.finditer(r"\bIS\s*(\d+)", text or "", _F)}:
        for s in db.query(IndianStandard).filter(IndianStandard.standard_number.ilike(f"IS {num}%")).limit(50).all():
            if re.match(rf"IS\s*{num}(?!\d)", s.standard_number, _F) and s.status != "Withdrawn":
                by_id[s.id] = s
    return list(by_id.values())


# --------------------------------------------------------------------------------------
# evaluate: metadata parsing, gates, buckets
# --------------------------------------------------------------------------------------

def _role(profile: Dict[str, Any], title: str) -> str:
    for role, pat in _GENERIC_ROLES + list(profile.get("roles", [])):
        if re.search(pat, title, _F):
            return role
    if all(re.search(p, title, _F) for p in profile["product_title"]):
        return "product"
    return "other"


def _range(spec: Dict[str, Any], title: str) -> Optional[Tuple[float, float]]:
    vals = [v for v, _, _ in _numeric_values({**spec, "min": 0, "max": float("inf")}, title)]
    if not vals:
        return None
    if len(vals) >= 2 and re.search(r"\bfrom\b", title, _F):
        return min(vals), max(vals)
    return 0.0, max(vals)


def parse_standard(profile: Dict[str, Any], std: IndianStandard) -> Dict[str, Any]:
    title = _merge_digit_groups(std.title)
    attrs: Dict[str, Any] = {}
    for spec in profile["attributes"]:
        kind = spec["kind"]
        if kind in ("enum", "multi"):
            attrs[spec["key"]] = {n for n, v in spec["values"].items() if re.search(_title_pat(v), title, _F)}
        elif kind == "token":
            attrs[spec["key"]] = {_key(m.group(0)) for m in re.finditer(spec["user"], title, _F)}
        elif kind == "numeric":
            attrs[spec["key"]] = _range(spec, title) if spec.get("title_range") else None
    return {
        "role": _role(profile, title),
        "attrs": attrs,
        "domains": [d for d, pat in profile["domains"].items() if re.search(pat, title, _F)],
        "title": title,
    }


def _fmt_range(spec: Dict[str, Any], rng: Tuple[float, float]) -> str:
    def f(v):
        return f"{v:g} {spec['canon']}"
    lo, hi = rng
    return f"up to {f(hi)}" if lo == 0 else f"{f(lo)} to {f(hi)}"


def _status(spec: Dict[str, Any], req: Optional[Dict[str, Any]], found) -> str:
    """match | mismatch | silent | variant | ignore | info for one attribute of one standard."""
    kind = spec["kind"]
    if req is None:
        return "variant" if (spec.get("variant") and kind == "enum" and found) else "ignore"
    if kind == "multi":
        return "info"
    if kind == "numeric":
        if found is None:
            return "silent"
        return "match" if found[0] <= req["values"][0] <= found[1] else "mismatch"
    if not found:
        return "silent"
    wanted = {_key(str(v)) for v in req["values"]} if kind == "token" else set(req["values"])
    have = {_key(str(v)) for v in found} if kind == "token" else found
    return "match" if wanted & have else "mismatch"


def _exclusion(std: IndianStandard, gate: str, reason: str) -> Dict[str, Any]:
    return {
        "standard_number": std.standard_number,
        "title": std.title,
        "category": std.category or "Unspecified",
        "retrieved_because": "Retrieved from the BIS catalogue as a candidate for the requested product family",
        "mismatch_type": gate,
        "gate": gate,
        "exclusion_reason": reason,
        "evidence_source": std.source_url or std.source or "BIS Standards Reference Catalogue",
        "recommendation_role": ROLE_EXCLUDED,
    }


def _shown(spec: Dict[str, Any], values) -> str:
    return ", ".join(f"{v:g} {spec['canon']}" if spec["kind"] == "numeric" else str(v) for v in values)


def _domain_exclusion(schema, std, meta) -> Optional[Dict[str, Any]]:
    """Title scoped to an application domain the procurement input never mentions."""
    waived = set(schema["requested_domains"])
    for dom in meta["domains"]:
        if dom not in waived:
            return _exclusion(std, "Application Domain Mismatch",
                              f"{std.standard_number} is scoped to {dom} applications per its BIS title ('{std.title}'); "
                              f"the procurement input does not state a {dom} use.")
    return None


def _evaluate_one(profile, schema, std, meta) -> Dict[str, Any]:
    """Gate + caveat evaluation. Returns {"exclusion": rec|None, "caveats": [...], "matches": [...], "statuses": {...}}."""
    num, role = std.standard_number, meta["role"]
    dom_ex = _domain_exclusion(schema, std, meta)
    if dom_ex:
        return {"exclusion": dom_ex}

    caveats, matches, statuses, earned, possible = [], [], {}, 0, 0
    for spec in profile["attributes"]:
        key = spec["key"]
        req = schema["attributes"].get(key)
        found = meta["attrs"].get(key)
        st = _status(spec, req, found)
        statuses[key] = st
        derived = bool(req and req["derived"])
        label = spec["label"]
        weight = spec.get("weight", 3)

        observable = st in ("match", "mismatch") or (st == "silent" and spec.get("on_silent") in ("conditional", "exclude"))
        if req and spec["kind"] != "multi" and role != "test_method" and observable:
            possible += weight
        if st == "match":
            earned += weight
            matches.append((spec, req, found))
        elif st == "mismatch":
            wanted_txt = _shown(spec, req["values"])
            if spec["kind"] == "numeric":
                have_txt = f"{label} {_fmt_range(spec, found)}"
            else:
                have_txt = f"{label} {', '.join(sorted(map(str, found)))}"
            if spec.get("gate") and not derived and role != "test_method":
                return {"exclusion": _exclusion(std, f"{label} Mismatch",
                                                f"{num} covers {have_txt} per its BIS title ('{std.title}'); "
                                                f"the procurement input requires {label} {wanted_txt}.")}
            if derived:
                caveats.append(f"its BIS title states {have_txt}, which conflicts with the {wanted_txt} implied by the input ({req['basis']})")
        elif st == "silent" and role in ("product", "design_reference", "component", "installation_code"):
            mode = spec.get("on_silent", "ignore")
            wanted_txt = _shown(spec, req["values"])
            if mode == "exclude" and not derived and role == "product":
                return {"exclusion": _exclusion(std, f"{label} Not Established",
                                                f"The BIS title for {num} does not state {label}; the procurement input requires {wanted_txt}.")}
            if mode in ("conditional", "exclude") and role == "product":
                basis = f" ({req['basis']})" if derived else ""
                caveats.append(f"its BIS title does not state {label} ({wanted_txt}{basis}), which needs official verification")
        elif st == "variant" and role == "product":
            caveats.append(f"its BIS title is specific to {label} {', '.join(sorted(map(str, found)))}, which the procurement input does not request")

        if role == "product" and req is None and spec.get("essential"):
            caveats.append(f"{label} was not provided in the procurement input")

    return {"exclusion": None, "caveats": caveats, "matches": matches, "statuses": statuses,
            "score": (earned / possible) if possible else 0.5}


def _matrix(profile, schema, std, meta, ev) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []

    def row(param, required, provision, result):
        rows.append({"parameter": param, "required_value": required, "procurement_requirement": required,
                     "standard_provision": provision, "indexed_standard_evidence": provision,
                     "result": result, "evaluation": result})

    row("Product Category", schema["label"], std.category or std.title[:60], "Potential Match")
    for spec in profile["attributes"]:
        req = schema["attributes"].get(spec["key"])
        found = meta["attrs"].get(spec["key"])
        st = ev["statuses"][spec["key"]]
        if req is None:
            if spec.get("essential"):
                row(spec["label"], "Not provided", "Required for detailed comparison", "Missing Input")
            continue
        for v in req["values"]:
            shown = f"{v:g} {spec['canon']}" if spec["kind"] == "numeric" else str(v)
            if req["derived"]:
                shown = f"{shown} ({req['basis']})"
            if spec["kind"] == "numeric" and found is not None:
                prov = f"{spec['label']} {_fmt_range(spec, found)} (BIS title)"
            elif spec["kind"] != "numeric" and found and spec["kind"] != "multi":
                prov = f"{', '.join(sorted(map(str, found)))} (BIS title)"
            else:
                prov = _VERIFY
            result = "Potential Match" if st == "match" else ("Mismatch" if st == "mismatch" else "Requires Official Verification")
            row(spec["label"], shown, prov, result)
    return rows


def _item(std, role, status, score, reasoning, matrix, evidence) -> Dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    verified = getattr(std, "verification_status", "") == "Verified"
    prov = {
        "source": std.source or "Local BIS Catalogue",
        "source_url": std.source_url if (verified and std.source_url) else None,
        "source_document": "Local Catalogue Record",
        "page_or_clause": "Clause verification required",
        "retrieved_at": std.retrieved_at or now_iso,
        "verification_status": "Verification Required",
    }
    strength = "High" if score >= 0.75 else ("Medium" if score >= 0.5 else "Low")
    return {
        "standard_number": std.standard_number, "title": std.title, "category": std.category,
        "scope": std.scope, "scope_summary": std.scope,
        "scope_label": "Scope summary from local catalogue — official document verification required.",
        "applicability_status": status, "recommendation_role": role, "engine_verified": True,
        "internal_match_score": round(min(score, 1.0), 2), "match_strength": strength,
        "field_comparison_matrix": matrix, "reasoning": reasoning,
        "latest_revision": std.revision or "Revision and amendment status requires verification from official BIS standards catalogue.",
        "revision_verification_status": "Unverified",
        "amendments": [std.amendment_details] if std.amendment_details else [],
        "related_standards": [],
        "evidence": evidence + ([std.evidence_text] if std.evidence_text else []),
        "verification_required": True,
        "source": prov["source"], "source_url": prov["source_url"], "source_document": prov["source_document"],
        "page_or_clause": prov["page_or_clause"], "retrieved_at": prov["retrieved_at"],
        "verification_status": "Verification Required", "provenance": prov,
    }


def _allied_item(std, role, rel_type, matched, description) -> Dict[str, Any]:
    return {
        "standard_number": std.standard_number, "title": std.title, "category": std.category,
        "relationship_type": rel_type, "matched_requirement": matched, "recommendation_role": role,
        "engine_verified": True, "description": description,
        "verification_status": "Catalogue metadata match; official document verification required",
        "source": std.source or "Local BIS Catalogue", "source_url": None,
        "status": std.status,
    }


def evaluate_candidates(profile: Dict[str, Any], schema: Dict[str, Any], candidates: List[IndianStandard]) -> Dict[str, Any]:
    """Gates first, then role separation and buckets. Every standard lands in exactly one bucket (or is dropped as irrelevant)."""
    products, related, test_install, excluded = [], {}, {}, []
    seen = set()

    for std in candidates:
        if std.standard_number in seen:
            continue
        seen.add(std.standard_number)
        meta = parse_standard(profile, std)
        role = meta["role"]
        if role == "other":
            # Unclassifiable title: only a stated foreign application domain is enough to record an exclusion.
            dom_ex = _domain_exclusion(schema, std, meta)
            if dom_ex:
                excluded.append(dom_ex)
            continue

        ev = _evaluate_one(profile, schema, std, meta)
        if ev["exclusion"]:
            excluded.append(ev["exclusion"])
            continue

        if role == "product":
            explicit = [(s, r) for s, r, _ in ev["matches"] if not r["derived"]]
            implied = [(s, r) for s, r, _ in ev["matches"] if r["derived"]]
            evidence = [f"{s['label']} {_shown(s, r['values'])}: matched BIS title '{std.title}'" for s, r in explicit]
            evidence += [f"{s['label']} {_shown(s, r['values'])}: BIS title consistent with constraint {r['basis']}" for s, r in implied]
            matrix = _matrix(profile, schema, std, meta, ev)
            matched_txt = "; ".join(f"{s['label']} {_shown(s, r['values'])}" for s, r in explicit)
            if implied:
                matched_txt += ("; " if matched_txt else "") + "; ".join(
                    f"consistent with {s['label']} {_shown(s, r['values'])} ({r['basis']})" for s, r in implied)
            score = ev["score"]
            if ev["caveats"]:
                reasoning = ("Potentially applicable because the standard addresses " + schema["product_type"]
                             + (f" and its BIS title matches {matched_txt}" if matched_txt else "")
                             + "; conditions: " + "; ".join(ev["caveats"]) + ". Final applicability requires confirmation against the official standard.")
                products.append(_item(std, ROLE_SECONDARY, "Potentially Applicable", score, reasoning, matrix, evidence))
            else:
                reasoning = (f"BIS title matches the requested {matched_txt}." if matched_txt
                             else f"BIS title addresses the requested {schema['label']}; no further title-level constraints to compare.")
                products.append(_item(std, ROLE_PRIMARY, "Recommended", score, reasoning, matrix, evidence))
            continue

        if role == "test_method":
            for spec in profile["attributes"]:
                req = schema["attributes"].get(spec["key"])
                if not req or req["derived"] or "values" not in spec:
                    continue
                for name in req["values"]:
                    allied = spec["values"].get(name, {}).get("allied")
                    if allied and re.search(allied, meta["title"], _F):
                        rec = test_install.setdefault(std.standard_number, _allied_item(
                            std, ROLE_TEST_INSTALLATION, "test_method", "", "Test method matching a requested requirement (BIS title)."))
                        rec["matched_requirement"] = f"{rec['matched_requirement']}; {name}" if rec["matched_requirement"] else name
        elif role == "installation_code":
            tied = any(r and not r["derived"] for _, r, _ in ev["matches"])   # positively tied to the request by title metadata
            if tied and (schema["installation_intent"] or "installation" in schema["attributes"]):
                test_install[std.standard_number] = _allied_item(
                    std, ROLE_TEST_INSTALLATION, "installation", schema["label"],
                    "Installation / practice document (BIS title); not a product specification.")
        else:  # design_reference, component and other profile-defined allied roles
            established = [(s, r) for s, r, _ in ev["matches"] if r and not r["derived"]]
            conflicts_soft = any(c for c in ev["caveats"])
            if established and not conflicts_soft:
                related[std.standard_number] = _allied_item(
                    std, ROLE_RELATED, role, "; ".join(f"{s['label']} {_shown(s, r['values'])}" for s, r in established),
                    "Allied document whose BIS title matches the requested attributes; a supporting reference, not the product specification.")

    products.sort(key=lambda i: (i["recommendation_role"] != ROLE_PRIMARY, -i["internal_match_score"], i["standard_number"]))
    return {"products": products, "related": list(related.values()),
            "test_installation": list(test_install.values()), "excluded": excluded}
