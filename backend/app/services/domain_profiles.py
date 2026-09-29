"""
Domain profiles: DATA ONLY. The compliance engine (compliance_engine.py) is domain-agnostic and
interprets these declarations; adding a domain means adding a profile here, never engine code.

Profile fields
  id, label, category      identity; `category` is used only when the caller gives no category hint
  detect                   [(regex, weight)] scored against input text + category hint
  product_title            [regex, ...] ALL must match a catalogue title for it to be a product spec
  roles                    [(role, regex)] extra document-role patterns (checked before product)
  domains                  {label: regex} application domains that make a title ineligible unless
                           the procurement input itself mentions them
  pool_nouns               catalogue-title substrings (any) that define the candidate family
  pool_near_miss           extra title substrings pulled in so near-misses get explicit exclusions
  pool_context_required    restrict the pool using attribute `pool` terms (families with big catalogues)
  attributes               requirement dimensions (see below)

Attribute fields
  key, label, category, kind   kind: enum | multi | token | numeric
  values {name: {user, title, allied, pool}}   enum/multi vocab: `user` regex on procurement text,
                               `title` regex on catalogue titles (defaults to `user`), `allied`
                               regex on test-method/allied titles that verify this requirement,
                               `pool` catalogue substrings used for retrieval
  user / title                 token kind regexes
  unit_re, scale, canon, min, max, pick, title_range   numeric kind
  gate         hard-exclude when the title states a different value than explicitly required
  on_silent    ignore | conditional | exclude   when the title does not state the attribute
  variant      title-specific value that the input never requested -> conditional
  essential    missing input keeps a standard out of PRIMARY and adds a "Missing Input" matrix row
  ask          reported under missing requirements when absent (does not block PRIMARY)
  infer        [{attr, match, value}] derive a soft (never gating) constraint from other attributes
  join         merge multi-values into one extracted requirement ("+", "/")
  type_fmt     how the value contributes to the product type string
  pool_alternatives   pull in alternative values' titles too (near-miss visibility)
"""

_PRE = r"(?<![\w.])"


def _v(user, title=None, allied=None, pool=None):
    return {"user": user, "title": title, "allied": allied, "pool": pool or []}


POWER_CABLE = {
    "id": "power_cable",
    "label": "power cable",
    "category": "Electrical Wires & Power Cables",
    "detect": [(r"\bcables?\b", 3), (r"\bwires?\b|\bwiring\b", 1)],
    "product_title": [r"cables?", r"insulated|sheathed"],
    "roles": [
        ("design_reference", r"recommended\s+(?:short[\s-]*circuit\s+|current\s+)?ratings?"),
        ("component", r"insulation\s+and\s+sheath|insulating\s+and\s+sheathing|conductors?\s+for|\bpipes?\b|\bducts?\b|glands?|fittings|lifters|castables|fictitious\s+calculation"),
    ],
    "domains": {
        "shipboard/offshore": r"\bships?\b|shipboard|offshore|marine|naval|shipbuilding",
        "mining": r"\bmines?\b|\bmining\b",
        "lift/flexible": r"\blifts?\b|flexible\s+(?:cables?|cords?|connections?)|trailing",
        "telecom/data": r"telecom\w*|telephone|optical|coaxial|radio[\s-]*frequency|ribbon|\bdata\b",
        "aerial/overhead": r"aerial|overhead",
        "rolling-stock/automotive": r"railway|rolling\s+stock|automotive|aircraft|welding",
        "submersible": r"submersible|\bpumps?\b",
    },
    "pool_nouns": ["cable"],
    "pool_near_miss": ["ship", "offshore", "marine"],
    "pool_context_required": True,
    "attributes": [
        {"key": "conductor", "label": "Conductor Material", "category": "Conductor", "kind": "enum",
         "gate": True, "on_silent": "ignore", "type_fmt": "{}",
         "values": {"Copper": _v(r"\bcopper\b|\bcu\b", r"copper"),
                    "Aluminium": _v(r"alumin(?:i)?um", r"alumin(?:i)?um")}},
        {"key": "insulation", "label": "Core Insulation", "category": "Base Insulation", "kind": "enum",
         "gate": True, "on_silent": "exclude", "variant": True, "essential": True, "pool_alternatives": True,
         "type_fmt": "{} insulated", "missing_prompt": "Core insulation material (PVC / XLPE / elastomer)",
         "values": {
             "PVC": _v(r"pvc[\s-]*insulat|polyvinyl chloride[\s-]*insulat|insulat\w*(?:\s*:\s*|\s+with\s+|\s+of\s+)pvc|pvc\s*/\s*pvc|pvc\s+insulation",
                       r"pvc[\s-]*insulat|polyvinyl chloride[\s-]*insulat|pvc\s+insulation",
                       allied=r"thermal\s+stability\s+of\s+pvc", pool=["pvc", "polyvinyl"]),
             "XLPE": _v(r"xlpe|cross[\s-]*linked\s+polyethylene", r"xlpe|cross[\s-]*linked\s+polyethylene[\s-]*insulat",
                        pool=["xlpe", "cross%linked", "crosslinked"]),
             "Elastomer": _v(r"elastomer\w*[\s-]*insulat|rubber[\s-]*insulat|\bepr\b|\bhofr\b",
                             r"elastomer\w*[\s-]*insulat|rubber[\s-]*insulat|elastomeric\s+insulation",
                             pool=["elastomer", "rubber"]),
         }},
        {"key": "sheath", "label": "Outer Sheath", "category": "Outer Sheath", "kind": "enum",
         "gate": True, "on_silent": "ignore", "type_fmt": "{} sheathed", "ask": True,
         "missing_prompt": "Outer sheath material (e.g., PVC Type ST1/ST2, Polyethylene, Polyolefin)",
         "values": {"PVC": _v(r"pvc[\s-]*sheath|sheath\w*(?:\s*:\s*|\s+with\s+|\s+of\s+)pvc|pvc\s*/\s*pvc", r"pvc\s*sheath"),
                    "Polyethylene": _v(r"\bpe[\s-]*sheath|polyethylene[\s-]*sheath", r"polyethylene\s+sheath|\bpe\s+sheath")}},
        {"key": "voltage", "label": "Working Voltage", "category": "Voltage Rating", "kind": "numeric",
         "unit_re": r"kv|volts?|v", "scale": {"kv": 1000}, "canon": "V", "min": 100, "max": 1_000_000,
         "pick": "max", "title_range": True, "gate": True, "on_silent": "conditional", "essential": True,
         "type_fmt": "({} V)", "missing_prompt": "Working Voltage rating (e.g., 1100 V)"},
        {"key": "core_configuration", "label": "Core Configuration", "category": "Cable Type", "kind": "multi", "join": " + ",
         "values": {"single-core": _v(r"single[\s-]*core"), "multicore": _v(r"multi[\s-]*core")}},
        {"key": "core_count", "label": "Core Count", "category": "Cable Type", "kind": "token", "ask": True,
         "user": r"\d+(?:\.\d+)?\s*(?:core|c)\b", "missing_prompt": "Number of cores (e.g., 3.5 core, 4 core)"},
        {"key": "size", "label": "Conductor Size", "category": "Conductor", "kind": "token", "ask": True,
         "user": r"\d+(?:\.\d+)?\s*(?:sq\.?\s*mm|mm2|mm²)",
         "missing_prompt": "Cable size or conductor cross-sectional area (e.g., 1.5 sq mm to 400 sq mm)"},
        {"key": "armouring", "label": "Armouring", "category": "Construction", "kind": "enum", "ask": True,
         "missing_prompt": "Armouring type (armoured / unarmoured; wire or strip)",
         "values": {"Unarmoured": _v(r"un[\s-]?armou?red"), "Armoured": _v(r"(?<!un)(?<!un-)armou?red")}},
        {"key": "installation", "label": "Laying Environment", "category": "Installation", "kind": "multi", "join": " / ",
         "values": {"underground": _v(r"underground|buried|direct[\s-]*burial|trench|\bducts?\b"),
                    "outdoor": _v(r"outdoor|open[\s-]*air"),
                    "indoor": _v(r"\bindoor\b")}},
        {"key": "fire", "label": "Flame/Smoke Requirement", "category": "Additional Insulation Requirement", "kind": "multi",
         "ask": True, "missing_prompt": "Fire-performance requirement (FRLS / LSZH / none)",
         "values": {"FRLS": _v(r"frls|flame[\s-]*retardant\s+low[\s-]*smoke", allied=r"flame\s+retardant\s+test|smoke\s+density"),
                    "LSZH": _v(r"lszh|low[\s-]*smoke\s+zero[\s-]*halogen|halogen[\s-]*free")}},
        {"key": "protection", "label": "Protection", "category": "Additional Property", "kind": "multi",
         "values": {"moisture resistance": _v(r"moisture|water[\s-]*(?:resist|proof|tight|ingress|absorption)|\bdamp",
                                              allied=r"water\s+absorption"),
                    "mechanical protection": _v(r"mechanical\s+protect|protect\w*\s+(?:against|from)\s+mechanical|rodent|crush|mechanical\s+(?:damage|strength|stress)",
                                                allied=r"heavy\s+duty\s+sheath")}},
        {"key": "duty", "label": "Duty Class", "category": "Construction", "kind": "enum",
         "gate": True, "on_silent": "conditional", "weight": 2,
         "infer": [{"attr": "installation", "match": r"underground", "value": "Heavy duty"},
                   {"attr": "protection", "match": r"mechanical protection", "value": "Heavy duty"}],
         "values": {"Heavy duty": _v(r"heavy[\s-]*duty"), "Light duty": _v(r"light[\s-]*duty")}},
        {"key": "tests", "label": "Test", "category": "Required Test", "kind": "multi",
         "values": {"conductor resistance": _v(r"conductor\s+resistance", allied=r"conductor\s+resistance"),
                    "insulation resistance": _v(r"insulation\s+resistance", allied=r"insulation\s+resistance"),
                    "high voltage / withstand": _v(r"\bhv\b|high[\s-]*voltage|withstand|dielectric|voltage\s+test|hipot",
                                                   allied=r"high\s+voltage\s+test"),
                    "dimensional": _v(r"dimension|thickness", allied=r"thickness\s+of\s+thermoplastic")}},
    ],
}

PLASTIC_PIPE = {
    "id": "plastic_pipe",
    "label": "pipes",
    "category": "Pipes & Water Management",
    "detect": [(r"\bpipes?\b|\bpiping\b", 3), (r"hdpe|polyethylene|\bu?pvc\b", 1)],
    "product_title": [r"\bpipes?\b"],
    "roles": [("component", r"fittings|joints?\b|couplings?|electrofusion")],
    "domains": {
        "gaseous fuel": r"gaseous\s+fuels?|\bgas\b",
        "irrigation": r"irrigation|sprinkler|lateral",
        "composite/multilayer": r"composite|aluminium",
        "telecommunication": r"telecom\w*",
    },
    "pool_nouns": ["pipe"],
    "pool_context_required": True,
    "attributes": [
        {"key": "material", "label": "Pipe Material", "category": "Material", "kind": "enum", "gate": True,
         "on_silent": "exclude", "type_fmt": "{}", "type_verbatim": True,
         "values": {"Polyethylene": _v(r"hdpe|mdpe|ldpe|polyethylene|\bpe[\s-]*(?:63|80|100)\b|\bpe\b",
                                       r"polyethylene|hdpe|\bpe\b", pool=["polyethylene", "hdpe"]),
                    "PVC": _v(r"\bu?pvc\b|polyvinyl\s+chloride", r"\bu?pvc\b|polyvinyl\s+chloride|unplasticized", pool=["pvc", "polyvinyl"]),
                    "Steel/Iron": _v(r"\bsteel\b|\biron\b|\bdi\b|\bgi\b", r"\bsteel\b|\biron\b"),
                    "Concrete/Cement": _v(r"concrete|\bcement\b|asbestos", r"concrete|\bcement\b|asbestos"),
                    "Stoneware/Clay": _v(r"stoneware|\bclay\b", r"stoneware|\bclay\b")}},
        {"key": "application", "label": "Intended Use", "category": "Application", "kind": "enum", "gate": True,
         "on_silent": "conditional",
         "values": {"potable water": _v(r"potable|drinking|water\s+(?:supply|distribution|conveyance)|municipal\s+water",
                                        r"potable|drinking|water\s+supplies|water\s+supply"),
                    "sewerage": _v(r"sewage|sewerage|sewer|drainage", r"sewage|sewerage|sewer"),
                    "industrial effluent": _v(r"effluents?|industrial\s+waste|plant\s+waste", r"effluents?"),
                    "gas": _v(r"\bgas\b|gaseous", r"gaseous|\bgas\b"),
                    "irrigation": _v(r"irrigation|sprinkler", r"irrigation|sprinkler")}},
        {"key": "grade", "label": "Material Grade", "category": "Material", "kind": "token", "ask": True,
         "user": r"\bpe[\s-]*(?:63|80|100)(?:rc)?\b", "missing_prompt": "HDPE pipe resin grade (PE 63, PE 80, PE 100)"},
        {"key": "pressure", "label": "Pressure Rating", "category": "Performance", "kind": "token", "essential": True,
         "user": r"\bpn[\s-]*\d+(?:\.\d+)?\b|\d+(?:\.\d+)?\s*(?:bar|mpa|kgf/cm2)\b",
         "missing_prompt": "Pressure rating (PN rating / working pressure)"},
        {"key": "diameter", "label": "Pipe Diameter", "category": "Dimensions", "kind": "token", "essential": True,
         "user": r"\bdn[\s-]*\d+\b|\d+(?:\.\d+)?\s*mm\b",
         "missing_prompt": "Nominal pipe outer diameter and wall thickness / SDR classification"},
        {"key": "installation", "label": "Laying Environment", "category": "Installation", "kind": "multi", "join": " / ",
         "values": {"underground": _v(r"underground|buried|trench"), "above ground": _v(r"above[\s-]*ground|exposed")}},
        {"key": "tests", "label": "Test", "category": "Required Test", "kind": "multi",
         "values": {"hydrostatic pressure": _v(r"hydrostatic|hydro[\s-]*test|pressure\s+test", allied=r"hydrostatic|internal\s+pressure"),
                    "melt flow rate": _v(r"\bmfr\b|melt\s+flow", allied=r"melt\s+flow")}},
    ],
}

SAFETY_GLOVES = {
    "id": "safety_gloves",
    "label": "gloves",
    "category": "Industrial Safety Gloves",
    "detect": [(r"\bgloves?\b|\bgauntlets?\b", 3)],
    "product_title": [r"\bgloves?\b"],
    "roles": [],
    "domains": {
        "sports": r"wicket|batting|boxing|cricket|\bsports?\b",
        "medical/surgical": r"surgical|examination|post[\s-]?mortem|medical|sterile|single[\s-]use|cardiovascular",
        "glove box (containment)": r"glove\s+box",
        "firefighting": r"firefight\w*|wildland",
        "agricultural": r"agro|harvest\w*",
    },
    "pool_nouns": ["glove"],
    "pool_context_required": False,
    "attributes": [
        {"key": "hazard", "label": "Hazard Protection", "category": "Protection", "kind": "enum", "gate": True,
         "on_silent": "exclude", "type_fmt": "{}-resistant",
         "values": {"Chemical": _v(r"chemical|\bacids?\b|alkali|corrosive|solvent", r"chemical|\bacids?\b"),
                    "Electrical": _v(r"live\s+working|electric\w*\s+(?:shock|insulat\w*)|insulating|high[\s-]voltage", r"live\s+working|insulating|electric"),
                    "Heat/Fire": _v(r"\bheat\b|thermal|welding", r"\bheat\b|thermal|welding"),
                    "Cut/Mechanical": _v(r"\bcut\b|abrasion|puncture", r"\bcut\b|abrasion")}},
        {"key": "material", "label": "Glove Material", "category": "Material", "kind": "multi", "type_fmt": "{}",
         "values": {"Nitrile": _v(r"nitrile"), "Neoprene": _v(r"neoprene"), "Latex/Rubber": _v(r"latex|rubber"),
                    "PVC": _v(r"\bpvc\b|polyvinyl"), "Leather": _v(r"leather")}},
        {"key": "size", "label": "Size Range", "category": "Dimensions", "kind": "token", "ask": True,
         "user": r"\bsize[s]?\s*\d+(?:\s*[-–to]+\s*\d+)?\b", "missing_prompt": "Glove size range (e.g., Size 7-11 / S to XXL)"},
    ],
}

SAFETY_HELMET = {
    "id": "safety_helmet",
    "label": "helmets",
    "category": "Industrial Safety Helmets",
    "detect": [(r"\bhelmets?\b|\bhard[\s-]?hats?\b", 3)],
    "product_title": [r"helmets?"],
    "roles": [],
    "domains": {
        "motorcycle/two-wheeler": r"motor\s*cycle|scooter|two[\s-]*wheeler|riders?",
        "bicycle/skating": r"bicycle|skateboard|roller\s+skate",
        "mountaineering": r"mountaineer\w*",
        "fire/police services": r"firem[ae]n|fire\s*fighter|civil\s+defence|police",
        "respiratory devices": r"respirat\w+|\bhood\b|filtering",
    },
    "pool_nouns": ["helmet"],
    "pool_context_required": False,
    "attributes": [
        {"key": "material", "label": "Shell Material", "category": "Material", "kind": "multi",
         "values": {"HDPE": _v(r"hdpe|polyethylene"), "ABS": _v(r"\babs\b"), "Fibreglass": _v(r"fib(?:re|er)[\s-]*glass|frp")}},
        {"key": "tests", "label": "Test", "category": "Required Test", "kind": "multi",
         "values": {"impact resistance": _v(r"impact|shock|penetration", allied=r"headform")}},
    ],
}

REINFORCEMENT_STEEL = {
    "id": "reinforcement_steel",
    "label": "reinforcement bars",
    "category": "Reinforcement Steel",
    "detect": [(r"\brebars?\b|reinforc\w*\s+(?:steel\s+)?bars?|\btmt\b|deformed\s+(?:steel\s+)?bars?|reinforcement\s+steel", 3),
               (r"\bfe\s*(?:415|500|550|600)", 2)],
    "product_title": [r"\bbars?\b", r"reinforc|concrete"],
    "roles": [("installation_code", r"welding|bending\s+and\s+fixing"), ("component", r"couplers?")],
    "domains": {"prestressing": r"prestress\w*|pre-stress\w*"},
    "pool_nouns": ["reinforc"],
    "pool_context_required": False,
    "attributes": [
        {"key": "material", "label": "Bar Material", "category": "Material", "kind": "enum", "gate": True,
         "on_silent": "ignore", "type_fmt": "{}",
         "values": {"Steel": _v(r"\bsteel\b|\btmt\b|\bfe\s*\d{3}", r"\bsteel\b|\bmild\b|\btmt\b"),
                    "FRP": _v(r"frp|gfrp|fib(?:re|er)[\s-]*reinforced\s+polymer|glass\s+fib", r"frp|gfrp|fib(?:re|er)|glass")}},
        {"key": "steel_type", "label": "Steel Type", "category": "Material", "kind": "enum", "gate": True,
         "on_silent": "ignore", "variant": True,
         "values": {"Stainless": _v(r"stainless", r"stainless")}},
        {"key": "grade", "label": "Grade", "category": "Material", "kind": "token", "ask": True,
         "user": r"\bfe\s*\d{3}[a-z]?\b", "missing_prompt": "Steel grade (e.g., Fe 500D)"},
        {"key": "strength", "label": "Strength Class", "category": "Material", "kind": "enum", "gate": True,
         "on_silent": "ignore",
         "infer": [{"attr": "grade", "match": r"fe\s*(?:415|500|550|600)", "value": "High strength"}],
         "values": {"High strength": _v(r"high[\s-]*strength", r"high[\s-]*strength"),
                    "Mild/medium tensile": _v(r"mild\s+steel|medium\s+tensile", r"mild\s+steel|medium\s+tensile")}},
        {"key": "coating", "label": "Coating", "category": "Finish", "kind": "enum", "variant": True,
         "values": {"Epoxy coated": _v(r"epoxy", r"epoxy"),
                    "Galvanized": _v(r"galvani[sz]ed|zinc|hot[\s-]*dip", r"galvani[sz]ed|zinc|hot[\s-]*dip")}},
        {"key": "tests", "label": "Test", "category": "Required Test", "kind": "multi",
         "values": {"tensile": _v(r"tensile", allied=r"tensile"), "bend": _v(r"\bbend\b|rebend", allied=r"\bbend")}},
    ],
}

PV_MODULE = {
    "id": "pv_module",
    "label": "photovoltaic modules",
    "category": "Renewable Energy & Solar",
    "detect": [(r"photovoltaic|solar\s+(?:pv|panels?|modules?|cells?)|\bpv\s+(?:modules?|panels?)", 3)],
    "product_title": [r"photovoltaic[\s\w()/-]{0,20}?modules?"],
    "roles": [("test_method", r"electroluminescence|measurements?|calibration|linearity|performance\s+testing|energy\s+rating|corrosion\s+testing"),
              ("component", r"junction\s+boxes?|connectors?|materials\s+used"),
              ("installation_code", r"guide\s+for|general\s+description")],
    "domains": {"solar thermal/heating": r"solar\s+heating|water\s+heating|solar\s+radiation"},
    "pool_nouns": ["photovoltaic"],
    "pool_context_required": False,
    "attributes": [
        {"key": "technology", "label": "Cell Technology", "category": "Technology", "kind": "enum", "gate": True,
         "on_silent": "ignore", "variant": True, "type_fmt": "{}",
         "values": {"Crystalline silicon": _v(r"crystalline|\bc[\s-]?si\b|silicon", r"crystalline\s+silicon"),
                    "Thin film": _v(r"thin[\s-]*film|cdte|cigs", r"thin[\s-]*film"),
                    "Concentrator": _v(r"concentrator|\bcpv\b", r"concentrator|\bcpv\b")}},
        {"key": "power", "label": "Rated Power", "category": "Performance", "kind": "token", "ask": True,
         "user": r"\d+(?:\.\d+)?\s*(?:wp|kwp|kw|w)\b", "missing_prompt": "Module rated power (Wp)"},
        {"key": "tests", "label": "Test", "category": "Required Test", "kind": "multi",
         "values": {"design qualification": _v(r"design\s+qualification|type\s+approval|iec\s*61215")}},
    ],
}

PROFILES = [POWER_CABLE, PLASTIC_PIPE, SAFETY_GLOVES, SAFETY_HELMET, REINFORCEMENT_STEEL, PV_MODULE]
