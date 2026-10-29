"""Locked, offline post-V2 diagnostics; original results and protocols stay intact.

The added frequency benchmark is a fixed heuristic. Its nominal-horizon
shrinkage factor is not a calibrated probability. No target is imputed.
"""
from __future__ import annotations

import json
import math
import platform
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from catalog_panel import ROOT, PROTOCOL_PATH, digest, load_panel
from run_study import MODELS, block_interval, month_add, nested_weights

PAIR_KEYS = ["origin_month", "horizon", "key", "provider", "market", "gpu"]
FREQUENCY_MODEL = "frequency_damped_trend"
ALL_MODELS = [*MODELS, FREQUENCY_MODEL]
OUT = ROOT / "results/v3"


def _positive(values, label):
    values = np.asarray(values, dtype=float)
    if not np.all(np.isfinite(values) & (values > 0)):
        raise ValueError(f"{label} must contain finite positive prices")
    return values


def _unique(frame, columns, label):
    if frame[columns].isna().any().any() or frame.duplicated(columns).any():
        raise ValueError(f"{label} has missing or duplicate case identities")


def _support(frame):
    return dict(cases=len(frame), origins=frame["origin_month"].nunique(),
                providers=frame["provider"].nunique(), keys=frame["key"].nunique(),
                provider_origins=len(frame[["provider", "origin_month"]].drop_duplicates()),
                target_months=frame["target_month"].nunique() if "target_month" in frame else 0)


def pair_timing_cases(actual, nominal):
    """Validate and pair the observed day-one intersection without changing it."""
    for frame, label in ((actual, "actual"), (nominal, "nominal")):
        _unique(frame, PAIR_KEYS, label)
    a = actual.loc[actual["target_price"].notna()]
    n = nominal.loc[nominal["target_price"].notna()]
    merged = a.merge(n, on=PAIR_KEYS, suffixes=("_actual", "_nominal"),
                     how="inner", validate="one_to_one")
    target = _positive(merged["target_price_actual"], "Timing targets")
    if not np.array_equal(target, merged["target_price_nominal"].to_numpy()):
        raise ValueError("Timing diagnostic target prices differ")
    for field in ("target_month", "target_cutoff", "target_published"):
        if not merged[field + "_actual"].equals(merged[field + "_nominal"]):
            raise ValueError(f"Timing diagnostic {field} differs")
    result = merged[PAIR_KEYS].copy()
    result["target_month"] = merged["target_month_actual"]
    result["target_cutoff"] = merged["target_cutoff_actual"]
    result["target_published"] = merged["target_published_actual"]
    result["target_price"] = target
    for mode in ("actual", "nominal"):
        forecast = _positive(merged["persistence_" + mode], mode + " persistence")
        result[mode + "_loss"] = np.abs(np.log(forecast / target))
    return result


def paired_origin_losses(paired):
    """Average keys within provider-origin, then providers within origin."""
    keys = ["market", "horizon", "origin_month"]
    columns = [*keys, "actual_loss", "nominal_loss", "paired_cases", "providers"]
    if paired.empty:
        return pd.DataFrame(columns=columns)
    means = paired.groupby(keys + ["provider"])[["actual_loss", "nominal_loss"]].mean()
    result = means.groupby(level=keys).mean().reset_index()
    support = paired.groupby(keys).agg(paired_cases=("key", "size"), providers=("provider", "nunique"))
    return result.merge(support.reset_index(), on=keys, validate="one_to_one")


def paired_calendar_bootstrap(actual_losses, nominal_losses, block_length, *,
                              replicates=2000, seed=27826, minimum_blocks=4):
    """Resample paired full-calendar arrays in circular contiguous month blocks.

    Missing endpoints and interior months must already be present as NaNs.
    Absolute intervals retain zero-baseline draws. A single such draw suppresses
    the ratio interval, with counts retained rather than silently dropping it.
    """
    actual = np.asarray(actual_losses, dtype=float)
    nominal = np.asarray(nominal_losses, dtype=float)
    if actual.ndim != 1 or actual.shape != nominal.shape:
        raise ValueError("Paired bootstrap arrays must have equal one-dimensional shapes")
    if block_length < 1 or replicates < 1 or minimum_blocks < 1:
        raise ValueError("Bootstrap counts and block length must be positive")
    observed = np.isfinite(actual)
    if not np.array_equal(observed, np.isfinite(nominal)):
        raise ValueError("Actual and nominal missingness must be paired")
    if np.isinf(actual).any() or np.isinf(nominal).any() or (actual[observed] < 0).any() or (nominal[observed] < 0).any():
        raise ValueError("Bootstrap losses must be nonnegative finite numbers or NaN")
    n_observed = int(observed.sum())
    result = dict(calendar_months=len(actual), observed_origins=n_observed,
                  missing_origins=len(actual) - n_observed, block_length=int(block_length),
                  requested_draws=int(replicates), attempted_draws=0, valid_draws=0,
                  empty_draws=0, valid_ratio_draws=0, undefined_ratio_draws=0,
                  absolute_reduction_ci_low=np.nan, absolute_reduction_ci_high=np.nan,
                  relative_reduction_ci_low=np.nan, relative_reduction_ci_high=np.nan,
                  absolute_interval_status="fewer_than_four_block_equivalents",
                  relative_interval_status="fewer_than_four_block_equivalents")
    if n_observed < minimum_blocks * block_length:
        return result
    rng = np.random.default_rng(seed)
    absolute, relative = [], []
    for _ in range(replicates):
        starts = rng.integers(0, len(actual), size=math.ceil(len(actual) / block_length))
        indexes = np.concatenate([(start + np.arange(block_length)) % len(actual) for start in starts])[:len(actual)]
        valid = observed[indexes]
        if not valid.any():
            result["empty_draws"] += 1
            continue
        mean_a = float(actual[indexes][valid].mean())
        mean_n = float(nominal[indexes][valid].mean())
        absolute.append(mean_a - mean_n)
        if mean_a == 0:
            result["undefined_ratio_draws"] += 1
        else:
            relative.append(1 - mean_n / mean_a)
    result.update(attempted_draws=int(replicates), valid_draws=len(absolute),
                  valid_ratio_draws=len(relative))
    if not absolute:
        result.update(absolute_interval_status="no_valid_draws", relative_interval_status="no_valid_draws")
        return result
    low, high = np.quantile(absolute, [0.025, 0.975])
    result.update(absolute_reduction_ci_low=float(low), absolute_reduction_ci_high=float(high),
                  absolute_interval_status="exploratory_paired_calendar_block_interval")
    if result["undefined_ratio_draws"]:
        result["relative_interval_status"] = "suppressed_zero_actual_mean_in_bootstrap_draw"
    else:
        low, high = np.quantile(relative, [0.025, 0.975])
        result.update(relative_reduction_ci_low=float(low), relative_reduction_ci_high=float(high),
                      relative_interval_status="exploratory_paired_calendar_block_interval")
    return result


def _calendar(config, horizon):
    month = config["evaluation_start_month"]
    end = month_add(config["data_end_month"], -int(horizon))
    months = []
    while month <= end:
        months.append(month)
        month = month_add(month, 1)
    return months


def timing_tables(paired, config):
    """Return descriptive slices, full-calendar origin pairs, and block intervals."""
    slices, calendars, intervals = [], [], []
    providers = sorted(paired["provider"].unique())
    for market in config["markets"]:
        for horizon in config["horizons"]:
            cell = paired.loc[(paired["market"] == market) & (paired["horizon"] == horizon)]
            months = _calendar(config, horizon)
            if not cell["origin_month"].isin(months).all():
                raise ValueError("Timing cases outside the locked evaluation calendar")
            full_origins = set(cell["origin_month"])
            selections = [("full", "all", cell)]
            selections += [("single_provider", p, cell.loc[cell["provider"] == p]) for p in providers]
            selections += [("leave_one_provider_out", p, cell.loc[cell["provider"] != p]) for p in providers]
            selections += [("origin_year", str(y), cell.loc[cell["origin_month"].str.startswith(str(y))]) for y in (2025, 2026)]
            for slice_type, slice_value, subset in selections:
                origins = paired_origin_losses(subset)
                actual = float(origins["actual_loss"].mean()) if len(origins) else np.nan
                nominal = float(origins["nominal_loss"].mean()) if len(origins) else np.nan
                support = _support(subset)
                slices.append(dict(market=market, horizon=horizon, model="persistence",
                                   slice_type=slice_type, slice_value=slice_value,
                                   **support, paired_cases=len(subset),
                                   origins_lost=len(full_origins - set(subset["origin_month"])),
                                   first_origin=subset["origin_month"].min() if len(subset) else "",
                                   last_origin=subset["origin_month"].max() if len(subset) else "",
                                   calendar_start=months[0], calendar_end=months[-1],
                                   actual_loss=actual, nominal_loss=nominal,
                                   absolute_reduction=actual - nominal,
                                   relative_reduction=1 - nominal / actual if actual > 0 else np.nan))
            origins = paired_origin_losses(cell).set_index("origin_month")
            calendar = origins.reindex(months).rename_axis("origin_month").reset_index()
            calendar["market"], calendar["horizon"] = market, horizon
            calendar["model"] = "persistence"
            calendar["observed"] = calendar["actual_loss"].notna()
            for column in ("paired_cases", "providers"):
                calendar[column] = calendar[column].fillna(0).astype(int)
            calendar["absolute_reduction"] = calendar["actual_loss"] - calendar["nominal_loss"]
            calendars.append(calendar)
            primary = max(3, int(horizon))
            lengths = sorted(set([primary, *config["bootstrap_sensitivity_lengths"]]))
            for length in lengths:
                estimate = paired_calendar_bootstrap(
                    calendar["actual_loss"], calendar["nominal_loss"], length,
                    replicates=config["bootstrap_replicates"], seed=config["bootstrap_seed"],
                    minimum_blocks=config["bootstrap_minimum_blocks"])
                actual = float(calendar["actual_loss"].mean())
                nominal = float(calendar["nominal_loss"].mean())
                intervals.append(dict(market=market, horizon=horizon, model="persistence",
                                      primary_length=length == primary,
                                      sensitivity_length=length in config["bootstrap_sensitivity_lengths"],
                                      calendar_start=months[0], calendar_end=months[-1],
                                      actual_loss=actual, nominal_loss=nominal,
                                      absolute_reduction=actual - nominal,
                                      relative_reduction=1 - nominal / actual if actual > 0 else np.nan,
                                      **estimate))
    return pd.DataFrame(slices), pd.concat(calendars, ignore_index=True), pd.DataFrame(intervals)


def frequency_features(history, horizon, last_price, damped_trend, config):
    """Count adjacent nominal-month changes in the fixed trailing observation window."""
    if int(horizon) != horizon or horizon < 1:
        raise ValueError("The nominal horizon must be a positive integer")
    last, trend = _positive([last_price, damped_trend], "Benchmark predictors")
    window = sorted(history, key=lambda row: row["published"])[-config["frequency_history_window"]:]
    pairs = [(left, right) for left, right in zip(window, window[1:])
             if month_add(left["month"], 1) == right["month"]]
    changed = sum(not np.isclose(float(left["price"]), float(right["price"]),
                                rtol=config["change_rtol"], atol=config["change_atol"])
                  for left, right in pairs)
    frequency = changed / len(pairs) if pairs else np.nan
    shrinkage = 1 - (1 - frequency) ** int(horizon) if pairs else 0.0
    forecast = last * math.exp(shrinkage * math.log(trend / last))
    return dict(past_change_frequency=frequency, frequency_pair_count=len(pairs),
                frequency_changed_count=int(changed), frequency_fallback=not bool(pairs),
                frequency_shrinkage=shrinkage, frequency_damped_trend=forecast)


def add_frequency_benchmark(cases, rows, config):
    """Reconcile saved histories against raw-derived records before the 12-row limit."""
    _unique(cases, PAIR_KEYS, "Primary benchmark")
    groups = defaultdict(list)
    for row in rows:
        groups[row["key"]].append(dict(row, _published=datetime.fromisoformat(row["published"])))
    for group in groups.values():
        group.sort(key=lambda row: row["_published"])
    histories, extras = {}, []
    for case in cases.to_dict("records"):
        cache_key = (case["key"], case["origin"])
        if cache_key not in histories:
            origin = datetime.fromisoformat(case["origin"])
            histories[cache_key] = [row for row in groups.get(case["key"], []) if row["_published"] <= origin]
        history = histories[cache_key]
        if len(history) != case["history_count"] or not history:
            raise ValueError(f"Saved history_count mismatch for {cache_key}")
        last = history[-1]
        if last["_published"] != datetime.fromisoformat(case["last_published"]):
            raise ValueError(f"Saved latest publication mismatch for {cache_key}")
        if not np.isclose(float(last["price"]), case["last_price"],
                          rtol=config["change_rtol"], atol=config["change_atol"]):
            raise ValueError(f"Saved latest price mismatch for {cache_key}")
        if any(last[field] != case[field] for field in ("provider", "market", "gpu")):
            raise ValueError(f"Saved exact-key attributes mismatch for {cache_key}")
        extras.append(frequency_features(history, case["horizon"], case["last_price"], case["damped_trend"], config))
    result = cases.copy()
    additions = pd.DataFrame(extras, index=result.index)
    for column in additions:
        result[column] = additions[column]
    return result


def conditional_losses(cases, config):
    """Retain full observed-cell weights when splitting changed and unchanged rows."""
    outputs = []
    observed = cases.loc[cases["target_price"].notna()]
    for (market, horizon), cell in observed.groupby(["market", "horizon"], sort=True):
        weights = nested_weights(cell)
        target = _positive(cell["target_price"], "Conditional targets")
        unchanged = np.isclose(target, cell["last_price"].to_numpy(),
                               rtol=config["change_rtol"], atol=config["change_atol"])
        for model in ALL_MODELS:
            forecast = _positive(cell[model], model)
            ale, ae = np.abs(np.log(forecast / target)), np.abs(forecast - target)
            for subgroup, selected in (("all", np.ones(len(cell), dtype=bool)),
                                       ("changed", ~unchanged), ("unchanged", unchanged)):
                mass = float(weights[selected].sum())
                log_contribution = float(weights[selected] @ ale[selected])
                usd_contribution = float(weights[selected] @ ae[selected])
                outputs.append(dict(market=market, horizon=int(horizon), model=model,
                                    subgroup=subgroup, **_support(cell.loc[selected]),
                                    observed_cell_cases=len(cell), weighted_mass=mass,
                                    raw_case_share=float(selected.mean()),
                                    male=log_contribution / mass if mass > 0 else np.nan,
                                    mae_usd=usd_contribution / mass if mass > 0 else np.nan,
                                    male_contribution=log_contribution,
                                    mae_usd_contribution=usd_contribution,
                                    weight_basis="complete_observed_market_horizon_cell"))
    return pd.DataFrame(outputs)


def attrition_tables(cases, config):
    """Descriptive selection diagnostics using original eligible-cell weights."""
    summaries, features = [], []
    group_fields = {"all": [], "provider": ["provider"], "gpu": ["gpu"],
                    "origin_year": ["origin_year"], "provider_gpu": ["provider", "gpu"]}
    all_statuses = sorted(set(cases["target_status"]) |
                          {"observed", "target_archive_late", "target_key_absent"})
    for (market, horizon), original in cases.groupby(["market", "horizon"], sort=True):
        cell = original.copy()
        cell["eligible_weight"] = nested_weights(cell)
        cell["origin_year"] = cell["origin_month"].str[:4]
        cell["absolute_last_return"] = cell["last_return"].abs()
        for group_type in config["attrition_groups"]:
            fields = group_fields[group_type]
            groups = [((), cell)] if not fields else cell.groupby(fields, sort=True)
            for value, group in groups:
                values = value if isinstance(value, tuple) else (value,)
                identity = dict(zip(fields, values))
                group_mass = float(group["eligible_weight"].sum())
                common = dict(market=market, horizon=int(horizon), group_type=group_type,
                              group_value="|".join(str(v) for v in values) if fields else "all",
                              provider=identity.get("provider", ""), gpu=identity.get("gpu", ""),
                              origin_year=identity.get("origin_year", ""),
                              eligible_cases=len(group), observed_cases=int(group["target_price"].notna().sum()),
                              eligible_origins=group["origin_month"].nunique(),
                              eligible_provider_origins=len(group[["provider", "origin_month"]].drop_duplicates()),
                              eligible_keys=group["key"].nunique(), eligible_target_months=group["target_month"].nunique(),
                              full_cell_eligible_cases=len(cell), group_weight_mass=group_mass,
                              group_raw_share_of_cell=len(group) / len(cell))
                for status in all_statuses:
                    subset = group.loc[group["target_status"] == status]
                    status_mass = float(subset["eligible_weight"].sum())
                    support = _support(subset)
                    summaries.append(dict(**common, target_status=status,
                                          status_cases=len(subset), status_origins=support["origins"],
                                          status_provider_origins=support["provider_origins"],
                                          status_providers=support["providers"], status_keys=support["keys"],
                                          status_target_months=support["target_months"],
                                          status_raw_share_within_group=len(subset) / len(group),
                                          status_raw_share_of_cell=len(subset) / len(cell),
                                          status_weight_share_within_group=status_mass / group_mass,
                                          status_weight_mass_of_cell=status_mass,
                                          weight_basis="complete_eligible_market_horizon_cell"))
                    for feature in config["attrition_features"]:
                        finite = subset[feature].dropna()
                        features.append(dict(**common, target_status=status, feature=feature,
                                             status_cases=len(subset), feature_observed_cases=len(finite),
                                             feature_missing_cases=len(subset) - len(finite),
                                             status_origins=support["origins"],
                                             status_provider_origins=support["provider_origins"],
                                             status_target_months=support["target_months"],
                                             mean=float(finite.mean()) if len(finite) else np.nan,
                                             mean_basis="unweighted_raw_cases_with_nonmissing_feature"))
    return pd.DataFrame(summaries), pd.DataFrame(features)


def benchmark_summary(cases, protocol, config):
    """Score six models on identical primary observed rows using original blocks."""
    result = []
    for (market, horizon), sample in cases.groupby(["market", "horizon"], sort=True):
        obs = sample.loc[sample["target_price"].notna()]
        if obs.empty:
            continue
        weights = nested_weights(obs)
        target = _positive(obs["target_price"], "Benchmark targets")
        base = np.abs(np.log(_positive(obs["persistence"], "Persistence") / target))
        baseline = float(weights @ base)
        unchanged = np.isclose(target, obs["last_price"], rtol=config["change_rtol"], atol=config["change_atol"])
        eligible_weights = nested_weights(sample)
        for model in ALL_MODELS:
            forecast = _positive(obs[model], model)
            ale, ae = np.abs(np.log(forecast / target)), np.abs(forecast - target)
            differences = obs[["origin_month", "provider"]].copy()
            differences["difference"] = ale - base
            origins = differences.groupby(["origin_month", "provider"])["difference"].mean().groupby(level="origin_month").mean()
            low, high, status = block_interval(list(origins.index), origins.to_numpy(), int(horizon), protocol)
            result.append(dict(mode="primary", market=market, horizon=int(horizon), model=model,
                               male=float(weights @ ale), mae_usd=float(weights @ ae),
                               difference_vs_persistence=float(origins.mean()),
                               ci_low=low, ci_high=high, interval_status=status,
                               interval_policy="original_horizon_calendar_block_policy",
                               skill=1 - float(weights @ ale) / baseline if baseline > 0 else np.nan,
                               eligible_cases=len(sample), observed_cases=len(obs),
                               observation_rate=len(obs) / len(sample), attrition=1 - len(obs) / len(sample),
                               origins=obs["origin_month"].nunique(), providers=obs["provider"].nunique(),
                               keys=obs["key"].nunique(),
                               provider_origins=len(obs[["provider", "origin_month"]].drop_duplicates()),
                               unchanged_fraction=float(weights @ unchanged),
                               unchanged_fraction_raw_rows=float(unchanged.mean()),
                               frequency_fallback_cases_eligible=int(sample["frequency_fallback"].sum()),
                               frequency_fallback_cases_observed=int(obs["frequency_fallback"].sum()),
                               frequency_fallback_rate_eligible=float(eligible_weights @ sample["frequency_fallback"].to_numpy(dtype=float)),
                               frequency_fallback_rate_observed=float(weights @ obs["frequency_fallback"].to_numpy(dtype=float)),
                               frequency_pair_count_mean_raw_eligible=float(sample["frequency_pair_count"].mean()),
                               past_change_frequency_mean_raw_eligible=float(sample["past_change_frequency"].mean()),
                               frequency_shrinkage_mean_raw_eligible=float(sample["frequency_shrinkage"].mean())))
    return pd.DataFrame(result)


def _safe_local_path(relative):
    """Normalize historical Windows paths without accepting paths outside ROOT."""
    normalized = str(relative).replace("\\", "/")
    path = (ROOT / normalized).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError(f"Manifest path escapes repository: {relative}")
    return path


def validate_reproduced_run_manifest(current, reference):
    """Allow operational rerun metadata changes, preserving every scientific field.

    The reference is separately authenticated against the frozen V3 input lock.
    Added scripts may appear after a clean rerun of the unchanged original study;
    every original code entry must still be present with its pinned hash.
    """
    operational = {"started_at_utc", "completed_at_utc", "python", "numpy", "pandas", "code_hashes"}
    if set(current) != set(reference):
        raise ValueError("Reproduced run manifest fields differ from the frozen reference")
    for field in set(reference) - operational:
        if current[field] != reference[field]:
            raise ValueError(f"Reproduced run manifest scientific field differs: {field}")

    def normalized_hashes(mapping):
        normalized = {}
        for relative, fingerprint in mapping.items():
            name = relative.replace("\\", "/")
            if name in normalized:
                raise ValueError(f"Duplicate normalized code path in run manifest: {name}")
            normalized[name] = fingerprint
        return normalized

    current_code = normalized_hashes(current["code_hashes"])
    reference_code = normalized_hashes(reference["code_hashes"])
    for name, fingerprint in reference_code.items():
        if current_code.get(name) != fingerprint:
            raise ValueError(f"Reproduced run manifest original code hash differs: {name}")


def verify_inputs():
    """Check the frozen supplement, original protocol, case inputs, and original code."""
    config_path = ROOT / "config/v3_supplement.json"
    lock_path = ROOT / "config/v3_supplement_lock.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if digest(config_path) != lock["supplement_sha256"]:
        raise ValueError("V3 supplement differs from its frozen lock")
    reference_path = ROOT / "config/v3_base_run_reference.json"
    if digest(reference_path) != lock["input_hashes"]["results/run_manifest.json"]:
        raise ValueError("Original run reference differs from the frozen V3 input hash")
    original = json.loads(reference_path.read_text(encoding="utf-8"))
    current_run = json.loads((ROOT / "results/run_manifest.json").read_text(encoding="utf-8"))
    validate_reproduced_run_manifest(current_run, original)
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    protocol_lock = json.loads((ROOT / "config/protocol_lock.json").read_text(encoding="utf-8"))
    protocol_hash = digest(PROTOCOL_PATH)
    if not (protocol_hash == protocol_lock["protocol_sha256"] == original["protocol_sha256"] == config["original_protocol_sha256"]):
        raise ValueError("Original protocol hash mismatch")
    input_hashes = {"config/v3_base_run_reference.json": digest(reference_path)}
    for relative, expected in lock["input_hashes"].items():
        path = _safe_local_path(relative)
        current_hash = digest(path)
        if path.relative_to(ROOT).as_posix() != "results/run_manifest.json" and current_hash != expected:
            raise ValueError(f"Locked input hash mismatch: {relative}")
        input_hashes[path.relative_to(ROOT).as_posix()] = current_hash
    if digest(ROOT / "config/protocol_amendment_01.json") != original["protocol_amendment_sha256"]:
        raise ValueError("Original protocol amendment hash mismatch")
    if digest(ROOT / "data/catalog_manifest.json") != original["source_manifest_sha256"]:
        raise ValueError("Original source manifest hash mismatch")
    original_code_hashes = {}
    for relative, expected in original["code_hashes"].items():
        path = _safe_local_path(relative)
        if digest(path) != expected:
            raise ValueError(f"Original code hash mismatch: {relative}")
        original_code_hashes[path.relative_to(ROOT).as_posix()] = expected
    return config, protocol, input_hashes, original_code_hashes


def main():
    started = datetime.now(timezone.utc).isoformat()
    config, protocol, input_hashes, original_code_hashes = verify_inputs()
    print("Verified frozen supplement, original code and saved inputs.", flush=True)
    actual = pd.read_csv(ROOT / "results/day_one_actual_cases.csv")
    nominal = pd.read_csv(ROOT / "results/day_one_nominal_cases.csv")
    paired = pair_timing_cases(actual, nominal)
    sensitivity, origins, bootstrap = timing_tables(paired, config)
    cases = pd.read_csv(ROOT / "results/forecast_cases.csv")
    primary = cases.loc[cases["mode"] == "primary"].copy()
    if ((primary["origin_month"] < protocol["evaluation_start_month"]) |
            (primary["history_count"] < protocol["minimum_history"])).any():
        raise ValueError("Saved primary cases violate original eligibility")
    if not (primary["target_status"].eq("observed") == primary["target_price"].notna()).all():
        raise ValueError("Primary observation status and target missingness disagree")
    print("Rebuilding the panel from hash-verified local archives without writing it.", flush=True)
    rows, source_manifest, panel_summary = load_panel(write=False)
    frequency = add_frequency_benchmark(primary, rows, config)
    conditional = conditional_losses(frequency, config)
    attrition, features = attrition_tables(frequency, config)
    benchmark = benchmark_summary(frequency, protocol, config)
    outputs = {"timing_sensitivity.csv": sensitivity, "paired_timing_origins.csv": origins,
               "timing_bootstrap.csv": bootstrap, "frequency_cases.csv": frequency,
               "conditional_losses.csv": conditional, "attrition_summary.csv": attrition,
               "attrition_features.csv": features, "benchmark_summary.csv": benchmark}
    OUT.mkdir(parents=True, exist_ok=True)
    for name, frame in outputs.items():
        frame.to_csv(OUT / name, index=False, float_format="%.12g", lineterminator="\n")
    # Recheck byte preservation after analysis, before recording successful completion.
    verify_inputs()
    protocol_paths = ["config/study_protocol.json", "config/protocol_lock.json",
                      "config/protocol_amendment_01.json", "config/v3_supplement.json",
                      "config/v3_supplement_lock.json"]
    report = dict(version=config["version"], status=config["status"],
                  started_at_utc=started, completed_at_utc=datetime.now(timezone.utc).isoformat(),
                  runtime_versions=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__),
                  supplement_sha256=digest(ROOT / "config/v3_supplement.json"),
                  base_run_reference_sha256=digest(ROOT / "config/v3_base_run_reference.json"),
                  protocol_hashes={name: digest(ROOT / name) for name in protocol_paths},
                  input_hashes=input_hashes, original_code_hashes=original_code_hashes,
                  code_hashes={name: digest(ROOT / name) for name in
                               ("scripts/robustness_diagnostics.py", "scripts/run_study.py", "scripts/catalog_panel.py")},
                  output_hashes={(OUT / name).relative_to(ROOT).as_posix(): digest(OUT / name) for name in outputs},
                  output_rows={name: len(frame) for name, frame in outputs.items()},
                  raw_archive_hashes={"data/catalog_raw/" + source["filename"]: source["sha256"] for source in source_manifest},
                  raw_archives_verified=True, panel=panel_summary,
                  matched_observed_timing_cases=len(paired),
                  primary_eligible_cases=len(frequency),
                  primary_observed_cases=int(frequency["target_price"].notna().sum()),
                  benchmark_interpretation=config["benchmark_interpretation"],
                  excluded_from_public_repository=["results/v3/frequency_cases.csv"])
    (OUT / "run_manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["output_rows"], indent=2), flush=True)


if __name__ == "__main__":
    main()
