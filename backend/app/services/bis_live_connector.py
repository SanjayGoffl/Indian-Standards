"""
Live connector against BIS's own public "Know Your Standards" search API
(standardsadmin.bis.gov.in/review-service/searchKnowStandards).

This is the real, unauthenticated backend the official bis.gov.in "Know Your
Standard" tool calls from the browser. There is no bulk export or public bulk
API for the full ~19,000-standard catalogue, so this connector reconstructs
full coverage by sweeping a large set of search terms (every standard number
from 1 upward, since the search matches numeric substrings of the standard
number) and de-duplicating by canonical standard number.

Rate-limited and checkpointed: progress is written to a local JSON file after
every batch so a sweep can be safely resumed or re-run without re-querying
numbers already covered in this run.
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import httpx

from app.services.bis_connector import BISConnectorInterface, normalize_bis_record

logger = logging.getLogger(__name__)

SEARCH_URL = "https://standardsadmin.bis.gov.in/review-service//searchKnowStandards"
# The API silently truncates every search to 500 results; terms that hit it may hide standards.
RESULT_CAP = 500
DETAILS_URL_TEMPLATE = "https://standards.bis.gov.in/website/know-your-standards?searchTerm={term}"

DEFAULT_CHECKPOINT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "scratch", "bis_live_sweep_checkpoint.json"
)


def _map_status(record: Dict[str, Any]) -> str:
    if record.get("withdrawStatus") not in (None, 0):
        return "Withdrawn"
    return "Active"


def _map_record(record: Dict[str, Any]) -> Dict[str, Any]:
    standard_number = (record.get("standardNumber") or "").strip()
    published_on = record.get("publishedOn") or ""
    revision_year = published_on[:4] if published_on else None

    return {
        "standard_number": standard_number,
        "title": record.get("standardName") or "Untitled Standard",
        "scope": "",
        "technical_requirements": "",
        "product_category": f"BIS Department {record.get('departmentId')}" if record.get("departmentId") else "General",
        "sector": f"Technical Committee {record.get('committeeId')}" if record.get("committeeId") else "General Sector",
        "revision_year": revision_year,
        "amendment_information": "",
        "status": _map_status(record),
        "source": "BIS Know Your Standards (Live API)",
        "source_type": "Official Document Record",
        "source_url": DETAILS_URL_TEMPLATE.format(term=standard_number.replace(" ", "%20")),
        "source_url_label": "BIS official standard lookup (verify current status before use)",
        # Deliberately empty: evidence_text is treated downstream as QCO/certification
        # evidence, which catalogue metadata (number/title/status) does not provide.
        "evidence_text": "",
        # "Verified" = number, title and active/withdrawn status confirmed against BIS's
        # own catalogue. It is not gazette/QCO evidence and not an applicability claim.
        "verification_status": "Verified",
        "retrieved_at": None,
    }


class BISLiveAPIConnector(BISConnectorInterface):
    """
    Sweeps BIS's live public search API across a numeric range to reconstruct
    catalogue coverage. `max_number` bounds the sweep (IS standard numbers
    currently top out well under 20000); `concurrency` and `delay_seconds`
    control load on the remote server.
    """

    def __init__(
        self,
        max_number: int = 20000,
        concurrency: int = 4,
        delay_seconds: float = 0.05,
        timeout_seconds: float = 30.0,
        checkpoint_path: str = DEFAULT_CHECKPOINT_PATH,
        progress_callback=None,
    ):
        self.max_number = max_number
        self.concurrency = concurrency
        self.delay_seconds = delay_seconds
        self.timeout_seconds = timeout_seconds
        self.checkpoint_path = checkpoint_path
        self.progress_callback = progress_callback
        self._last_fetch_count = 0
        self.last_sweep_stats: Dict[str, Any] = {}

    def get_source_metadata(self) -> Dict[str, Any]:
        return {
            "source_type": "bis_live_api",
            "endpoint": SEARCH_URL,
            "max_number_swept": self.max_number,
            "last_fetch_count": self._last_fetch_count,
            **self.last_sweep_stats,
        }

    def _load_checkpoint(self) -> Dict[str, Any]:
        if os.path.exists(self.checkpoint_path):
            try:
                with open(self.checkpoint_path, "r", encoding="utf-8") as f:
                    state = json.load(f)
                if "records_by_standard" in state:
                    return state
            except Exception:
                pass
        return {"completed_numbers": [], "records_by_standard": {}, "capped_terms": [], "failed_terms": []}

    def _save_checkpoint(self, state: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.checkpoint_path), exist_ok=True)
        tmp_path = self.checkpoint_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(state, f)
        os.replace(tmp_path, self.checkpoint_path)

    async def _sweep_async(self) -> List[Dict[str, Any]]:
        state = self._load_checkpoint()
        completed = set(state.get("completed_numbers", []))
        records_by_standard: Dict[str, Dict[str, Any]] = state.get("records_by_standard", {})
        capped_terms = set(state.get("capped_terms", []))
        failed_terms = set(state.get("failed_terms", [])) - completed

        def snapshot():
            return {
                "completed_numbers": sorted(completed, key=int),
                "records_by_standard": records_by_standard,
                "capped_terms": sorted(capped_terms, key=int),
                "failed_terms": sorted(failed_terms, key=int),
            }

        pending = [n for n in range(1, self.max_number + 1) if str(n) not in completed]
        sem = asyncio.Semaphore(self.concurrency)
        checkpoint_lock = asyncio.Lock()
        done_counter = {"n": 0}

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:

            async def fetch_one(number: int):
                term = str(number)
                async with sem:
                    try:
                        resp = await client.post(
                            SEARCH_URL,
                            json={
                                "searchText": term,
                                "token": None,
                                "refreshToken": None,
                                "clientId": None,
                                "clientSecret": None,
                                "sub": None,
                            },
                            headers={"Content-Type": "application/json"},
                        )
                        if resp.status_code == 200:
                            hits = resp.json().get("data") or []
                            ok = True
                        else:
                            logger.warning(f"BIS live sweep got HTTP {resp.status_code} for '{term}'")
                            hits, ok = [], False
                    except Exception as e:
                        logger.warning(f"BIS live sweep request failed for '{term}': {e!r}")
                        hits, ok = [], False

                    await asyncio.sleep(self.delay_seconds)

                async with checkpoint_lock:
                    if ok:
                        for hit in hits:
                            std_num = (hit.get("standardNumber") or "").strip()
                            if std_num:
                                hit.pop("standardEncId", None)
                                records_by_standard[std_num] = hit
                        if len(hits) >= RESULT_CAP:
                            capped_terms.add(term)
                        completed.add(term)
                        failed_terms.discard(term)
                    else:
                        # Not marked complete, so a re-run retries it.
                        failed_terms.add(term)
                    done_counter["n"] += 1
                    if done_counter["n"] % 1000 == 0:
                        self._save_checkpoint(snapshot())
                        if self.progress_callback:
                            self.progress_callback(done_counter["n"], len(pending))
                        logger.info(
                            f"BIS live sweep progress: {done_counter['n']}/{len(pending)} terms, "
                            f"{len(records_by_standard)} distinct standards, {len(failed_terms)} failed terms"
                        )

            await asyncio.gather(*(fetch_one(n) for n in pending))

        self._save_checkpoint(snapshot())
        self.last_sweep_stats = {
            "terms_completed": len(completed),
            "terms_failed": len(failed_terms),
            "terms_hitting_result_cap": len(capped_terms),
            "distinct_standards_discovered": len(records_by_standard),
        }
        logger.info(f"BIS live sweep finished: {self.last_sweep_stats}")
        return list(records_by_standard.values())

    def fetch_standards(self) -> List[Dict[str, Any]]:
        raw_records = asyncio.run(self._sweep_async())
        self._last_fetch_count = len(raw_records)
        normalized = []
        for r in raw_records:
            rec = normalize_bis_record(_map_record(r), "BIS Know Your Standards (Live API)")
            # Department/committee ids are not domain categories; the ingestion
            # pipeline must not let them overwrite curated categories.
            rec["category_is_placeholder"] = True
            normalized.append(rec)
        return normalized
