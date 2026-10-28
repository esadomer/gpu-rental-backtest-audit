"""Audit cached real observations. This program fits no models and fills no gaps."""

from __future__ import annotations

import calendar
import csv
import hashlib
import io
import json
import re
import statistics
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "derived"
START = date(2023, 1, 1)
CUTOFF = date(2026, 10, 28)
GPUS = {"A100-40GB", "A100-80GB", "H100", "H200"}
MANIFEST = ROOT / "data" / "source_manifest.json"


def read_source(source_id: str) -> bytes:
    records = json.loads(MANIFEST.read_text(encoding="utf-8"))
    record = next(r for r in records if r["id"] == source_id)
    content = (RAW / record["file"]).read_bytes()
    if hashlib.sha256(content).hexdigest() != record["sha256"]:
        raise ValueError(f"Raw source hash mismatch: {source_id}")
    return content


def write_csv(name: str, rows: list[dict], fields: list[str] | None = None) -> None:
    if fields is None:
        if not rows:
            raise ValueError(f"Empty CSV needs explicit columns: {name}")
        fields = list(rows[0])
    with (OUT / name).open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def number(value: str) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite() or result <= 0:
        raise ValueError(f"Price must be positive and finite: {value}")
    return result


def month_number(month: str) -> int:
    parsed = date.fromisoformat(month + "-01")
    return parsed.year * 12 + parsed.month - 1


def longest_run(months: set[str]) -> int:
    best = run = 0
    previous = None
    for current in sorted(month_number(m) for m in months):
        run = run + 1 if previous is not None and current == previous + 1 else 1
        best = max(best, run)
        previous = current
    return best


def evidence_date(row: dict) -> date:
    # This is the date of the cited artifact, NOT the earliest possible date the
    # price was public. One AWS publication header is independently checked below.
    if row["source"] == "aws_bulk":
        return datetime.strptime(row["source_version"], "%Y%m%d%H%M%S").date()
    return date.fromisoformat(row["snapshot_date"])


def rejection_reasons(row: dict) -> list[str]:
    reasons = []
    if row["in_index"] not in {"True", "False"}:
        raise ValueError("Unknown upstream in_index value")
    if row["in_index"] != "True":
        reasons.append("upstream_not_in_index")
    if row["observation_type"] == "effective_date_backfill":
        reasons.append("effective_date_backfill")
    if row["form_factor"] not in {"SXM", "PCIe", "NVL"}:
        reasons.append("unresolved_form_factor")
    if not row["source_version"] or not row["instance_types"]:
        reasons.append("missing_provenance_or_instance_label")
    if evidence_date(row) > CUTOFF:
        reasons.append("cited_artifact_after_cutoff")
    number(row["usd_per_gpu_hour"])
    return reasons


def quote_identity(row: dict) -> tuple:
    return tuple(row[k] for k in ("gpu", "form_factor", "segment", "provider", "region",
                                  "source", "source_version", "instance_types"))


def summarize_rental(group: list[dict]) -> dict:
    months = {r["month"] for r in group}
    provider_months = {(r["provider"], r["month"]) for r in group}
    source_quotes = {quote_identity(r) for r in group}
    series = defaultdict(list)
    for r in group:
        key = tuple(r[k] for k in ("provider", "region", "source", "instance_types"))
        series[key].append(r)
    pair_count = changed_pairs = 0
    repricing_cells = set()
    for observations in series.values():
        # Ambiguous multiple rows in the same month are not averaged or compared.
        month_groups = defaultdict(list)
        for r in observations:
            month_groups[r["month"]].append(r)
        observations = [v[0] for _, v in sorted(month_groups.items()) if len(v) == 1]
        for before, after in zip(observations, observations[1:]):
            if month_number(after["month"]) - month_number(before["month"]) != 1:
                continue
            if before["source_version"] == after["source_version"]:
                continue
            pair_count += 1
            if number(before["usd_per_gpu_hour"]) != number(after["usd_per_gpu_hour"]):
                changed_pairs += 1
                repricing_cells.add((after["provider"], after["month"]))
    after_start = after_end = reused_month = 0
    fresh_provider_months = set()
    for r in group:
        evidence = evidence_date(r)
        first = date.fromisoformat(r["month"] + "-01")
        last = first.replace(day=calendar.monthrange(first.year, first.month)[1])
        after_start += evidence > first
        after_end += evidence > last
        reused_month += evidence < first
        if first <= evidence <= last:
            fresh_provider_months.add((r["provider"], r["month"]))
    per_month = Counter(m for _, m in provider_months)
    return {
        "rows": len(group), "first_month": min(months), "last_month": max(months),
        "observed_months": len(months), "longest_month_run": longest_run(months),
        "providers": len({r["provider"] for r in group}),
        "provider_months": len(provider_months), "distinct_source_quote_keys": len(source_quotes),
        "distinct_source_versions": len({(r["provider"], r["source"], r["source_version"]) for r in group}),
        "months_with_at_least_three_providers": sum(n >= 3 for n in per_month.values()),
        "rows_with_artifact_before_month": reused_month,
        "rows_with_artifact_after_month_start": after_start,
        "rows_with_artifact_after_month_end": after_end,
        "provider_months_with_artifact_in_month": len(fresh_provider_months),
        "adjacent_same_label_new_snapshot_pairs": pair_count,
        "changed_same_label_pairs": changed_pairs,
        "provider_months_with_same_label_price_change": len(repricing_cells),
    }


def rental_audit() -> dict:
    rows = list(csv.DictReader(io.StringIO(read_source("rental_panel").decode("utf-8"))))
    focus = [dict(r, csv_line=i + 2) for i, r in enumerate(rows)
             if r["gpu"] in GPUS and START.strftime("%Y-%m") <= r["month"] <= CUTOFF.strftime("%Y-%m")]
    accepted, rejected = [], []
    for r in focus:
        reasons = rejection_reasons(r)
        if reasons:
            rejected.append({"csv_line": r["csv_line"], "gpu": r["gpu"], "form_factor": r["form_factor"],
                             "month": r["month"], "reasons": "|".join(reasons)})
        else:
            accepted.append(r)
    quotes = defaultdict(set)
    for r in accepted:
        quotes[quote_identity(r)].add(number(r["usd_per_gpu_hour"]))
    conflicts = {k for k, prices in quotes.items() if len(prices) > 1}
    if conflicts:
        raise ValueError(f"Conflicting prices within {len(conflicts)} source quote identities")
    coverage = []
    groups = defaultdict(list)
    for r in accepted:
        groups[(r["gpu"], r["form_factor"], r["segment"])].append(r)
    for (gpu, form, segment), group in sorted(groups.items()):
        coverage.append(dict(gpu=gpu, form_factor=form, segment=segment, **summarize_rental(group)))
    # Same scope as the initial chat's preliminary count; it is coverage only.
    headline = []
    for gpu in sorted(GPUS):
        group = [r for r in accepted if r["gpu"] == gpu and r["form_factor"] == "SXM"
                 and r["market"] == "on_demand"]
        headline.append(dict(gpu=gpu, form_factor="SXM", **summarize_rental(group)))
    provider_groups = defaultdict(list)
    for r in accepted:
        provider_groups[(r["gpu"], r["form_factor"], r["segment"], r["provider"])].append(r)
    provider_coverage = []
    for (gpu, form, segment, provider), group in sorted(provider_groups.items()):
        provider_coverage.append(dict(gpu=gpu, form_factor=form, segment=segment, provider=provider,
                                      **summarize_rental(group)))
    monthly = []
    for (gpu, form, segment), group in sorted(groups.items()):
        for month in sorted({r["month"] for r in group}):
            selected = [r for r in group if r["month"] == month]
            monthly.append(dict(gpu=gpu, form_factor=form, segment=segment, month=month,
                                providers=len({r["provider"] for r in selected}), rows=len(selected)))
    write_csv("rental_coverage.csv", coverage)
    write_csv("rental_headline.csv", headline)
    write_csv("rental_provider_coverage.csv", provider_coverage)
    write_csv("rental_monthly_coverage.csv", monthly)
    write_csv("rental_rejections.csv", rejected)
    timing = [{"csv_line": r["csv_line"], "gpu": r["gpu"], "month": r["month"],
               "source": r["source"], "snapshot_date": r["snapshot_date"],
               "cited_artifact_date": evidence_date(r).isoformat(), "source_version": r["source_version"]}
              for r in accepted if evidence_date(r) > date.fromisoformat(r["month"] + "-01")]
    write_csv("rental_timing_flags.csv", timing)
    return dict(raw_rows=len(rows), target_rows=len(focus), candidate_rows=len(accepted),
                rejected_rows=len(rejected), observation_types=dict(Counter(r["observation_type"] for r in focus)),
                rejection_counts=dict(Counter(reason for r in rejected for reason in r["reasons"].split("|"))),
                headline=headline)


def parse_tracker(html: str) -> dict:
    match = re.search(r"\bvar\s+homePageItems\s*=\s*(\[.*?\]);", html, re.DOTALL)
    if not match:
        raise ValueError("Missing public homePageItems JSON")
    data = json.loads(match.group(1))
    if len(data) != 1 or not isinstance(data[0].get("updates"), list):
        raise ValueError("Unexpected tracker schema")
    return data[0]


def summarize_updates(updates: list[dict]) -> tuple[dict, list[tuple[int, Decimal]]]:
    all_unique = {(int(r["date"]), number(r["price"])) for r in updates}
    # pMsg is undocumented and often forms midnight chart sequences. Inventory
    # it, but do not claim it is an observed quote. Unknown categories also fail
    # closed. The remaining labels still do not certify seller/condition history.
    candidate_updates = [r for r in updates if r.get("source") in {"pPrice", "pIncrease"}]
    unique = sorted({(int(r["date"]), number(r["price"])) for r in candidate_updates})
    grouped = defaultdict(set)
    for timestamp, price in unique:
        grouped[timestamp].add(price)
    conflicts = sum(len(prices) > 1 for prices in grouped.values())
    eligible = [(t, p) for t, p in unique
                if START <= datetime.fromtimestamp(t / 1000, timezone.utc).date() <= CUTOFF]
    unambiguous = [(t, p) for t, p in eligible if len(grouped[t]) == 1]
    dates = {datetime.fromtimestamp(t / 1000, timezone.utc).date() for t, _ in eligible}
    changes = sum(a[1] != b[1] for a, b in zip(unambiguous, unambiguous[1:]))
    gaps = [(b[0] - a[0]) / 86_400_000 for a, b in zip(unambiguous, unambiguous[1:])]
    return dict(raw_updates=len(updates), unique_timestamp_price_records=len(all_unique),
                duplicate_records=len(updates) - len(all_unique),
                excluded_ambiguous_category_records=len(updates) - len(candidate_updates),
                candidate_unique_records=len(unique),
                candidate_duplicate_records=len(candidate_updates) - len(unique), conflicting_timestamps=conflicts,
                in_window_unique_records=len(eligible), observed_days=len(dates),
                first_observed_date=min(dates).isoformat() if dates else "",
                last_observed_date=max(dates).isoformat() if dates else "",
                observed_months=len({d.strftime("%Y-%m") for d in dates}),
                distinct_prices=len({p for _, p in eligible}), observed_price_changes=changes,
                max_capture_gap_days=round(max(gaps, default=0), 3),
                observations_before_window=sum(datetime.fromtimestamp(t / 1000, timezone.utc).date() < START for t, _ in all_unique),
                observations_after_cutoff=sum(datetime.fromtimestamp(t / 1000, timezone.utc).date() > CUTOFF for t, _ in all_unique)), eligible


PHYSICAL = {
    "glassit_h100_newegg": ("H100", "PCIe", "title_and_current_listing_only"),
    "glassit_h100_viperatech": ("H100", "PCIe", "historical_condition_unverified"),
    "glassit_h100_cdw": ("H100", "unresolved_kit", "historical_condition_unverified"),
    "glassit_h100_amazon": ("H100", "PCIe_claimed", "historical_condition_unverified"),
    "glassit_a100_newegg": ("A100-40GB", "PCIe", "historical_condition_unverified"),
    "glassit_a100_amazon": ("A100-40GB", "PCIe_claimed", "historical_condition_unverified"),
    "glassit_a100_ebay": ("A100-40GB", "unknown", "historical_condition_unverified"),
    "glassit_a100_80_ebay": ("A100-80GB", "PCIe_claimed", "historical_condition_unverified"),
    "glassit_h100_identity_drift": ("H100", "unknown", "rejected_identity_drift"),
}


def physical_audit() -> dict:
    summary, observations, metadata, raw_records = [], [], [], []
    for source_id, (gpu, form, condition) in PHYSICAL.items():
        payload = parse_tracker(read_source(source_id).decode("utf-8"))
        stats, unique = summarize_updates(payload["updates"])
        if payload.get("currency") != "USD":
            raise ValueError(f"Unexpected currency: {source_id}")
        status = "rejected_identity_drift" if condition == "rejected_identity_drift" else "exploratory_quotes_only"
        summary.append(dict(source_id=source_id, gpu=gpu, form_factor=form, status=status,
                            historical_condition=condition, historical_seller="unverified",
                            verified_new_observations=0, declared_data_size=payload.get("dataSize"), **stats))
        categories = defaultdict(set)
        for i, record in enumerate(payload["updates"]):
            key = (int(record["date"]), number(record["price"]))
            category = record.get("source", "missing")
            categories[key].add(category)
            raw_records.append(dict(source_id=source_id, raw_update_index=i, timestamp_ms=key[0],
                                    quoted_usd=str(key[1]), source_category=category,
                                    category_retained=category in {"pPrice", "pIncrease"}, series_status=status))
        metadata.append(dict(source_id=source_id, source_category_counts=dict(Counter(r.get("source", "missing") for r in payload["updates"])),
                             **{k: v for k, v in payload.items() if k != "updates"}))
        for timestamp, price in unique:
            observations.append(dict(source_id=source_id, gpu=gpu, form_factor=form,
                                     observed_at_utc=datetime.fromtimestamp(timestamp / 1000, timezone.utc).isoformat(),
                                     timestamp_ms=timestamp, quoted_usd=str(price),
                                     source_categories="|".join(sorted(categories[(timestamp, price)])), status=status,
                                     historical_new_verified=False, historical_seller_verified=False))
    write_csv("physical_series.csv", summary)
    write_csv("physical_all_tracker_records.csv", raw_records)
    write_csv("physical_quote_observations.csv", observations)
    (OUT / "physical_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return dict(verified_new_price_histories=0, verified_executed_new_sales=0,
                extracted_tracker_histories=len(summary), series=summary)


def upstream_checks() -> list[dict]:
    panel = list(csv.DictReader(io.StringIO(read_source("rental_panel").decode())))
    results = []
    specifications = [
        ("skypilot_lambda_20230117", None, "2023-02", "lambda", "A100-40GB", "PCIe", "asia-northeast-1"),
        ("gpuhunt_20240701", "runpod.csv", "2024-07", "runpod", "H100", "SXM", "CA-MTL-2"),
        ("gpuhunt_20250501", "datacrunch.csv", "2025-05", "verda", "H200", "SXM", "FIN-01"),
    ]
    for source_id, member, month, provider, gpu, form, region in specifications:
        matches = [r for r in panel if (r["month"], r["provider"], r["gpu"], r["form_factor"], r["region"])
                   == (month, provider, gpu, form, region) and r["in_index"] == "True" and r["market"] == "on_demand"]
        if len(matches) != 1:
            raise ValueError(f"Ambiguous verification target: {source_id}")
        target = matches[0]
        content = read_source(source_id)
        if member:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                # Read an explicitly named member in memory; never extract archive paths.
                content = archive.read(member)
        raw = list(csv.DictReader(io.StringIO(content.decode())))
        instances = set(target["instance_types"].split("|"))
        values = []
        for r in raw:
            if member:
                if r["instance_name"] not in instances or r["location"] != region or r["spot"] != "False":
                    continue
                # July 2024 RunPod mixed Secure/Community at a location. For this
                # specific sample the upstream uses the higher, secure offer.
                values.append(number(r["price"]) / number(r["gpu_count"]))
            elif r["InstanceType"] in instances and r["Region"] == region:
                values.append(number(r["Price"]) / number(r["AcceleratorCount"]))
        if provider == "runpod":
            highest = max(values)
            values = [v for v in values if abs(v - highest) < Decimal("0.000001")]
        if not values:
            raise ValueError(f"No original quotes found for {source_id}")
        recomputed = statistics.median(values)
        passed = abs(recomputed - number(target["usd_per_gpu_hour"])) < Decimal("0.000001")
        results.append(dict(source_id=source_id, month=month, provider=provider, gpu=gpu, form_factor=form,
                            region=region, panel_value=target["usd_per_gpu_hour"], recomputed_value=str(recomputed),
                            source_quotes=len(values), passed=passed,
                            limitation="secure tier inferred by higher price" if provider == "runpod" else "catalog arithmetic only"))
    gcp_rows = list(csv.DictReader(io.StringIO(read_source("skypilot_gcp_20240930").decode())))
    hosts = {r["AvailabilityZone"]: number(r["Price"]) for r in gcp_rows
             if r["Region"] == "us-central1" and r["InstanceType"] == "a3-highgpu-8g"}
    gpu_rows = {r["AvailabilityZone"]: number(r["Price"]) for r in gcp_rows
                if r["Region"] == "us-central1" and r["AcceleratorName"] == "H100" and r["AcceleratorCount"] == "8"}
    if not hosts or set(hosts) != set(gpu_rows):
        raise ValueError("GCP host/accelerator zone coverage differs")
    recomputed = statistics.median((hosts[z] + gpu_rows[z]) / 8 for z in hosts)
    matches = [r for r in panel if r["month"] == "2024-10" and r["provider"] == "gcp"
               and r["gpu"] == "H100" and r["region"] == "us-central1"
               and r["source"] == "skypilot" and r["market"] == "on_demand" and r["in_index"] == "True"]
    if len(matches) != 1:
        raise ValueError("Ambiguous GCP verification target")
    target = matches[0]
    results.append(dict(source_id="skypilot_gcp_20240930", month="2024-10", provider="gcp", gpu="H100",
                        form_factor="SXM", region="us-central1", panel_value=target["usd_per_gpu_hour"],
                        recomputed_value=str(recomputed), source_quotes=len(hosts),
                        passed=format(float(recomputed), ".6g") == target["usd_per_gpu_hour"],
                        limitation="host plus eight accelerators; compared at stored six-significant-digit precision"))
    if not all(r["passed"] for r in results):
        raise ValueError(f"Upstream sample mismatch: {results}")
    header = read_source("aws_20250703_header").decode()
    if '"Publication Date","2025-07-03T20:49:06Z"' not in header:
        raise ValueError("AWS publication header changed")
    write_csv("upstream_sample_checks.csv", results)
    return results


def cross_market_overlap() -> list[dict]:
    """Calendar overlap of candidate PCIe quotes, never a certified NEW panel."""
    panel = list(csv.DictReader(io.StringIO(read_source("rental_panel").decode())))
    rentals = [r for r in panel if r["gpu"] in GPUS and r["market"] == "on_demand"
               and START.strftime("%Y-%m") <= r["month"] <= CUTOFF.strftime("%Y-%m")
               and not rejection_reasons(r)]
    with (OUT / "physical_quote_observations.csv").open(encoding="utf-8", newline="") as f:
        physical = list(csv.DictReader(f))
    overlap = []
    for source_id, (gpu, form, _) in PHYSICAL.items():
        if form != "PCIe":
            continue
        months = {r["observed_at_utc"][:7] for r in physical if r["source_id"] == source_id}
        providers = defaultdict(set)
        for r in rentals:
            if r["gpu"] == gpu and r["form_factor"] == form and r["month"] in months:
                providers[r["month"]].add(r["provider"])
        shared = set(providers)
        overlap.append(dict(source_id=source_id, gpu=gpu, form_factor=form, physical_observed_months=len(months),
                            shared_observed_months=len(shared), longest_shared_month_run=longest_run(shared),
                            shared_months_with_three_rental_providers=sum(len(p) >= 3 for p in providers.values()),
                            rental_providers_over_shared_window=len(set().union(*providers.values())) if providers else 0,
                            shared_months="|".join(sorted(shared)), verified_joint_new_months=0,
                            status="exploratory_only_historical_condition_and_seller_unverified"))
    write_csv("cross_market_overlap.csv", overlap)
    return overlap


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    summary = dict(window_start=START.isoformat(), cutoff=CUTOFF.isoformat(),
                   rental=rental_audit(), physical=physical_audit(), upstream_checks=upstream_checks(),
                   exploratory_cross_market_overlap=cross_market_overlap())
    (OUT / "audit_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"target_rental_rows": summary["rental"]["target_rows"],
                      "candidate_rental_rows": summary["rental"]["candidate_rows"],
                      "physical_histories_extracted": summary["physical"]["extracted_tracker_histories"],
                      "verified_new_physical_histories": 0, "upstream_samples_passed": len(summary["upstream_checks"])}))


if __name__ == "__main__":
    main()
