"""A distributed manifest must restore exact missing bytes without changing provenance."""
import hashlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fetch_catalogs
import fetch_sources


class Response:
    def __init__(self, data):
        self.data=data
        self.headers={"Last-Modified":"Mon, 01 Jan 2024 00:00:00 GMT", "Content-Type":"application/octet-stream"}
        self.url="https://example.test/registered"
        self.status=200
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self,limit): return self.data[:limit]


class RestoreTests(unittest.TestCase):
    def test_missing_registered_source_restored_without_manifest_change(self):
        content=b"test fixture only"
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);raw=root/"raw";manifest=root/"manifest.json"
            source=dict(id="rental_panel",url="https://example.test/registered",file="panel.csv")
            record=dict(source,sha256=hashlib.sha256(content).hexdigest(),retrieved_at_utc="original")
            (root/"sources.json").write_text(json.dumps([source]))
            manifest.write_text(json.dumps([record]));before=manifest.read_bytes()
            with patch.multiple(fetch_sources,ROOT=root,RAW=raw,MANIFEST=manifest),patch.object(fetch_sources,"urlopen",return_value=Response(content)):
                fetch_sources.main(["rental_panel"])
            self.assertEqual((raw/"panel.csv").read_bytes(),content)
            self.assertEqual(manifest.read_bytes(),before)

    def test_changed_registered_vintage_is_not_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);raw=root/"raw";manifest=root/"manifest.json"
            source=dict(id="x",url="https://example.test/registered",file="x.csv")
            (root/"sources.json").write_text(json.dumps([source]))
            manifest.write_text(json.dumps([dict(source,sha256=hashlib.sha256(b"old").hexdigest())]))
            with patch.multiple(fetch_sources,ROOT=root,RAW=raw,MANIFEST=manifest),patch.object(fetch_sources,"urlopen",return_value=Response(b"new")):
                with self.assertRaisesRegex(ValueError,"vintage"): fetch_sources.main()
            self.assertFalse((raw/"x.csv").exists())

    def test_only_selection_avoids_unrelated_live_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);raw=root/"raw";manifest=root/"manifest.json"
            sources=[dict(id=id,url="https://example.test/"+id,file=id+".csv") for id in ["rental","live"]]
            (root/"sources.json").write_text(json.dumps(sources))
            with patch.multiple(fetch_sources,ROOT=root,RAW=raw,MANIFEST=manifest),patch.object(fetch_sources,"urlopen",return_value=Response(b"fixture")) as call:
                fetch_sources.main(["rental"])
                self.assertEqual(call.call_count,1)
                self.assertIn("/rental",call.call_args.args[0].full_url)
            self.assertFalse((raw/"live.csv").exists())

    def catalog(self):
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,"w") as archive: archive.writestr("version","20240101")
        content=buffer.getvalue()
        record=dict(nominal_month="2024-01",sha256=hashlib.sha256(content).hexdigest(),
                    object_last_modified_utc="2024-01-01T00:00:00+00:00",retrieved_at_utc="original")
        return content,record

    def test_missing_catalog_restores_registered_bytes(self):
        content,record=self.catalog()
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(fetch_catalogs,"RAW",Path(tmp)),patch.object(fetch_catalogs,"urlopen",return_value=Response(content)):
                result=fetch_catalogs.fetch(("2024-01","v1/20240101"),{"v1/20240101":record})
            self.assertEqual(result,record)
            self.assertEqual((Path(tmp)/"v1_20240101.zip").read_bytes(),content)

    def test_existing_corrupt_catalog_is_not_overwritten(self):
        content,record=self.catalog()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"v1_20240101.zip";path.write_bytes(b"corrupt")
            with patch.object(fetch_catalogs,"RAW",Path(tmp)),patch.object(fetch_catalogs,"urlopen") as call:
                with self.assertRaisesRegex(ValueError,"hash mismatch"):
                    fetch_catalogs.fetch(("2024-01","v1/20240101"),{"v1/20240101":record})
                call.assert_not_called()
            self.assertEqual(path.read_bytes(),b"corrupt")

    def test_changed_catalog_publication_proxy_is_not_written(self):
        content,record=self.catalog();record["object_last_modified_utc"]="2024-01-02T00:00:00+00:00"
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(fetch_catalogs,"RAW",Path(tmp)),patch.object(fetch_catalogs,"urlopen",return_value=Response(content)):
                with self.assertRaisesRegex(ValueError,"publication proxy"):
                    fetch_catalogs.fetch(("2024-01","v1/20240101"),{"v1/20240101":record})
            self.assertFalse((Path(tmp)/"v1_20240101.zip").exists())


if __name__=="__main__": unittest.main()
