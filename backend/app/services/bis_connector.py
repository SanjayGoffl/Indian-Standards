"""
BIS Connector Interface and Source Adapter Implementations.
Provides modular connectors to ingest Indian Standards from authorized local JSON, CSV,
mock APIs, or official BIS data feeds without inventing data.
Standardizes records to 15 unified schema fields.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import json
import csv
import logging
import os
import hashlib
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


import re

def parse_standard_number(raw_num: str) -> Dict[str, Optional[str]]:
    """
    Parses raw standard identifier into canonical components.
    e.g. 'IS 7098 (Part 1):1988' -> base: 'IS 7098', part: 'Part 1', year: '1988', canonical: 'IS 7098 (Part 1):1988'
    """
    raw_num = (raw_num or "").strip()
    if not raw_num:
        return {
            "raw_standard_number": "",
            "canonical_standard_number": "",
            "base_standard_number": "",
            "part_number": None,
            "revision_year": None
        }

    base_match = re.search(r"\bIS\s*(\d+)", raw_num, re.IGNORECASE)
    base_num_str = f"IS {base_match.group(1)}" if base_match else raw_num.split()[0]

    part_match = re.search(r"\(?\bPart\s*(\d+)\)?", raw_num, re.IGNORECASE)
    part_str = f"Part {part_match.group(1)}" if part_match else None

    year_match = re.search(r":?\b(19\d{2}|20\d{2})\b", raw_num)
    year_str = year_match.group(1) if year_match else None

    parts = [base_num_str]
    if part_str:
        parts.append(f"({part_str})")
    canonical = " ".join(parts)
    if year_str:
        canonical += f":{year_str}"

    return {
        "raw_standard_number": raw_num,
        "canonical_standard_number": canonical,
        "base_standard_number": base_num_str,
        "part_number": part_str,
        "revision_year": year_str
    }


def compute_content_hash(record: Dict[str, Any]) -> str:
    """
    Computes deterministic SHA-256 content hash across standardized fields.
    """
    fields = [
        str(record.get("standard_number", "")).strip(),
        str(record.get("title", "")).strip(),
        str(record.get("scope", "")).strip(),
        str(record.get("technical_requirements", "")).strip(),
        str(record.get("product_category", "")).strip(),
        str(record.get("sector", "")).strip(),
        str(record.get("revision_year", "")).strip(),
        str(record.get("amendment_information", "")).strip(),
        str(record.get("status", "")).strip(),
    ]
    raw_str = "|".join(fields)
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


def normalize_bis_record(raw: Dict[str, Any], default_source: str = "Authorized Local Import") -> Dict[str, Any]:
    """
    Normalizes a raw dictionary record into the standard 15-field schema + canonical identifier attributes.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    std_num = (raw.get("standard_number") or raw.get("standard_no") or raw.get("is_number") or "").strip()
    parsed_id = parse_standard_number(std_num)

    title = (raw.get("title") or raw.get("standard_title") or "Untitled Standard").strip()
    scope = (raw.get("scope") or raw.get("description") or "").strip()
    tech_reqs = (raw.get("technical_requirements") or raw.get("specifications") or "").strip()
    category = (raw.get("product_category") or raw.get("category") or "General").strip()
    sector = (raw.get("sector") or "General Sector").strip()
    revision_year = str(raw.get("revision_year") or parsed_id["revision_year"] or raw.get("revision") or raw.get("publication_date") or "").strip()
    amendment_info = str(raw.get("amendment_information") or raw.get("amendment_details") or "").strip()
    status = (raw.get("status") or "Active").strip()
    source_name = (raw.get("source") or default_source).strip()
    source_type = (raw.get("source_type") or ("Local Metadata Index" if "Mock" in source_name or "Local" in source_name else "Official Document Record")).strip()
    source_url = (raw.get("source_url") or "").strip()
    evidence_text = (raw.get("evidence_text") or scope or "").strip()
    retrieved_at = (raw.get("retrieved_at") or now_iso).strip()
    verification_status = (raw.get("verification_status") or "Verification Required").strip()

    partial_record = {
        "standard_number": std_num,
        "raw_standard_number": parsed_id["raw_standard_number"],
        "canonical_standard_number": parsed_id["canonical_standard_number"],
        "base_standard_number": parsed_id["base_standard_number"],
        "part_number": parsed_id["part_number"],
        "title": title,
        "scope": scope,
        "technical_requirements": tech_reqs,
        "product_category": category,
        "sector": sector,
        "revision_year": revision_year,
        "amendment_information": amendment_info,
        "status": status,
        "source": source_name,
        "source_type": source_type,
        "source_url": source_url,
        "evidence_text": evidence_text,
        "retrieved_at": retrieved_at,
        "verification_status": verification_status,
        "certifications": raw.get("certifications", []),
        "relationships": raw.get("relationships", [])
    }

    content_hash = compute_content_hash(partial_record)
    partial_record["content_hash"] = content_hash
    partial_record["last_updated"] = now_iso

    return partial_record


class BISConnectorInterface(ABC):
    """
    Abstract Base Class for BIS Standards data connectors.
    """

    @abstractmethod
    def fetch_standards(self) -> List[Dict[str, Any]]:
        """
        Fetch standard records as a list of normalized dictionary payloads.
        """
        pass

    @abstractmethod
    def get_source_metadata(self) -> Dict[str, Any]:
        """
        Returns metadata about the connector source.
        """
        pass


class LocalJSONBISConnector(BISConnectorInterface):
    """
    Connector that loads BIS standards data from a structured local JSON file.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path

    def fetch_standards(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.file_path):
            logger.warning(f"Local BIS JSON file not found: {self.file_path}")
            return []
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                raw_list = []
                if isinstance(data, list):
                    raw_list = data
                elif isinstance(data, dict) and "standards" in data:
                    raw_list = data["standards"]

                normalized = [normalize_bis_record(r, "Local JSON File") for r in raw_list]
                return normalized
        except Exception as e:
            logger.error(f"Error reading local BIS standards file {self.file_path}: {str(e)}")
            return []

    def get_source_metadata(self) -> Dict[str, Any]:
        return {
            "source_type": "local_json",
            "file_path": self.file_path,
            "exists": os.path.exists(self.file_path)
        }


class CSVBISConnector(BISConnectorInterface):
    """
    Connector that loads BIS standards data from a CSV file.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path

    def fetch_standards(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.file_path):
            logger.warning(f"Local BIS CSV file not found: {self.file_path}")
            return []
        try:
            records = []
            with open(self.file_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append(normalize_bis_record(row, "Local CSV File"))
            return records
        except Exception as e:
            logger.error(f"Error reading local BIS CSV file {self.file_path}: {str(e)}")
            return []

    def get_source_metadata(self) -> Dict[str, Any]:
        return {
            "source_type": "local_csv",
            "file_path": self.file_path,
            "exists": os.path.exists(self.file_path)
        }


class MockBISConnector(BISConnectorInterface):
    """
    Mock Connector used when live BIS access is unavailable.
    Provides sample structured standards payload adhering to exact BIS fields.
    """

    def __init__(self, initial_payload: Optional[List[Dict[str, Any]]] = None):
        self.raw_payload = initial_payload or []

    def fetch_standards(self) -> List[Dict[str, Any]]:
        return [normalize_bis_record(r, "Authorized Mock Connector") for r in self.raw_payload]

    def get_source_metadata(self) -> Dict[str, Any]:
        return {
            "source_type": "mock_authorized_connector",
            "status": "active",
            "count": len(self.raw_payload)
        }
