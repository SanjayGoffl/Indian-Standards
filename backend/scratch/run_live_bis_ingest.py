"""
One-off runner: sweeps the real BIS "Know Your Standards" API and ingests
results into the live DB via the standard ingestion pipeline (change
detection, ChromaDB embedding, audit logging). Safe to re-run — it's
incremental via content hashing, and the sweep itself resumes from
scratch/bis_live_sweep_checkpoint.json if interrupted.
"""
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from app.core.database import SessionLocal
from app.services.bis_live_connector import BISLiveAPIConnector
from app.services.standards_ingestion import ingest_standards

def main():
    session = SessionLocal()
    try:
        connector = BISLiveAPIConnector(max_number=20000, concurrency=4, delay_seconds=0.05)
        summary = ingest_standards(session, connector)
        print("SWEEP STATS:", connector.last_sweep_stats)
        print("INGEST SUMMARY:", {k: v for k, v in summary.items() if k != "error_summary"})
        print("ERRORS (first 20):", summary.get("error_summary", [])[:20])
    finally:
        session.close()

if __name__ == "__main__":
    main()
