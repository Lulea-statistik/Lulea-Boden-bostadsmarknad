from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import requests

API_URL = "https://api.scb.se/OV0104/v1/doris/sv/ssd/START/BO/BO0201/BO0201C/PrisPerAreorSM02"
SOURCE_URL = "https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__BO__BO0201__BO0201C/PrisPerAreorSM02/"
OUT = Path("data/scb/new_small_house_prices.csv")
FIELDS = ["measure", "region", "price_type", "year", "value", "source_url"]


def fetch_metadata() -> dict:
    r = requests.get(
        API_URL,
        timeout=60,
        headers={"User-Agent": "Lulea-Boden-bostadsmarknad/1.0 (public statistical analysis)"},
    )
    r.raise_for_status()
    return r.json()


def build_query(metadata: dict) -> dict:
    query = []
    for variable in metadata["variables"]:
        query.append(
            {
                "code": variable["code"],
                "selection": {"filter": "all", "values": ["*"]},
            }
        )
    return {"query": query, "response": {"format": "json-stat2"}}


def labels_from_metadata(metadata: dict) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for variable in metadata["variables"]:
        values = variable.get("values", [])
        labels = variable.get("valueTexts", values)
        out[variable["code"]] = dict(zip(values, labels))
    return out


def identify_dimensions(metadata: dict) -> dict[str, str]:
    result = {}
    for variable in metadata["variables"]:
        code = variable["code"]
        text = (variable.get("text", "") + " " + code).lower()
        if "region" in text:
            result["region"] = code
        elif "brutto" in text or "netto" in text or "pris" in text and "tabell" not in text:
            result["price_type"] = code
        elif "tabellinnehåll" in text or "contents" in text:
            result["measure"] = code
        elif "år" in text or "time" in text or variable.get("time"):
            result["year"] = code

    # Fallback to table order used by this SCB table.
    codes = [v["code"] for v in metadata["variables"]]
    if "region" not in result and len(codes) > 0:
        result["region"] = codes[0]
    if "price_type" not in result and len(codes) > 1:
        result["price_type"] = codes[1]
    if "measure" not in result and len(codes) > 2:
        result["measure"] = codes[2]
    if "year" not in result and len(codes) > 3:
        result["year"] = codes[3]
    return result


def ordered_codes(category: dict) -> list[str]:
    idx = category.get("index", {})
    if isinstance(idx, list):
        return idx
    return [k for k, _ in sorted(idx.items(), key=lambda kv: kv[1])]


def main() -> None:
    metadata = fetch_metadata()
    query = build_query(metadata)

    r = requests.post(
        API_URL,
        json=query,
        timeout=120,
        headers={"User-Agent": "Lulea-Boden-bostadsmarknad/1.0 (public statistical analysis)"},
    )
    r.raise_for_status()
    data = r.json()

    dim_ids = data["id"]
    dimensions = data["dimension"]
    values = data["value"]
    labels = labels_from_metadata(metadata)
    dims = identify_dimensions(metadata)

    codes_by_dim = {d: ordered_codes(dimensions[d]["category"]) for d in dim_ids}

    rows = []
    flat_index = 0

    import itertools
    for combo in itertools.product(*(codes_by_dim[d] for d in dim_ids)):
        combo_map = dict(zip(dim_ids, combo))
        value = values[flat_index] if isinstance(values, list) else values.get(str(flat_index))
        flat_index += 1

        def label(dim_key: str) -> str:
            code = dims[dim_key]
            raw = combo_map[code]
            return labels.get(code, {}).get(raw, raw)

        rows.append(
            {
                "measure": label("measure"),
                "region": label("region"),
                "price_type": label("price_type"),
                "year": label("year"),
                "value": "" if value is None else value,
                "source_url": SOURCE_URL,
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} SCB rows to {OUT}")
    print("Regions:", ", ".join(sorted({r["region"] for r in rows})))
    print("Measures:", ", ".join(sorted({r["measure"] for r in rows})))


if __name__ == "__main__":
    main()
