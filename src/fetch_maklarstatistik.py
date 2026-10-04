from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup


SOURCES = {
    "Luleå": "https://www.maklarstatistik.se/omrade/riket/norrbottens-lan/lulea/",
    "Boden": "https://www.maklarstatistik.se/omrade/riket/norrbottens-lan/boden/",
}

PROPERTY_TYPES = ["Bostadsrätter", "Villor", "Fritidshus"]
PERIODS = ["3 månader", "12 månader"]

OUTDIR = Path("data/maklarstatistik")
CURRENT = OUTDIR / "current.csv"
HISTORY = OUTDIR / "history.csv"

FIELDS = [
    "snapshot_date",
    "source_updated",
    "kommun",
    "bostadstyp",
    "period",
    "pris_per_m2",
    "medelpris",
    "antal_salda",
    "prisutveckling_pct",
    "prisutveckling_status",
    "source_url",
]


def parse_int(value: str) -> Optional[int]:
    digits = re.sub(r"[^0-9-]", "", value)
    return int(digits) if digits else None


def parse_change(value: str) -> tuple[Optional[float], str]:
    value = value.strip().replace(",", ".")
    if value in {"F", "N"}:
        return None, value
    match = re.search(r"([+-]?\d+(?:\.\d+)?)", value)
    if not match:
        return None, value or "saknas"
    return float(match.group(1)), "OK"


def fetch_text(url: str) -> str:
    headers = {
        "User-Agent": (
            "Lulea-Boden-bostadsmarknad/1.0 "
            "(municipal market analysis; low-frequency public-page collection)"
        )
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    return "\n".join(
        line.strip()
        for line in soup.get_text("\n").splitlines()
        if line.strip()
    )


def parse_source_updated(text: str) -> str:
    match = re.search(
        r"Uppdaterat:\s*(\d{2})\s+([A-Za-zÅÄÖåäö]+)\s+(\d{4})",
        text,
        re.IGNORECASE,
    )
    if not match:
        return ""

    day, month_name, year = match.groups()
    months = {
        "januari": 1, "februari": 2, "mars": 3, "april": 4,
        "maj": 5, "juni": 6, "juli": 7, "augusti": 8,
        "september": 9, "oktober": 10, "november": 11, "december": 12,
    }
    month = months.get(month_name.lower())
    if not month:
        return ""
    return f"{year}-{month:02d}-{int(day):02d}"


def parse_rows(kommun: str, url: str, text: str) -> list[dict]:
    # The top summary is published in a fixed order:
    # Bostadsrätter, Villor, Fritidshus; each with 3 and 12 months.
    # We only parse the summary before the first "Prisutveckling" chart section.
    summary = text.split("\n## Prisutveckling", 1)[0]
    if summary == text:
        summary = text.split("\nPrisutveckling\n", 1)[0]

    pattern = re.compile(
        r"(3 månader|12 månader)\s*"
        r"([0-9\s]+)\s*kr/kvm\s*"
        r"([0-9\s]+)\s*medelpris\s*"
        r"([0-9\s]+)\s*antal sålda\s*"
        r"([+\-]?\d+(?:[\.,]\d+)?%|F|N)\s*prisutveckling",
        re.IGNORECASE,
    )

    matches = list(pattern.finditer(summary))
    if len(matches) < 6:
        # Fallback for HTML text where line breaks/spacing differ.
        compact = re.sub(r"\s+", " ", summary)
        matches = list(pattern.finditer(compact))

    if len(matches) < 6:
        raise RuntimeError(
            f"Expected at least 6 summary blocks for {kommun}, found {len(matches)}. "
            "The source page structure may have changed."
        )

    source_updated = parse_source_updated(text)
    snapshot = date.today().isoformat()
    rows: list[dict] = []

    for index, match in enumerate(matches[:6]):
        property_type = PROPERTY_TYPES[index // 2]
        period, ppm2, mean_price, sold, change = match.groups()
        change_value, change_status = parse_change(change.replace("%", ""))

        rows.append(
            {
                "snapshot_date": snapshot,
                "source_updated": source_updated,
                "kommun": kommun,
                "bostadstyp": property_type,
                "period": period,
                "pris_per_m2": parse_int(ppm2),
                "medelpris": parse_int(mean_price),
                "antal_salda": parse_int(sold),
                "prisutveckling_pct": change_value,
                "prisutveckling_status": change_status,
                "source_url": url,
            }
        )

    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def update_history(new_rows: list[dict]) -> None:
    existing: list[dict] = []
    if HISTORY.exists():
        with HISTORY.open("r", newline="", encoding="utf-8-sig") as f:
            existing = list(csv.DictReader(f))

    # One observation per source publication date + municipality/type/period.
    # Re-running the workflow therefore does not duplicate unchanged monthly data.
    keyed = {}
    for row in existing + new_rows:
        key = (
            row.get("source_updated", ""),
            row.get("kommun", ""),
            row.get("bostadstyp", ""),
            row.get("period", ""),
        )
        keyed[key] = row

    rows = sorted(
        keyed.values(),
        key=lambda r: (
            r.get("source_updated", ""),
            r.get("kommun", ""),
            r.get("bostadstyp", ""),
            r.get("period", ""),
        ),
    )
    write_csv(HISTORY, rows)


def validate(rows: list[dict]) -> None:
    expected = len(SOURCES) * len(PROPERTY_TYPES) * len(PERIODS)
    if len(rows) != expected:
        raise RuntimeError(f"Expected {expected} rows, got {len(rows)}")

    for row in rows:
        if not row["source_updated"]:
            raise RuntimeError(f"Missing source_updated: {row}")
        if row["antal_salda"] is None:
            raise RuntimeError(f"Missing antal_salda: {row}")


def main() -> None:
    all_rows: list[dict] = []
    for kommun, url in SOURCES.items():
        print(f"Fetching {kommun}: {url}")
        text = fetch_text(url)
        rows = parse_rows(kommun, url, text)
        all_rows.extend(rows)
        print(f"  parsed {len(rows)} rows")

    validate(all_rows)
    write_csv(CURRENT, all_rows)
    update_history(all_rows)
    print(f"Wrote {CURRENT} and {HISTORY}")


if __name__ == "__main__":
    main()
