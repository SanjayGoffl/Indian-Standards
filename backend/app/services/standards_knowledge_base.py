"""
Indian Standards Knowledge Base Service.
Provides seeding, relational mapping, vector indexing, and catalog queries for BIS Indian Standards.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.models import IndianStandard, StandardRelationship, CertificationRequirement
from app.rag.chromadb_service import chroma_service

logger = logging.getLogger(__name__)

INITIAL_INDIAN_STANDARDS_SEED: List[Dict[str, Any]] = [
    {
        "standard_number": "IS 694:2010",
        "title": "Polyvinyl Chloride Insulated Cables for Working Voltages Up to and Including 1100 V",
        "scope": "Covers requirements for single core and multicore PVC insulated cables for electric power and lighting in residential, commercial, and industrial procurement. Specifies conductor resistance, insulation thickness, flame retardance, and dielectric strength.",
        "category": "Electrical & Cables",
        "sector": "Power & Public Utilities",
        "publication_date": "2010",
        "revision": "Fourth Revision (Reaffirmed 2020)",
        "amendment_details": "Amendment No. 1 & 2 incorporated",
        "status": "Active",
        "source_url": "https://www.services.bis.gov.in/php/BIS_2.0/bis_review/standard_details/IS694",
        "evidence_text": "Mandatory under Electrical Wires, Cables, Appliances and Protection Devices (Quality Control) Order. Must bear ISI Mark under Scheme-I.",
        "certifications": [
            {
                "certification_type": "BIS Product Certification / ISI",
                "applicability": "Mandatory",
                "source_url": "https://www.bis.gov.in/product-certification/products-under-mandatory-certification/",
                "verification_status": "Verified by QCO Notification"
            }
        ],
        "relationships": [
            {
                "related_standard_number": "IS 10810",
                "relationship_type": "test_method",
                "description": "Methods of test for cables"
            },
            {
                "related_standard_number": "IS 8130",
                "relationship_type": "material",
                "description": "Conductors for insulated electric cables and flexible cords"
            }
        ]
    },
    {
        "standard_number": "IS 7098 (Part 1):1988",
        "title": "Cross-linked Polyethylene Insulated PVC Sheathed Cables - Part 1: For Working Voltages Up to and Including 1100 V",
        "scope": "Specifies technical requirements for XLPE insulated, PVC sheathed electric power cables designed for working voltages up to 1100 V. Includes conductor material, insulation properties, inner/outer sheath dimensions, and mechanical armor requirements.",
        "category": "Electrical & Cables",
        "sector": "Power & Infrastructure",
        "publication_date": "1988",
        "revision": "Reaffirmed 2021",
        "amendment_details": "Amendment No. 1, 2, 3",
        "status": "Active",
        "source_url": "https://www.services.bis.gov.in/php/BIS_2.0/bis_review/standard_details/IS7098",
        "evidence_text": "Covered under BIS Scheme-I Mandatory Certification for heavy duty power supply procurement.",
        "certifications": [
            {
                "certification_type": "BIS Product Certification / ISI",
                "applicability": "Mandatory",
                "source_url": "https://www.bis.gov.in/",
                "verification_status": "Verified by QCO"
            }
        ],
        "relationships": [
            {
                "related_standard_number": "IS 10810",
                "relationship_type": "test_method",
                "description": "Standard cable testing procedures"
            },
            {
                "related_standard_number": "IS 5831",
                "relationship_type": "material",
                "description": "PVC insulation and sheath of electric cables"
            }
        ]
    },
    {
        "standard_number": "IS 14286:2010 / IEC 61215:2005",
        "title": "Crystalline Silicon Terrestrial Photovoltaic (PV) Modules - Design Qualification and Type Approval",
        "scope": "Lays down requirements for design qualification and type approval of terrestrial PV modules suitable for long-term operation in outdoor climates. Covers thermal cycling, humidity freeze, damp heat, mechanical load, and hail impact tests.",
        "category": "Renewable Energy & Solar",
        "sector": "Energy & Sustainability",
        "publication_date": "2010",
        "revision": "First Revision (Reaffirmed 2019)",
        "amendment_details": "Aligned with IEC 61215",
        "status": "Active",
        "source_url": "https://www.bis.gov.in/",
        "evidence_text": "Mandatory under Solar Photovoltaics, Systems, Devices and Components Goods (Requirements for Compulsory Registration) Order.",
        "certifications": [
            {
                "certification_type": "Compulsory Registration Scheme (CRS)",
                "applicability": "Mandatory",
                "source_url": "https://www.crsbis.in/BIS/",
                "verification_status": "Verified under MNRE / BIS CRS scheme"
            }
        ],
        "relationships": [
            {
                "related_standard_number": "IS 16270:2014",
                "relationship_type": "safety",
                "description": "Secondary cell and batteries for solar photovoltaic systems"
            }
        ]
    },
    {
        "standard_number": "IS 456:2000",
        "title": "Plain and Reinforced Concrete - Code of Practice",
        "scope": "Deals with the general structural design and construction of plain and reinforced concrete structures. Covers material quality (cement, aggregates, water, reinforcement), mix proportions, durability, fire resistance, and structural design principles.",
        "category": "Civil & Construction",
        "sector": "Infrastructure & Buildings",
        "publication_date": "2000",
        "revision": "Fourth Revision (Reaffirmed 2021)",
        "amendment_details": "Amendment No. 1 to 5",
        "status": "Active",
        "source_url": "https://www.services.bis.gov.in/php/BIS_2.0/bis_review/standard_details/IS456",
        "evidence_text": "Fundamental code of practice for all public works departments (CPWD, PWD, Railways, Defense infrastructure tenders).",
        "certifications": [
            {
                "certification_type": "Code of Practice / Compliance",
                "applicability": "Mandatory for Design & Procurement Specs",
                "source_url": "https://www.bis.gov.in/",
                "verification_status": "Standard Engineering Practice Code"
            }
        ],
        "relationships": [
            {
                "related_standard_number": "IS 1786:2008",
                "relationship_type": "normative_reference",
                "description": "High strength deformed steel bars and wires for concrete reinforcement"
            },
            {
                "related_standard_number": "IS 269:2015",
                "relationship_type": "material",
                "description": "Ordinary Portland Cement specs"
            },
            {
                "related_standard_number": "IS 383:2016",
                "relationship_type": "material",
                "description": "Coarse and fine aggregate for concrete"
            }
        ]
    },
    {
        "standard_number": "IS 1786:2008",
        "title": "High Strength Deformed Steel Bars and Wires for Concrete Reinforcement - Specification",
        "scope": "Covers requirements for deformed steel bars (Fe 415, Fe 500, Fe 550, Fe 600 grades) and wires for use as reinforcement in concrete. Specifies chemical composition, yield stress, tensile strength, elongation, bend test, and rib geometry.",
        "category": "Civil & Construction",
        "sector": "Infrastructure & Steel",
        "publication_date": "2008",
        "revision": "Fourth Revision (Reaffirmed 2018)",
        "amendment_details": "Amendment No. 1, 2, 3",
        "status": "Active",
        "source_url": "https://www.services.bis.gov.in/",
        "evidence_text": "Mandatory under Steel and Steel Products (Quality Control) Order. Mandatory ISI Mark.",
        "certifications": [
            {
                "certification_type": "BIS Product Certification / ISI",
                "applicability": "Mandatory",
                "source_url": "https://www.bis.gov.in/",
                "verification_status": "Verified by Ministry of Steel QCO"
            }
        ],
        "relationships": [
            {
                "related_standard_number": "IS 1608",
                "relationship_type": "test_method",
                "description": "Metallic materials - Tensile testing"
            },
            {
                "related_standard_number": "IS 456:2000",
                "relationship_type": "normative_reference",
                "description": "Code of practice for plain and reinforced concrete"
            }
        ]
    },
    {
        "standard_number": "IS 13252 (Part 1):2010 / IEC 60950-1:2005",
        "title": "Information Technology Equipment - Safety - Part 1: General Requirements",
        "scope": "Applicable to mains-powered or battery-powered information technology equipment, including servers, laptops, desktop PCs, power adapters, and peripherals. Covers electrical safety, fire protection, thermal safety, and mechanical hazard prevention.",
        "category": "IT & Electronics",
        "sector": "IT Procurement & Electronics",
        "publication_date": "2010",
        "revision": "Second Revision (Reaffirmed 2020)",
        "amendment_details": "Amendment No. 1 & 2",
        "status": "Active",
        "source_url": "https://www.crsbis.in/BIS/",
        "evidence_text": "Mandatory under Electronics and Information Technology Goods (Requirement for Compulsory Registration) Order (CRO).",
        "certifications": [
            {
                "certification_type": "Compulsory Registration Scheme (CRS)",
                "applicability": "Mandatory",
                "source_url": "https://www.crsbis.in/BIS/",
                "verification_status": "Verified by MeitY CRO Notification"
            }
        ],
        "relationships": [
            {
                "related_standard_number": "IS 16333 (Part 3):2017",
                "relationship_type": "terminology",
                "description": "Language support for mobile phones and devices"
            }
        ]
    },
    {
        "standard_number": "IS 4984:2016",
        "title": "High Density Polyethylene (HDPE) Pipes for Potable Water Supplies, Sewage and Industrial Effluents - Specification",
        "scope": "Specifies requirements for HDPE pipes (PE 63, PE 80, PE 100 grades) intended for underground water supply networks, irrigation, and pressure effluent transport. Defines hydrostatic strength, melt flow rate, carbon black content, and pressure ratings.",
        "category": "Pipes & Water Management",
        "sector": "Water Resources & Municipal Procurement",
        "publication_date": "2016",
        "revision": "Fifth Revision",
        "amendment_details": "Amendment No. 1 & 2",
        "status": "Active",
        "source_url": "https://www.services.bis.gov.in/",
        "evidence_text": "Widely mandated in Jal Jeevan Mission, AMRUT, and State Water Board procurement specifications.",
        "certifications": [
            {
                "certification_type": "BIS Product Certification / ISI",
                "applicability": "Mandatory in Public Procurement",
                "source_url": "https://www.bis.gov.in/",
                "verification_status": "Verified by Department of Chemicals QCO"
            }
        ],
        "relationships": [
            {
                "related_standard_number": "IS 10500:2012",
                "relationship_type": "normative_reference",
                "description": "Drinking Water Specification"
            },
            {
                "related_standard_number": "IS 7634",
                "relationship_type": "installation",
                "description": "Code of practice for plastics pipe work"
            }
        ]
    },
    {
        "standard_number": "IS 10500:2012",
        "title": "Drinking Water - Specification",
        "scope": "Prescribes requirements, test methods, and limits for physical, chemical, toxic, and bacteriological characteristics of drinking water for public water supply systems and packaged drinking water.",
        "category": "Water Quality & Environment",
        "sector": "Public Health & Municipal Utilities",
        "publication_date": "2012",
        "revision": "Second Revision (Reaffirmed 2018)",
        "amendment_details": "Amendment No. 1 & 2",
        "status": "Active",
        "source_url": "https://www.bis.gov.in/",
        "evidence_text": "Mandatory standard for all municipal water supply agencies, packaged drinking water plants, and public water purification projects.",
        "certifications": [
            {
                "certification_type": "BIS Product Certification / ISI",
                "applicability": "Mandatory for Packaged Water / Public Supply Specs",
                "source_url": "https://www.bis.gov.in/",
                "verification_status": "Verified under FSSAI and BIS mandatory certification"
            }
        ],
        "relationships": [
            {
                "related_standard_number": "IS 3025",
                "relationship_type": "test_method",
                "description": "Methods of sampling and test (physical and chemical) for water and wastewater"
            },
            {
                "related_standard_number": "IS 1622",
                "relationship_type": "test_method",
                "description": "Methods of sampling and microbiological examination of water"
            }
        ]
    },
    {
        "standard_number": "IS 2925:1984",
        "title": "Specification for Industrial Safety Helmets",
        "scope": "Covers requirements for industrial safety helmets meant for head protection against falling objects, mechanical impacts, and low electrical exposure in construction, mining, and industrial environments.",
        "category": "Safety Equipment & PPE",
        "sector": "Industrial & Construction Safety",
        "publication_date": "1984",
        "revision": "Second Revision (Reaffirmed 2019)",
        "amendment_details": "Amendment No. 1, 2, 3",
        "status": "Active",
        "source_url": "https://www.bis.gov.in/",
        "evidence_text": "Mandatory under Personal Protective Equipment (Quality Control) Order.",
        "certifications": [
            {
                "certification_type": "BIS Product Certification / ISI",
                "applicability": "Mandatory",
                "source_url": "https://www.bis.gov.in/",
                "verification_status": "Verified under PPE QCO"
            }
        ],
        "relationships": [
            {
                "related_standard_number": "IS 15298",
                "relationship_type": "safety",
                "description": "Personal protective equipment - Safety footwear"
            }
        ]
    },
    {
        "standard_number": "IS 10245 (Part 2):1994",
        "title": "Respiratory Protective Devices - Breathing Apparatus - Specification",
        "scope": "Specifies safety requirements, testing procedures, and performance metrics for self-contained open-circuit compressed air breathing apparatus used by fire services and chemical plant responders.",
        "category": "Safety Equipment & PPE",
        "sector": "Disaster Management & Defense",
        "publication_date": "1994",
        "revision": "Reaffirmed 2020",
        "amendment_details": "Amendment No. 1",
        "status": "Active",
        "source_url": "https://www.bis.gov.in/",
        "evidence_text": "Required for fire service, PSU refinery, and hazardous material responder procurement tenders.",
        "certifications": [
            {
                "certification_type": "BIS Product Certification / ISI",
                "applicability": "Mandatory in Fire & Emergency Procurement",
                "source_url": "https://www.bis.gov.in/",
                "verification_status": "Verified by Safety QCO"
            }
        ],
        "relationships": [
            {
                "related_standard_number": "IS 9473",
                "relationship_type": "safety",
                "description": "Filtering half masks to protect against particles"
            }
        ]
    }
]


def seed_indian_standards(db: Session) -> Dict[str, Any]:
    """
    Seeds initial authentic Indian Standards into PostgreSQL database and ChromaDB vector collection.
    """
    seeded_count = 0
    updated_count = 0

    # Ensure vector store collection exists
    collection = chroma_service.get_or_create_collection("indian_standards_kb")

    # Map of standard_number -> db object
    standard_map: Dict[str, IndianStandard] = {}

    for item in INITIAL_INDIAN_STANDARDS_SEED:
        existing = db.query(IndianStandard).filter(IndianStandard.standard_number == item["standard_number"]).first()

        if not existing:
            standard = IndianStandard(
                standard_number=item["standard_number"],
                title=item["title"],
                scope=item["scope"],
                category=item["category"],
                sector=item["sector"],
                publication_date=item.get("publication_date"),
                revision=item.get("revision"),
                amendment_details=item.get("amendment_details"),
                status=item.get("status", "Active"),
                source_url=item.get("source_url"),
                evidence_text=item.get("evidence_text"),
            )
            db.add(standard)
            db.flush()
            standard_map[item["standard_number"]] = standard
            seeded_count += 1
        else:
            existing.title = item["title"]
            existing.scope = item["scope"]
            existing.category = item["category"]
            existing.sector = item["sector"]
            existing.revision = item.get("revision")
            existing.evidence_text = item.get("evidence_text")
            standard_map[item["standard_number"]] = existing
            updated_count += 1

        db.commit()

        # Add certifications
        std_obj = standard_map[item["standard_number"]]
        for cert in item.get("certifications", []):
            existing_cert = db.query(CertificationRequirement).filter(
                CertificationRequirement.standard_id == std_obj.id,
                CertificationRequirement.certification_type == cert["certification_type"]
            ).first()
            if not existing_cert:
                cert_obj = CertificationRequirement(
                    standard_id=std_obj.id,
                    certification_type=cert["certification_type"],
                    applicability=cert.get("applicability", "Mandatory"),
                    source_url=cert.get("source_url"),
                    verification_status=cert.get("verification_status")
                )
                db.add(cert_obj)
        db.commit()

        # Vector collection insertion
        text_for_embedding = f"Standard Number: {item['standard_number']}\nTitle: {item['title']}\nCategory: {item['category']}\nSector: {item['sector']}\nScope: {item['scope']}\nEvidence: {item.get('evidence_text', '')}"
        
        # We check if document exists in vector store, if not add
        try:
            collection.upsert(
                documents=[text_for_embedding],
                metadatas=[{
                    "standard_number": item["standard_number"],
                    "title": item["title"],
                    "category": item["category"],
                    "sector": item["sector"],
                    "revision": item.get("revision", "")
                }],
                ids=[item["standard_number"].replace(" ", "_").replace("/", "_").replace(":", "_")]
            )
        except Exception as e:
            logger.warning(f"ChromaDB upsert failed for {item['standard_number']}: {str(e)}")

    # Add relationships
    for item in INITIAL_INDIAN_STANDARDS_SEED:
        parent_std = standard_map.get(item["standard_number"])
        if not parent_std:
            continue
        for rel in item.get("relationships", []):
            rel_std_number = rel["related_standard_number"]
            # Look up related std
            rel_std = db.query(IndianStandard).filter(IndianStandard.standard_number.like(f"%{rel_std_number}%")).first()
            if rel_std and rel_std.id != parent_std.id:
                existing_rel = db.query(StandardRelationship).filter(
                    StandardRelationship.standard_id == parent_std.id,
                    StandardRelationship.related_standard_id == rel_std.id
                ).first()
                if not existing_rel:
                    rel_obj = StandardRelationship(
                        standard_id=parent_std.id,
                        related_standard_id=rel_std.id,
                        relationship_type=rel["relationship_type"],
                        description=rel.get("description")
                    )
                    db.add(rel_obj)
    db.commit()

    logger.info(f"Seeded {seeded_count} new Indian Standards, updated {updated_count}.")
    return {"seeded": seeded_count, "updated": updated_count, "total": len(INITIAL_INDIAN_STANDARDS_SEED)}
