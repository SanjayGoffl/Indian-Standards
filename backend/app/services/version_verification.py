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


def verify_standard_version_details(standard_number: str, raw_revision: str, amendment_details: str = None, has_catalog_sync: bool = False) -> Dict[str, Any]:
    """
    Validates standard revision metadata and builds verification warnings.
    """
    warnings = []

    if not has_catalog_sync:
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

