#!/usr/bin/env python3
"""Audit public-safe rental summary, not live listing availability."""
from __future__ import annotations
import json
from pathlib import Path

DOCS=Path(__file__).resolve().parents[1]/"docs"

def check():
    with (DOCS/"villa_site_overlap.json").open(encoding="utf-8") as f:
        net=json.load(f)
    with (DOCS/"villa_rental_aggregates.json").open(encoding="utf-8") as f:
        old=json.load(f)
    sites=net["sites"]
    counts={x["name"]:x for x in sites}
    coverage=net["coverage"]
    pairs=net["overlap_pairs"]
    buckets=net["site_count_distribution"]
    assert len(sites)==9 and "Stugknuten" in counts and "Vrbo" in counts, "Nya källor saknas i nätverket"
    assert coverage["reviewed_objects_in_master"]==48
    assert coverage["recorded_listing_rows"]==70
    assert coverage["source_page_only_without_historical_activity"]==17
    assert coverage["distinct_site_object_links"]==sum(x["unique_objects"] for x in sites)==sum(x["site_count"]*x["object_count"] for x in buckets)==68
    assert coverage["objects_with_listing_links"]==sum(x["object_count"] for x in buckets)==48
    assert coverage["unique_objects_multi_site"]==17
    assert coverage["unique_objects_single_site"]==31
    assert coverage["master_groups_confirmed"]==34
    assert coverage["master_groups_probable"]==14
    for p in pairs:
        a,b=p["site_a"],p["site_b"]
        assert a in counts and b in counts and a!=b
        n=p["shared_unique_objects"]
        assert 0<n<=min(counts[a]["unique_objects"],counts[b]["unique_objects"])
    pairmap={frozenset((x["site_a"],x["site_b"])):x["shared_unique_objects"] for x in pairs}
    assert len(pairmap)==len(pairs)==12
    assert pairmap[frozenset(("Airbnb","Vrbo"))]==1
    assert pairmap[frozenset(("Qasa","Stugknuten"))]==1
    assert old["uncollected_snapshot_dates"]==["2026-10-23","2026-10-30"]
    assert [x["identified_unique_objects"] for x in old["snapshots"]]==[31,38,52,66]
    assert old["master_groups_registered"]==48
    assert old["registered_listing_rows"]==70
    assert net["historical_snapshot_2026_10_16_total_not_recomputed"] is True
    assert net["is_current_private_register_overlap"] is True
    assert all(x["name"] not in counts for x in net["pending_sources"])
    for forbidden in ("LUL-","LIST-","source_url","source_key","address_as_published","canonical_address","Lövskärsvägen","Flarkenvägen"):
        assert forbidden not in json.dumps(net,ensure_ascii=False), f"Privat objektinformation får inte publiceras: {forbidden}"
    assert "simultaneously" not in net.get("analysis_scope","")
    print(f"OK: {len(sites)} webbplatser, {len(pairs)} dokumenterade par, 48 mastergrupper, 70 annonsrader.")
    print("Observera: ingen aktuell tillgänglighet verifieras. 23/30 oktober redovisas som saknade.")
if __name__=="__main__":
    check()
