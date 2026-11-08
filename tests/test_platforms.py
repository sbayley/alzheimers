"""Synthetic platform SOFT fixtures; no scientific observations or network."""

import hashlib
from pathlib import Path
import tempfile
import unittest

from alzresearch.platforms import PlatformInspectionError, inspect_platform


BRIEF = ("^PLATFORM = GPL1\n"
         "!Platform_title = Synthetic test array\n"
         "!Platform_manufacturer = Synthetic fixture only\n"
         "!Platform_technology = in situ oligonucleotide\n"
         "!Platform_organism = Homo sapiens\n"
         "!Platform_last_update_date = Nov 01 2026\n"
         "!Platform_sample_id = GSM1\n"
         "!Platform_sample_id = GSM1\n"
         "!Platform_series_id = GSE1\n")


class PlatformTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "synthetic_platform.soft.txt"

    def inspect(self, text=BRIEF, **kwargs):
        self.path.write_text(text)
        return inspect_platform(self.path, "GPL1", **kwargs)

    def test_brief_record_preserves_evidence_but_not_reference_lists(self):
        result = self.inspect()
        self.assertEqual(result["title"], ["Synthetic test array"])
        self.assertEqual(result["record_fields"]["title"][0]["line"], 2)
        self.assertEqual(result["sample_reference_count"], 2)
        self.assertEqual(result["series_reference_count"], 1)
        self.assertNotIn("sample_id", result["record_fields"])
        self.assertNotIn("series_id", result["record_fields"])
        self.assertFalse(result["annotation_table"]["present"])
        self.assertEqual(result["annotation_table"]["completeness"], "not_present_in_record")
        self.assertEqual(result["source_bytes"], self.path.stat().st_size)
        self.assertEqual(result["source_sha256"], hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_wrong_record_html_empty_and_malformed_metadata_rejected(self):
        for text in ["", "<html>error</html>", "^PLATFORM = GPL2\n",
                     BRIEF + "!Platform_organism\n", BRIEF + "^SAMPLE = GSM1\n"]:
            with self.subTest(text=text):
                with self.assertRaises(PlatformInspectionError):
                    self.inspect(text)

    def test_table_present_counted_without_retaining_rows(self):
        text = (BRIEF + "!Platform_data_row_count = 2\n#ID = probe identifier\n"
                "!platform_table_begin\nID\tGene Symbol\nprobe1\tA\nprobe2\tB\n"
                "!platform_table_end\n")
        result = self.inspect(text)
        table = result["annotation_table"]
        self.assertEqual(table["columns"], ["ID", "Gene Symbol"])
        self.assertEqual(table["row_count"], 2)
        self.assertEqual(table["completeness"], "row_count_matches_record_declaration")
        self.assertEqual(result["column_definitions"][0]["original"], "#ID = probe identifier")
        self.assertNotIn("rows", table)

    def test_partial_table_is_not_declared_complete(self):
        result = self.inspect(BRIEF + "!Platform_data_row_count = 100\n"
                              "!platform_table_begin\nID\tGene\np1\tA\n!platform_table_end\n")
        self.assertEqual(result["annotation_table"]["completeness"],
                         "row_count_differs_from_record_declaration")

    def test_malformed_or_unclosed_table_rejected(self):
        table = BRIEF + "!platform_table_begin\nID\tGene\np1\tA\n"
        for text in [table, table.replace("p1\tA", "p1\tA\textra") + "!platform_table_end\n",
                     BRIEF + "!platform_table_end\n",
                     table.replace("ID\tGene", "Gene\tID") + "!platform_table_end\n"]:
            with self.subTest(text=text):
                with self.assertRaises(PlatformInspectionError):
                    self.inspect(text)

    def test_size_limit_rejected_before_read(self):
        with self.assertRaises(PlatformInspectionError):
            self.inspect(max_bytes=20)


if __name__ == "__main__":
    unittest.main()
