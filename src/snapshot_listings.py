from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

CURRENT = Path("data/listings/current.csv")
HISTORY = Path("data/listings/history.csv")

FIELDS = [
    "snapshot_date",
    "object_id",
    "kommun",
    "omrade",
    "adress",
    "bostadstyp",
    "utgangspris",
    "boarea",
    "rum",
    "avgift",
    "pris_per_m2",
    "maklare",
    "nyproduktion",
    "first_seen",
    "last_seen",
    "source",
    "source_url",
]


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    today = date.today().isoformat()
    current = read_csv(CURRENT)
    history = read_csv(HISTORY)

    # Empty current file is valid while no permitted listing source is connected.
    if not current:
        print("No listing rows in current.csv; no snapshot created.")
        return

    first_seen_by_id: dict[str, str] = {}
    for row in history:
        oid = row.get("object_id", "").strip()
        first_seen = row.get("first_seen", "").strip()
        if oid and first_seen:
            old = first_seen_by_id.get(oid)
            if old is None or first_seen < old:
                first_seen_by_id[oid] = first_seen

    snapshot_rows: list[dict] = []
    for row in current:
        oid = row.get("object_id", "").strip()
        if not oid:
            raise RuntimeError("Every listing row must have a non-empty object_id.")

        out = {field: row.get(field, "") for field in FIELDS}
        out["snapshot_date"] = today
        out["first_seen"] = first_seen_by_id.get(oid) or row.get("first_seen", "").strip() or today
        out["last_seen"] = today
        snapshot_rows.append(out)

    # Deduplicate on snapshot date + object ID. Re-running the same day is safe.
    keyed: dict[tuple[str, str], dict] = {}
    for row in history + snapshot_rows:
        key = (row.get("snapshot_date", ""), row.get("object_id", ""))
        keyed[key] = row

    rows = sorted(
        keyed.values(),
        key=lambda r: (r.get("snapshot_date", ""), r.get("object_id", "")),
    )
    write_csv(HISTORY, rows)

    # Keep current.csv synchronized with first/last seen values too.
    write_csv(CURRENT, snapshot_rows)

    print(f"Snapshotted {len(snapshot_rows)} active listings for {today}.")
    print(f"History now contains {len(rows)} rows.")


if __name__ == "__main__":
    main()
