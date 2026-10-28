"""Synthetic fixtures exercise behavior only; empirical scripts never import tests."""
import copy
import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from catalog_panel import canonical_number, member_fingerprint, normalize, resolve_duplicates
from run_study import (FEATURES, ROOT, add_ridge, block_interval, cutoff, history_features,
                       make_cases, matured_training, nested_weights, nested_rate, origin_losses, ridge_fit)

PROTOCOL = json.loads((ROOT / "config/study_protocol.json").read_text())


def fixture_panel():
    rows, manifest = [], []
    for i in range(1, 10):
        month = f"2025-{i:02d}"
        published = f"{month}-02T00:00:00+00:00"
        manifest.append(dict(nominal_month=month, object_last_modified_utc=published))
        rows.append(dict(key="key", strict_key="strict", price=float(i), published=published,
                         month=month, version=month, gpu_count="1", gpu_memory="80", gpu="H100_80",
                         provider="aws", market="on_demand", member_repeated=False))
    return rows, manifest


class ForecastBehavior(unittest.TestCase):
    def test_numeric_identity_is_exact_decimal(self):
        self.assertEqual(canonical_number("80.0"), canonical_number("80"))
        self.assertNotEqual(canonical_number("80.00000000000001"), canonical_number("80"))
        for value in ("nan", "inf", "0", "-1"):
            with self.assertRaises(ValueError): canonical_number(value)

    def test_whole_member_hash_ignores_order_and_numeric_spelling(self):
        a = [{"price":"1.0", "gpu_memory":"80", "instance_name":"a"}, {"price":"2", "instance_name":"b"}]
        b = copy.deepcopy(a[::-1]); b[1]["price"] = "1"; b[1]["gpu_memory"] = "80.0"
        self.assertEqual(member_fingerprint(a), member_fingerprint(b))
        b[0]["price"] = "3"
        self.assertNotEqual(member_fingerprint(a), member_fingerprint(b))

    def test_conflicting_price_is_not_cheapest_selected(self):
        base = dict(version="v1", key="k", price=2, disk_size="unknown", cpu_arch="unknown", month="2025-01")
        kept, rejected = resolve_duplicates([base, dict(base, price=1)])
        self.assertEqual(kept, [])
        self.assertEqual(len(rejected), 2)

    def test_identical_duplicate_counts_once(self):
        base = dict(version="v1", key="k", price=2, disk_size="unknown", cpu_arch="unknown", month="2025-01")
        kept, rejected = resolve_duplicates([base, dict(base)])
        self.assertEqual(len(kept), 1)
        self.assertEqual(rejected[0]["reason"], "duplicate_capture")

    def test_day_one_cannot_see_second_day_archive(self):
        rows, manifest = fixture_panel()
        actual = make_cases(rows, manifest, PROTOCOL, "day_one_actual")
        naive = make_cases(rows, manifest, PROTOCOL, "day_one_nominal")
        a = actual[(actual.origin_month == "2025-05") & (actual.horizon == 1)].iloc[0]
        n = naive[(naive.origin_month == "2025-05") & (naive.horizon == 1)].iloc[0]
        self.assertEqual(a.last_price, 4)
        self.assertEqual(n.last_price, 5)
        self.assertLess(n.quote_age_days, 0)

    def test_missing_target_is_not_forward_filled(self):
        rows, manifest = fixture_panel(); rows = [r for r in rows if r["month"] != "2025-06"]
        cases = make_cases(rows, manifest, PROTOCOL)
        row = cases[(cases.origin_month == "2025-05") & (cases.horizon == 1)].iloc[0]
        self.assertTrue(math.isnan(row.target_price))
        self.assertEqual(row.target_status, "target_key_absent")

    def test_late_target_remains_missing(self):
        rows, manifest = fixture_panel()
        rows[5]["published"] = manifest[5]["object_last_modified_utc"] = "2025-06-20T00:00:00+00:00"
        cases = make_cases(rows, manifest, PROTOCOL)
        row = cases[(cases.origin_month == "2025-05") & (cases.horizon == 1)].iloc[0]
        self.assertEqual(row.target_status, "target_archive_late")
        self.assertTrue(math.isnan(row.target_price))

    def test_future_prices_do_not_change_prior_features_or_forecasts(self):
        rows, manifest = fixture_panel()
        old = make_cases(rows, manifest, PROTOCOL)
        changed = copy.deepcopy(rows)
        for r in changed:
            if r["month"] >= "2025-06": r["price"] *= 100
        new = make_cases(changed, manifest, PROTOCOL)
        columns = FEATURES + ["persistence", "drift", "local_trend", "damped_trend"]
        np.testing.assert_array_equal(old.loc[old.origin_month <= "2025-05", columns].values,
                                      new.loc[new.origin_month <= "2025-05", columns].values)

    def test_repeated_member_excluded_from_history_and_targets(self):
        rows, manifest = fixture_panel(); rows[5]["member_repeated"] = True
        cases = make_cases(rows, manifest, PROTOCOL, "provider_member_freshness")
        target = cases[(cases.origin_month == "2025-05") & (cases.horizon == 1)].iloc[0]
        later = cases[(cases.origin_month == "2025-07") & (cases.horizon == 1)].iloc[0]
        self.assertEqual(target.target_status, "repeated_provider_member")
        self.assertEqual(later.history_count, 6)

    def test_mature_labels_need_both_publication_and_cutoff(self):
        train = pd.DataFrame([
            dict(origin="2025-01-08", target_cutoff="2025-03-08", target_published="2025-03-02", horizon=1, target_price=1, provider="a"),
            dict(origin="2025-01-08", target_cutoff="2025-03-08", target_published="2025-04-02", horizon=1, target_price=1, provider="b"),
            dict(origin="2025-01-08", target_cutoff="2025-04-08", target_published="2025-03-02", horizon=1, target_price=1, provider="c")])
        result = matured_training(train, "2025-03-08", 1)
        self.assertEqual(result.provider.tolist(), ["a"])

    def test_training_weights_equal_origins_then_providers(self):
        frame = pd.DataFrame([dict(origin="1",provider="a")]*8 + [dict(origin="1",provider="b")] + [dict(origin="2",provider="a")])
        w = nested_weights(frame)
        self.assertAlmostEqual(w[:8].sum(), .25)
        self.assertAlmostEqual(w[8], .25)
        self.assertAlmostEqual(w[9], .5)

    def test_diagnostic_rates_use_nested_weights(self):
        frame = pd.DataFrame([dict(origin="1",provider="a")]*8 + [dict(origin="1",provider="b")] + [dict(origin="2",provider="a")])
        self.assertAlmostEqual(nested_rate(frame,[1]*8+[0,0]), .25)

    def test_evaluation_does_not_weight_regional_row_count(self):
        frame = pd.DataFrame([dict(mode="p", market="spot", horizon=1, model="x", origin_month="2025-01",provider="a",ale=1,ae=1)]*10 +
                             [dict(mode="p", market="spot", horizon=1, model="x", origin_month="2025-01",provider="b",ale=3,ae=3)])
        self.assertEqual(origin_losses(frame).iloc[0].ale, 2)

    def test_ridge_fallback_is_explicit(self):
        rows, manifest = fixture_panel()
        cases = add_ridge(make_cases(rows, manifest, PROTOCOL), PROTOCOL)
        self.assertTrue(cases.ridge_fallback.all())
        np.testing.assert_array_equal(cases.pooled_ridge, cases.last_price)

    def test_ridge_forecast_unchanged_when_unavailable_labels_change(self):
        rows, manifest = fixture_panel()
        protocol = dict(PROTOCOL, ridge_minimum_training_cases=2, ridge_minimum_training_origins=2)
        base = make_cases(rows, manifest, protocol)
        original = add_ridge(base, protocol)
        mutated = base.copy()
        mutated.loc[mutated.target_cutoff > "2025-07-08T00:00:00+00:00", "target_price"] *= 100
        updated = add_ridge(mutated, protocol)
        mask = original.origin_month <= "2025-07"
        self.assertFalse(original.loc[mask, "ridge_fallback"].all())
        np.testing.assert_array_equal(original.loc[mask, "pooled_ridge"], updated.loc[mask, "pooled_ridge"])

    def test_ridge_provider_holdout_excludes_own_labels(self):
        rows, manifest = fixture_panel()
        protocol = dict(PROTOCOL, ridge_minimum_training_cases=2, ridge_minimum_training_origins=2)
        cases = make_cases(rows, manifest, protocol)
        normal = add_ridge(cases, protocol)
        held = add_ridge(cases, protocol, holdout=True)
        self.assertFalse(normal.ridge_fallback.all())
        self.assertTrue(held.ridge_fallback.all())
        self.assertTrue((held.ridge_training_cases == 0).all())

    def test_long_horizon_interval_is_suppressed(self):
        lo, hi, reason = block_interval([f"2025-{i:02d}" for i in range(1,10)], np.ones(9), 6, PROTOCOL)
        self.assertTrue(math.isnan(lo))
        self.assertIn("fewer", reason)

    def test_calendar_gaps_are_preserved(self):
        months = [f"2025-{i:02d}" for i in range(1,13)] + ["2026-02", "2026-03"]
        one = block_interval(months, np.arange(14), 1, PROTOCOL)
        two = block_interval(months, np.arange(14), 1, PROTOCOL)
        self.assertEqual(one, two)


if __name__ == "__main__": unittest.main()
