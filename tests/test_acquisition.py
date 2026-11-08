"""Synthetic, offline acquisition fixtures; none are scientific data."""

import gzip
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import urllib.error

from alzresearch.acquisition import (AcquisitionError, LimitError, Limits,
                                     download, validate_content, data_bytes)


class Response(io.BytesIO):
    def __init__(self, body, headers=None):
        super().__init__(body)
        self.headers = headers or {}
        self.status = 200

    def geturl(self):
        return "https://example.invalid/final"


class AcquisitionTests(unittest.TestCase):
    def test_unknown_length_aggregate_budget_counts_all_streamed_chunks(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'existing').write_bytes(b'x' * 15000)
            limits = Limits(max_file_bytes=100000, max_total_bytes=90000,
                            max_expanded_bytes=100000, retries=0,
                            min_interval_seconds=0, disk_reserve_bytes=0)
            with mock.patch('urllib.request.urlopen', return_value=Response(b'd' * 80000)):
                with self.assertRaises(LimitError):
                    download('https://example.invalid/synthetic', root / 'new.txt',
                             accession='SYNTHETIC', data_root=root, limits=limits)
            self.assertFalse((root / 'new.txt').exists())
            self.assertFalse((root / 'new.txt.part').exists())

    def test_storage_budget_counts_hardlinked_content_once(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original = root / 'original.bin'
            original.write_bytes(b'synthetic payload')
            os.link(original, root / 'linked.bin')
            (root / 'other.bin').write_bytes(b'other')
            self.assertEqual(data_bytes(root), len(b'synthetic payload') + len(b'other'))

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "data"
        self.root.mkdir()
        self.dest = self.root / "raw" / "fixture.txt.gz"
        self.url = "https://example.invalid/fixture.txt.gz"
        self.limits = Limits(max_file_bytes=1000, max_total_bytes=10_000,
                             max_expanded_bytes=2000, retries=0,
                             min_interval_seconds=0, disk_reserve_bytes=0)

    def run_download(self, body, headers=None, **kwargs):
        with mock.patch("urllib.request.urlopen", return_value=Response(body, headers)):
            return download(self.url, self.dest, accession="SYNTHETIC",
                            data_root=self.root, limits=kwargs.pop("limits", self.limits),
                            **kwargs)

    def test_valid_gzip_provenance_and_idempotence(self):
        body = gzip.compress(b'!Series_title\t"synthetic test"\n')
        record = self.run_download(body, {"Content-Length": str(len(body)), "ETag": "synthetic"})
        self.assertEqual(record["status"], "downloaded")
        self.assertEqual(record["byte_count"], len(body))
        self.assertEqual(record["http_headers"]["ETag"], "synthetic")
        self.assertEqual(len(record["sha256"]), 64)
        self.assertTrue(record["validation"]["gzip"])
        with mock.patch("urllib.request.urlopen") as opener:
            cached = download(self.url, self.dest, accession="SYNTHETIC",
                              data_root=self.root, limits=self.limits)
        self.assertEqual(cached["status"], "cached")
        opener.assert_not_called()
        self.assertFalse(self.dest.with_name(self.dest.name + ".part").exists())

    def test_unknown_length_stream_enforces_file_limit(self):
        with self.assertRaises(LimitError):
            self.run_download(b"x" * 1001)
        self.assertFalse(self.dest.exists())
        self.assertFalse(self.dest.with_name(self.dest.name + ".part").exists())

    def test_known_length_preflight_rejects_large_response(self):
        with self.assertRaises(LimitError):
            self.run_download(b"unused", {"Content-Length": "1001"})
        self.assertFalse(self.dest.exists())

    def test_total_budget_includes_preexisting_and_temporary_files(self):
        (self.root / "other.part").write_bytes(b"x" * 100)
        limits = Limits(max_file_bytes=1000, max_total_bytes=200,
                        max_expanded_bytes=2000, retries=0, min_interval_seconds=0,
                        disk_reserve_bytes=0)
        with self.assertRaises(LimitError):
            self.run_download(b"x" * 150, limits=limits)
        self.assertEqual((self.root / "other.part").stat().st_size, 100)
        self.assertFalse(self.dest.exists())

    def test_html_disguised_as_data_rejected(self):
        for body, headers in [(b"<html>failure</html>", {}),
                              (b"server failure", {"Content-Type": "text/html"})]:
            with self.subTest(body=body), self.assertRaises(AcquisitionError):
                self.run_download(body, headers)
        self.assertFalse(self.dest.exists())

    def test_compressed_html_and_expansion_bomb_rejected(self):
        for body, error in [(gzip.compress(b"<html>error</html>"), AcquisitionError),
                            (gzip.compress(b"a" * 2001), LimitError)]:
            with self.subTest(error=error), self.assertRaises(error):
                self.run_download(body)

    def test_html_only_allowed_with_explicit_flag(self):
        destination = self.root / "listing.html"
        with mock.patch("urllib.request.urlopen", return_value=Response(b"<html>listing</html>")):
            record = download("https://example.invalid/", destination,
                              accession="SYNTHETIC", data_root=self.root,
                              limits=self.limits, allow_html=True)
        self.assertEqual(record["status"], "downloaded")
        self.assertTrue(record["allow_html"])

    def test_geo_matrix_content_kind_rejects_unexpected_text(self):
        with self.assertRaisesRegex(AcquisitionError, "metadata markers"):
            self.run_download(gzip.compress(b"arbitrary successful HTTP text"), content_kind="geo_matrix")
        record = self.run_download(gzip.compress(b'!Series_title\t"synthetic"\n'), content_kind="geo_matrix")
        self.assertEqual(record["content_kind"], "geo_matrix")

    def test_cached_format_validation_is_preserved_and_recorded(self):
        self.run_download(gzip.compress(b'!Series_title\t"synthetic"\n'), content_kind="geo_matrix")
        with mock.patch("urllib.request.urlopen") as opener:
            record = download(self.url, self.dest, accession="SYNTHETIC",
                              data_root=self.root, limits=self.limits)
        self.assertEqual(record["content_kind"], "geo_matrix")
        self.assertEqual(record["cache_validation"]["content_kind"], "geo_matrix")
        opener.assert_not_called()

    def test_malformed_or_mislocated_provenance_rejected(self):
        self.run_download(gzip.compress(b"synthetic"))
        sidecar = self.dest.with_name(self.dest.name + ".provenance.json")
        original = json.loads(sidecar.read_text())
        for value in [[], dict(original, local_path="data/wrong-file.gz")]:
            sidecar.write_text(json.dumps(value))
            with self.subTest(value=value), self.assertRaises(AcquisitionError):
                download(self.url, self.dest, accession="SYNTHETIC",
                         data_root=self.root, limits=self.limits)

    def test_wrong_gzip_magic_truncation_and_empty_rejected(self):
        corrupt_deflate = b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03" + b"\xff" * 20
        for body in [b"plain text", gzip.compress(b"value")[:-4], corrupt_deflate, b""]:
            with self.subTest(body=body), self.assertRaises(AcquisitionError):
                self.run_download(body)

    def test_content_length_mismatch_rejected(self):
        with self.assertRaisesRegex(AcquisitionError, "Content-Length mismatch"):
            self.run_download(gzip.compress(b"ok"), {"Content-Length": "100"})

    def test_existing_without_provenance_and_tampering_fail_closed(self):
        self.dest.parent.mkdir()
        self.dest.write_bytes(b"preexisting")
        with self.assertRaisesRegex(AcquisitionError, "lacks provenance"):
            self.run_download(gzip.compress(b"new"))
        self.assertEqual(self.dest.read_bytes(), b"preexisting")
        self.dest.unlink()
        self.run_download(gzip.compress(b"new"))
        self.dest.write_bytes(b"tampered")
        with self.assertRaisesRegex(AcquisitionError, "mismatch"):
            self.run_download(gzip.compress(b"new"))

    def test_paths_must_be_inside_data_root_and_not_symlinks(self):
        with self.assertRaises(AcquisitionError):
            download(self.url, self.root.parent / "outside", accession="SYNTHETIC",
                     data_root=self.root, limits=self.limits)
        link = self.root / "link"
        link.symlink_to(self.root.parent / "outside")
        with self.assertRaises(AcquisitionError):
            download(self.url, link, accession="SYNTHETIC",
                     data_root=self.root, limits=self.limits)

    def test_http_error_is_precise_and_bounded(self):
        error = urllib.error.HTTPError(self.url, 403, "Forbidden", {}, None)
        with mock.patch("urllib.request.urlopen", side_effect=error) as opener:
            with self.assertRaisesRegex(AcquisitionError, "HTTP 403 Forbidden"):
                download(self.url, self.dest, accession="SYNTHETIC",
                         data_root=self.root, limits=self.limits)
        self.assertEqual(opener.call_count, 1)

    def test_transient_error_retries_then_succeeds(self):
        limits = Limits(retries=1, min_interval_seconds=0, disk_reserve_bytes=0)
        body = gzip.compress(b"synthetic")
        error = urllib.error.HTTPError(self.url, 503, "Unavailable", {}, None)
        with mock.patch("urllib.request.urlopen", side_effect=[error, Response(body)]) as opener:
            with mock.patch("time.sleep"):
                record = download(self.url, self.dest, accession="SYNTHETIC",
                                  data_root=self.root, limits=limits)
        self.assertEqual(record["status"], "downloaded")
        self.assertEqual(opener.call_count, 2)


if __name__ == "__main__":
    unittest.main()
