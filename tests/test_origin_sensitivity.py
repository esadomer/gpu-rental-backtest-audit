"""Synthetic boundary tests for whole-origin deletion, not empirical observations."""
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from origin_sensitivity import origin_deletions, summarize


def fixture():
    return pd.DataFrame(dict(market=["on_demand"]*4, horizon=[1]*4, model=["persistence"]*4,
                             origin_month=["2025-01", "2025-02", "2025-03", "2025-04"],
                             actual_loss=[1., 4., np.nan, 0.], nominal_loss=[.5, 1., np.nan, 0.],
                             paired_cases=[1000, 1, 0, 10], observed=[True, True, False, True]))


class OriginDeletionTests(unittest.TestCase):
    def test_equal_origin_weight_not_case_weight_and_ratio_of_means(self):
        out = origin_deletions(fixture()).set_index("omitted_origin")
        self.assertAlmostEqual(out.loc["2025-04", "relative_reduction"], .7)
        self.assertAlmostEqual(out.loc["2025-02", "relative_reduction"], .5)
        self.assertEqual(out.loc["2025-02", "retained_paired_cases"], 1010)
        self.assertAlmostEqual(out.loc["2025-02", "omitted_signed_reduction_share"], 3/3.5)

    def test_missing_calendar_origin_is_not_a_deletion(self):
        result = origin_deletions(fixture())
        self.assertEqual(len(result), 3)
        self.assertNotIn("2025-03", result.omitted_origin.tolist())
        self.assertTrue((result.retained_origins == 2).all())

    def test_zero_loss_baseline_and_empty_retained_sample_are_undefined(self):
        frame = fixture().iloc[[3]]
        result = origin_deletions(frame)
        self.assertTrue(result.relative_reduction.isna().all())
        self.assertEqual(result.retained_origins.iloc[0], 0)
        self.assertTrue(np.isnan(summarize(result).minimum_reduction.iloc[0]))
        zeros = fixture().iloc[[0, 3]].assign(actual_loss=0., nominal_loss=0.)
        self.assertTrue(origin_deletions(zeros).relative_reduction.isna().all())

    def test_duplicate_or_unpaired_origin_is_rejected(self):
        with self.assertRaises(ValueError): origin_deletions(pd.concat([fixture(), fixture().iloc[:1]]))
        bad = fixture(); bad.loc[2, "nominal_loss"] = 0.
        with self.assertRaises(ValueError): origin_deletions(bad)

    def test_negative_influence_is_retained_without_clipping(self):
        frame = fixture(); frame.loc[0, "nominal_loss"] = 2.
        result = origin_deletions(frame).set_index("omitted_origin")
        self.assertLess(result.loc["2025-01", "omitted_signed_reduction_share"], 0)
        self.assertLess(result.loc["2025-02", "relative_reduction"], 0)

    def test_diagnostic_does_not_mutate_inputs(self):
        frame = fixture(); before = frame.copy(deep=True)
        result = origin_deletions(frame); summary = summarize(result)
        pd.testing.assert_frame_equal(frame, before)
        self.assertEqual(summary.minimum_omitted_origin.iloc[0], "2025-02")
        self.assertEqual(summary.maximum_omitted_origin.iloc[0], "2025-01")


if __name__ == "__main__": unittest.main()
