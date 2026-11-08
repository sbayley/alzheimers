"""Inspect current GEO probe-to-symbol candidates without choosing ambiguous maps.

These mappings reconstruct the current official GEO tables. They do not establish
the annotation release or preprocessing used by the target paper's authors.
"""

from collections import Counter
import csv
import gzip
import hashlib
import json
from pathlib import Path
import re

from .acquisition import sha256_file


class GeneMappingError(ValueError):
    """A local source or mapping cannot be interpreted safely."""


PLATFORM_FIELDS = {
    "GPL570": "Gene Symbol",
    "GPL6244": "gene_assignment",
    "GPL10558": "Symbol",
    "GPL10904": "ID",
}


def verify_local_provenance(path, accession, *, project_root=None, expected_url=None):
    """Verify a saved source offline; this function never retrieves missing data."""
    path = Path(path)
    sidecar = path.with_name(path.name + ".provenance.json")
    if not path.is_file() or not sidecar.is_file():
        raise GeneMappingError("Local source/provenance is missing: " + str(path))
    try:
        record = json.loads(sidecar.read_text())
    except (ValueError, OSError) as error:
        raise GeneMappingError("Cannot read provenance: " + str(error)) from error
    if not isinstance(record, dict) or record.get("accession") != accession:
        raise GeneMappingError("Source provenance accession mismatch")
    if expected_url is not None and record.get("url") != expected_url:
        raise GeneMappingError("Source provenance URL mismatch")
    if record.get("byte_count") != path.stat().st_size or record.get("sha256") != sha256_file(path):
        raise GeneMappingError("Source size/SHA-256 differs from saved provenance")
    if project_root is not None:
        local = record.get("local_path")
        if not isinstance(local, str) or (Path(project_root) / local).resolve() != path.resolve():
            raise GeneMappingError("Source provenance local_path mismatch")
    return record


def candidate_symbols(platform, feature_id, raw_value):
    """Return source symbols, parsing status and a documented parsing rule.

    No symbol casing, synonyms or historical labels are modernized. Malformed
    multipart data never yield an apparently clean unique-symbol assignment.
    """
    if platform not in PLATFORM_FIELDS:
        raise GeneMappingError("Unsupported platform: " + platform)
    if platform == "GPL10904":
        value = str(feature_id).strip()
        return ([value] if value else []), ("unique" if value else "unmapped"), "GPL10904_exact_ID_v1"
    value = str(raw_value).strip()
    if value in ("", "---"):
        return [], "unmapped", platform + "_source_symbol_v1"
    values = []
    malformed = False
    truncated = "[WARNING: THIS FIELD TRUNCATED]" in value
    if platform == "GPL6244":
        for assignment in value.split("///"):
            if "[WARNING: THIS FIELD TRUNCATED]" in assignment:
                # Preserve the full source file as evidence. Do not promote a
                # partial final assignment to a complete gene-symbol candidate.
                continue
            parts = [part.strip() for part in assignment.split("//")]
            if len(parts) < 2:
                malformed = True
                continue
            symbol = parts[1]
            if symbol not in ("", "---"):
                values.append(symbol)
        rule = "GPL6244_gene_assignment_second_component_v1"
    else:
        values = [part.strip() for part in value.split("///") if part.strip() not in ("", "---")]
        # Do not guess the meaning of an undocumented secondary separator.
        malformed = any("//" in part or ";" in part or "," in part for part in values)
        rule = platform + "_source_symbol_triple_slash_v1"
    symbols = list(dict.fromkeys(values))
    status = ("source_truncated_assignment" if truncated else
              "malformed_assignment" if malformed else "unmapped" if not symbols
              else "unique" if len(symbols) == 1 else "multiple_symbols")
    return symbols, status, rule


def _bounded_lines(source, limit):
    consumed = 0
    line_number = 0
    while True:
        raw = source.readline(min(8 * 1024 * 1024 + 1, limit - consumed + 1))
        if not raw:
            return
        consumed += len(raw)
        line_number += 1
        if consumed > limit or len(raw) > 8 * 1024 * 1024:
            raise GeneMappingError("Input exceeds byte/line safety bound")
        try:
            line = raw.decode("utf-8-sig" if line_number == 1 else "utf-8").rstrip("\r\n")
        except UnicodeDecodeError as error:
            raise GeneMappingError("Source is not UTF-8 text") from error
        yield line_number, line, raw


def inspect_platform_mapping(path, platform, *, max_bytes=250_000_000,
                             project_root=None, expected_url=None):
    """Verify a full SOFT record and retain one candidate row per feature ID."""
    path = Path(path)
    if platform not in PLATFORM_FIELDS or max_bytes <= 0:
        raise GeneMappingError("Unsupported platform or invalid byte limit")
    provenance = verify_local_provenance(path, platform, project_root=project_root,
                                         expected_url=expected_url)
    if path.stat().st_size > max_bytes:
        raise GeneMappingError("Platform source exceeds configured file limit")
    mappings = {}
    fields = None
    in_table = ended = seen = False
    raw_rows = duplicate_rows = duplicate_conflicts = 0
    digest = hashlib.sha256()
    declared_rows = None
    with path.open("rb") as stream:
        for line_number, line, raw in _bounded_lines(stream, max_bytes):
            digest.update(raw)
            if not line.strip():
                continue
            if not seen:
                if line != "^PLATFORM = " + platform:
                    raise GeneMappingError("Source does not begin with requested platform")
                seen = True
                continue
            if line.startswith("^"):
                raise GeneMappingError("Unexpected additional SOFT entity")
            if line == "!platform_table_begin":
                if in_table or fields is not None:
                    raise GeneMappingError("Multiple platform tables")
                in_table = True
                continue
            if line == "!platform_table_end":
                if not in_table or fields is None:
                    raise GeneMappingError("Table end without a header")
                in_table, ended = False, True
                continue
            if not in_table:
                if line.startswith("!Platform_data_row_count = "):
                    declared_rows = int(line.split(" = ", 1)[1])
                continue
            cells = next(csv.reader([line], delimiter="\t", quoting=csv.QUOTE_NONE))
            if fields is None:
                fields = cells
                if (not fields or fields[0] != "ID" or len(set(fields)) != len(fields)
                        or PLATFORM_FIELDS[platform] not in fields):
                    raise GeneMappingError("Required unique ID/mapping columns are absent")
                mapping_index = fields.index(PLATFORM_FIELDS[platform])
                continue
            if len(cells) != len(fields) or not cells[0].strip():
                raise GeneMappingError("Malformed platform row at line %d" % line_number)
            raw_rows += 1
            feature = cells[0].strip()
            symbols, status, rule = candidate_symbols(platform, feature, cells[mapping_index])
            row = {"feature_id": feature, "candidate_symbols": symbols,
                   "unique_symbol": symbols[0] if status == "unique" else "",
                   "status": status, "source_lines": [line_number], "mapping_rule": rule}
            if feature in mappings:
                duplicate_rows += 1
                previous = mappings[feature]
                conflict = (previous["status"] == "conflicting_duplicate_id"
                            or set(previous["candidate_symbols"]) != set(symbols)
                            or previous["status"] != status)
                previous["source_lines"].append(line_number)
                if conflict:
                    if previous["status"] != "conflicting_duplicate_id":
                        duplicate_conflicts += 1
                    previous["candidate_symbols"] = list(dict.fromkeys(previous["candidate_symbols"] + symbols))
                    previous["status"], previous["unique_symbol"] = "conflicting_duplicate_id", ""
            else:
                mappings[feature] = row
    if not seen or fields is None or not ended or in_table:
        raise GeneMappingError("Complete platform annotation table is absent")
    if digest.hexdigest() != provenance["sha256"]:
        raise GeneMappingError("Platform changed between provenance verification and parsing")
    return {"platform": platform, "source_path": str(path), "source_bytes": path.stat().st_size,
            "source_sha256": provenance["sha256"], "source_url": provenance["url"],
            "mapping_field": PLATFORM_FIELDS[platform], "annotation_rows": raw_rows,
            "declared_annotation_rows": declared_rows,
            "unique_feature_ids": len(mappings), "duplicate_id_rows": duplicate_rows,
            "duplicate_id_conflicts": duplicate_conflicts,
            "mapping_status_counts": dict(Counter(row["status"] for row in mappings.values())),
            "interpretation": "Current GEO mapping reconstruction candidates; author annotation release is unconfirmed. A unique source symbol is not an independently validated current human gene identifier.",
            "mappings": mappings}


def inspect_matrix_feature_ids(path, accession, *, max_file_bytes=250_000_000,
                               max_expanded_bytes=2_000_000_000, project_root=None):
    """Read matrix feature identities only; no expression values are retained."""
    path = Path(path)
    provenance = verify_local_provenance(path, accession, project_root=project_root)
    if path.stat().st_size > max_file_bytes:
        raise GeneMappingError("Matrix source exceeds configured file limit")
    ids = []
    header = None
    in_table = ended = False
    observed_series = None
    with gzip.open(path, "rb") as source:
        for line_number, line, raw in _bounded_lines(source, max_expanded_bytes):
            cells = next(csv.reader([line], delimiter="\t"))
            if not cells:
                continue
            if cells[0] == "!Series_geo_accession" and len(cells) == 2:
                observed_series = cells[1]
            if cells[0] == "!series_matrix_table_begin":
                if header is not None or in_table:
                    raise GeneMappingError("Multiple expression tables")
                in_table = True
                continue
            if cells[0] == "!series_matrix_table_end":
                in_table, ended = False, True
                continue
            if not in_table:
                continue
            if header is None:
                if cells[0] != "ID_REF":
                    raise GeneMappingError("Expression table lacks ID_REF header")
                header = cells[1:]
            else:
                if len(cells) != len(header) + 1 or not cells[0]:
                    raise GeneMappingError("Malformed matrix row at line %d" % line_number)
                ids.append(cells[0])
    if observed_series != accession or header is None or not ended or in_table:
        raise GeneMappingError("Missing/mismatched series or incomplete expression table")
    counts = Counter(ids)
    return {"accession": accession, "source_path": str(path), "source_sha256": provenance["sha256"],
            "feature_ids": ids, "feature_count": len(ids), "sample_count": len(header),
            "duplicate_feature_ids": {feature: count for feature, count in counts.items() if count > 1}}


def matched_mapping_rows(mapping, feature_ids):
    """Export one row per requested feature, including unmatched/ambiguous IDs."""
    for feature in dict.fromkeys(feature_ids):
        yield mapping["mappings"].get(feature, {"feature_id": feature,
            "candidate_symbols": [], "unique_symbol": "", "status": "not_in_annotation",
            "source_lines": [], "mapping_rule": "exact_feature_ID_match_v1"})


def write_mapping_csv(path, rows):
    """Atomically write candidate mappings; ambiguous rows keep blank unique_symbol."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    try:
        with temporary.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["feature_id", "candidate_symbols", "unique_symbol",
                "status", "source_lines", "mapping_rule"])
            writer.writeheader()
            for row in rows:
                item = dict(row)
                for key in ("candidate_symbols", "source_lines"):
                    item[key] = json.dumps(item[key], ensure_ascii=False)
                writer.writerow(item)
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()
