"""
Version Verification Module.
Validates Indian Standard revisions, reaffirmation dates, and active amendments.
Enforces anti-hallucination verification notices.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

UNVERIFIED_REVISION_TEXT = (
    "Verification required from the official BIS standard document."
)


def verify_standard_version_details(
    standard_number: str,
    raw_revision: str,
    amendment_details: str = None,
    has_catalog_sync: bool = False,
    catalogue_status: str = None,
    newer_active_revision: str = None,
    catalogue_retrieved_at: str = None,
) -> Dict[str, Any]:
    """
    Validates standard revision metadata and builds verification warnings.

    When the record was synced from BIS's own catalogue (has_catalog_sync), its
    active/withdrawn status and the existence of a newer active revision are
    reported as catalogue facts. Amendments are still not available from that
    source, so verification_required stays True.
    """
    warnings = []

    if has_catalog_sync and catalogue_status:
        as_of = f" as of {catalogue_retrieved_at[:10]}" if catalogue_retrieved_at else ""
        if catalogue_status == "Withdrawn":
            successor = newer_active_revision or "no active successor found in catalogue"
            display_revision = f"WITHDRAWN per BIS catalogue{as_of} — current standard: {successor}"
            revision_status = "Withdrawn"
            warnings.append(f"Standard {standard_number} is withdrawn; reference {successor} instead.")
        elif newer_active_revision:
            display_revision = f"{standard_number} — newer active revision in BIS catalogue{as_of}: {newer_active_revision}"
            revision_status = "Superseded Revision"
            warnings.append(f"Standard {standard_number} has a newer revision: {newer_active_revision}.")
        else:
            display_revision = f"{standard_number} — active in BIS catalogue{as_of}"
            revision_status = "Verified Active (BIS catalogue)"
        verification_required = True
        warnings.append(f"Standard {standard_number}: amendment status not available from catalogue sync. {UNVERIFIED_REVISION_TEXT}")
    elif not has_catalog_sync:
        display_revision = "Unverified (Official BIS catalogue verification required)"
        revision_status = "Unverified"
        verification_required = True
        warnings.append(f"Standard {standard_number}: {UNVERIFIED_REVISION_TEXT}")
    else:
        display_revision = f"Catalog Seed Record: {raw_revision} (Live official BIS verification required)"
        revision_status = "Unverified"
        verification_required = True

    amendments_list = []
    if amendment_details:
        amendments_list = [a.strip() for a in amendment_details.split(",") if a.strip()]

    return {
        "latest_revision": display_revision,
        "revision_verification_status": revision_status,
        "amendments": amendments_list,
        "verification_required": verification_required,
        "version_warnings": warnings
    }

