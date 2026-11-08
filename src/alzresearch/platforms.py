"""Inspect GEO platform SOFT records without retaining large accession lists.

A brief platform record may enumerate many associated samples while omitting the
probe annotation table. Reference counts below are record entries, not unique
participants, and downloading a record does not establish annotation completeness.
"""

import csv
import hashlib
from pathlib import Path
import re


class PlatformInspectionError(ValueError):
    """The input is not a safely interpretable requested platform record."""


def inspect_platform(path, accession, max_bytes=250_000_000):
    """Stream one plain-text platform SOFT record and return descriptive evidence.

    Original metadata values and one-based line numbers are retained, except for
    potentially enormous sample/series accession lists, which are counted only.
    Feature rows are counted and checked when present, but not copied into memory.
    """
    path = Path(path)
    if not re.fullmatch(r"GPL[0-9]+", accession):
        raise PlatformInspectionError("Expected a GPL platform accession.")
    if max_bytes <= 0:
        raise PlatformInspectionError("max_bytes must be positive.")
    if path.stat().st_size > max_bytes:
        raise PlatformInspectionError("Platform record exceeds configured byte limit.")
    digest = hashlib.sha256()
    record_fields = {}
    definitions = []
    sample_references = series_references = 0
    table = {"present": False, "columns": [], "row_count": 0,
             "declared_row_count": None, "completeness": "not_present_in_record"}
    seen_platform = False
    in_table = False
    table_ended = False
    total_bytes = line_number = 0
    with path.open("rb") as stream:
        while True:
            raw = stream.readline(min(8 * 1024 * 1024 + 1,
                                      max_bytes - total_bytes + 1))
            if not raw:
                break
            total_bytes += len(raw)
            line_number += 1
            if total_bytes > max_bytes:
                raise PlatformInspectionError("Platform record exceeds configured byte limit.")
            if len(raw) > 8 * 1024 * 1024:
                raise PlatformInspectionError("Platform line exceeds the 8 MB safety limit.")
            digest.update(raw)
            try:
                line = raw.decode("utf-8-sig" if line_number == 1 else "utf-8").rstrip("\r\n")
            except UnicodeDecodeError as exc:
                raise PlatformInspectionError("Platform record is not UTF-8 text at line %d." % line_number) from exc
            if not line.strip():
                continue
            if not seen_platform:
                if line.strip() != "^PLATFORM = " + accession:
                    raise PlatformInspectionError("Input does not begin with the requested platform record.")
                seen_platform = True
                continue
            if line.startswith("^"):
                raise PlatformInspectionError("Unexpected additional SOFT entity at line %d." % line_number)
            if line == "!platform_table_begin":
                if table["present"]:
                    raise PlatformInspectionError("Multiple platform tables are not supported.")
                table["present"] = True
                table["begin_line"] = line_number
                in_table = True
                continue
            if line == "!platform_table_end":
                if not in_table or not table["columns"]:
                    raise PlatformInspectionError("Platform table end has no table/header.")
                in_table = False
                table_ended = True
                table["end_line"] = line_number
                continue
            if in_table:
                cells = next(csv.reader([line], delimiter="\t", quoting=csv.QUOTE_NONE))
                if not table["columns"]:
                    if not cells or cells[0] != "ID":
                        raise PlatformInspectionError("Platform table must begin with an ID column.")
                    if len(set(cells)) != len(cells):
                        raise PlatformInspectionError("Platform table has duplicate column names.")
                    table["columns"] = cells
                else:
                    if len(cells) != len(table["columns"]):
                        raise PlatformInspectionError("Platform table row %d has %d columns; expected %d." %
                                                      (line_number, len(cells), len(table["columns"])))
                    if not cells[0]:
                        raise PlatformInspectionError("Empty feature ID at line %d." % line_number)
                    table["row_count"] += 1
                continue
            if line.startswith("!Platform_"):
                if " = " not in line:
                    raise PlatformInspectionError("Malformed platform metadata at line %d." % line_number)
                key, value = line[len("!Platform_"):].split(" = ", 1)
                if key == "sample_id":
                    sample_references += 1
                elif key == "series_id":
                    series_references += 1
                else:
                    record_fields.setdefault(key, []).append({"value": value, "line": line_number})
                continue
            if line.startswith("#"):
                definitions.append({"original": line, "line": line_number})
                continue
            raise PlatformInspectionError("Unexpected platform content at line %d." % line_number)
    if not seen_platform:
        raise PlatformInspectionError("Empty platform record.")
    if in_table or (table["present"] and not table_ended):
        raise PlatformInspectionError("Platform table lacks an end marker.")
    declared = record_fields.get("data_row_count", [])
    if declared:
        values = {entry["value"] for entry in declared}
        if len(values) == 1 and next(iter(values)).isdigit():
            table["declared_row_count"] = int(next(iter(values)))
    if table["present"]:
        if table["declared_row_count"] is None:
            table["completeness"] = "delimited_table_present_total_unverified"
        elif table["declared_row_count"] == table["row_count"]:
            table["completeness"] = "row_count_matches_record_declaration"
        else:
            table["completeness"] = "row_count_differs_from_record_declaration"
    result = {"accession": accession, "source_path": str(path),
              "source_bytes": total_bytes, "source_sha256": digest.hexdigest(),
              "record_fields": record_fields,
              "sample_reference_count": sample_references,
              "series_reference_count": series_references,
              "annotation_table": table, "column_definitions": definitions,
              "interpretation": "Sample/series reference counts are entries in this platform record, not unique donors. A brief record without a table does not supply probe/gene annotations."}
    for field in ("title", "manufacturer", "technology", "organism", "submission_date", "last_update_date"):
        result[field] = [entry["value"] for entry in record_fields.get(field, [])]
    return result
