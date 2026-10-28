"""Frozen, rolling-origin catalog forecasts. No network calls or target imputation."""
from __future__ import annotations

import hashlib
import json
import math
import platform
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from catalog_panel import ROOT, PROTOCOL_PATH, digest, load_panel

UTC = timezone.utc
DAYS_PER_MONTH = 365.25 / 12
OUT = ROOT / "results"
FEATURES = ["last_return", "trend", "volatility", "log_price", "log_count", "log_memory", "is_spot"]
MODELS = ["persistence", "drift", "local_trend", "damped_trend", "pooled_ridge"]


def month_add(month, increment):
    y, m = map(int, month.split("-"))
    index = y * 12 + m - 1 + increment
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def cutoff(month, day=8):
    return datetime.fromisoformat(f"{month}-{day:02d}T00:00:00+00:00")


def months_between(a, b):
    return (b - a).total_seconds() / 86400 / DAYS_PER_MONTH


def history_features(history, target_cutoff, protocol):
    prices = np.array([r["price"] for r in history], dtype=float)
    times = np.array([months_between(history[0]["pub"], r["pub"]) for r in history])
    if np.any(np.diff(times) <= 0):
        raise ValueError("Non-increasing observation times")
    logs = np.log(prices)
    window = protocol["local_trend_window"]
    x, y = times[-window:], logs[-window:]
    xc = x - x.mean()
    trend = float(xc @ (y - y.mean()) / (xc @ xc))
    returns = np.diff(y) / np.diff(x)
    last = history[-1]
    features = [float(returns[-1]), trend, float(np.std(returns)), float(logs[-1]),
                math.log(float(last["gpu_count"])), math.log(float(last["gpu_memory"])),
                float(last["market"] == "spot")]
    lead = months_between(last["pub"], target_cutoff)
    drift = (logs[-1] - logs[0]) / (times[-1] - times[0])
    changes = dict(persistence=0.0, drift=float(drift * lead), local_trend=trend * lead,
                   damped_trend=protocol["damping"] * trend * lead)
    return features, changes


def bounded_forecast(price, change, protocol):
    bound = protocol["forecast_log_return_bound"]
    return price * math.exp(float(np.clip(change, -bound, bound))), abs(change) > bound


def make_cases(rows, manifest, protocol, mode="primary"):
    strict = mode == "strict_identity"
    fresh = mode == "provider_member_freshness"
    lag = timedelta(days=1 if mode == "publication_plus_24_hours" else 0)
    day = 1 if mode.startswith("day_one") else protocol["primary_origin_day"]
    naive = mode == "day_one_nominal"
    key_field = "strict_key" if strict else "key"
    groups = defaultdict(list)
    lookup = {}
    archives = {s["nominal_month"]: datetime.fromisoformat(s["object_last_modified_utc"]) + lag for s in manifest}
    for original in rows:
        r = dict(original, pub=datetime.fromisoformat(original["published"]))
        r["available"] = r["pub"] + lag
        lookup[(r[key_field], r["month"])] = r
        if not fresh or not r["member_repeated"]:
            groups[r[key_field]].append(r)
    for group in groups.values():
        group.sort(key=lambda r: r["pub"])
    start = min(r["month"] for r in rows)
    end = protocol["data_end_month"]
    cases = []
    month = start
    while month < end:
        origin = cutoff(month, day)
        for key, group in groups.items():
            history = [r for r in group if (cutoff(r["month"], 1) if naive else r["available"]) <= origin]
            if len(history) < protocol["ridge_training_minimum_history"]:
                continue
            last = history[-1]
            age = (origin - last["pub"]).total_seconds() / 86400
            if age > protocol["maximum_quote_age_days"]:
                continue
            if not naive and last["available"] > origin:
                raise AssertionError("Future history")
            for horizon in protocol["horizons_months"]:
                target_month = month_add(month, horizon)
                if target_month > end:
                    continue
                target_cutoff = cutoff(target_month)
                target = lookup.get((key, target_month))
                reason = "observed"
                if target_month not in archives:
                    reason = "no_target_archive"
                elif archives[target_month] > target_cutoff:
                    reason = "target_archive_late"
                elif target is None:
                    reason = "target_key_absent"
                elif fresh and target["member_repeated"]:
                    reason = "repeated_provider_member"
                observed = reason == "observed"
                features, changes = history_features(history, target_cutoff, protocol)
                case = dict(mode=mode, origin=origin.isoformat(), origin_month=month, horizon=horizon,
                            target_month=target_month, target_cutoff=target_cutoff.isoformat(), key=key,
                            provider=last["provider"], gpu=last["gpu"], market=last["market"],
                            history_count=len(history), last_price=last["price"], quote_age_days=age,
                            last_published=last["published"], last_version=last["version"],
                            target_price=target["price"] if observed else np.nan,
                            target_published=target["published"] if observed else "",
                            actual_lead_days=(target["pub"] - origin).total_seconds() / 86400 if observed else np.nan,
                            target_repeated_member=bool(target["member_repeated"]) if observed else False,
                            target_status=reason)
                case.update(dict(zip(FEATURES, features)))
                for model, change in changes.items():
                    case[model], case[model + "_bounded"] = bounded_forecast(last["price"], change, protocol)
                cases.append(case)
        month = month_add(month, 1)
    return pd.DataFrame(cases)


def nested_weights(frame):
    """Equal origins, providers within origin, and examples within provider-origin."""
    group_size = frame.groupby(["origin", "provider"])["provider"].transform("size").to_numpy()
    provider_count = frame.groupby("origin")["provider"].transform("nunique").to_numpy()
    weights = 1.0 / group_size / provider_count / frame["origin"].nunique()
    assert np.isclose(weights.sum(), 1.0)
    return weights


def nested_rate(frame, values):
    return float(nested_weights(frame) @ np.asarray(values, dtype=float))


def matured_training(cases, origin, horizon, excluded_provider=None):
    good = ((cases["horizon"] == horizon) & (cases["origin"] < origin)
            & (cases["target_cutoff"] <= origin) & cases["target_price"].notna()
            & (cases["target_published"] <= origin))
    if excluded_provider is not None:
        good &= cases["provider"] != excluded_provider
    return cases.loc[good]


def ridge_fit(train, protocol):
    if len(train) < protocol["ridge_minimum_training_cases"] or train["origin"].nunique() < protocol["ridge_minimum_training_origins"]:
        return None
    w = nested_weights(train)
    x = train[FEATURES].to_numpy(dtype=float)
    y = np.log(train["target_price"].to_numpy() / train["last_price"].to_numpy())
    mean = w @ x
    scale = np.sqrt(w @ ((x - mean) ** 2))
    scale[scale < 1e-12] = 1.0
    z = np.column_stack([np.ones(len(x)), (x - mean) / scale])
    penalty = np.eye(z.shape[1]) * protocol["ridge_penalty"]
    penalty[0, 0] = 0.0
    beta = np.linalg.solve(z.T @ (w[:, None] * z) + penalty, z.T @ (w * y))
    return mean, scale, beta


def add_ridge(cases, protocol, holdout=False):
    result = cases.copy()
    result["pooled_ridge"] = result["last_price"]
    result["pooled_ridge_bounded"] = False
    result["ridge_fallback"] = True
    result["ridge_training_cases"] = 0
    result["ridge_training_origins"] = 0
    result["ridge_latest_target"] = ""
    for (origin, horizon), batch in result.groupby(["origin", "horizon"], sort=True):
        subgroups = list(batch.groupby("provider")) if holdout else [(None, batch)]
        for provider, subgroup in subgroups:
            train = matured_training(cases, origin, horizon, provider)
            idx = subgroup.index
            result.loc[idx, "ridge_training_cases"] = len(train)
            result.loc[idx, "ridge_training_origins"] = train["origin"].nunique()
            if len(train):
                result.loc[idx, "ridge_latest_target"] = train["target_published"].max()
            fit = ridge_fit(train, protocol)
            if fit is None:
                continue
            mean, scale, beta = fit
            z = np.column_stack([np.ones(len(subgroup)), (subgroup[FEATURES].to_numpy() - mean) / scale])
            change = z @ beta
            bound = protocol["forecast_log_return_bound"]
            result.loc[idx, "pooled_ridge"] = subgroup["last_price"].to_numpy() * np.exp(np.clip(change, -bound, bound))
            result.loc[idx, "pooled_ridge_bounded"] = np.abs(change) > bound
            result.loc[idx, "ridge_fallback"] = False
    return result


def eligible(cases, protocol, minimum=None):
    return cases.loc[(cases["origin_month"] >= protocol["evaluation_start_month"])
                     & (cases["history_count"] >= (minimum or protocol["minimum_history"]))].copy()


def scored_long(cases, models=MODELS):
    observed = cases[cases["target_price"].notna()]
    outputs = []
    for model in models:
        r = observed[["mode", "origin_month", "horizon", "key", "provider", "gpu", "market"]].copy()
        r["model"] = model
        r["ale"] = np.abs(np.log(observed[model].to_numpy() / observed["target_price"].to_numpy()))
        r["ae"] = np.abs(observed[model].to_numpy() - observed["target_price"].to_numpy())
        outputs.append(r)
    return pd.concat(outputs, ignore_index=True)


def origin_losses(scores, by_gpu=False):
    keys = ["mode", "market", "horizon", "model", "origin_month"] + (["gpu"] if by_gpu else [])
    within = scores.groupby(keys + ["provider"])[["ale", "ae"]].mean()
    return within.groupby(level=keys).mean().reset_index()


def block_interval(origin_months, differences, horizon, protocol):
    """Calendar-preserving circular block sensitivity; missing origins remain missing."""
    values_by_month = dict(zip(origin_months, differences))
    start, end = min(origin_months), max(origin_months)
    values, month = [], start
    while month <= end:
        values.append(values_by_month.get(month, np.nan))
        month = month_add(month, 1)
    values = np.asarray(values)
    length = max(3, horizon)
    n_obs = np.isfinite(values).sum()
    if n_obs < protocol["bootstrap_minimum_blocks"] * length:
        return np.nan, np.nan, "fewer_than_four_block_equivalents"
    rng = np.random.default_rng(protocol["bootstrap_seed"])
    estimates = []
    for _ in range(protocol["bootstrap_replicates"]):
        starts = rng.integers(0, len(values), size=math.ceil(len(values) / length))
        indexes = np.concatenate([(s + np.arange(length)) % len(values) for s in starts])[:len(values)]
        sample = values[indexes]
        if np.isfinite(sample).any():
            estimates.append(float(np.nanmean(sample)))
    low, high = np.quantile(estimates, [0.025, 0.975])
    return float(low), float(high), "exploratory_calendar_block_interval"


def summarize(scores, cases, protocol):
    losses = origin_losses(scores)
    result = []
    for (mode, market, horizon), cell in losses.groupby(["mode", "market", "horizon"]):
        wide = cell.pivot(index="origin_month", columns="model", values="ale")
        sample = cases[(cases["mode"] == mode) & (cases["market"] == market) & (cases["horizon"] == horizon)]
        obs = sample[sample["target_price"].notna()]
        for model in sorted(cell["model"].unique()):
            current = cell[cell["model"] == model]
            difference = wide[model] - wide["persistence"]
            lo, hi, status = block_interval(list(wide.index), difference.to_numpy(), int(horizon), protocol)
            baseline = float(wide["persistence"].mean())
            result.append(dict(mode=mode, market=market, horizon=int(horizon), model=model,
                               male=float(current["ale"].mean()), mae_usd=float(current["ae"].mean()),
                               difference_vs_persistence=float(difference.mean()), ci_low=lo, ci_high=hi,
                               interval_status=status, skill=1 - float(current["ale"].mean()) / baseline if baseline > 0 else np.nan,
                               eligible_cases=len(sample), observed_cases=len(obs), attrition=1-len(obs)/len(sample),
                               origins=obs["origin_month"].nunique(), providers=obs["provider"].nunique(),
                               keys=obs["key"].nunique(), provider_origins=len(obs[["provider", "origin_month"]].drop_duplicates()),
                               unchanged_fraction=nested_rate(obs, np.isclose(obs["target_price"], obs["last_price"], rtol=1e-10, atol=1e-12)),
                               repeated_member_fraction=nested_rate(obs, obs["target_repeated_member"]),
                               unchanged_fraction_raw_rows=float(np.isclose(obs["target_price"], obs["last_price"], rtol=1e-10, atol=1e-12).mean()),
                               repeated_member_fraction_raw_rows=float(obs["target_repeated_member"].mean()),
                               ridge_fallback_fraction=float(obs["ridge_fallback"].mean()) if "ridge_fallback" in obs else np.nan,
                               bounded_forecasts=int(obs[model + "_bounded"].sum())))
    return pd.DataFrame(result), losses


def save(frame, filename):
    OUT.mkdir(exist_ok=True)
    frame.to_csv(OUT / filename, index=False, float_format="%.12g", lineterminator="\n")


def timing_comparison(actual, nominal, protocol):
    keys = ["origin_month", "horizon", "key", "provider", "market", "gpu"]
    a = eligible(actual, protocol); n = eligible(nominal, protocol)
    merged = a[a.target_price.notna()].merge(n[n.target_price.notna()], on=keys, suffixes=("_actual", "_nominal"), validate="one_to_one")
    if not np.allclose(merged.target_price_actual, merged.target_price_nominal):
        raise AssertionError("Timing diagnostic targets differ")
    rows = []
    for model in MODELS[:-1]:
        group = merged[keys].copy()
        group["model"] = model
        for mode in ("actual", "nominal"):
            group[mode] = np.abs(np.log(merged[model + "_" + mode] / merged.target_price_actual))
        agg = group.groupby(["market", "horizon", "model", "origin_month", "provider"])[["actual", "nominal"]].mean()
        agg = agg.groupby(level=["market", "horizon", "model", "origin_month"]).mean().reset_index()
        rows.append(agg)
    save(pd.concat(rows), "timing_paired_origin_losses.csv")
    save(merged[keys + ["last_published_actual", "last_published_nominal", "quote_age_days_actual", "quote_age_days_nominal"]], "timing_matched_cases.csv")
    return dict(actual_eligible=len(a), nominal_eligible=len(n), matched_observed=len(merged),
                nominal_future_predictor_fraction=float((merged.quote_age_days_nominal < 0).mean()))


def main():
    started = datetime.now(UTC).isoformat()
    protocol = json.loads(PROTOCOL_PATH.read_text())
    fingerprint = digest(PROTOCOL_PATH)
    lock = ROOT / "config/protocol_lock.json"
    if not lock.exists() or json.loads(lock.read_text())["protocol_sha256"] != fingerprint:
        raise ValueError("Protocol must be explicitly frozen before evaluating forecasts")
    rows, manifest, panel_summary = load_panel(write=True)
    base = make_cases(rows, manifest, protocol)
    base = add_ridge(base, protocol)
    frames = [eligible(base, protocol)]
    six = eligible(base, protocol, 6); six["mode"] = "six_observation_history"; frames.append(six)
    for mode in ("strict_identity", "publication_plus_24_hours", "provider_member_freshness"):
        print("Evaluating", mode, flush=True)
        cases = add_ridge(make_cases(rows, manifest, protocol, mode), protocol)
        frames.append(eligible(cases, protocol))
    holdout = add_ridge(base, protocol, holdout=True)
    holdout["mode"] = "ridge_provider_holdout"
    frames.append(eligible(holdout, protocol))
    all_cases = pd.concat(frames, ignore_index=True)
    scores = scored_long(all_cases)
    summary, losses = summarize(scores, all_cases, protocol)
    save(all_cases, "forecast_cases.csv")
    save(summary, "forecast_summary.csv")
    save(losses, "origin_losses.csv")
    gpu_losses = origin_losses(scores, by_gpu=True)
    save(gpu_losses.groupby(["mode", "market", "gpu", "horizon", "model"])[["ale", "ae"]].mean().reset_index(), "gpu_results.csv")
    save(all_cases.groupby(["mode", "market", "horizon", "target_status"]).size().rename("cases").reset_index(), "target_attrition.csv")
    save(all_cases.groupby(["mode", "market", "horizon", "provider"])
         .agg(eligible=("key", "size"), observed=("target_price", "count"), origins=("origin_month", "nunique"))
         .reset_index(), "provider_evaluation_coverage.csv")
    loo = []
    primary_scores = scores[scores["mode"] == "primary"]
    for provider in sorted(primary_scores.provider.unique()):
        p = origin_losses(primary_scores[primary_scores.provider != provider])
        p = p.groupby(["market", "horizon", "model"])[["ale", "ae"]].mean().reset_index()
        p["omitted_provider"] = provider; loo.append(p)
    save(pd.concat(loo), "provider_leave_one_out.csv")
    actual = make_cases(rows, manifest, protocol, "day_one_actual")
    nominal = make_cases(rows, manifest, protocol, "day_one_nominal")
    timing = timing_comparison(actual, nominal, protocol)
    save(eligible(actual, protocol), "day_one_actual_cases.csv")
    save(eligible(nominal, protocol), "day_one_nominal_cases.csv")
    primary = frames[0]
    data = pd.DataFrame(rows).sort_values(["key", "published"])
    prev = data.groupby("key")["price"].shift()
    repriced = data[prev.notna() & ~np.isclose(data.price, prev.fillna(data.price), rtol=1e-10, atol=1e-12)]
    save(repriced[["provider", "month", "key", "gpu", "market", "price", "version"]], "observed_repricing_records.csv")
    report = dict(protocol_sha256=fingerprint, panel=panel_summary, timing=timing,
                  started_at_utc=started, completed_at_utc=datetime.now(UTC).isoformat(),
                  protocol_amendment_sha256=digest(ROOT / "config/protocol_amendment_01.json"),
                  primary_eligible_cases=len(primary), primary_observed_cases=int(primary.target_price.notna().sum()),
                  repricing_records=len(repriced), repricing_provider_months=len(repriced[["provider", "month"]].drop_duplicates()),
                  python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
                  source_manifest_sha256=digest(ROOT / "data/catalog_manifest.json"),
                  code_hashes={str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT / "scripts").glob("*.py"))})
    (OUT / "run_manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    print(summary[summary["mode"] == "primary"][["market", "horizon", "model", "male", "skill", "observed_cases", "origins"]].to_string(index=False))


if __name__ == "__main__":
    main()
