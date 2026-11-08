#!/usr/bin/env python3
"""Acquire full official GEO platform records and verify annotation tables.

Uses the official accession viewer's Full SOFT selection, not guessed filenames.
These current GEO tables are candidate reconstruction inputs, not confirmed copies
of the paper's unspecified annotation database/version.
"""
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'src'))
from alzresearch.acquisition import download
from alzresearch.platforms import inspect_platform
from alzresearch.workflow import load_config, save_json, utc_now

config, limits = load_config(root / 'configs/pashaei_2025.json')
manifest = json.loads((root / config['manifest']).read_text())
results = {'started_utc': utc_now(), 'interpretation': 'Current official GEO table reconstruction candidates. Historical author annotation is unconfirmed.', 'platforms': []}
for record in manifest['platform_records']:
    accession = record['accession']
    url = record['url'].replace('view=brief', 'view=full')
    path = root / config['data_root'] / 'raw/platforms' / (accession + '.full.soft.txt')
    row = {'accession': accession, 'url': url, 'discovered_from': record['url'],
           'selection': 'Official accession viewer: Scope Self, Format SOFT, Amount Full'}
    try:
        row['provenance'] = download(url, path, accession=accession,
                                    data_root=root / config['data_root'], limits=limits)
        row['inspection'] = inspect_platform(path, accession, max_bytes=limits.max_file_bytes)
        table = row['inspection']['annotation_table']
        if not table['present'] or table['completeness'] != 'row_count_matches_record_declaration':
            raise ValueError('Full platform annotation table absent or declared count does not match')
        row['status'] = 'acquired_and_inspected'
    except Exception as exc:
        row['status'] = 'blocked'
        row['error'] = type(exc).__name__ + ': ' + str(exc)
    results['platforms'].append(row)
    save_json(root / 'registry/pashaei_2025_annotation_acquisition.json', results)
    print(json.dumps({'accession': accession, 'status': row['status'],
        'bytes': row.get('provenance', {}).get('byte_count'),
        'table': row.get('inspection', {}).get('annotation_table'), 'error': row.get('error')}), flush=True)
results['completed_utc'] = utc_now()
save_json(root / 'registry/pashaei_2025_annotation_acquisition.json', results)
if any(row['status'] == 'blocked' for row in results['platforms']):
    raise SystemExit(1)
