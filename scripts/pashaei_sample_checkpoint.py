#!/usr/bin/env python3
"""Compare explicit AD/control array selection to published sample counts.

This is a descriptive reproduction checkpoint, not a disease-effect analysis.
"""
from collections import Counter
import csv
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'src'))
from alzresearch.workflow import save_json, utc_now

PUBLISHED = {'GSE48350': (80, 173), 'GSE36980': (33, 47), 'GSE132903': (97, 98),
             'GSE118553': (167, 100), 'GSE5281': (87, 74), 'GSE109887': (46, 32)}
inventory = json.loads((root / 'data/processed/pashaei_2025/sample_inventory.json').read_text())
report = {'generated_utc': utc_now(), 'source_paper': 'https://doi.org/10.3390/ijms26051816',
    'selection_rule': 'Include exact evidence-backed AD or control labels; retain other groups as explicit exclusions. No quality-control exclusions yet.',
    'interpretation': 'Matching array counts does not establish matching exact sample selection, donor independence, or reproduced gene-level results.',
    'datasets': []}
rows = []
for dataset in inventory['datasets']:
    accession = dataset['dataset']
    expected_ad, expected_control = PUBLISHED[accession]
    selected = [s for s in dataset['samples'] if s['diagnosis'] in ("Alzheimer's disease", 'control')]
    excluded = [s for s in dataset['samples'] if s['diagnosis'] not in ("Alzheimer's disease", 'control')]
    observed = Counter(s['diagnosis'] for s in selected)
    row = {'accession': accession, 'role': 'test' if accession == 'GSE109887' else 'development',
        'raw_array_count': len(dataset['samples']), 'selected_array_count': len(selected),
        'observed_ad': observed["Alzheimer's disease"], 'observed_control': observed['control'],
        'published_ad': expected_ad, 'published_control': expected_control,
        'count_match': observed["Alzheimer's disease"] == expected_ad and observed['control'] == expected_control,
        'excluded_group_counts': dict(Counter(s['diagnosis'] for s in excluded)),
        'source_sha256': dataset['source_sha256'],
        'selected_donor_id_count': len({s['donor_id'] for s in selected if s['donor_id'] != 'unknown'}),
        'selected_unknown_donor_arrays': sum(s['donor_id'] == 'unknown' for s in selected)}
    report['datasets'].append(row)
    for sample in dataset['samples']:
        rows.append({key: sample.get(key) for key in ['dataset', 'sample_accession', 'diagnosis',
                     'original_label', 'brain_region', 'donor_id', 'diagnosis_mapping_rule', 'source_sha256']})
        rows[-1]['paper_group_eligible'] = sample in selected
        rows[-1]['selection_reason'] = ('AD/control label eligible; source QC not yet applied' if sample in selected
                                        else 'Outside paper AD/control groups; preserve source group')
report['all_published_counts_match'] = all(row['count_match'] for row in report['datasets'])
report['development_arrays'] = sum(row['selected_array_count'] for row in report['datasets'] if row['role'] == 'development')
report['test_arrays'] = sum(row['selected_array_count'] for row in report['datasets'] if row['role'] == 'test')
save_json(root / 'reports/pashaei_2025/sample_checkpoint.json', report)
out = root / 'data/processed/pashaei_2025/paper_sample_selection.csv'
with out.open('w', newline='') as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
print(json.dumps(report, indent=2))
