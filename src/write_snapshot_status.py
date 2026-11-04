from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from pathlib import Path

CURRENT = Path("data/listings/current.csv")
STATUS = Path("data/listings/run_status.csv")
FIELDS = [
    "run_id", "run_attempt", "run_at_utc", "run_date_utc",
    "trigger", "snapshot_result", "indicators_result", "dashboard_result",
    "input_rows", "collection_status", "workflow_status",
]


def count_input_rows() -> int:
    if not CURRENT.exists():
        return 0
    with CURRENT.open(newline="", encoding="utf-8-sig") as handle:
        return sum(1 for row in csv.DictReader(handle)
                   if any(str(value or "").strip() for value in row.values()))


def classify(snapshot: str, indicators: str, dashboard: str, count: int) -> tuple[str, str]:
    outcomes = (snapshot, indicators, dashboard)
    if any(outcome != "success" for outcome in outcomes):
        return "incomplete", "failed"
    if count == 0:
        # No connected/usable listing feed: this is NOT an observation of zero active houses.
        return "no_input_rows", "success_no_data"
    return "input_rows_available", "success_with_data"


def main() -> None:
    now = datetime.now(timezone.utc)
    outcomes = [os.environ.get(name, "unknown") for name in
                ("SNAPSHOT_OUTCOME", "INDICATORS_OUTCOME", "DASHBOARD_OUTCOME")]
    count = count_input_rows()
    collection, overall = classify(*outcomes, count)
    row = {
        "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", "1"),
        "run_at_utc": now.isoformat(timespec="seconds"),
        "run_date_utc": now.date().isoformat(),
        "trigger": os.environ.get("GITHUB_EVENT_NAME", "manual"),
        "snapshot_result": outcomes[0],
        "indicators_result": outcomes[1],
        "dashboard_result": outcomes[2],
        "input_rows": count,
        "collection_status": collection,
        "workflow_status": overall,
    }
    rows = []
    if STATUS.exists():
        with STATUS.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
    rows = [existing for existing in rows
            if (existing.get("run_id"), existing.get("run_attempt"))
            != (row["run_id"], row["run_attempt"])]
    rows.append(row)
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    with STATUS.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    summary = (f"### Weekly listings run status\n"
               f"- Run: {row['run_id']} (attempt {row['run_attempt']})\n"
               f"- UTC time: {row['run_at_utc']}\n"
               f"- Steps: snapshot={outcomes[0]}, indicators={outcomes[1]}, dashboard={outcomes[2]}\n"
               f"- Current input rows: {count}\n"
               f"- Collection: **{collection}**; workflow: **{overall}**\n"
               f"- No input rows must not be interpreted as zero active rental houses.\n")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
            handle.write(summary)
    print(summary)


if __name__ == "__main__":
    main()
