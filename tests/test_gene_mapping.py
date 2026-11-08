"""Synthetic mapping fixtures, deliberately separate from scientific observations."""
import csv
import gzip
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from alzresearch.gene_mapping import (GeneMappingError, candidate_symbols,
    inspect_platform_mapping, inspect_matrix_feature_ids, matched_mapping_rows, write_mapping_csv)


class GeneMappingTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def fixture(self, content, accession="GPL570", gzip_content=False):
        path = self.root / (accession + (".txt.gz" if gzip_content else ".soft.txt"))
        data = content.encode()
        path.write_bytes(gzip.compress(data) if gzip_content else data)
        raw = path.read_bytes()
        path.with_name(path.name + ".provenance.json").write_text(json.dumps({
            "accession": accession, "url": "https://example.org/synthetic",
            "local_path": path.name, "byte_count": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}))
        return path

    def platform(self, body, platform="GPL570", column="Gene Symbol"):
        text = "^PLATFORM = " + platform + "\n!platform_table_begin\nID\t" + column + "\n" + body + "!platform_table_end\n"
        return self.fixture(text, platform)

    def test_unique_multiple_and_blank_symbols(self):
        path = self.platform("p1\tA\np2\tA /// B\np3\t---\np4\tA /// A\n")
        result = inspect_platform_mapping(path, "GPL570", project_root=self.root)
        self.assertEqual(result["mappings"]["p1"]["unique_symbol"], "A")
        self.assertEqual(result["mappings"]["p2"]["status"], "multiple_symbols")
        self.assertEqual(result["mappings"]["p2"]["unique_symbol"], "")
        self.assertEqual(result["mappings"]["p3"]["status"], "unmapped")
        self.assertEqual(result["mappings"]["p4"]["candidate_symbols"], ["A"])

    def test_transcript_assignment_parses_second_component_and_deduplicates(self):
        symbols, status, rule = candidate_symbols("GPL6244", "p1",
            "NM_1 // OLD1 // description // 1q // 10 /// NM_2 // OLD1 // second // --- // 10")
        self.assertEqual((symbols, status), (["OLD1"], "unique"))
        symbols, status, _ = candidate_symbols("GPL6244", "p2", "NM_1 // A // desc /// NM_2 // B // desc")
        self.assertEqual((symbols, status), (["A", "B"], "multiple_symbols"))

    def test_malformed_assignment_never_yields_unique_clean_mapping(self):
        symbols, status, _ = candidate_symbols("GPL6244", "p", "NM_1 // A // desc /// broken")
        self.assertEqual(symbols, ["A"])
        self.assertEqual(status, "malformed_assignment")
        self.assertEqual(candidate_symbols("GPL10558", "p", "A;B")[1], "malformed_assignment")

    def test_explicit_source_truncation_is_distinguished_from_parser_failure(self):
        symbols, status, _ = candidate_symbols("GPL6244", "p", "NM_1 // A // desc /// NM_2 [WARNING: THIS FIELD TRUNCATED]")
        self.assertEqual(symbols, ["A"])
        self.assertEqual(status, "source_truncated_assignment")

    def test_symbol_platform_preserves_obsolete_id(self):
        path = self.platform("A2BP1\tRBFOX1\n", platform="GPL10904", column="ORF")
        result = inspect_platform_mapping(path, "GPL10904", project_root=self.root)
        self.assertEqual(result["mappings"]["A2BP1"]["unique_symbol"], "A2BP1")

    def test_duplicate_id_conflicts_are_not_first_mapping(self):
        path = self.platform("p1\tA\np1\tB\np2\tC\np2\tC\n")
        result = inspect_platform_mapping(path, "GPL570", project_root=self.root)
        self.assertEqual(result["duplicate_id_conflicts"], 1)
        self.assertEqual(result["mappings"]["p1"]["status"], "conflicting_duplicate_id")
        self.assertEqual(result["mappings"]["p1"]["unique_symbol"], "")
        self.assertEqual(result["mappings"]["p1"]["candidate_symbols"], ["A", "B"])
        self.assertEqual(result["mappings"]["p2"]["unique_symbol"], "C")

    def test_wrong_accession_bad_table_and_missing_end_rejected(self):
        for content in ["<html>synthetic error</html>",
                        "^PLATFORM = GPL2\n!platform_table_begin\nID\tGene Symbol\np\tA\n!platform_table_end\n",
                        "^PLATFORM = GPL570\n!platform_table_begin\nID\tGene Symbol\np\tA\textra\n!platform_table_end\n",
                        "^PLATFORM = GPL570\n!platform_table_begin\nID\tGene Symbol\np\tA\n"]:
            with self.assertRaises(GeneMappingError):
                inspect_platform_mapping(self.fixture(content), "GPL570", project_root=self.root)

    def test_provenance_hash_and_url_are_verified_offline(self):
        path = self.platform("p\tA\n")
        with self.assertRaises(GeneMappingError):
            inspect_platform_mapping(path, "GPL570", expected_url="https://example.org/wrong")
        path.write_bytes(path.read_bytes() + b"tamper")
        with self.assertRaises(GeneMappingError):
            inspect_platform_mapping(path, "GPL570")

    def test_limit_and_unmatched_export_are_explicit(self):
        path = self.platform("p\tA\n")
        with self.assertRaises(GeneMappingError):
            inspect_platform_mapping(path, "GPL570", max_bytes=1)
        result = inspect_platform_mapping(path, "GPL570")
        rows = list(matched_mapping_rows(result, ["p", "absent", "p"]))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]["status"], "not_in_annotation")
        target = self.root / "mapping.csv"
        write_mapping_csv(target, rows)
        with target.open() as stream:
            exported = list(csv.DictReader(stream))
        self.assertEqual(exported[0]["unique_symbol"], "A")
        self.assertEqual(json.loads(exported[1]["candidate_symbols"]), [])

    def test_matrix_feature_inspection_keeps_ids_without_expression(self):
        text = '!Series_geo_accession\t"GSE1"\n!series_matrix_table_begin\n"ID_REF"\t"GSM1"\n"p1"\t1.5\n"p2"\t2.5\n!series_matrix_table_end\n'
        path = self.fixture(text, "GSE1", gzip_content=True)
        result = inspect_matrix_feature_ids(path, "GSE1", project_root=self.root)
        self.assertEqual(result["feature_ids"], ["p1", "p2"])
        self.assertEqual(result["sample_count"], 1)
        self.assertNotIn("expression", result)
