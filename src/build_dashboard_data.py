from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(".")
OUT = Path("docs/dashboard_data.json")


def read_csv(path: str) -> list[dict]:
    p = ROOT / path
    if not p.exists():
        return []
    with p.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main() -> None:
    data = {
        "maklar_current": read_csv("data/maklarstatistik/current.csv"),
        "maklar_history": read_csv("data/maklarstatistik/history.csv"),
        "listing_weekly": read_csv("data/indicators/weekly.csv"),
        "listing_monthly": read_csv("data/indicators/monthly.csv"),
        "scb_newbuild": read_csv("data/scb/new_small_house_prices.csv"),
        "scb_holiday_house": read_csv("data/scb/holiday_house_prices_quarterly.csv"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "Dashboard data:",
        len(data["maklar_current"]),
        "current market rows,",
        len(data["maklar_history"]),
        "market history rows,",
        len(data["listing_weekly"]),
        "weekly listing rows,",
        len(data["scb_newbuild"]),
        "SCB new-build rows,",
        len(data["scb_holiday_house"]),
        "SCB holiday-house rows",
    )


if __name__ == "__main__":
    main()
