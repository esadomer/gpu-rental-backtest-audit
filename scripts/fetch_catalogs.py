"""Download explicit historical gpuhunt snapshots and preserve server timestamps.

The published Mittal panel is a locator for snapshot URLs, never the model input.
No downloaded code is executed and no ZIP paths are extracted to the filesystem.
"""

from __future__ import annotations

import concurrent.futures
import csv
import hashlib
import io
import json
import re
import time
import zipfile
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.request import Request, urlopen

from audit_data import read_source

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "catalog_raw"
MANIFEST = ROOT / "data" / "catalog_manifest.json"
BASE = "https://dstack-gpu-pricing.s3.eu-west-1.amazonaws.com"
LIMIT = 10_000_000


def fetch(spec: tuple[str, str], cached: dict) -> dict:
    month, version = spec
    if not re.fullmatch(r"v[12]/\d{8}(?:-\d+)?", version):
        raise ValueError(f"Unexpected catalog version: {version}")
    filename = version.replace("/", "_") + ".zip"
    path = RAW / filename
    if version in cached:
        record = cached[version]
        if record["nominal_month"] != month:
            raise ValueError(f"Catalog month changed: {version}")
        if path.exists():
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
                raise ValueError(f"Cached catalog hash mismatch: {version}")
            return record
    url = f"{BASE}/{version}/catalog.zip"
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={"User-Agent": "GPU-Rental-Research/0.1"}), timeout=30) as response:
                content = response.read(LIMIT + 1)
                modified = response.headers.get("Last-Modified")
                etag = response.headers.get("ETag")
                final_url = response.url
            break
        except OSError:
            if attempt == 2:
                raise
            time.sleep(1 + attempt)
    if len(content) > LIMIT or not modified:
        raise ValueError(f"Missing publication proxy or excessive archive size: {version}")
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        embedded = archive.read("version").decode("utf-8").strip()
        if embedded != version.split("/")[1]:
            raise ValueError(f"Embedded archive version mismatch: {version} / {embedded}")
        members = archive.namelist()
    if version in cached:
        record = cached[version]
        if hashlib.sha256(content).hexdigest() != record["sha256"]:
            raise ValueError(f"Registered catalog vintage changed: {version}")
        observed_modified = parsedate_to_datetime(modified).astimezone(timezone.utc).isoformat()
        if observed_modified != record["object_last_modified_utc"]:
            raise ValueError(f"Catalog publication proxy changed: {version}")
        path.write_bytes(content)
        return record
    path.write_bytes(content)
    return dict(nominal_month=month, version=version, filename=filename, url=url, final_url=final_url,
                nominal_snapshot_date=datetime.strptime(version.split("/")[1][:8], "%Y%m%d").date().isoformat(),
                object_last_modified_utc=parsedate_to_datetime(modified).astimezone(timezone.utc).isoformat(),
                availability_basis="S3 Last-Modified; proxy for archived-object publication, not proof of historical public ACL",
                retrieved_at_utc=datetime.now(timezone.utc).isoformat(), etag=etag, bytes=len(content),
                sha256=hashlib.sha256(content).hexdigest(), embedded_version=embedded, members=members)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    rows = csv.DictReader(io.StringIO(read_source("rental_panel").decode("utf-8")))
    specs = sorted({(r["month"], r["source_version"]) for r in rows if r["source"] == "gpuhunt"
                    and "2023-01" <= r["month"] <= "2026-09"})
    existing = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else []
    cached = {r["version"]: r for r in existing}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fetch, spec, cached): spec for spec in specs}
        for future in concurrent.futures.as_completed(futures):
            record = future.result()
            cached[record["version"]] = record
            MANIFEST.write_text(json.dumps(sorted(cached.values(), key=lambda r: r["nominal_month"]), indent=2) + "\n", encoding="utf-8")
            print(f"Verified {record['nominal_month']}: {record['version']}", flush=True)
    print(f"Catalog archives ready: {len(cached)}", flush=True)


if __name__ == "__main__":
    main()
