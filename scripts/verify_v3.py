"""Independent checks of V3 outputs; does not import the diagnostic implementation."""
from pathlib import Path
import hashlib
import json
import math

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/v3"


def close(actual, expected):
    assert np.allclose(actual, expected, rtol=1e-8, atol=1e-10, equal_nan=True), (actual, expected)


def weights(frame):
    result = pd.Series(0., index=frame.index)
    for _, origin in frame.groupby("origin_month"):
        for _, provider in origin.groupby("provider"):
            result.loc[provider.index] = 1 / frame.origin_month.nunique() / origin.provider.nunique() / len(provider)
    return result


def subgroup(frame, record):
    kind = record.group_type
    if kind in ("provider", "provider_gpu"): frame = frame[frame.provider == record.provider]
    if kind in ("gpu", "provider_gpu"): frame = frame[frame.gpu == record.gpu]
    if kind == "origin_year": frame = frame[frame.origin_month.str[:4] == str(int(record.origin_year))]
    return frame


def main():
    manifest = json.loads((OUT / "run_manifest.json").read_text())
    for section in ("protocol_hashes", "input_hashes", "original_code_hashes", "code_hashes", "output_hashes"):
        for path, expected in manifest[section].items():
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
    config = json.loads((ROOT / "config/v3_supplement.json").read_text())
    base = pd.read_csv(ROOT / "results/forecast_cases.csv")
    base = base[base["mode"] == "primary"].reset_index(drop=True)
    cases = pd.read_csv(OUT / "frequency_cases.csv")
    pd.testing.assert_frame_equal(base, cases[base.columns], check_exact=False, rtol=1e-10, atol=1e-12)
    assert len(cases) == 22868 and cases.target_price.notna().sum() == 18226

    # Independently reconstruct every historical frequency and forecast from the saved panel.
    panel = pd.read_csv(ROOT / "data/research/catalog_panel.csv")
    histories = {key: group.sort_values("published") for key, group in panel.groupby("key")}
    cache = {}
    for r in cases.itertuples():
        key = (r.key, r.origin)
        if key not in cache:
            history = histories[r.key]
            history = history[history.published <= r.origin]
            assert len(history) == r.history_count and history.iloc[-1].published == r.last_published
            close(history.iloc[-1].price, r.last_price)
            recent = list(history.tail(config["frequency_history_window"]).itertuples())
            pairs = [(a, b) for a, b in zip(recent, recent[1:])
                     if pd.Period(b.month, freq="M").ordinal - pd.Period(a.month, freq="M").ordinal == 1]
            changed = sum(not np.isclose(b.price, a.price, rtol=1e-10, atol=1e-12) for a, b in pairs)
            cache[key] = (len(pairs), changed)
        n, changes = cache[key]
        assert (r.frequency_pair_count, r.frequency_changed_count) == (n, changes)
        f = changes / n if n else np.nan
        q = 1 - (1 - f) ** r.horizon if n else 0.
        close(r.past_change_frequency, f); close(r.frequency_shrinkage, q)
        close(r.frequency_damped_trend, math.exp((1-q) * math.log(r.last_price) + q * math.log(r.damped_trend)))
        assert bool(r.frequency_fallback) == (n == 0)

    conditional = pd.read_csv(OUT / "conditional_losses.csv")
    benchmarks = pd.read_csv(OUT / "benchmark_summary.csv")
    attrition = pd.read_csv(OUT / "attrition_summary.csv")
    features = pd.read_csv(OUT / "attrition_features.csv")
    for (market, h), eligible in cases.groupby(["market", "horizon"]):
        eligible = eligible.copy()
        eligible["weight"] = weights(eligible)
        eligible["absolute_last_return"] = eligible.last_return.abs()
        observed = eligible[eligible.target_price.notna()].copy()
        observed["weight"] = weights(observed)
        same = np.isclose(observed.last_price, observed.target_price, rtol=1e-10, atol=1e-12)
        for r in conditional[(conditional.market == market) & (conditional.horizon == h)].itertuples():
            mask = np.ones(len(observed), dtype=bool) if r.subgroup == "all" else (same if r.subgroup == "unchanged" else ~same)
            selected = observed.loc[mask]; mass = selected.weight.sum()
            assert len(selected) == r.cases and selected.origin.nunique() == r.origins
            close(r.weighted_mass, mass)
            for metric, errors in [("male", np.abs(np.log(selected[r.model] / selected.target_price))),
                                   ("mae_usd", np.abs(selected[r.model] - selected.target_price))]:
                contribution = float(selected.weight @ errors)
                close(getattr(r, metric + "_contribution"), contribution)
                close(getattr(r, metric), contribution / mass if mass else np.nan)
        for r in benchmarks[(benchmarks.market == market) & (benchmarks.horizon == h)].itertuples():
            close(r.male, observed.weight @ np.abs(np.log(observed[r.model] / observed.target_price)))
            close(r.mae_usd, observed.weight @ np.abs(observed[r.model] - observed.target_price))
        for r in attrition[(attrition.market == market) & (attrition.horizon == h)].itertuples():
            group = subgroup(eligible, r); selected = group[group.target_status == r.target_status]
            assert len(group) == r.eligible_cases and len(selected) == r.status_cases
            assert selected.target_month.nunique() == r.status_target_months
            close(r.status_raw_share_within_group, len(selected) / len(group))
            close(r.status_weight_share_within_group, selected.weight.sum() / group.weight.sum())
        for r in features[(features.market == market) & (features.horizon == h)].itertuples():
            group = subgroup(eligible, r); selected = group[group.target_status == r.target_status]
            close(r.mean, selected[r.feature].mean())

    # Independent exact-case join and explicit nested loss loops for all timing slices.
    a = pd.read_csv(ROOT / "results/day_one_actual_cases.csv")
    n = pd.read_csv(ROOT / "results/day_one_nominal_cases.csv")
    keys = ["origin_month", "horizon", "key", "provider", "market", "gpu"]
    paired = a[a.target_price.notna()].merge(n[n.target_price.notna()], on=keys,
                                           suffixes=("_a", "_n"), validate="one_to_one")
    assert (paired.target_price_a == paired.target_price_n).all()
    paired["a"] = abs(np.log(paired.persistence_a / paired.target_price_a))
    paired["n"] = abs(np.log(paired.persistence_n / paired.target_price_n))
    timing = pd.read_csv(OUT / "timing_sensitivity.csv")
    for r in timing.itertuples():
        sample = paired[(paired.market == r.market) & (paired.horizon == r.horizon)]
        if r.slice_type == "single_provider": sample = sample[sample.provider == r.slice_value]
        if r.slice_type == "leave_one_provider_out": sample = sample[sample.provider != r.slice_value]
        if r.slice_type == "origin_year": sample = sample[sample.origin_month.str[:4] == str(r.slice_value)]
        assert len(sample) == r.paired_cases and sample.origin_month.nunique() == r.origins
        wa = weights(sample)
        actual = wa @ sample.a if len(sample) else np.nan
        nominal = wa @ sample.n if len(sample) else np.nan
        close(r.actual_loss, actual); close(r.nominal_loss, nominal)
        close(r.relative_reduction, 1 - nominal / actual if actual > 0 else np.nan)

    # Vectorized block-index reconstruction, independent of the implementation's draw loop.
    boot = pd.read_csv(OUT / "timing_bootstrap.csv")
    for r in boot.itertuples():
        sample = paired[(paired.market == r.market) & (paired.horizon == r.horizon)]
        grouped = sample.groupby(["origin_month", "provider"])[["a", "n"]].mean().groupby(level=0).mean()
        calendar = pd.period_range("2025-01", pd.Period("2026-09", freq="M") - r.horizon, freq="M").astype(str)
        values = grouped.reindex(calendar).to_numpy()
        assert len(values) == r.calendar_months
        if np.isfinite(values[:, 0]).sum() < 4 * r.block_length:
            assert r.attempted_draws == 0 and np.isnan(r.absolute_reduction_ci_low)
            continue
        rng = np.random.default_rng(27826)
        starts = rng.integers(0, len(values), (2000, math.ceil(len(values) / r.block_length)))
        ix = ((starts[:, :, None] + np.arange(r.block_length)) % len(values)).reshape(2000, -1)[:, :len(values)]
        means = np.nanmean(values[ix], axis=1)
        valid = np.isfinite(means).all(axis=1); undefined = valid & (means[:, 0] == 0)
        assert valid.sum() == r.valid_draws and undefined.sum() == r.undefined_ratio_draws
        close([r.absolute_reduction_ci_low, r.absolute_reduction_ci_high],
              np.quantile(means[valid, 0] - means[valid, 1], [.025, .975]))
        if not undefined.any():
            close([r.relative_reduction_ci_low, r.relative_reduction_ci_high],
                  np.quantile(1 - means[valid, 1] / means[valid, 0], [.025, .975]))
    print(json.dumps(dict(status="passed", frequency_cases=len(cases), conditional_rows=len(conditional),
                         timing_slices=len(timing), bootstrap_cells=len(boot), attrition_rows=len(attrition),
                         feature_rows=len(features), hashes="verified"), indent=2))


if __name__ == "__main__":
    main()
