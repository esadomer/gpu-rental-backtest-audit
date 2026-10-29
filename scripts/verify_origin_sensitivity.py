"""Reconstruct every origin deletion directly from the two original case files."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT / "results/origin_sensitivity"
    manifest = json.loads((folder / "run_manifest.json").read_text())
    for section in ("input_hashes", "code_hashes", "output_hashes"):
        for path, expected in manifest[section].items():
            assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == expected, path
    for file, field in [("origin_sensitivity.json", "protocol_sha256"),
                        ("origin_sensitivity_lock.json", "lock_sha256")]:
        assert hashlib.sha256((ROOT/"config"/file).read_bytes()).hexdigest() == manifest[field]
    a = pd.read_csv(ROOT / "results/day_one_actual_cases.csv")
    n = pd.read_csv(ROOT / "results/day_one_nominal_cases.csv")
    keys = ["origin_month", "horizon", "key", "provider", "market", "gpu"]
    paired = a[a.target_price.notna()].merge(n[n.target_price.notna()], on=keys,
                                           suffixes=("_a", "_n"), validate="one_to_one")
    assert (paired.target_price_a == paired.target_price_n).all()
    paired["a"] = abs(np.log(paired.persistence_a / paired.target_price_a))
    paired["n"] = abs(np.log(paired.persistence_n / paired.target_price_n))
    results = pd.read_csv(folder / "leave_one_origin_out.csv")
    summary = pd.read_csv(folder / "summary.csv")
    checked = 0
    for (market, horizon), cell in paired.groupby(["market", "horizon"]):
        # Mean within provider, equal providers within origin, then equal origins.
        expected_months = set(cell.origin_month)
        actual_rows = results[(results.market == market) & (results.horizon == horizon)]
        assert set(actual_rows.omitted_origin) == expected_months and len(actual_rows) == len(expected_months)
        full = cell.groupby(["origin_month", "provider"])[["a", "n"]].mean().groupby(level=0).mean()
        for r in actual_rows.itertuples():
            retained = cell[cell.origin_month != r.omitted_origin]
            means = []
            for _, month in retained.groupby("origin_month"):
                means.append(np.mean([p[["a", "n"]].mean().to_numpy() for _, p in month.groupby("provider")], axis=0))
            mean_a, mean_n = np.mean(means, axis=0)
            assert len(retained) == r.retained_paired_cases
            assert len(means) == r.retained_origins
            assert np.allclose([mean_a, mean_n, 1-mean_n/mean_a],
                               [r.actual_loss, r.nominal_loss, r.relative_reduction], rtol=1e-9, atol=1e-11)
            share = (full.loc[r.omitted_origin, "a"]-full.loc[r.omitted_origin, "n"]) / (full.a-full.n).sum()
            assert np.isclose(share, r.omitted_signed_reduction_share, rtol=1e-9, atol=1e-11)
            checked += 1
        s = summary[(summary.market == market) & (summary.horizon == horizon)].iloc[0]
        assert np.isclose(s.minimum_reduction, actual_rows.relative_reduction.min())
        assert np.isclose(s.maximum_reduction, actual_rows.relative_reduction.max())
        assert s.minimum_omitted_origin == actual_rows.loc[actual_rows.relative_reduction.idxmin(), "omitted_origin"]
        assert s.maximum_omitted_origin == actual_rows.loc[actual_rows.relative_reduction.idxmax(), "omitted_origin"]
    assert checked == len(results) == 94
    print(f"PASS: {checked} complete-origin deletions independently reconstructed from original matched cases.")


if __name__ == "__main__": main()
