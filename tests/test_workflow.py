"""Synthetic source fixtures; not scientific data."""
import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory
import contextlib
import io

from alzresearch.workflow import matrix_links, parse_soft_record, acquire, inspect, acquire_platforms, run_path, report_dir
from alzresearch.acquisition import Limits, AcquisitionError


class DiscoveryTests(unittest.TestCase):
    def test_paper_outputs_are_isolated_from_initial_audit(self):
        with TemporaryDirectory() as folder, patch('alzresearch.workflow.ROOT', Path(folder)):
            self.assertEqual(run_path({}, 'acquisition_run'), Path(folder) / 'registry/acquisition_run.json')
            self.assertEqual(run_path({'output_namespace': 'pashaei_2025'}, 'acquisition_run'),
                             Path(folder) / 'registry/pashaei_2025_acquisition_run.json')
            self.assertEqual(report_dir({'output_namespace': 'pashaei_2025'}), Path(folder) / 'reports/pashaei_2025')
            with self.assertRaises(ValueError):
                report_dir({'output_namespace': '../other'})

    def test_reject_wrong_accession_or_html(self):
        for text in ['<html>error</html>', '^SERIES = GSE2\n!Series_title = wrong']:
            with self.assertRaises(ValueError):
                parse_soft_record(text, 'GSE1')

    def test_keep_repeated_record_fields(self):
        fields = parse_soft_record('^SERIES = GSE1\n!Series_sample_id = GSM1\n!Series_sample_id = GSM2\n', 'GSE1')
        self.assertEqual(fields['sample_id'], ['GSM1', 'GSM2'])

    def test_discover_only_official_matrix_links(self):
        text = ('<a href="GSE1_series_matrix.txt.gz">ok</a>'
                '<a href="https://example.org/GSE1_series_matrix.txt.gz">bad</a>'
                '<a href="GSE2_series_matrix.txt.gz">other</a>')
        base = 'https://ftp.ncbi.nlm.nih.gov/geo/series/GSEnnn/GSE1/matrix/'
        self.assertEqual(matrix_links(text, base, 'GSE1'), [base + 'GSE1_series_matrix.txt.gz'])

    def test_acquisition_accounts_for_failed_discovery(self):
        manifest = {'datasets': [{'accession': 'GSE1', 'files': [], 'errors': ['HTTP 403']}]}
        with patch('alzresearch.workflow.save_json'), contextlib.redirect_stdout(io.StringIO()):
            result = acquire({'data_root': 'data'}, Limits(), manifest)
        self.assertEqual(result['results'][0]['status'], 'blocked')
        self.assertIn('HTTP 403', result['results'][0]['error'])

    def test_inspection_rejects_unverified_file_and_continues(self):
        with TemporaryDirectory() as folder:
            paths = [Path(folder) / ('GSE%d.txt.gz' % i) for i in (1, 2)]
            for path in paths:
                path.write_bytes(b'synthetic test fixture')
            manifest = {'datasets': [{'accession': 'GSE%d' % i, 'files': [
                {'kind': 'processed_series_matrix', 'url': 'https://example.org/fixture', 'path': str(path)}]}
                for i, path in zip((1, 2), paths)]}
            with patch('alzresearch.workflow.ROOT', Path(folder)), \
                 patch('alzresearch.workflow.download', side_effect=[AcquisitionError('SHA mismatch'), {}]), \
                 patch('alzresearch.inspection.inspect_matrix', return_value={'samples': []}) as parse, \
                 patch('alzresearch.inspection.write_inventory', return_value={}), \
                 patch('alzresearch.workflow.save_json') as save, \
                 contextlib.redirect_stdout(io.StringIO()):
                results = inspect({'data_root': folder, 'limits': {}}, Limits(), manifest)
            self.assertEqual(len(results), 1)
            parse.assert_called_once()
            rows = save.call_args.args[1]['results']
            self.assertEqual([row['inspection'] for row in rows], ['blocked', 'completed'])

    def test_platform_requests_use_normal_limit_and_preserve_previous_failure(self):
        manifest = {'datasets': [{'platforms': ['GPL570', 'GPL10558']}],
                    'platform_records': [{'accession': 'GPL570', 'status': 'blocked',
                                          'error': 'Old 2 MB cap'}]}
        observed_limits = []
        def fixture_download(url, path, *, accession, data_root, limits):
            observed_limits.append(limits.max_file_bytes)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('^PLATFORM = ' + accession + '\n!Platform_title = Synthetic test\n')
            return {'status': 'downloaded', 'byte_count': path.stat().st_size}
        with TemporaryDirectory() as folder, \
             patch('alzresearch.workflow.ROOT', Path(folder)), \
             patch('alzresearch.workflow.download', side_effect=fixture_download), \
             patch('alzresearch.workflow.save_json'), \
             contextlib.redirect_stdout(io.StringIO()):
            run = acquire_platforms({'data_root': 'data', 'manifest': 'registry/test.json',
                                     'discovery_record_max_bytes': 2}, Limits(), manifest)
        self.assertEqual(observed_limits, [250_000_000, 250_000_000])
        self.assertTrue(all(row['status'] == 'metadata_open_verified' for row in run['results']))
        gpl570 = next(row for row in run['results'] if row['accession'] == 'GPL570')
        self.assertEqual(gpl570['previous_attempts'][0]['error'], 'Old 2 MB cap')

    def test_wrong_platform_response_is_recorded_and_other_platform_continues(self):
        manifest = {'datasets': [{'platforms': ['GPL570', 'GPL10558']}]}
        def fixture_download(url, path, *, accession, data_root, limits):
            path.parent.mkdir(parents=True, exist_ok=True)
            returned_id = 'GPL999' if accession == 'GPL10558' else accession
            path.write_text('^PLATFORM = ' + returned_id + '\n')
            return {'status': 'downloaded', 'byte_count': path.stat().st_size}
        with TemporaryDirectory() as folder, \
             patch('alzresearch.workflow.ROOT', Path(folder)), \
             patch('alzresearch.workflow.download', side_effect=fixture_download), \
             patch('alzresearch.workflow.save_json'), \
             contextlib.redirect_stdout(io.StringIO()):
            run = acquire_platforms({'data_root': 'data', 'manifest': 'registry/test.json'}, Limits(), manifest)
        self.assertEqual([row['status'] for row in run['results']], ['blocked', 'metadata_open_verified'])
        self.assertIn('Not the requested GEO platform record', run['results'][0]['error'])
