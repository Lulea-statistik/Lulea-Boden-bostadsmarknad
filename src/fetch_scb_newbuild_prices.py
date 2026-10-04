from __future__ import annotations

import csv
import itertools
import json
import re
from pathlib import Path

import requests

TABLE_ID = "000003J5"
API_URL = f"https://statistikdatabasen.scb.se/api/v2/tables/{TABLE_ID}/data"
OUT = Path("data/scb/new_small_house_prices.csv")
FIELDS = ["measure", "region", "price_type", "year", "value", "table_id", "source_url"]


def ordered_codes(category: dict) -> list[str]:
    index = category.get("index", {})
    if isinstance(index, list):
        return list(index)
    if isinstance(index, dict):
        return [k for k, _ in sorted(index.items(), key=lambda kv: kv[1])]
    return []


def label_for(category: dict, code: str) -> str:
    labels = category.get("label", {}) or {}
    return labels.get(code, code)


def normalise_label(value: str) -> str:
    return re.sub(r"[^a-zåäö0-9]+", "", value.lower())


def choose_dimension(dim_ids: list[str], dimensions: dict, kind: str) -> str:
    candidates = []
    for dim_id in dim_ids:
        label = str(dimensions.get(dim_id, {}).get("label", dim_id))
        norm = normalise_label(label + " " + dim_id)
        candidates.append((dim_id, norm))
    tests = {
        "measure": ["tabellinnehåll", "contents", "content"],
        "region": ["region"],
        "price_type": ["bruttonettopris", "pristyp", "price"],
        "year": ["år", "time", "year"],
    }
    for needle in tests[kind]:
        for dim_id, norm in candidates:
            if normalise_label(needle) in norm:
                return dim_id
    raise RuntimeError(f"Could not identify {kind} dimension from {candidates}")


def main() -> None:
    params = [
        ("lang", "sv"),
        ("outputFormat", "json-stat2"),
    ]
    response = requests.get(
        API_URL,
        params=params,
        timeout=60,
        headers={"User-Agent": "Lulea-Boden-bostadsmarknad/1.0 (public statistical analysis)"},
    )
    response.raise_for_status()
    data = response.json()

    dim_ids = data["id"]
    sizes = data["size"]
    dimensions = data["dimension"]
    values = data.get("value", [])

    measure_dim = choose_dimension(dim_ids, dimensions, "measure")
    region_dim = choose_dimension(dim_ids, dimensions, "region")
    price_dim = choose_dimension(dim_ids, dimensions, "price_type")
    year_dim = choose_dimension(dim_ids, dimensions, "year")

    codes_by_dim = {d: ordered_codes(dimensions[d]["category"]) for d in dim_ids}
    expected = 1
    for size in sizes:
        expected *= size
    if isinstance(values, list) and len(values) != expected:
        raise RuntimeError(f"Unexpected JSON-stat value count: {len(values)} != {expected}")

    rows = []
    combos = itertools.product(*(codes_by_dim[d] for d in dim_ids))
    for flat_index, combo in enumerate(combos):
        combo_map = dict(zip(dim_ids, combo))
        if isinstance(values, list):
            value = values[flat_index]
        else:
            value = values.get(str(flat_index))

        def lbl(dim: str) -> str:
            return label_for(dimensions[dim]["category"], combo_map[dim])

        rows.append(
            {
                "measure": lbl(measure_dim),
                "region": lbl(region_dim),
                "price_type": lbl(price_dim),
                "year": lbl(year_dim),
                "value": "" if value is None else value,
                "table_id": TABLE_ID,
                "source_url": "https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__BO__BO0201__BO0201C/PrisPerAreorSM02/",
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} SCB rows to {OUT}")
    print("Regions:", ", ".join(sorted({r["region"] for r in rows})))


if __name__ == "__main__":
    main()
