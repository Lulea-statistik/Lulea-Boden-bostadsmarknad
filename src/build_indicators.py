from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Optional

HISTORY = Path("data/listings/history.csv")
OUT = Path("data/indicators/monthly.csv")

FIELDS = [
    "year_month",
    "kommun",
    "bostadstyp",
    "active_objects",
    "new_objects",
    "removed_objects",
    "price_reductions",
    "median_asking_price",
    "median_price_per_m2",
    "median_days_on_market",
]


def parse_date(value: str) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_float(value: str) -> Optional[float]:
    if value is None:
        return None
    value = str(value).strip().replace(" ", "").replace(",", ".")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def median(values: Iterable[float]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return statistics.median(vals) if vals else None


def read_history() -> list[dict]:
    if not HISTORY.exists():
        return []
    with HISTORY.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def build(rows: list[dict]) -> list[dict]:
    if not rows:
        return []

    snapshots = sorted(
        {d for d in (parse_date(r.get("snapshot_date", "")) for r in rows) if d}
    )

    by_snapshot: dict[date, list[dict]] = defaultdict(list)
    for r in rows:
        d = parse_date(r.get("snapshot_date", ""))
        if d:
            by_snapshot[d].append(r)

    # Compare each snapshot with the immediately preceding one.
    transitions: dict[date, dict] = {}
    previous_ids: set[str] = set()
    previous_prices: dict[str, float] = {}

    for d in snapshots:
        current = by_snapshot[d]
        current_ids = {r["object_id"] for r in current if r.get("object_id")}
        current_prices = {
            r["object_id"]: p
            for r in current
            if r.get("object_id") and (p := parse_float(r.get("utgangspris", ""))) is not None
        }

        new_ids = current_ids - previous_ids if previous_ids else current_ids
        removed_ids = previous_ids - current_ids if previous_ids else set()
        reduced_ids = {
            oid
            for oid, price in current_prices.items()
            if oid in previous_prices and price < previous_prices[oid]
        }

        transitions[d] = {
            "new_ids": new_ids,
            "removed_ids": removed_ids,
            "reduced_ids": reduced_ids,
            "previous_rows": by_snapshot.get(snapshots[snapshots.index(d)-1], []) if snapshots.index(d) > 0 else [],
        }

        previous_ids = current_ids
        previous_prices = current_prices

    # Monthly output uses the latest snapshot in each month.
    latest_by_month: dict[str, date] = {}
    for d in snapshots:
        latest_by_month[d.strftime("%Y-%m")] = d

    out: list[dict] = []
    for ym, snapshot in sorted(latest_by_month.items()):
        current = by_snapshot[snapshot]
        transition = transitions[snapshot]

        groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for r in current:
            groups[(r.get("kommun", ""), r.get("bostadstyp", ""))].append(r)

        # Include groups present only in the previous snapshot so removals are not lost.
        previous_rows = transition["previous_rows"]
        for r in previous_rows:
            groups.setdefault((r.get("kommun", ""), r.get("bostadstyp", "")), [])

        for (kommun, bostadstyp), group in sorted(groups.items()):
            ids = {r.get("object_id", "") for r in group}
            previous_group_ids = {
                r.get("object_id", "")
                for r in previous_rows
                if r.get("kommun", "") == kommun and r.get("bostadstyp", "") == bostadstyp
            }

            asking_prices = [parse_float(r.get("utgangspris", "")) for r in group]
            ppm2 = [parse_float(r.get("pris_per_m2", "")) for r in group]

            days = []
            for r in group:
                first = parse_date(r.get("first_seen", ""))
                if first:
                    days.append((snapshot - first).days)

            out.append(
                {
                    "year_month": ym,
                    "kommun": kommun,
                    "bostadstyp": bostadstyp,
                    "active_objects": len(ids - {""}),
                    "new_objects": len((ids & transition["new_ids"]) - {""}),
                    "removed_objects": len((previous_group_ids & transition["removed_ids"]) - {""}),
                    "price_reductions": len((ids & transition["reduced_ids"]) - {""}),
                    "median_asking_price": median(asking_prices),
                    "median_price_per_m2": median(ppm2),
                    "median_days_on_market": median(days),
                }
            )

    return out


def write(rows: list[dict]) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    rows = read_history()
    indicators = build(rows)
    write(indicators)
    print(f"Read {len(rows)} listing rows")
    print(f"Wrote {len(indicators)} indicator rows to {OUT}")


if __name__ == "__main__":
    main()
