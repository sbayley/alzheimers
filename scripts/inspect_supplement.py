#!/usr/bin/env python3
"""Inspect the real, small GEO XLS supplement without changing its contents."""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'src'))
from alzresearch.acquisition import download
from alzresearch.workflow import load_config, save_json


def main():
    import xlrd  # Optional pinned reader; never executes spreadsheet macros.
    config, limits = load_config(root / 'configs/project.json')
    manifest = json.loads((root / config['manifest']).read_text())
    dataset = next(d for d in manifest['datasets'] if d['accession'] == 'GSE5281')
    source = next(f for f in dataset['files'] if f['kind'] == 'sample_metadata_supplement')
    path = root / source['path']
    if not path.exists():
        raise SystemExit('Acquire the verified supplement first; this command is offline.')
    provenance = download(source['url'], path, accession='GSE5281',
                          data_root=root / config['data_root'], limits=limits)
    book = xlrd.open_workbook(path, on_demand=True)
    sheets = []
    processed = root / 'data/processed'
    processed.mkdir(parents=True, exist_ok=True)
    try:
        for index in range(book.nsheets):
            sheet = book.sheet_by_index(index)
            # The verified workbook is tiny; also cap cells before materializing.
            if sheet.nrows * sheet.ncols > 100_000:
                raise ValueError('Supplement exceeds the 100,000-cell inspection bound')
            rows = [sheet.row_values(i) for i in range(sheet.nrows)]
            headers = [str(value).strip() for value in rows[0]]
            records = [dict(zip(headers, row)) for row in rows[1:] if any(str(v).strip() for v in row)]
            accession_key = 'GEO Accession:'
            ids = [str(row.get(accession_key, '')).strip() for row in records]
            normalized = [{key: str(value).replace('\u00a0', ' ').strip() for key, value in row.items()}
                          for row in records]
            output = processed / ('GSE5281_supplement_sheet_' + str(index) + '.csv')
            with output.open('w', newline='') as handle:
                writer = csv.writer(handle)
                writer.writerows(rows)
            summary = {'sheet': sheet.name, 'rows_including_header': sheet.nrows,
                'columns': sheet.ncols, 'headers': headers, 'data_rows': len(records),
                'unique_sample_accessions': len(set(ids)),
                'duplicate_sample_accessions': [key for key, count in Counter(ids).items() if count > 1],
                'invalid_sample_accessions': [value for value in ids if not re.fullmatch(r'GSM\d+', value)],
                'diagnosis_as_recorded_counts': dict(Counter(row.get('Disease State:', '') for row in normalized)),
                'region_as_recorded_counts': dict(Counter(row.get('Organ Region:', '') for row in normalized)),
                'donor_identifiers': 'unknown: no explicitly identified donor/person field; MAGE biosample identifiers are not assumed to identify donors',
                'csv_path': str(output.relative_to(root))}
            inventory_path = processed / 'sample_inventory.json'
            if inventory_path.exists():
                inventory = json.loads(inventory_path.read_text())
                matrix = next(d for d in inventory['datasets'] if d['dataset'] == 'GSE5281')
                matrix_ids = {sample['sample_accession'] for sample in matrix['samples']}
                summary['matrix_sample_set_matches'] = matrix_ids == set(ids)
                summary['only_in_supplement'] = sorted(set(ids) - matrix_ids)
                summary['only_in_matrix'] = sorted(matrix_ids - set(ids))
            sheets.append(summary)
    finally:
        book.release_resources()
    summary = {'source_path': str(path.relative_to(root)), 'source_url': source['url'],
        'source_bytes': path.stat().st_size, 'sha256': provenance['sha256'],
        'reader': 'xlrd ' + xlrd.__version__, 'sheets': sheets,
        'interpretation': 'Original cells exported without inference. Sample-set matching does not establish donor independence.'}
    save_json(root / 'reports/GSE5281_supplement_audit.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
