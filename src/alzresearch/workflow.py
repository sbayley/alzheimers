"""Small auditable workflow: discover links, acquire, inspect, report."""

import argparse
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request

from .acquisition import Limits, download


ROOT = Path(__file__).resolve().parents[2]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def run_path(config, stem):
    prefix = config.get('output_namespace', '')
    if prefix and not re.fullmatch(r'[A-Za-z0-9_-]+', prefix):
        raise ValueError('output_namespace must be a simple name')
    return ROOT / 'registry' / ((prefix + '_' if prefix else '') + stem + '.json')


def report_dir(config):
    run_path(config, 'validation')  # Validate namespace before using it as a path.
    return ROOT / 'reports' / config.get('output_namespace', '')


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temp.replace(path)


def load_config(path):
    config = json.loads(Path(path).read_text())
    concurrency = config.get('max_concurrent_downloads', 1)
    if not 1 <= concurrency <= 2:
        raise ValueError('max_concurrent_downloads must be between 1 and 2')
    # This first-session workflow intentionally serializes all requests.
    return config, Limits(**config['limits'])


def parse_soft_record(text, accession):
    if not re.search(r'^\^SERIES = ' + re.escape(accession) + r'\s*$', text, re.M):
        raise ValueError('Not the requested GEO SOFT series record')
    fields = {}
    for line in text.splitlines():
        if line.startswith('!Series_') and ' = ' in line:
            key, value = line.split(' = ', 1)
            fields.setdefault(key[8:], []).append(value)
    return fields


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'a':
            self.hrefs.extend(value for key, value in attrs if key == 'href' and value)


def matrix_links(text, listing_url, accession):
    parser = Links()
    parser.feed(text)
    found = []
    for href in parser.hrefs:
        url = urllib.parse.urljoin(listing_url, href)
        parsed = urllib.parse.urlparse(url)
        name = Path(parsed.path).name
        if (parsed.scheme == 'https' and parsed.hostname == 'ftp.ncbi.nlm.nih.gov'
                and name.startswith(accession + '_') and name.endswith('.txt.gz')):
            found.append(url)
    return sorted(set(found))


def file_headers(url, timeout):
    try:
        request = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'alzresearch/0.1 public metadata audit'})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            value = response.headers.get('Content-Length')
            return {'status': response.status, 'content_length': int(value) if value else None,
                    'last_modified': response.headers.get('Last-Modified'),
                    'etag': response.headers.get('ETag'), 'url': response.geturl()}
    except Exception as exc:
        return {'error': type(exc).__name__ + ': ' + str(exc), 'content_length': None}


def discover(config, limits):
    data_root = ROOT / config['data_root']
    manifest = {'schema_version': 1, 'discovered_utc': utc_now(), 'datasets': []}
    discovery_cap = config.get('discovery_record_max_bytes', 2_000_000)
    if not isinstance(discovery_cap, int) or discovery_cap <= 0:
        raise ValueError('discovery_record_max_bytes must be a positive integer')
    small = replace(limits, max_file_bytes=min(limits.max_file_bytes, discovery_cap))
    for accession in config['accessions']:
        if not re.fullmatch(r'GSE\d+', accession):
            raise ValueError('Invalid GEO accession: ' + accession)
        prefix = accession[:-3] + 'nnn' if len(accession[3:]) > 3 else 'GSEnnn'
        base = 'https://ftp.ncbi.nlm.nih.gov/geo/series/' + prefix + '/' + accession + '/'
        record_url = ('https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=' + accession
                      + '&targ=self&form=text&view=brief')
        entry = {'accession': accession, 'official_record': record_url,
                 'matrix_directory': base + 'matrix/', 'files': [], 'errors': []}
        folder = data_root / 'raw' / accession
        try:
            record_path = folder / 'series_record.soft.txt'
            entry['record_provenance'] = download(record_url, record_path, accession=accession,
                data_root=data_root, limits=small)
            fields = parse_soft_record(record_path.read_text(), accession)
            entry['record_fields'] = fields
            entry['declared_sample_count'] = len(fields.get('sample_id', []))
            entry['platforms'] = fields.get('platform_id', [])
            entry['access_status'] = 'metadata_open_verified'
            listing_path = folder / 'matrix_directory.html'
            entry['listing_provenance'] = download(base + 'matrix/', listing_path,
                accession=accession, data_root=data_root, limits=small, allow_html=True)
            listing_text = listing_path.read_text()
            for url in matrix_links(listing_text, base + 'matrix/', accession):
                time.sleep(limits.min_interval_seconds)
                head = file_headers(url, limits.timeout_seconds)
                size = head.get('content_length')
                entry['files'].append({'kind': 'processed_series_matrix', 'url': url,
                    'discovered_from': base + 'matrix/', 'http_preview': head,
                    'within_file_limit': size is None or size <= limits.max_file_bytes,
                    'path': str((folder / Path(urllib.parse.urlparse(url).path).name).relative_to(ROOT))})
            if not entry['files']:
                entry['errors'].append('No processed matrix link found in official listing')
            # A small donor/covariate supplement is useful; do not pull raw archives.
            for original in fields.get('supplementary_file', []):
                if accession == 'GSE5281' and original.endswith('_sample_characteristics.xls'):
                    url = original.replace('ftp://', 'https://', 1)
                    time.sleep(limits.min_interval_seconds)
                    head = file_headers(url, limits.timeout_seconds)
                    size = head.get('content_length')
                    entry['files'].append({'kind': 'sample_metadata_supplement', 'url': url,
                        'discovered_from': record_url, 'http_preview': head,
                        'within_file_limit': size is None or size <= limits.max_file_bytes,
                        'path': str((folder / Path(urllib.parse.urlparse(url).path).name).relative_to(ROOT))})
        except Exception as exc:
            entry['errors'].append(type(exc).__name__ + ': ' + str(exc))
        manifest['datasets'].append(entry)
        save_json(ROOT / config['manifest'], manifest)
        print(json.dumps({'accession': accession, 'files_discovered': len(entry['files']),
                          'errors': entry['errors']}), flush=True)
    acquire_platforms(config, limits, manifest)
    return manifest


def acquire_platforms(config, limits, manifest):
    """Fetch verified platform IDs under the normal configured file limit.

    A platform's SOFT description may enumerate many linked samples/series, so it
    must not inherit the smaller cap used for directory listings/series records.
    """
    data_root = ROOT / config['data_root']
    prior = {record['accession']: record for record in manifest.get('platform_records', [])}
    run = {'started_utc': utc_now(), 'max_file_bytes': limits.max_file_bytes,
           'max_total_bytes': limits.max_total_bytes, 'results': []}
    manifest['platform_records'] = []
    for platform in sorted({platform for entry in manifest['datasets']
                            for platform in entry.get('platforms', [])}):
        if not re.fullmatch(r'GPL\d+', platform):
            continue
        url = ('https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=' + platform
               + '&targ=self&form=text&view=brief')
        path = data_root / 'raw' / 'platforms' / (platform + '.soft.txt')
        platform_record = {'accession': platform, 'url': url}
        old_record = prior.get(platform, {})
        history = list(old_record.get('previous_attempts', []))
        if old_record.get('status') == 'blocked':
            history.append({key: value for key, value in old_record.items()
                            if key != 'previous_attempts'})
        if history:
            platform_record['previous_attempts'] = history
        try:
            platform_record['provenance'] = download(url, path, accession=platform,
                data_root=data_root, limits=limits)
            with path.open('rb') as handle:
                first_line = handle.readline(4096).decode('utf-8-sig').strip()
            if first_line != '^PLATFORM = ' + platform:
                raise ValueError('Not the requested GEO platform record')
            platform_record['status'] = 'metadata_open_verified'
        except Exception as exc:
            platform_record['status'] = 'blocked'
            platform_record['error'] = type(exc).__name__ + ': ' + str(exc)
        manifest['platform_records'].append(platform_record)
        run['results'].append(platform_record)
        save_json(run_path(config, 'platform_acquisition_run'), run)
        print(json.dumps({'accession': platform, 'status': platform_record['status'],
                          'bytes': platform_record.get('provenance', {}).get('byte_count'),
                          'error': platform_record.get('error')}), flush=True)
    run['completed_utc'] = utc_now()
    save_json(run_path(config, 'platform_acquisition_run'), run)
    save_json(ROOT / config['manifest'], manifest)
    return run


def inspect_platform_records(config, limits, manifest):
    from .platforms import inspect_platform
    results = []
    for record in manifest.get('platform_records', []):
        item = {'accession': record['accession'], 'source_url': record['url']}
        path = ROOT / config['data_root'] / 'raw' / 'platforms' / (record['accession'] + '.soft.txt')
        try:
            if not path.exists():
                raise ValueError('Platform file is missing; run platforms first')
            # This call stays offline for existing files and verifies provenance.
            provenance = download(record['url'], path, accession=record['accession'],
                                  data_root=ROOT / config['data_root'], limits=limits)
            item.update(inspect_platform(path, record['accession'], max_bytes=limits.max_file_bytes))
            item['provenance'] = provenance
            item['status'] = 'inspected'
        except Exception as exc:
            item['status'] = 'blocked'
            item['error'] = type(exc).__name__ + ': ' + str(exc)
        results.append(item)
        print(json.dumps({'accession': item['accession'], 'status': item['status'],
                          'error': item.get('error')}), flush=True)
    save_json(report_dir(config) / 'platform_inventory.json',
              {'generated_utc': utc_now(), 'platforms': results})
    return results


def preview(manifest, limits):
    total = 0
    for dataset in manifest['datasets']:
        for file in dataset['files']:
            size = file['http_preview'].get('content_length')
            total += size or 0
            print(json.dumps({'accession': dataset['accession'], 'kind': file['kind'],
                'url': file['url'], 'bytes_from_head': size,
                'within_limit': file['within_file_limit']}))
    print(json.dumps({'known_planned_bytes': total, 'per_file_limit': limits.max_file_bytes,
                      'total_data_limit': limits.max_total_bytes,
                      'unknown_lengths_enforced_during_stream': True}))


def acquire(config, limits, manifest):
    run = {'started_utc': utc_now(), 'results': []}
    for dataset in manifest['datasets']:
        if not dataset['files']:
            row = {'accession': dataset['accession'], 'status': 'blocked',
                   'error': 'No discovered files: ' + '; '.join(dataset.get('errors', []))}
            run['results'].append(row)
            save_json(run_path(config, 'acquisition_run'), run)
            print(json.dumps(row), flush=True)
        for file in dataset['files']:
            row = {'accession': dataset['accession'], 'url': file['url'], 'kind': file['kind']}
            try:
                if not file.get('within_file_limit'):
                    raise ValueError('Official HEAD size exceeds configured per-file limit')
                row['provenance'] = download(file['url'], ROOT / file['path'],
                    accession=dataset['accession'], data_root=ROOT / config['data_root'], limits=limits,
                    content_kind='geo_matrix' if file['kind'] == 'processed_series_matrix' else None)
                row['status'] = row['provenance'].get('status', 'completed')
            except Exception as exc:
                row['status'] = 'blocked'
                row['error'] = type(exc).__name__ + ': ' + str(exc)
            run['results'].append(row)
            save_json(run_path(config, 'acquisition_run'), run)
            print(json.dumps(row), flush=True)
    run['completed_utc'] = utc_now()
    save_json(run_path(config, 'acquisition_run'), run)
    return run


def inspect(config, limits, manifest):
    from .inspection import inspect_matrix, write_inventory
    results = []
    run = {'started_utc': utc_now(), 'results': []}
    for dataset in manifest['datasets']:
        if not dataset['files']:
            row = {'accession': dataset['accession'], 'inspection': 'blocked',
                   'error': 'No discovered files: ' + '; '.join(dataset.get('errors', []))}
            run['results'].append(row)
            print(json.dumps(row), flush=True)
        for file in dataset['files']:
            if file['kind'] != 'processed_series_matrix':
                continue
            path = ROOT / file['path']
            if not path.exists():
                row = {'accession': dataset['accession'], 'inspection': 'blocked',
                       'error': 'Acquired file is missing', 'path': str(path)}
                run['results'].append(row)
                print(json.dumps(row), flush=True)
                continue
            try:
                # Existing-only verification checks provenance, SHA and gzip.
                # Missing files were handled above, so inspection stays offline.
                download(file['url'], path, accession=dataset['accession'],
                         data_root=ROOT / config['data_root'], limits=limits,
                         content_kind='geo_matrix')
                result = inspect_matrix(path, accession=dataset['accession'],
                                        max_expanded_bytes=limits.max_expanded_bytes)
                results.append(result)
                row = {'accession': dataset['accession'], 'inspection': 'completed',
                       'samples': len(result.get('samples', []))}
            except Exception as exc:
                row = {'accession': dataset['accession'], 'inspection': 'blocked',
                       'error': type(exc).__name__ + ': ' + str(exc)}
            run['results'].append(row)
            print(json.dumps(row), flush=True)
    paths = write_inventory(results, ROOT / 'data' / 'processed' / config.get('output_namespace', ''),
                            metadata_report_path=report_dir(config) / 'metadata_quality.md')
    acquisition_path = run_path(config, 'acquisition_run')
    acquisition = json.loads(acquisition_path.read_text()) if acquisition_path.exists() else {}
    aggregate = {'generated_utc': utc_now(), 'limits': config['limits'],
                 'interpretation': 'Array/sample counts are not independent participant counts. No disease effects estimated.',
                 'acquisition_results': acquisition.get('results', []),
                 'datasets': []}
    for result in results:
        dataset = {key: value for key, value in result.items()
                   if key not in ('samples', 'original_series_metadata')}
        for field in ('platform', 'tissue', 'cell_compartment', 'sex_as_recorded'):
            dataset[field + '_counts'] = dict(Counter(sample[field] for sample in result['samples']))
        dataset['data_processing_as_recorded'] = sorted({text for sample in result['samples']
            for text in sample['original_fields'].get('data_processing', [])})
        aggregate['datasets'].append(dataset)
    aggregate['inspection_results'] = run['results']
    save_json(report_dir(config) / 'dataset_inventory.json', aggregate)
    run['completed_utc'] = utc_now()
    run['artifacts'] = {key: str(value) for key, value in paths.items()}
    save_json(run_path(config, 'inspection_run'), run)
    print(json.dumps({'artifacts': paths}, default=str), flush=True)
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['discover', 'preview', 'acquire', 'inspect', 'inventory',
                                          'platforms', 'platform-inspect'])
    parser.add_argument('--config', default=str(ROOT / 'configs' / 'project.json'))
    args = parser.parse_args(argv)
    config, limits = load_config(args.config)
    if args.command == 'discover':
        manifest = discover(config, limits)
        if (any(entry['errors'] for entry in manifest['datasets'])
                or any(entry['status'] == 'blocked' for entry in manifest.get('platform_records', []))):
            raise SystemExit(1)
        return
    manifest_path = ROOT / config['manifest']
    if not manifest_path.exists():
        parser.error('No dataset manifest exists. Run the discover command first.')
    manifest = json.loads(manifest_path.read_text())
    if args.command == 'preview':
        preview(manifest, limits)
    elif args.command == 'platforms':
        run = acquire_platforms(config, limits, manifest)
        if any(row['status'] == 'blocked' for row in run['results']):
            raise SystemExit(1)
    elif args.command == 'platform-inspect':
        results = inspect_platform_records(config, limits, manifest)
        if any(row['status'] == 'blocked' for row in results):
            raise SystemExit(1)
    elif args.command == 'acquire':
        run = acquire(config, limits, manifest)
        if any(row['status'] == 'blocked' for row in run['results']):
            raise SystemExit(1)
    else:
        inspect(config, limits, manifest)
        run = json.loads(run_path(config, 'inspection_run').read_text())
        if any(row['inspection'] == 'blocked' for row in run['results']):
            raise SystemExit(1)


if __name__ == '__main__':
    main()
