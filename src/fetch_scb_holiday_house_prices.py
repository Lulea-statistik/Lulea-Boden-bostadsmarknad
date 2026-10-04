from __future__ import annotations

import csv
import itertools
from pathlib import Path

import requests

API_URL = "https://api.scb.se/OV0104/v1/doris/sv/ssd/START/BO/BO0501/BO0501B/FastprisFHRegKv"
SOURCE_URL = "https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__BO__BO0501__BO0501B/FastprisFHRegKv/"
OUT = Path("data/scb/holiday_house_prices_quarterly.csv")
FIELDS = ["measure", "region", "quarter", "value", "source_url"]


def fetch_metadata() -> dict:
    r = requests.get(
        API_URL,
        timeout=60,
        headers={"User-Agent": "Lulea-Boden-bostadsmarknad/1.0 (public statistical analysis)"},
    )
    r.raise_for_status()
    return r.json()


def build_query(metadata: dict) -> dict:
    return {
        "query": [
            {
                "code": v["code"],
                "selection": {"filter": "all", "values": ["*"]},
            }
            for v in metadata["variables"]
        ],
        "response": {"format": "json-stat2"},
    }


def label_maps(metadata: dict) -> dict[str, dict[str, str]]:
    out = {}
    for v in metadata["variables"]:
        values = v.get("values", [])
        labels = v.get("valueTexts", values)
        out[v["code"]] = dict(zip(values, labels))
    return out


def identify_dimensions(metadata: dict) -> dict[str, str]:
    result = {}
    for v in metadata["variables"]:
        code = v["code"]
        text = (v.get("text", "") + " " + code).lower()
        if "region" in text:
            result["region"] = code
        elif "tabellinnehåll" in text or "contents" in text:
            result["measure"] = code
        elif "kvartal" in text or "quarter" in text or v.get("time"):
            result["quarter"] = code

    codes = [v["code"] for v in metadata["variables"]]
    if "measure" not in result and len(codes) > 0:
        result["measure"] = codes[0]
    if "region" not in result and len(codes) > 1:
        result["region"] = codes[1]
    if "quarter" not in result and len(codes) > 2:
        result["quarter"] = codes[2]
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
    labels = label_maps(metadata)
    dims = identify_dimensions(metadata)
    codes_by_dim = {d: ordered_codes(dimensions[d]["category"]) for d in dim_ids}

    rows = []
    for flat_index, combo in enumerate(itertools.product(*(codes_by_dim[d] for d in dim_ids))):
        combo_map = dict(zip(dim_ids, combo))
        value = values[flat_index] if isinstance(values, list) else values.get(str(flat_index))

        def label(dim_key: str) -> str:
            code = dims[dim_key]
            raw = combo_map[code]
            return labels.get(code, {}).get(raw, raw)

        rows.append(
            {
                "measure": label("measure"),
                "region": label("region"),
                "quarter": label("quarter"),
                "value": "" if value is None else value,
                "source_url": SOURCE_URL,
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} SCB fritidshus rows to {OUT}")
    print("Regions:", ", ".join(sorted({r["region"] for r in rows})))
    print("Measures:", ", ".join(sorted({r["measure"] for r in rows})))
    print("Quarter range:", min(r["quarter"] for r in rows), "-", max(r["quarter"] for r in rows))


if __name__ == "__main__":
    main()
