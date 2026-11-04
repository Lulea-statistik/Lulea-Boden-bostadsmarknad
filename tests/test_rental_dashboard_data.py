"""Regressionskontroller för offentlig småhusbevakning och insamlingsstatus."""
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from src.write_listing_collection_status import build_status

ROOT = Path(__file__).resolve().parents[1]

def load(name):
    return json.loads((ROOT / "docs" / name).read_text(encoding="utf-8"))

class RentalDashboardDataTest(unittest.TestCase):
    def test_register_links_and_new_sources(self):
        data=load("villa_site_overlap.json")
        coverage=data["coverage"]
        self.assertEqual(coverage["reviewed_objects_in_master"],48)
        self.assertEqual(coverage["recorded_listing_rows"],70)
        self.assertEqual(coverage["source_page_only_without_historical_activity"],17)
        self.assertEqual(coverage["distinct_site_object_links"],68)
        self.assertEqual(coverage["unique_objects_multi_site"],17)
        self.assertEqual(len(data["sites"]),9)
        self.assertEqual(len(data["overlap_pairs"]),12)
        names={x["name"]:x for x in data["sites"]}
        self.assertEqual(names["Stugknuten"]["unique_objects"],1)
        self.assertEqual(names["Vrbo"]["unique_objects"],1)
        pairs={frozenset((x["site_a"],x["site_b"])):x["shared_unique_objects"]
               for x in data["overlap_pairs"]}
        self.assertEqual(pairs[frozenset(("Qasa","Stugknuten"))],1)
        self.assertEqual(pairs[frozenset(("Airbnb","Vrbo"))],1)
        self.assertEqual(sum(x["object_count"] for x in data["site_count_distribution"]),48)
        self.assertEqual(sum(x["site_count"]*x["object_count"]
                             for x in data["site_count_distribution"]),68)
        self.assertEqual(sum(x["unique_objects"] for x in data["sites"]),68)

    def test_older_snapshots_not_backfilled(self):
        rental=load("villa_rental_aggregates.json")
        self.assertEqual([x["snapshot"] for x in rental["snapshots"]],
                         ["2026-09-25","2026-10-02","2026-10-09","2026-10-16"])
        self.assertEqual([x["identified_unique_objects"] for x in rental["snapshots"]],
                         [31,38,52,66])
        self.assertEqual(rental["registered_listing_rows"],70)
        data=load("villa_site_overlap.json")
        self.assertTrue(data["historical_snapshot_2026_10_16_total_not_recomputed"])
        self.assertEqual(data["historical_snapshot_2026_10_16_total"],66)
        self.assertIn("not_market_availability",data["analysis_scope"])

    def test_no_private_rental_details_are_exposed(self):
        content=json.dumps(load("villa_site_overlap.json"),ensure_ascii=False)
        for token in ("LUL-","LIST-","canonical_address","source_url","source_key",
                      "Lövskärsvägen","Kängsövägen","https://"):
            self.assertNotIn(token,content)
        pending={x["name"] for x in load("villa_site_overlap.json")["pending_sources"]}
        self.assertTrue({"Stuga.se","Houserent","Stayment"}.issubset(pending))
        self.assertFalse({"Stuga.se","Houserent","Stayment"} &
                         {x["name"] for x in load("villa_site_overlap.json")["sites"]})

    def test_status_no_input_is_not_zero_active_houses(self):
        t=datetime(2026,11,6,6,30,tzinfo=timezone.utc)
        result=build_status(t,[],[], "synthetic-test")
        self.assertEqual(result["run_utc_date"],"2026-11-06")
        self.assertEqual(result["current_input_rows"],0)
        self.assertEqual(result["result"],"no_source_data")
        self.assertFalse(result["snapshot_created"])
        self.assertNotIn("active_objects",result)
        recorded=load("listing_collection_status.json")
        self.assertEqual(recorded["run_utc_date"],"2026-11-01")
        self.assertEqual(recorded["current_input_rows"],0)
        self.assertFalse(recorded["snapshot_created"])

    def test_status_with_supplied_row_is_not_external_collection_proof(self):
        t=datetime(2026,11,6,6,30,tzinfo=timezone.utc)
        current=[{"object_id":"EXAMPLE-ONLY-001"}]
        history=[{"object_id":"EXAMPLE-ONLY-001","snapshot_date":"2026-11-06"}]
        result=build_status(t,current,history)
        self.assertTrue(result["snapshot_created"])
        self.assertFalse(result["automated_external_listing_collection_configured"])
        self.assertEqual(result["result"],"snapshot_created_from_supplied_rows")

    def test_frontend_shows_current_network_and_collection_warning(self):
        html=(ROOT/"docs/uthyrning_smahus.html").read_text(encoding="utf-8")
        js=(ROOT/"docs/uthyrning_smahus.js").read_text(encoding="utf-8")
        self.assertIn("Stugknuten och Vrbo ingår",html)
        self.assertIn("rentalCollectionLatest",html)
        self.assertIn("source_page_only_without_historical_activity",js)
        self.assertIn("listing_collection_status.json",js)
        self.assertNotIn("INTE omräknade för det nyare registret",js)

if __name__ == "__main__":
    unittest.main()
