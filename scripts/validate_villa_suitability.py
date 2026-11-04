#!/usr/bin/env python3
"""Validate an anonymous rental suitability aggregate; reject everything else."""
import json
import sys
from pathlib import Path

def validate(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    expected = {"scope", "master_groups_reviewed", "class_counts", "classification_coverage",
                "current_available_permanent_housing", "historical_total_2026_10_16", "note"}
    if set(data) != expected:
        raise ValueError("Export has unexpected fields")
    if data["scope"] != "existing_private_registry_master_groups_not_active_rentals":
        raise ValueError("Incorrect scope")
    counts = data["class_counts"]
    if set(counts) != {"A","B","C","D","U"} or any(type(v) is not int or v<0 for v in counts.values()):
        raise ValueError("Invalid counts")
    n = data["master_groups_reviewed"]
    if type(n) is not int or n < 0 or sum(counts.values()) != n:
        raise ValueError("Invalid master total")
    if data["classification_coverage"] != sum(counts[k] for k in ("A","B","C")):
        raise ValueError("Invalid coverage")
    if data["current_available_permanent_housing"] is not None or data["historical_total_2026_10_16"] != 66:
        raise ValueError("Unsafe availability/historical status")
    if not isinstance(data["note"],str) or len(data["note"]) > 250:
        raise ValueError("Invalid note")
    return json.dumps(data,ensure_ascii=False,indent=2)+"\n"

if __name__=="__main__":
    print(validate(sys.argv[1]),end="")
