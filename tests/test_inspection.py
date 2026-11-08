"""Synthetic fixtures for metadata edge cases; these are never research data."""

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from alzresearch.inspection import (InspectionError, audit_samples,
                                    check_split_leakage, inspect_matrix, write_inventory)


def synthetic_matrix(diagnoses=("AD", "control"), donors=("D1", "D2"), ages=("77 years", "80 years")):
    rows = [
        '!Series_geo_accession\t"GSE123"',
        '!Series_type\t"Expression profiling by array"',
        '!Sample_geo_accession\t"GSM1"\t"GSM2"',
        '!Sample_title\t"synthetic AD label"\t"synthetic control label"',
        '!Sample_platform_id\t"GPL1"\t"GPL1"',
        '!Sample_characteristics_ch1\t"diagnosis: %s"\t"diagnosis: %s"' % diagnoses,
        '!Sample_characteristics_ch1\t"donor id: %s"\t"donor id: %s"' % donors,
        '!Sample_characteristics_ch1\t"age: %s"\t"age: %s"' % ages,
        '!Sample_characteristics_ch1\t"brain region: hippocampus"\t"brain region: hippocampus"',
        '!series_matrix_table_begin',
        '"ID_REF"\t"GSM1"\t"GSM2"',
        '"probe1"\t1.5\t3.0',
        '"probe2"\tNA\t5.0',
        '!series_matrix_table_end',
    ]
    return "\n".join(rows) + "\n"


class InspectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "synthetic_series_matrix.txt.gz"

    def inspect(self, text=None, **kwargs):
        with gzip.open(self.path, "wt") as stream:
            stream.write(synthetic_matrix() if text is None else text)
        return inspect_matrix(self.path, **kwargs)

    def test_real_shape_and_original_evidence_preserved(self):
        result = self.inspect(accession="GSE123")
        self.assertEqual(result["summary"]["sample_count"], 2)
        self.assertEqual(result["summary"]["total_donor_count"], 2)
        self.assertEqual(result["matrix"]["feature_count"], 2)
        self.assertEqual(result["matrix"]["missing_value_count"], 1)
        self.assertEqual(result["matrix"]["minimum"], 1.5)
        sample = result["samples"][0]
        self.assertEqual(sample["diagnosis"], "Alzheimer's disease")
        self.assertEqual(sample["age_value"], 77)
        self.assertEqual(sample["age_units"], "years")
        self.assertEqual(sample["original_characteristics"][0]["original"], "diagnosis: AD")
        self.assertEqual(len(sample["source_sha256"]), 64)
        self.assertEqual(sample["inclusion_decision"], "not_assessed")

    def test_unknown_donor_is_not_sample_id(self):
        result = self.inspect(synthetic_matrix(donors=("unknown", "unknown")))
        self.assertIsNone(result["summary"]["total_donor_count"])
        self.assertEqual(result["summary"]["observed_known_donor_ids"], 0)
        self.assertEqual(result["samples"][0]["donor_id"], "unknown")

    def test_unsupported_label_is_not_inferred_from_title(self):
        result = self.inspect(synthetic_matrix(diagnoses=("possible AD", "MCI")))
        self.assertEqual(result["summary"]["diagnosis_counts"], {"unknown": 2})
        self.assertIn("ambiguous_diagnosis", {issue["code"] for issue in result["issues"]})

    def test_asymad_is_preserved_as_separate_source_defined_group(self):
        text = synthetic_matrix(diagnoses=('AsymAD', 'AD')).replace('GSE123', 'GSE118553')
        text = '!Series_summary\t"Asymptomatic AD (AsymAD) subjects have intact cognition and AD neuropathology."\n' + text
        result = self.inspect(text)
        self.assertEqual(result['samples'][0]['diagnosis'], "asymptomatic Alzheimer's disease")
        self.assertEqual(result['samples'][1]['diagnosis'], "Alzheimer's disease")
        self.assertIn('Series_summary', {v['key'] for v in result['samples'][0]['diagnosis_evidence']})
        without_definition = self.inspect(text.split('\n', 1)[1])
        self.assertEqual(without_definition['samples'][0]['diagnosis'], 'unknown')

    def test_gse36980_explicit_source_labels_do_not_generalize_to_other_series(self):
        text = synthetic_matrix().replace('GSE123', 'GSE36980')
        text = text.replace('!Sample_characteristics_ch1\t"diagnosis: AD"\t"diagnosis: control"\n', '')
        text = '!Sample_source_name_ch1\t"Frontal cortex of AD brain"\t"Temporal cortex of non-AD brain"\n' + text
        result = self.inspect(text)
        self.assertEqual(result['summary']['diagnosis_counts'], {"Alzheimer's disease": 1, 'control': 1})
        other = self.inspect(text.replace('GSE36980', 'GSE999'))
        self.assertEqual(other['summary']['diagnosis_counts'], {'unknown': 2})

    def test_conflicting_explicit_diagnoses_are_unknown(self):
        text = synthetic_matrix().replace("!series_matrix_table_begin", '!Sample_characteristics_ch1\t"disease: control"\t"disease: control"\n!series_matrix_table_begin')
        result = self.inspect(text)
        self.assertEqual(result["samples"][0]["diagnosis"], "unknown")

    def test_repeated_donor_and_inconsistent_metadata(self):
        result = self.inspect(synthetic_matrix(donors=("D1", "D1")))
        codes = {issue["code"] for issue in result["issues"]}
        self.assertIn("repeated_measures", codes)
        self.assertIn("inconsistent_donor_metadata", codes)
        self.assertEqual(result["summary"]["total_donor_count"], 1)

    def test_repeated_donor_region_is_flagged_without_automatic_exclusion(self):
        result = self.inspect(synthetic_matrix(donors=('D1', 'D1')))
        codes = {issue['code'] for issue in result['issues']}
        self.assertIn('repeated_donor_region', codes)
        self.assertTrue(all(s['inclusion_decision'] == 'not_assessed' for s in result['samples']))
        text = synthetic_matrix(donors=('D1', 'D1')).replace(
            '"brain region: hippocampus"\t"brain region: hippocampus"',
            '"brain region: hippocampus"\t"brain region: frontal cortex"')
        different_regions = self.inspect(text)
        self.assertNotIn('repeated_donor_region', {i['code'] for i in different_regions['issues']})

    def test_duplicate_samples_are_flagged(self):
        result = self.inspect(synthetic_matrix().replace('"GSM2"', '"GSM1"'))
        self.assertIn("duplicate_sample", {issue["code"] for issue in result["issues"]})

    def test_conflicting_donor_fields_are_unknown(self):
        text = synthetic_matrix().replace("!series_matrix_table_begin", '!Sample_characteristics_ch1\t"subject id: D9"\t"subject id: D2"\n!series_matrix_table_begin')
        result = self.inspect(text)
        self.assertEqual(result["samples"][0]["donor_id"], "unknown")
        self.assertIn("inconsistent_donor_identifiers", {issue["code"] for issue in result["issues"]})

    def test_age_units_are_not_assumed(self):
        result = self.inspect(synthetic_matrix(ages=("77", "80")))
        self.assertEqual(result["samples"][0]["age_value"], 77)
        self.assertEqual(result["samples"][0]["age_units"], "unknown")

    def test_seed_characteristic_key_aliases(self):
        text = synthetic_matrix().replace('"brain region: hippocampus"', '"Organ Region: hippocampus "')
        text = text.replace("!series_matrix_table_begin", '!Sample_characteristics_ch1\t"Organ/Tissue Type: brain "\t"Organ/Tissue Type: brain "\n!series_matrix_table_begin')
        result = self.inspect(text)
        self.assertEqual(result["samples"][0]["brain_region"], "hippocampus")
        self.assertEqual(result["samples"][0]["tissue"], "brain")

    def test_gse132903_nd_requires_source_definition_and_preserves_censored_age(self):
        text = synthetic_matrix(diagnoses=("ND", "AD"), ages=("90+", "82")).replace("GSE123", "GSE132903")
        text = text.replace("age:", "expired_age (years):")
        definition = '!Series_overall_design\t"Middle temporal gyrus compared Alzheimer’s Disease (AD = 97) and non-demented controls (ND = 98)."\n'
        result = self.inspect(definition + text)
        control = result["samples"][0]
        self.assertEqual(control["diagnosis"], "control")
        self.assertEqual(control["diagnosis_mapping_rule"], "GSE132903_official_design_ND_definition_v1")
        self.assertIsNone(control["age_value"])
        self.assertEqual(control["age_lower_bound"], 90)
        self.assertTrue(control["age_is_censored"])
        self.assertEqual(control["age_units"], "years")
        without_definition = self.inspect(text)
        self.assertEqual(without_definition["samples"][0]["diagnosis"], "unknown")

    def test_gse48350_title_labels_require_official_definition_not_donor_inference(self):
        text = synthetic_matrix().replace("GSE123", "GSE48350")
        text = text.replace('!Sample_characteristics_ch1\t"diagnosis: AD"\t"diagnosis: control"\n', "")
        text = text.replace('"synthetic AD label"', '"hippocampus_female_76_AD_48"').replace('"synthetic control label"', '"Hippocampus_male_70yrs_indiv10"')
        text = text.replace('donor id: D1', 'unrelated: D1').replace('donor id: D2', 'individual: 10, C')
        definition = '!Series_overall_design\t"Cases labeled indiv refers to normal controls (young and aged), and AD cases are labeled AD."\n'
        result = self.inspect(definition + text)
        self.assertEqual(result["samples"][0]["diagnosis"], "Alzheimer's disease")
        self.assertEqual(result["samples"][1]["diagnosis"], "control")
        self.assertEqual(result["samples"][0]["donor_id"], "unknown")
        self.assertEqual(result["samples"][1]["donor_id"], "10, C")
        self.assertIsNone(result["summary"]["total_donor_count"])
        self.assertEqual(self.inspect(text)["samples"][0]["diagnosis"], "unknown")

    def test_greater_than_age_remains_censored_and_units_retained(self):
        result = self.inspect(synthetic_matrix(ages=(">90 years", "80 years")))
        sample = result["samples"][0]
        self.assertIsNone(sample["age_value"])
        self.assertEqual(sample["age_lower_bound"], 90)
        self.assertEqual(sample["age_censoring_operator"], ">")
        self.assertEqual(sample["age_units"], "years")
        self.assertEqual(result["summary"]["censored_age_sample_count"], 1)

    def test_explicit_adult_age_unit_conflict_is_not_silently_corrected(self):
        text = synthetic_matrix(ages=("85 days", "80 years")).replace("!series_matrix_table_begin", '!Sample_characteristics_ch1\t"Developmental Stage: Adult"\t"Developmental Stage: Adult"\n!series_matrix_table_begin')
        result = self.inspect(text)
        self.assertEqual(result["samples"][0]["age_value"], 85)
        self.assertEqual(result["samples"][0]["age_units"], "days")
        self.assertIn("age_unit_conflict", {issue["code"] for issue in result["issues"]})

    def test_region_format_variants_remain_separate(self):
        text = synthetic_matrix().replace('"brain region: hippocampus"\t"brain region: hippocampus"', '"brain region: postcentral gyrus"\t"brain region: post-central gyrus"')
        result = self.inspect(text)
        self.assertEqual(len(result["summary"]["brain_region_counts"]), 2)
        self.assertIn("region_label_format_variants", {issue["code"] for issue in result["issues"]})

    def test_donor_split_leakage_detected(self):
        result = self.inspect(synthetic_matrix(donors=("D1", "D1")))
        codes = {issue["code"] for issue in check_split_leakage(result["samples"], {"GSM1": "train", "GSM2": "test"})}
        self.assertIn("donor_split_leakage", codes)

    def test_unknown_donors_cannot_establish_leakage_free_splits(self):
        result = self.inspect(synthetic_matrix(donors=("unknown", "unknown")))
        self.assertIn("split_independence_unverified", {issue["code"] for issue in check_split_leakage(result["samples"], {})})

    def test_donor_ids_are_dataset_scoped(self):
        result = self.inspect()
        samples = result["samples"]
        other = dict(samples[0], dataset="GSE999", donor_namespace="GSE999", sample_accession="GSM999")
        self.assertNotIn("repeated_measures", {issue["code"] for issue in audit_samples(samples + [other])})

    def test_malformed_metadata_columns_rejected(self):
        text = synthetic_matrix().replace('"age: 77 years"\t"age: 80 years"', '"age: 77 years"')
        with self.assertRaisesRegex(InspectionError, "inconsistent column count"):
            self.inspect(text)

    def test_malformed_expression_columns_rejected(self):
        with self.assertRaisesRegex(InspectionError, "expected 2"):
            self.inspect(synthetic_matrix().replace('"probe1"\t1.5\t3.0', '"probe1"\t1.5'))

    def test_mismatched_expression_sample_order_rejected(self):
        with self.assertRaisesRegex(InspectionError, "column identities"):
            self.inspect(synthetic_matrix().replace('"ID_REF"\t"GSM1"\t"GSM2"', '"ID_REF"\t"GSM2"\t"GSM1"'))

    def test_missing_expression_end_rejected(self):
        with self.assertRaisesRegex(InspectionError, "end marker"):
            self.inspect(synthetic_matrix().replace("!series_matrix_table_end", ""))

    def test_metadata_only_is_inspected_honestly(self):
        result = self.inspect(synthetic_matrix().split("!series_matrix_table_begin")[0])
        self.assertEqual(result["summary"]["sample_count"], 2)
        self.assertEqual(result["matrix"]["feature_count"], 0)
        self.assertIn("expression_table_absent", {issue["code"] for issue in result["issues"]})

    def test_expansion_limit_enforced(self):
        with self.assertRaisesRegex(InspectionError, "byte limit"):
            self.inspect(max_expanded_bytes=100)

    def test_invalid_gzip_is_rejected(self):
        self.path.write_bytes(b"this is not gzip")
        with self.assertRaises(InspectionError):
            inspect_matrix(self.path)

    def test_requested_accession_mismatch_rejected(self):
        with self.assertRaisesRegex(InspectionError, "does not match"):
            self.inspect(accession="GSE999")

    def test_report_and_inventory_include_evidence(self):
        result = self.inspect()
        paths = write_inventory([result], Path(self.tmp.name) / "reports")
        document = json.loads(Path(paths["json"]).read_text())
        self.assertEqual(document["datasets"][0]["samples"][0]["diagnosis_evidence"][0]["value"], "AD")
        self.assertIn("Sample counts are not donor counts", Path(paths["report"]).read_text())
        self.assertIn("source_sha256", Path(paths["csv"]).read_text())

    def test_report_destination_can_be_separate_from_sample_data(self):
        result = self.inspect()
        report = Path(self.tmp.name) / "reports" / "metadata_quality.md"
        paths = write_inventory([result], Path(self.tmp.name) / "data" / "processed", metadata_report_path=report)
        self.assertEqual(paths["report"], str(report))
        self.assertTrue(report.exists())
        self.assertFalse((Path(paths["csv"]).parent / "metadata_quality.md").exists())


if __name__ == "__main__":
    unittest.main()
