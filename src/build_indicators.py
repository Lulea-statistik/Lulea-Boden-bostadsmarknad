from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Optional

HISTORY = Path("data/listings/history.csv")
WEEKLY_OUT = Path("data/indicators/weekly.csv")
MONTHLY_OUT = Path("data/indicators/monthly.csv")

WEEKLY_FIELDS = [
    "snapshot_date",
    "year_week",
    "kommun",
    "bostadstyp",
    "active_objects",
    "new_objects",
    "removed_objects",
    "net_change",
    "price_reductions",
    "median_asking_price",
    "median_price_per_m2",
    "median_days_on_market",
]

MONTHLY_FIELDS = [
    "year_month",
    "kommun",
    "bostadstyp",
    "active_objects",
    "new_objects",
    "removed_objects",
    "net_change",
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


def median(values: Iterable[Optional[float]]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return statistics.median(vals) if vals else None


def read_history() -> list[dict]:
    if not HISTORY.exists():
        return []
    with HISTORY.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def build_weekly(rows: list[dict]) -> list[dict]:
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

    out: list[dict] = []
    previous_rows: list[dict] = []

    for snapshot in snapshots:
        current = by_snapshot[snapshot]
        current_by_group: dict[tuple[str, str], list[dict]] = defaultdict(list)
        previous_by_group: dict[tuple[str, str], list[dict]] = defaultdict(list)

        for r in current:
            current_by_group[(r.get("kommun", ""), r.get("bostadstyp", ""))].append(r)
        for r in previous_rows:
            previous_by_group[(r.get("kommun", ""), r.get("bostadstyp", ""))].append(r)

        groups = sorted(set(current_by_group) | set(previous_by_group))
        for kommun, bostadstyp in groups:
            group = current_by_group.get((kommun, bostadstyp), [])
            prev_group = previous_by_group.get((kommun, bostadstyp), [])

            ids = {r.get("object_id", "") for r in group if r.get("object_id")}
            prev_ids = {r.get("object_id", "") for r in prev_group if r.get("object_id")}
            new_ids = ids - prev_ids if previous_rows else ids
            removed_ids = prev_ids - ids if previous_rows else set()

            prev_prices = {
                r.get("object_id", ""): p
                for r in prev_group
                if r.get("object_id")
                and (p := parse_float(r.get("utgangspris", ""))) is not None
            }
            reduced = 0
            for r in group:
                oid = r.get("object_id", "")
                price = parse_float(r.get("utgangspris", ""))
                if oid in prev_prices and price is not None and price < prev_prices[oid]:
                    reduced += 1

            asking = [parse_float(r.get("utgangspris", "")) for r in group]
            ppm2 = [parse_float(r.get("pris_per_m2", "")) for r in group]
            days: list[float] = []
            for r in group:
                first = parse_date(r.get("first_seen", ""))
                if first:
                    days.append(float((snapshot - first).days))

            iso_year, iso_week, _ = snapshot.isocalendar()
            out.append(
                {
                    "snapshot_date": snapshot.isoformat(),
                    "year_week": f"{iso_year}-V{iso_week:02d}",
                    "kommun": kommun,
                    "bostadstyp": bostadstyp,
                    "active_objects": len(ids),
                    "new_objects": len(new_ids),
                    "removed_objects": len(removed_ids),
                    "net_change": len(new_ids) - len(removed_ids),
                    "price_reductions": reduced,
                    "median_asking_price": median(asking),
                    "median_price_per_m2": median(ppm2),
                    "median_days_on_market": median(days),
                }
            )

        previous_rows = current

    return out


def build_monthly(weekly: list[dict]) -> list[dict]:
    latest: dict[tuple[str, str, str], dict] = {}
    for row in weekly:
        ym = row["snapshot_date"][:7]
        key = (ym, row["kommun"], row["bostadstyp"])
        old = latest.get(key)
        if old is None or row["snapshot_date"] > old["snapshot_date"]:
            latest[key] = row

    out: list[dict] = []
    for (ym, kommun, bostadstyp), row in sorted(latest.items()):
        out.append(
            {
                "year_month": ym,
                "kommun": kommun,
                "bostadstyp": bostadstyp,
                "active_objects": row["active_objects"],
                "new_objects": row["new_objects"],
                "removed_objects": row["removed_objects"],
                "net_change": row["net_change"],
                "price_reductions": row["price_reductions"],
                "median_asking_price": row["median_asking_price"],
                "median_price_per_m2": row["median_price_per_m2"],
                "median_days_on_market": row["median_days_on_market"],
            }
        )
    return out


def write(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    rows = read_history()
    weekly = build_weekly(rows)
    monthly = build_monthly(weekly)
    write(WEEKLY_OUT, WEEKLY_FIELDS, weekly)
    write(MONTHLY_OUT, MONTHLY_FIELDS, monthly)
    print(f"Read {len(rows)} listing rows")
    print(f"Wrote {len(weekly)} weekly indicator rows to {WEEKLY_OUT}")
    print(f"Wrote {len(monthly)} monthly indicator rows to {MONTHLY_OUT}")


if __name__ == "__main__":
    main()
