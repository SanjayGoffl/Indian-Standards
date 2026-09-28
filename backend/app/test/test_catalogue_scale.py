"""
Regression tests for behaviour that only breaks at catalogue scale (~20k standards):
identifier collisions, curated-field clobbering, substring IS-number matches,
withdrawn-standard handling, and version verification from live catalogue data.
Fixture rows use numbers outside the real BIS range and are removed afterwards.
"""

import pytest

from app.core.database import SessionLocal
from app.core.models import IndianStandard
from app.rag.chromadb_service import chroma_service
from app.services.bis_connector import MockBISConnector, parse_standard_number
from app.services.standards_ingestion import ingest_standards
from app.services.standards_retrieval import _is_exact_number_match, retrieve_candidate_standards
from app.services.version_verification import verify_standard_version_details

FIXTURE_BASE = "IS 97310"


@pytest.fixture()
def db():
    session = SessionLocal()
    yield session
    rows = session.query(IndianStandard).filter(IndianStandard.base_standard_number == FIXTURE_BASE).all()
    ids = [r.standard_number.replace(" ", "_").replace("/", "_").replace(":", "_") for r in rows]
    for r in rows:
        session.delete(r)
    session.commit()
    if ids:
        try:
            chroma_service.get_or_create_collection("indian_standards_kb").delete(ids=ids)
        except Exception:
            pass
    session.close()


@pytest.mark.parametrize("raw,canonical,base,part,year", [
    ("IS 2500 (Part 1/Sec 2):2000", "IS 2500 (Part 1/Sec 2):2000", "IS 2500", "Part 1/Sec 2", "2000"),
    ("IS/IEC 60947-1:2020", "IS/IEC 60947-1:2020", "IS/IEC 60947", None, "2020"),
    ("is/iso 9001 : 2015", "IS/ISO 9001:2015", "IS/ISO 9001", None, "2015"),
    ("IS 2000:1990", "IS 2000:1990", "IS 2000", None, "1990"),
    ("IS4984:2016", "IS 4984:2016", "IS 4984", None, "2016"),
])
def test_canonical_identifiers_are_lossless(raw, canonical, base, part, year):
    p = parse_standard_number(raw)
    assert p["canonical_standard_number"] == canonical
    assert p["base_standard_number"] == base
    assert p["part_number"] == part
    assert p["revision_year"] == year


def test_distinct_sections_and_iec_numbers_do_not_collide():
    a = parse_standard_number("IS 2500 (Part 1/Sec 1):2000")["canonical_standard_number"]
    b = parse_standard_number("IS 2500 (Part 1/Sec 2):2000")["canonical_standard_number"]
    c = parse_standard_number("IS/IEC 60947-1:2020")["canonical_standard_number"]
    d = parse_standard_number("IS/IEC 61439-2:2020")["canonical_standard_number"]
    assert len({a, b, c, d}) == 4


def test_exact_is_number_match_is_digit_bounded():
    assert _is_exact_number_match("IS 694:2010", "694")
    assert _is_exact_number_match("IS 694 (Part 1):2010", "694")
    assert not _is_exact_number_match("IS 6940:1973", "694")
    assert not _is_exact_number_match("IS 16940:2018", "694")


def test_ingestion_keeps_sections_distinct_counts_duplicates_and_is_incremental(db):
    payload = [
        {"standard_number": f"{FIXTURE_BASE} (Part 1/Sec 1):2026", "title": "Fixture section one"},
        {"standard_number": f"{FIXTURE_BASE} (Part 1/Sec 2):2026", "title": "Fixture section two"},
        {"standard_number": f"{FIXTURE_BASE} (Part 1/Sec 2) : 2026", "title": "Fixture section two"},
    ]
    first = ingest_standards(db, MockBISConnector(payload))
    assert first["new_records"] == 2
    assert first["duplicate_records"] == 1
    assert first["embeddings_created"] == 2
    stored = db.query(IndianStandard).filter(IndianStandard.base_standard_number == FIXTURE_BASE).all()
    assert len(stored) == 2
    assert all(s.embedding_status == "indexed" for s in stored)

    second = ingest_standards(db, MockBISConnector(payload))
    assert second["new_records"] == 0
    assert second["unchanged_records"] == 2
    assert second["embeddings_created"] == 0 and second["embeddings_updated"] == 0


def test_metadata_only_update_does_not_clobber_curated_fields(db):
    number = f"{FIXTURE_BASE}:2026"
    curated = [{
        "standard_number": number, "title": "Fixture curated title",
        "scope": "Curated scope text describing the product in detail.",
        "product_category": "Pipes & Water Management", "sector": "Water",
    }]
    ingest_standards(db, MockBISConnector(curated))

    metadata_only = [{"standard_number": number, "title": "Fixture official title", "scope": "",
                      "product_category": "BIS Department 1", "sector": "Technical Committee 1"}]
    connector = MockBISConnector(metadata_only)
    records = connector.fetch_standards()
    records[0]["category_is_placeholder"] = True
    connector.fetch_standards = lambda: records
    result = ingest_standards(db, connector)
    assert result["updated_records"] == 1

    row = db.query(IndianStandard).filter(IndianStandard.standard_number == number).one()
    assert row.title == "Fixture official title"
    assert row.scope == "Curated scope text describing the product in detail."
    assert row.category == "Pipes & Water Management"


def test_withdrawn_standard_replaced_by_active_successor(db):
    payload = [
        {"standard_number": f"{FIXTURE_BASE}:2001", "title": "Zirconoxide fixture widget specification", "status": "Withdrawn"},
        {"standard_number": f"{FIXTURE_BASE}:2024", "title": "Zirconoxide fixture widget specification", "status": "Active"},
    ]
    ingest_standards(db, MockBISConnector(payload))

    uncited = [s.standard_number for s in retrieve_candidate_standards(db, "zirconoxide fixture widget", top_k=10)]
    assert f"{FIXTURE_BASE}:2024" in uncited
    assert f"{FIXTURE_BASE}:2001" not in uncited

    cited = [s.standard_number for s in retrieve_candidate_standards(db, "zirconoxide widget as per IS 97310:2001", top_k=10)]
    assert f"{FIXTURE_BASE}:2001" in cited and f"{FIXTURE_BASE}:2024" in cited


def test_version_verification_uses_catalogue_status():
    withdrawn = verify_standard_version_details("IS 269:2013", "2013", has_catalog_sync=True,
                                                catalogue_status="Withdrawn", newer_active_revision="IS 269:2015")
    assert withdrawn["revision_verification_status"] == "Withdrawn"
    assert "IS 269:2015" in withdrawn["latest_revision"]

    superseded = verify_standard_version_details("IS 432 (Part 1):1982", "1982", has_catalog_sync=True,
                                                 catalogue_status="Active", newer_active_revision="IS 432 (Part 1):2026")
    assert superseded["revision_verification_status"] == "Superseded Revision"

    legacy = verify_standard_version_details("IS 4984:2016", "2016", has_catalog_sync=False)
    assert legacy["revision_verification_status"] == "Unverified"


def test_large_catalogue_exact_lookup_precision():
    session = SessionLocal()
    try:
        if session.query(IndianStandard).count() < 1000:
            pytest.skip("Live BIS catalogue not ingested")
        results = retrieve_candidate_standards(session, "HDPE pipes for water supply as per IS 4984", top_k=10)
        numbers = [s.standard_number for s in results]
        assert numbers and _is_exact_number_match(numbers[0], "4984")
        assert not any(("49840" in n or "14984" in n) for n in numbers)
    finally:
        session.close()
