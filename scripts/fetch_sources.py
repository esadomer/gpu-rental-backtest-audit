"""Cache the explicit public source register; never execute downloaded content."""

from __future__ import annotations

import hashlib
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MANIFEST = ROOT / "data" / "source_manifest.json"
MAX_BYTES = 50_000_000


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def main(source_ids=None) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    sources = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    if source_ids:
        unknown = set(source_ids) - {source["id"] for source in sources}
        if unknown:
            raise ValueError(f"Unknown source ids: {sorted(unknown)}")
        sources = [source for source in sources if source["id"] in source_ids]
    existing = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else []
    known = {record["id"]: record for record in existing}
    for source in sources:
        expected = known.get(source["id"])
        target = (RAW / source["file"]).resolve()
        if not target.is_relative_to(RAW.resolve()):
            raise ValueError("Source cache path must stay inside data/raw")
        if source["id"] in known:
            record = known[source["id"]]
            if record["url"] != source["url"] or record["file"] != source["file"]:
                raise ValueError(f"Registered source changed: {source['id']}")
            if target.exists():
                if not target.is_file() or digest(target.read_bytes()) != record["sha256"]:
                    raise ValueError(f"Cached source failed integrity check: {source['id']}")
                print(f"Verified cache: {source['id']}")
                continue
        if target.exists():
            raise ValueError(f"Refusing to overwrite an unregistered file: {target}")
        if not source["url"].startswith("https://"):
            raise ValueError("Only explicit HTTPS sources are supported")
        headers = {"User-Agent": "GPU-Price-Data-Audit/0.1"}
        if "range" in source:
            headers["Range"] = source["range"]
        request = Request(source["url"], headers=headers)
        with urlopen(request, timeout=40) as response:
            if "range" in source and response.status != 206:
                raise ValueError(f"Source did not honor range request: {source['id']}")
            content = response.read(MAX_BYTES + 1)
            if len(content) > MAX_BYTES:
                raise ValueError(f"Source exceeds download limit: {source['id']}")
            record = dict(source, retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
                          final_url=response.url, content_type=response.headers.get("Content-Type"),
                          content_range=response.headers.get("Content-Range"),
                          bytes=len(content), sha256=digest(content))
        if expected and digest(content) != expected["sha256"]:
            raise ValueError(f"Registered vintage is no longer available: {source['id']}; downloaded bytes differ from the saved hash")
        target.write_bytes(content)
        if expected:
            print(f"Restored exact registered bytes: {source['id']} ({len(content):,} bytes)")
            continue
        known[source["id"]] = record
        MANIFEST.write_text(json.dumps(list(known.values()), indent=2) + "\n", encoding="utf-8")
        print(f"Downloaded: {source['id']} ({len(content):,} bytes)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="+", help="Fetch only these registered source ids (avoids unrelated live pages)")
    main(parser.parse_args().only)
