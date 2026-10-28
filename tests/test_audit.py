"""Synthetic fixtures test accounting rules only; they never enter research outputs."""

import sys
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_data import evidence_date, longest_run, number, parse_tracker, rejection_reasons, summarize_rental, summarize_updates


def row(month="2025-01", price="2", version="v2/20250101-1", **overrides):
    record = dict(gpu="H100", form_factor="SXM", segment="neocloud_on_demand", market="on_demand",
                  provider="fixture", region="fixture-region", source="gpuhunt", source_version=version,
                  month=month, snapshot_date=month + "-01", usd_per_gpu_hour=price,
                  instance_types="fixture-instance", in_index="True", observation_type="catalog_snapshot")
    return dict(record, **overrides)


def update(day, price):
    timestamp = int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp() * 1000)
    return dict(date=timestamp, price=price, source="pPrice")


class AuditTests(unittest.TestCase):
    def test_backfill_is_excluded_even_when_upstream_includes_it(self):
        self.assertIn("effective_date_backfill", rejection_reasons(row(observation_type="effective_date_backfill")))

    def test_aws_uses_publication_version_not_effective_month(self):
        observed = evidence_date(row(month="2025-06", source="aws_bulk", version="20250703204906"))
        self.assertEqual(observed, date(2025, 7, 3))

    def test_reused_snapshot_does_not_create_a_new_comparison(self):
        summary = summarize_rental([row(), row(month="2025-02", snapshot_date="2025-01-01")])
        self.assertEqual(summary["provider_months"], 2)
        self.assertEqual(summary["distinct_source_quote_keys"], 1)
        self.assertEqual(summary["adjacent_same_label_new_snapshot_pairs"], 0)

    def test_gap_and_changed_bundle_do_not_create_matched_pairs(self):
        for other in [row(month="2025-03", price="3", version="v2/20250301-2"),
                      row(month="2025-02", price="3", version="v2/20250201-2", instance_types="different-bundle")]:
            self.assertEqual(summarize_rental([row(), other])["changed_same_label_pairs"], 0)

    def test_regional_changes_collapse_to_one_provider_month(self):
        records = [row(region=r) for r in ["one", "two"]]
        records += [row(month="2025-02", price="3", version="v2/20250201-2", region=r) for r in ["one", "two"]]
        summary = summarize_rental(records)
        self.assertEqual(summary["changed_same_label_pairs"], 2)
        self.assertEqual(summary["provider_months_with_same_label_price_change"], 1)

    def test_duplicate_capture_is_not_another_observation(self):
        records = [update("2025-01-01", 20), update("2025-01-01", 20), update("2025-02-01", 10)]
        summary, values = summarize_updates(records)
        self.assertEqual(len(values), 2)
        self.assertEqual(summary["duplicate_records"], 1)
        self.assertEqual(summary["observed_days"], 2)
        self.assertEqual(summary["observed_price_changes"], 1)
        self.assertEqual(summary["max_capture_gap_days"], 31)

    def test_cutoff_and_conflicting_timestamps_are_explicit(self):
        summary, _ = summarize_updates([update("2022-01-01", 1), update("2025-01-01", 2),
                                       update("2025-01-01", 3), update("2026-10-29", 4)])
        self.assertEqual(summary["observations_before_window"], 1)
        self.assertEqual(summary["observations_after_cutoff"], 1)
        self.assertEqual(summary["conflicting_timestamps"], 1)
        self.assertEqual(summary["observed_price_changes"], 0)

    def test_ambiguous_categories_remain_inventory_only(self):
        records = [update("2025-01-01", 20), dict(update("2025-01-02", 15), source="pMsg"),
                   dict(update("2025-01-03", 12), source="unknown"), update("2025-01-04", 10)]
        summary, values = summarize_updates(records)
        self.assertEqual(summary["unique_timestamp_price_records"], 4)
        self.assertEqual(summary["excluded_ambiguous_category_records"], 2)
        self.assertEqual(summary["in_window_unique_records"], 2)
        self.assertEqual(summary["observed_days"], 2)
        self.assertEqual(len(values), 2)

    def test_missing_json_and_invalid_prices_fail(self):
        with self.assertRaises(ValueError):
            parse_tracker("<html>No data</html>")
        for value in ["NaN", "Infinity", "0", "-1"]:
            with self.assertRaises(ValueError):
                number(value)

    def test_calendar_coverage_has_real_gaps(self):
        self.assertEqual(longest_run({"2023-12", "2024-01", "2024-03"}), 2)


if __name__ == "__main__":
    unittest.main()
