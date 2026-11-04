"""Publicera status för veckojobbet separat från marknadsobservationer.

En lyckad schemalagd GitHub Actions-körning är inte bevis på att externa
annonser hämtats, och tom indata ska INTE skapa en nollobservation.
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

CURRENT = Path("data/listings/current.csv")
HISTORY = Path("data/listings/history.csv")
OUT = Path("docs/listing_collection_status.json")

def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def build_status(now: datetime, current: list[dict], history: list[dict], run_id: str = "") -> dict:
    day = now.astimezone(timezone.utc).date().isoformat()
    saved = [row for row in history if row.get("snapshot_date") == day]
    has_snapshot = bool(current) and len(saved) == len({r.get("object_id") for r in current})
    result = "snapshot_created_from_supplied_rows" if has_snapshot else (
        "no_source_data" if not current else "snapshot_not_verified"
    )
    return {
        "run_utc_date": day,
        "run_utc_timestamp": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "github_run_id": run_id,
        "result": result,
        "current_input_rows": len(current),
        "snapshot_created": has_snapshot,
        "archived_today_rows": len(saved),
        "cadence": "fredagar 06:30 UTC",
        "input_path": "data/listings/current.csv",
        "automated_external_listing_collection_configured": False,
        "date_of_last_manually_reported_rental_aggregate": "2026-10-16",
        "interpretation": "Statusen gäller arkivering av redan tillförda annonser. Ingen extern annonshämtare är kopplad till current.csv och teknisk success betyder inte att nya marknadsobservationer finns."
    }

def main() -> None:
    result = build_status(
        datetime.now(timezone.utc), read_rows(CURRENT), read_rows(HISTORY),
        os.environ.get("GITHUB_RUN_ID", ""),
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Collection status {result['run_utc_date']}: {result['result']} ({result['current_input_rows']} input rows).")

if __name__ == "__main__":
    main()
