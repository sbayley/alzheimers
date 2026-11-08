#!/usr/bin/env python3
"""Run the frozen single-dataset R0 reconstruction with hashed inputs."""
import csv
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'src'))
from alzresearch.acquisition import sha256_file
from alzresearch.gene_mapping import verify_local_provenance
from alzresearch.workflow import save_json, utc_now

matrix = root / 'data/raw/GSE132903/GSE132903_series_matrix.txt.gz'
mapping = root / 'data/processed/pashaei_2025/mappings/GPL10558.csv'
samples = root / 'data/processed/pashaei_2025/paper_sample_selection.csv'
annotation = root / 'data/raw/platforms/GPL10558.full.soft.txt'
script = root / 'scripts/pashaei_limma_checkpoint.R'
plan = root / 'plans/pashaei_2025_reproduction.md'
runtime = root / '.r-env/bin/Rscript'
out = root / 'data/processed/pashaei_2025/R0_GSE132903_v1'
registry = root / 'registry/pashaei_2025_R0_run.json'
report = root / 'reports/pashaei_2025/R0_checkpoint.json'
if (out / 'checkpoint_summary.csv').exists():
    raise SystemExit('Completed R0 output already exists. Preserve it; use its saved registry/report rather than overwrite.')
inputs = {}
for path in (matrix, mapping, samples, annotation, script, plan):
    if not path.is_file():
        raise SystemExit('Missing prerequisite: ' + str(path.relative_to(root)))
    inputs[str(path.relative_to(root))] = {'sha256': sha256_file(path), 'bytes': path.stat().st_size}
verify_local_provenance(matrix, 'GSE132903', project_root=root)
verify_local_provenance(annotation, 'GPL10558', project_root=root)
record = {'started_utc': utc_now(), 'variant': 'R0_GSE132903_v1',
    'plan': 'plans/pashaei_2025_reproduction.md', 'inputs': inputs,
    'interpretation': 'Historical numerical reconstruction with explicit current-GEO mapping/model assumptions. No correction variant or classifier.',
    'status': 'prepared'}
command = [str(runtime), '--vanilla', str(script), str(matrix), str(samples), str(mapping), str(out), 'GSE132903']
record['command'] = command
save_json(registry, record)
if not runtime.is_file():
    record.update(status='blocked', error='Project-local Rscript is not installed yet')
    save_json(registry, record)
    raise SystemExit(record['error'])
out.mkdir(parents=True, exist_ok=True)
(out / 'plan_snapshot.md').write_bytes(plan.read_bytes())
try:
    with (out / 'run.log').open('w') as log:
        result = subprocess.run(command, cwd=root, stdout=log, stderr=subprocess.STDOUT, timeout=300)
    record['returncode'] = result.returncode
    if result.returncode:
        raise RuntimeError('Rscript returned %s; inspect %s' % (result.returncode, out / 'run.log'))
    with (out / 'checkpoint_summary.csv').open() as handle:
        summary = next(csv.DictReader(handle))
    record.update(status='completed', completed_utc=utc_now(), summary=summary,
                  outputs={str(path.relative_to(root)): {'sha256': sha256_file(path), 'bytes': path.stat().st_size}
                           for path in sorted(out.iterdir()) if path.is_file()})
    save_json(registry, record)
    save_json(report, record)
    print(json.dumps(summary, indent=2))
except Exception as exc:
    record.update(status='blocked', completed_utc=utc_now(), error=type(exc).__name__ + ': ' + str(exc))
    save_json(registry, record)
    raise
