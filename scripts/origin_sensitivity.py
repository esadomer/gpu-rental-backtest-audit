"""Paired leave-one-origin-out influence diagnostics, without refitting forecasts."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/origin_sensitivity"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def origin_deletions(frame):
    """Delete each observed calendar origin as a unit, preserving paired losses."""
    identity = ["market", "horizon", "model", "origin_month"]
    if frame[identity].isna().any().any() or frame.duplicated(identity).any():
        raise ValueError("Missing or duplicate origin identity")
    if not frame["model"].eq("persistence").all():
        raise ValueError("This diagnostic is specified for persistence only")
    a, n = frame.actual_loss.to_numpy(), frame.nominal_loss.to_numpy()
    valid = np.isfinite(a)
    if (not np.array_equal(valid, np.isfinite(n)) or np.isinf(a).any() or np.isinf(n).any()
            or (a[valid] < 0).any() or (n[valid] < 0).any()):
        raise ValueError("Losses must be nonnegative and missing together")
    if not np.array_equal(frame.observed.to_numpy(), valid):
        raise ValueError("Observed flag disagrees with paired loss availability")
    counts = frame.paired_cases.to_numpy(dtype=float)
    if (not np.isfinite(counts).all() or (counts < 0).any() or (counts != np.floor(counts)).any()
            or (counts[valid] < 1).any() or (counts[~valid] != 0).any()):
        raise ValueError("Paired-case counts disagree with observed origins")
    output = []
    for (market, horizon), all_months in frame.groupby(["market", "horizon"], sort=True):
        cell = all_months[all_months.observed].sort_values("origin_month")
        full_a, full_n = cell.actual_loss.mean(), cell.nominal_loss.mean()
        signed_total = float((cell.actual_loss - cell.nominal_loss).sum())
        for omitted in cell.itertuples():
            retained = cell[cell.origin_month != omitted.origin_month]
            actual, nominal = retained.actual_loss.mean(), retained.nominal_loss.mean()
            reduction = 1 - nominal / actual if actual > 0 else np.nan
            full_reduction = 1 - full_n / full_a if full_a > 0 else np.nan
            output.append(dict(market=market, horizon=int(horizon), model="persistence",
                               omitted_origin=omitted.origin_month, full_origins=len(cell),
                               retained_origins=len(retained), omitted_paired_cases=int(omitted.paired_cases),
                               retained_paired_cases=int(retained.paired_cases.sum()),
                               full_actual_loss=full_a, full_nominal_loss=full_n,
                               full_relative_reduction=full_reduction,
                               actual_loss=actual, nominal_loss=nominal,
                               absolute_reduction=actual-nominal, relative_reduction=reduction,
                               reduction_change_percentage_points=100*(reduction-full_reduction),
                               omitted_actual_loss=omitted.actual_loss,
                               omitted_nominal_loss=omitted.nominal_loss,
                               omitted_signed_reduction_share=(omitted.actual_loss-omitted.nominal_loss)/signed_total
                               if signed_total != 0 else np.nan))
    return pd.DataFrame(output)


def summarize(deletions):
    records = []
    for (market, horizon), group in deletions.groupby(["market", "horizon"], sort=True):
        defined = group[group.relative_reduction.notna()]
        low = defined.loc[defined.relative_reduction.idxmin()] if len(defined) else None
        high = defined.loc[defined.relative_reduction.idxmax()] if len(defined) else None
        influence = group[group.omitted_signed_reduction_share.notna()]
        largest = influence.loc[influence.omitted_signed_reduction_share.idxmax()] if len(influence) else None
        records.append(dict(market=market, horizon=int(horizon), full_origins=int(group.full_origins.iloc[0]),
                            deletion_runs=len(group), defined_ratios=len(defined),
                            full_relative_reduction=group.full_relative_reduction.iloc[0],
                            minimum_reduction=low.relative_reduction if low is not None else np.nan,
                            minimum_omitted_origin=low.omitted_origin if low is not None else "",
                            maximum_reduction=high.relative_reduction if high is not None else np.nan,
                            maximum_omitted_origin=high.omitted_origin if high is not None else "",
                            strictly_positive_runs=int((defined.relative_reduction > 0).sum()),
                            largest_signed_share=largest.omitted_signed_reduction_share if largest is not None else np.nan,
                            largest_signed_share_origin=largest.omitted_origin if largest is not None else ""))
    return pd.DataFrame(records)


def main():
    config_path = ROOT / "config/origin_sensitivity.json"
    lock_path = ROOT / "config/origin_sensitivity_lock.json"
    spec = json.loads(config_path.read_text())
    lock = json.loads(lock_path.read_text())
    if sha(config_path) != lock["protocol_sha256"]:
        raise ValueError("Origin diagnostic differs from its frozen plan")
    source = ROOT / spec["input"]
    if sha(source) != spec["input_sha256"]:
        raise ValueError("Origin diagnostic input differs from its frozen hash")
    frame = pd.read_csv(source)
    if set(zip(frame.market, frame.horizon)) != {(m, h) for m in spec["markets"] for h in spec["horizons"]}:
        raise ValueError("Unexpected market/horizon coverage")
    deletions = origin_deletions(frame)
    summary = summarize(deletions)
    OUT.mkdir(parents=True, exist_ok=True)
    outputs = {"leave_one_origin_out.csv": deletions, "summary.csv": summary}
    for name, values in outputs.items():
        values.to_csv(OUT / name, index=False, float_format="%.12g", lineterminator="\n")
    manifest = dict(status=spec["status"], completed_at_utc=datetime.now(timezone.utc).isoformat(),
                    protocol_sha256=sha(config_path), lock_sha256=sha(lock_path),
                    input_hashes={spec["input"]: sha(source)},
                    code_hashes={"scripts/origin_sensitivity.py": sha(__file__)},
                    output_hashes={(OUT / name).relative_to(ROOT).as_posix(): sha(OUT / name) for name in outputs})
    (OUT / "run_manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
