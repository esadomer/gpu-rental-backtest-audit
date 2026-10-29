"""Synthetic boundary fixtures for the post-V2 supplement, never empirical data."""
import copy
import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from robustness_diagnostics import (
    add_frequency_benchmark, attrition_tables, conditional_losses,
    frequency_features, pair_timing_cases, paired_calendar_bootstrap,
    paired_origin_losses, timing_tables, validate_reproduced_run_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config/v3_supplement.json").read_text())
MODELS = ["persistence", "drift", "local_trend", "damped_trend", "pooled_ridge",
          "frequency_damped_trend"]


def timing_fixture():
    base = dict(origin="2025-02-01T00:00:00+00:00", origin_month="2025-02",
                horizon=1, target_month="2025-03", key="a", provider="p", market="on_demand", gpu="H100_80",
                target_price=4., target_cutoff="2025-03-08T00:00:00+00:00",
                target_published="2025-03-02T00:00:00+00:00", target_status="observed",
                persistence=2.)
    return pd.DataFrame([base]), pd.DataFrame([dict(base, persistence=3.)])


def history_fixture():
    return [dict(key="a", month=month, published=month + "-02T00:00:00+00:00",
                 provider="p", market="on_demand", gpu="H100_80", price=price) for month, price in
            [("2025-01", 100.), ("2025-02", 100.), ("2025-04", 200.),
             ("2025-05", 100.), ("2025-06", 50.)]]


def case_fixture():
    rows = []
    # Large provider p has only unchanged outcomes; small q has one changed outcome.
    # Original weights assign half the origin to each provider, not 10/11 to p.
    for k in range(11):
        row = dict(mode="primary", origin="2025-01-08T00:00:00+00:00",
                   origin_month="2025-01", horizon=1, target_month="2025-02",
                   key=str(k), provider="p" if k < 10 else "q", gpu="H100_80",
                   market="on_demand", last_price=1., target_price=1. if k < 10 else 2.,
                   target_status="observed", quote_age_days=6., history_count=12,
                   last_return=0., volatility=0., past_change_frequency=0.)
        row.update({model: 1. for model in MODELS})
        rows.append(row)
    return pd.DataFrame(rows)


class PairedTimingTests(unittest.TestCase):
    def test_unmatched_cases_do_not_change_paired_sample(self):
        a, n = timing_fixture()
        a = pd.concat([a, a.assign(key="unmatched", persistence=999.)], ignore_index=True)
        p = pair_timing_cases(a, n)
        self.assertEqual(len(p), 1)
        self.assertAlmostEqual(p.actual_loss.iloc[0], math.log(2.))
        self.assertAlmostEqual(p.nominal_loss.iloc[0], math.log(4. / 3.))

    def test_duplicate_case_is_rejected(self):
        a, n = timing_fixture()
        with self.assertRaises((ValueError, AssertionError, pd.errors.MergeError)):
            pair_timing_cases(pd.concat([a, a]), n)

    def test_different_target_price_or_publication_is_rejected(self):
        a, n = timing_fixture()
        for column, value in [("target_price", 5.),
                              ("target_published", "2025-03-03T00:00:00+00:00"),
                              ("target_cutoff", "2025-03-09T00:00:00+00:00")]:
            with self.subTest(column=column):
                bad = n.copy(); bad[column] = value
                with self.assertRaises((ValueError, AssertionError)):
                    pair_timing_cases(a, bad)

    def test_provider_balance_survives_regional_replication(self):
        a, n = timing_fixture()
        a = pd.concat([a, a.assign(key="b", provider="q", persistence=4.)], ignore_index=True)
        n = pd.concat([n, n.assign(key="b", provider="q", persistence=4.)], ignore_index=True)
        original = paired_origin_losses(pair_timing_cases(a, n))
        copies_a = [a] + [a[a.provider == "p"].assign(key=f"p{k}") for k in range(10)]
        copies_n = [n] + [n[n.provider == "p"].assign(key=f"p{k}") for k in range(10)]
        replicated = paired_origin_losses(pair_timing_cases(pd.concat(copies_a), pd.concat(copies_n)))
        pd.testing.assert_frame_equal(original[["actual_loss", "nominal_loss"]],
                                      replicated[["actual_loss", "nominal_loss"]], check_exact=False)

    def test_calendar_retains_missing_endpoints_and_interior(self):
        a, n = timing_fixture()
        config = dict(CONFIG, markets=["on_demand"], horizons=[1])
        slices, calendar, bootstrap = timing_tables(pair_timing_cases(a, n), config)
        self.assertEqual(calendar.origin_month.iloc[0], "2025-01")
        self.assertEqual(calendar.origin_month.iloc[-1], "2026-08")
        self.assertEqual(len(calendar), 20)
        self.assertEqual(calendar.actual_loss.notna().sum(), 1)
        self.assertEqual(int(bootstrap.observed_origins.iloc[0]), 1)
        empty = slices[(slices.slice_type == "leave_one_provider_out") & (slices.slice_value == "p")].iloc[0]
        self.assertEqual(empty.paired_cases, 0)
        self.assertTrue(np.isnan(empty.relative_reduction))
        self.assertEqual(empty.origins_lost, 1)


class PairedBootstrapTests(unittest.TestCase):
    def test_same_indexes_preserve_exact_ratio(self):
        actual = np.arange(1., 21.); actual[[0, 7, 19]] = np.nan
        out = paired_calendar_bootstrap(actual, .5 * actual, 3, replicates=400)
        self.assertAlmostEqual(out["relative_reduction_ci_low"], .5)
        self.assertAlmostEqual(out["relative_reduction_ci_high"], .5)
        self.assertEqual(out["valid_draws"], 400)
        self.assertEqual(out["calendar_months"], 20)
        self.assertEqual(out["observed_origins"], 17)

    def test_zero_baseline_draws_suppress_ratio_not_absolute_interval(self):
        out = paired_calendar_bootstrap([0., 0., 0., 1.], [0., 0., 0., .5], 1,
                                        replicates=400, seed=3, minimum_blocks=1)
        self.assertGreater(out["undefined_ratio_draws"], 0)
        self.assertTrue(np.isnan(out["relative_reduction_ci_low"]))
        self.assertTrue(np.isfinite(out["absolute_reduction_ci_low"]))
        self.assertEqual(out["valid_ratio_draws"] + out["undefined_ratio_draws"], out["valid_draws"])

    def test_sparse_sample_suppresses_interval_before_resampling(self):
        out = paired_calendar_bootstrap(np.ones(11), np.zeros(11), 3)
        self.assertEqual(out["attempted_draws"], 0)
        self.assertTrue(np.isnan(out["absolute_reduction_ci_low"]))

    def test_unpaired_missingness_is_rejected(self):
        with self.assertRaises(ValueError):
            paired_calendar_bootstrap([1., np.nan], [1., 0.], 1)


class ConditionalAndAttritionTests(unittest.TestCase):
    def test_subgroup_mass_and_contribution_use_original_weights(self):
        frame = case_fixture()
        # Introduce a second origin with only unchanged cases: changed mass is 1/4,
        # whereas renesting a changed-only subset would give it total weight one.
        extra = frame.iloc[:1].copy()
        extra["origin"] = "2025-02-08T00:00:00+00:00"; extra["origin_month"] = "2025-02"
        extra["target_month"] = "2025-03"
        result = conditional_losses(pd.concat([frame, extra], ignore_index=True), CONFIG)
        for _, rows in result.groupby("model"):
            g = rows.set_index("subgroup")
            self.assertAlmostEqual(g.loc["changed", "weighted_mass"], .25)
            self.assertAlmostEqual(g.loc["changed", "male"], math.log(2.))
            self.assertAlmostEqual(g.loc["all", "male"], .25 * math.log(2.))
            for metric in ("male", "mae_usd"):
                self.assertAlmostEqual(g.loc["changed", metric + "_contribution"] +
                                       g.loc["unchanged", metric + "_contribution"], g.loc["all", metric])

    def test_empty_changed_subset_stays_missing(self):
        result = conditional_losses(case_fixture().assign(target_price=1.), CONFIG)
        changed = result[result.subgroup == "changed"]
        self.assertTrue(changed.male.isna().all())
        self.assertTrue((changed.weighted_mass == 0).all())

    def test_missing_target_retains_eligible_weight_and_reason(self):
        frame = case_fixture()
        frame.loc[frame.provider == "q", "target_price"] = np.nan
        frame.loc[frame.provider == "q", "target_status"] = "target_archive_late"
        summary, features = attrition_tables(frame, CONFIG)
        all_rows = summary[summary.group_type == "all"]
        missing = all_rows[all_rows.target_status == "target_archive_late"].iloc[0]
        self.assertEqual(missing.eligible_cases, 11)
        self.assertEqual(missing.status_cases, 1)
        self.assertAlmostEqual(missing.status_raw_share_within_group, 1 / 11)
        self.assertAlmostEqual(missing.status_weight_share_within_group, .5)
        self.assertAlmostEqual(all_rows.status_weight_mass_of_cell.sum(), 1.)
        self.assertEqual(all_rows.status_cases.sum(), 11)
        self.assertFalse(features.empty)


class FrequencyTests(unittest.TestCase):
    def test_gap_is_not_treated_as_one_month_change(self):
        out = frequency_features(history_fixture(), 3, 50., 40., CONFIG)
        self.assertEqual(out["frequency_pair_count"], 3)
        self.assertEqual(out["frequency_changed_count"], 2)
        self.assertAlmostEqual(out["past_change_frequency"], 2 / 3)
        self.assertAlmostEqual(out["frequency_shrinkage"], 1 - (1 / 3) ** 3)
        self.assertGreaterEqual(out["frequency_damped_trend"], 40.)
        self.assertLessEqual(out["frequency_damped_trend"], 50.)

    def test_no_pair_has_explicit_fallback_and_missing_frequency(self):
        history = [history_fixture()[1], history_fixture()[2]]
        out = frequency_features(history, 1, 200., 100., CONFIG)
        self.assertTrue(out["frequency_fallback"])
        self.assertTrue(np.isnan(out["past_change_frequency"]))
        self.assertEqual(out["frequency_damped_trend"], 200.)

    def test_zero_and_one_frequencies_have_correct_endpoints(self):
        for prices, expected in [([100., 100.], 100.), ([200., 100.], 70.)]:
            history = copy.deepcopy(history_fixture()[:2])
            for record, price in zip(history, prices): record["price"] = price
            out = frequency_features(history, 6, 100., 70., CONFIG)
            self.assertAlmostEqual(out["frequency_damped_trend"], expected)

    def test_future_prices_and_future_targets_cannot_change_forecast(self):
        rows = history_fixture()
        cases = pd.DataFrame([dict(key="a", provider="p", market="on_demand", gpu="H100_80",
                                   origin="2025-06-08T00:00:00+00:00",
                                   origin_month="2025-06", horizon=1, history_count=5,
                                   last_published=rows[-1]["published"], last_price=50.,
                                   damped_trend=40., target_price=np.nan)])
        base = add_frequency_benchmark(cases, rows, CONFIG)
        future = dict(key="a", month="2025-07", published="2025-07-02T00:00:00+00:00", price=1e9)
        poisoned = add_frequency_benchmark(cases.assign(target_price=1e12), rows + [future], CONFIG)
        self.assertEqual(len(poisoned), 1)
        self.assertTrue(base.target_price.isna().all())
        for field in ("past_change_frequency", "frequency_pair_count", "frequency_damped_trend"):
            np.testing.assert_array_equal(base[field], poisoned[field])

    def test_saved_history_mismatch_fails(self):
        rows = history_fixture()
        case = dict(key="a", provider="p", market="on_demand", gpu="H100_80",
                    origin="2025-06-08T00:00:00+00:00", origin_month="2025-06",
                    horizon=1, history_count=4, last_published=rows[-1]["published"],
                    last_price=50., damped_trend=40.)
        with self.assertRaises((ValueError, AssertionError)):
            add_frequency_benchmark(pd.DataFrame([case]), rows, CONFIG)


class ReproductionManifestTests(unittest.TestCase):
    def test_new_run_metadata_and_additional_scripts_are_allowed(self):
        reference = json.loads((ROOT / "config/v3_base_run_reference.json").read_text())
        current = copy.deepcopy(reference)
        current["started_at_utc"] = "2030-01-01T00:00:00+00:00"
        current["python"] = "3.12.99"
        current["code_hashes"] = {k.replace("\\", "/"): v for k, v in current["code_hashes"].items()}
        current["code_hashes"]["scripts/additional.py"] = "extra"
        validate_reproduced_run_manifest(current, reference)

    def test_changed_scientific_result_or_pinned_code_is_rejected(self):
        reference = json.loads((ROOT / "config/v3_base_run_reference.json").read_text())
        for kind in ("count", "code", "missing_code", "extra_field"):
            current = copy.deepcopy(reference)
            if kind == "count": current["primary_eligible_cases"] += 1
            elif kind == "code": current["code_hashes"][next(iter(current["code_hashes"]))] = "altered"
            elif kind == "missing_code": current["code_hashes"].pop(next(iter(current["code_hashes"])))
            else: current["new_scientific_claim"] = True
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                validate_reproduced_run_manifest(current, reference)


if __name__ == "__main__":
    unittest.main()
