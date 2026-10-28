"""Read original, hash-verified catalogs; never interpolate or run remote code."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import zipfile
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "config/study_protocol.json"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_number(value, positive=True):
    n = Decimal(value)
    if not n.is_finite() or (positive and n <= 0) or (not positive and n < 0):
        raise ValueError("Invalid numeric field")
    return format(n.normalize(), "f")


def normalize(raw, provider, spec, line, protocol):
    if provider not in protocol["providers"]:
        return None, "excluded_provider"
    if raw.get("gpu_name") not in protocol["gpu_labels"]:
        return None, "non_target_gpu"
    if raw.get("flags", ""):
        return None, "flagged_service"
    if raw.get("spot") not in ("True", "False"):
        return None, "unknown_market"
    try:
        row = {k: canonical_number(raw[k]) for k in
               ("gpu_memory", "gpu_count", "cpu", "memory", "price")}
        if any(float(row[k]) != int(float(row[k])) for k in ("gpu_count", "cpu")):
            return None, "nonintegral_hardware_count"
        disk = canonical_number(raw["disk_size"], False) if raw.get("disk_size") else "unknown"
    except (KeyError, TypeError, ValueError, OverflowError, InvalidOperation):
        return None, "invalid_numeric_field"
    if not raw.get("instance_name") or not raw.get("location"):
        return None, "missing_identity"
    row.update(provider=provider, location=raw["location"].strip(), instance_name=raw["instance_name"].strip(),
               gpu_name=raw["gpu_name"], market="spot" if raw["spot"] == "True" else "on_demand",
               disk_size=disk, cpu_arch=raw.get("cpu_arch") or "unknown",
               month=spec["nominal_month"], version=spec["version"],
               published=spec["object_last_modified_utc"], source_line=line,
               source_member=provider + ".csv", source_sha256=spec["sha256"])
    row["raw_record"] = json.dumps(raw, sort_keys=True, separators=(",", ":"))
    row["price_instance"] = float(row.pop("price"))
    row["price"] = row["price_instance"] / float(row["gpu_count"])
    for mode, fields in (("key", protocol["core_identity"]),
                         ("strict_key", protocol["core_identity"] + protocol["strict_identity_additions"])):
        row[mode] = hashlib.sha256(json.dumps([row[k] for k in fields], separators=(",", ":")).encode()).hexdigest()[:24]
    row["gpu"] = row["gpu_name"] + "_" + row["gpu_memory"]
    return row, "candidate"


def resolve_duplicates(rows):
    """A conflicting core service is not recoverable by choosing the cheapest row."""
    groups = defaultdict(list)
    for row in rows:
        groups[(row["version"], row["key"])].append(row)
    kept, excluded = [], []
    for group in groups.values():
        signatures = {(r["price"], r["disk_size"], r["cpu_arch"]) for r in group}
        if len(signatures) != 1:
            excluded.extend(dict(r, reason="conflicting_same_snapshot_identity") for r in group)
        else:
            kept.append(group[0])
            excluded.extend(dict(r, reason="duplicate_capture") for r in group[1:])
    return sorted(kept, key=lambda r: (r["month"], r["key"])), excluded


def write_csv(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]) if rows else fields or ["empty"])
        writer.writeheader()
        writer.writerows(rows)


def load_panel(write=False):
    protocol = json.loads(PROTOCOL_PATH.read_text())
    manifest = json.loads((ROOT / "data/catalog_manifest.json").read_text())
    amendment = json.loads((ROOT / "config/protocol_amendment_01.json").read_text())
    candidates, exclusions, tally = [], [], Counter()
    members, prior_members = [], {}
    for spec in manifest:
        path = ROOT / "data/catalog_raw" / spec["filename"]
        if digest(path) != spec["sha256"]:
            raise ValueError(f"Archive hash mismatch: {path.name}")
        with zipfile.ZipFile(path) as archive:
            snapshot_members = {}
            if archive.read("version").decode().strip() != spec["embedded_version"]:
                raise ValueError("Embedded version mismatch")
            for name in sorted(archive.namelist()):
                if not name.endswith(".csv"):
                    continue
                if archive.getinfo(name).file_size > 100_000_000:
                    raise ValueError("Oversized catalog member")
                provider = name.removesuffix(".csv")
                content = archive.read(name)
                raw_rows = list(csv.DictReader(io.StringIO(content.decode("utf-8"))))
                member_hash = hashlib.sha256(content).hexdigest()
                semantic_hash = member_fingerprint(raw_rows)
                alias_of = amendment["duplicate_provider_aliases"].get(provider)
                if alias_of and snapshot_members.get(alias_of) != semantic_hash:
                    raise ValueError(f"Provider alias is not an exact semantic duplicate: {spec['version']} / {provider}")
                snapshot_members[provider] = semantic_hash
                previous = prior_members.get(provider)
                member = dict(version=spec["version"], month=spec["nominal_month"], provider=provider,
                              raw_sha256=member_hash, semantic_sha256=semantic_hash,
                              repeated_raw=bool(previous and previous[0] == member_hash),
                              repeated_semantic=bool(previous and previous[1] == semantic_hash))
                members.append(member)
                prior_members[provider] = (member_hash, semantic_hash)
                for line, raw in enumerate(raw_rows, 2):
                    row, reason = normalize(raw, provider, spec, line, protocol)
                    if alias_of and row is not None:
                        row, reason = None, "duplicate_provider_alias"
                    tally[reason] += 1
                    if row:
                        row["member_repeated"] = member["repeated_semantic"]
                        row["member_sha256"] = member_hash
                        candidates.append(row)
                    elif raw.get("gpu_name") in protocol["gpu_labels"]:
                        exclusions.append(dict(version=spec["version"], member=name, line=line, reason=reason))
    rows, duplicate_exclusions = resolve_duplicates(candidates)
    for r in duplicate_exclusions:
        tally[r["reason"]] += 1
        exclusions.append(dict(version=r["version"], member=r["source_member"], line=r["source_line"], reason=r["reason"]))
    summary = dict(archives=len(manifest), rows=len(rows), raw_row_categories=dict(sorted(tally.items())),
                   keys=len({r["key"] for r in rows}), strict_keys=len({r["strict_key"] for r in rows}),
                   first_month=min(r["month"] for r in rows), last_month=max(r["month"] for r in rows))
    coverage = []
    for provider in protocol["providers"]:
        for gpu in sorted({r["gpu"] for r in rows}):
            for market in ("on_demand", "spot"):
                group = [r for r in rows if (r["provider"], r["gpu"], r["market"]) == (provider, gpu, market)]
                if group:
                    coverage.append(dict(provider=provider, gpu=gpu, market=market, rows=len(group),
                                         keys=len({r["key"] for r in group}), months=len({r["month"] for r in group}),
                                         first_month=min(r["month"] for r in group), last_month=max(r["month"] for r in group)))
    if write:
        folder = ROOT / "data/research"
        write_csv(folder / "catalog_panel.csv", rows)
        write_csv(folder / "catalog_exclusions.csv", exclusions)
        write_csv(folder / "catalog_coverage.csv", coverage)
        write_csv(folder / "provider_members.csv", members)
        (folder / "catalog_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return rows, manifest, summary


def member_fingerprint(rows):
    """Order-invariant whole-provider core-offer state, ignoring schema additions."""
    fields = ("instance_name", "location", "price", "cpu", "memory", "gpu_count", "gpu_name", "gpu_memory", "spot")
    numeric = {"price", "cpu", "memory", "gpu_count", "gpu_memory"}
    normalized = set()
    for row in rows:
        values = []
        for field in fields:
            value = row.get(field, "").strip()
            if field in numeric and value:
                try:
                    value = canonical_number(value, False)
                except (ValueError, InvalidOperation):
                    pass
            values.append(value)
        normalized.add(tuple(values))
    return hashlib.sha256(json.dumps(sorted(normalized), separators=(",", ":")).encode()).hexdigest()


if __name__ == "__main__":
    print(json.dumps(load_panel(write=True)[2], indent=2))
