"""Descriptive GEO series-matrix inspection; no disease-effect analysis.

Normalization is deliberately conservative. A sample accession is not a donor
identifier, and the absence of matching identifiers is not cohort independence.
The parser streams expression rows without retaining the expression matrix.
"""

import csv
import gzip
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


class InspectionError(ValueError):
    """An input cannot be interpreted safely as a GEO series matrix."""


def _canonical(value):
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


DIAGNOSES = {
    "ad": "Alzheimer's disease",
    "alzheimer s disease": "Alzheimer's disease",
    "alzheimers disease": "Alzheimer's disease",
    "alzheimer disease": "Alzheimer's disease",
    "alzheimer s disease ad": "Alzheimer's disease",
    "alzheimer disease ad": "Alzheimer's disease",
    "control": "control",
    "controls": "control",
    "normal": "control",
    "normal control": "control",
    "normal controls": "control",
    "healthy control": "control",
    "healthy controls": "control",
    "non demented": "control",
    "nondemented": "control",
    "non demented control": "control",
    "non dementia": "control",
    "no dementia": "control",
}
DIAGNOSIS_KEYS = {
    "diagnosis", "disease", "disease state", "disease status", "disease condition",
    "dementia status", "ad status", "clinical diagnosis", "group", "condition",
}
DONOR_KEYS = {"donor", "donor id", "donor identifier", "subject", "subject id",
              "subject identifier", "patient id", "individual id", "individual"}
MISSING = {"", "na", "n/a", "nan", "null", "none", "unknown", "not available"}


def _issue(code, message, samples=None, severity="warning"):
    item = {"code": code, "severity": severity, "message": message}
    if samples is not None:
        item["samples"] = list(samples)
    return item


def _evidence_for(characteristics, keys):
    return [entry for entry in characteristics if _canonical(entry["key"]) in keys]


def _first_field(characteristics, keys):
    evidence = _evidence_for(characteristics, set(keys))
    values = list(dict.fromkeys(item["value"] for item in evidence
                                if item["value"].strip().lower() not in MISSING))
    return (values[0] if len(values) == 1 else "unknown"), evidence


def _numeric_with_units(value, evidence):
    match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)\s*([A-Za-z.]*)\s*", value)
    number = float(match.group(1)) if match else None
    text = " ".join([value] + [item["key"] for item in evidence]).lower()
    if re.search(r"\b(years?|yrs?|y)\b", text):
        units = "years"
    elif re.search(r"\b(months?|mos?)\b", text):
        units = "months"
    elif re.search(r"\b(hours?|hrs?|h)\b", text):
        units = "hours"
    elif re.search(r"\b(days?|d)\b", text):
        units = "days"
    else:
        units = "unknown"
    return number, units


def _normalize_sample(sample, issues, series):
    fields = sample["original_fields"]
    characteristics = []
    for raw in fields.get("characteristics_ch1", []):
        if ":" in raw:
            key, value = raw.split(":", 1)
            characteristics.append({"key": key.strip(), "value": value.strip(),
                                    "original": raw})
        else:
            characteristics.append({"key": "", "value": raw, "original": raw})
    sample["original_characteristics"] = characteristics
    sample["original_label"] = fields.get("title", [""])[0]
    sample["source_name"] = fields.get("source_name_ch1", [""])[0]
    sample["platform"] = fields.get("platform_id", ["unknown"])[0]
    design = " ".join(value for row in series.get("overall_design", []) for value in row)
    diagnoses = _evidence_for(characteristics, DIAGNOSIS_KEYS)
    sample["original_diagnosis"] = [item["value"] for item in diagnoses]
    sample["diagnosis_evidence"] = list(diagnoses)
    diagnosis_map = dict(DIAGNOSES)
    summary_text = ' '.join(value for row in series.get('summary', []) for value in row)
    asymad_definition = (sample['dataset'] == 'GSE118553'
                         and 'asymptomatic ad' in _canonical(summary_text)
                         and 'asymad' in _canonical(summary_text))
    if asymad_definition:
        diagnosis_map['asymad'] = "asymptomatic Alzheimer's disease"
    nd_definition = (sample["dataset"] == "GSE132903"
                     and "non demented controls" in _canonical(design)
                     and re.search(r"\bND\s*=\s*[0-9]+", design))
    if nd_definition:
        diagnosis_map["nd"] = "control"
    mapped = {diagnosis_map[_canonical(item["value"])] for item in diagnoses
              if _canonical(item["value"]) in diagnosis_map}
    unmapped = [item["value"] for item in diagnoses
                if _canonical(item["value"]) not in diagnosis_map
                and item["value"].lower() not in MISSING]
    if len(mapped) == 1 and not unmapped:
        sample["diagnosis"] = next(iter(mapped))
        sample["diagnosis_mapping_rule"] = "exact_explicit_characteristic_label_v1"
        if asymad_definition and any(_canonical(item['value']) == 'asymad' for item in diagnoses):
            sample['diagnosis_mapping_rule'] = 'GSE118553_official_summary_AsymAD_definition_v1'
            sample['diagnosis_evidence'].append({'key': 'Series_summary', 'value': summary_text,
                                                'original': summary_text})
        if nd_definition and any(_canonical(item["value"]) == "nd" for item in diagnoses):
            sample["diagnosis_mapping_rule"] = "GSE132903_official_design_ND_definition_v1"
            sample["diagnosis_evidence"].append({"key": "Series_overall_design", "value": design, "original": design})
    else:
        sample["diagnosis"] = "unknown"
        sample["diagnosis_mapping_rule"] = "ambiguous_or_unmapped" if diagnoses else "no_explicit_diagnosis"
        if len(mapped) > 1 or unmapped:
            issues.append(_issue("ambiguous_diagnosis", "Diagnosis labels conflict or include unsupported values; no diagnosis assigned.",
                                 [sample["sample_accession"]]))
    # This accession's official design explicitly defines its title labels.
    # The rule is gated on that retained source statement, never generalized to
    # other datasets, and never used to turn a title suffix into a donor ID.
    design_defines_titles = (sample["dataset"] == "GSE48350"
                            and "refers to normal controls" in _canonical(design)
                            and "ad cases are labeled ad" in _canonical(design))
    if not diagnoses and design_defines_titles:
        title = sample["original_label"]
        code = None
        if re.search(r"(?:^|_)indiv[^_]+$", title):
            sample["diagnosis"], code = "control", "indiv"
        elif re.search(r"(?:^|_)AD_[^_]+$", title):
            sample["diagnosis"], code = "Alzheimer's disease", "AD"
        if code:
            sample["original_diagnosis"] = [code]
            sample["diagnosis_mapping_rule"] = "GSE48350_official_design_title_label_v1"
            sample["diagnosis_evidence"] = [
                {"key": "Sample_title", "value": title, "original": title},
                {"key": "Series_overall_design", "value": design, "original": design}]
    if sample['dataset'] == 'GSE36980' and not diagnoses:
        # Six explicitly disease-labeled source descriptions, not a title suffix.
        source_map = {
            'Frontal cortex of AD brain': "Alzheimer's disease",
            'Temporal cortex of AD brain': "Alzheimer's disease",
            'Hippocampus of of AD brain': "Alzheimer's disease",
            'Frontal cortex of non-AD brain': 'control',
            'Temporal cortex of non-AD brain': 'control',
            'Hippocampus of of non-AD brain': 'control',
        }
        if sample['source_name'] in source_map:
            sample['diagnosis'] = source_map[sample['source_name']]
            sample['original_diagnosis'] = [sample['source_name']]
            sample['diagnosis_mapping_rule'] = 'GSE36980_explicit_source_disease_label_v1'
            sample['diagnosis_evidence'] = [{'key': 'Sample_source_name_ch1',
                'value': sample['source_name'], 'original': sample['source_name']}]
    donor, donor_evidence = _first_field(characteristics, DONOR_KEYS)
    sample["donor_id"] = donor
    sample["donor_evidence"] = donor_evidence
    sample["donor_namespace"] = sample["dataset"]
    sample["donor_identity_scope"] = "dataset_only" if donor != "unknown" else "unknown"
    donor_values = {item["value"] for item in donor_evidence
                    if item["value"].lower() not in MISSING}
    if len(donor_values) > 1:
        issues.append(_issue("inconsistent_donor_identifiers", "Explicit donor fields disagree within this sample; donor identity left unknown.",
                             [sample["sample_accession"]]))
    field_keys = {
        "tissue": {"tissue", "tissue type", "organ", "source tissue", "organ tissue type"},
        "brain_region": {"brain region", "region", "anatomical region", "tissue region", "organ region"},
        "cell_compartment": {"cell type", "cell population", "cell compartment", "cell"},
        "sex_as_recorded": {"sex", "gender"},
        "age_as_recorded": {"age", "age years", "age yrs", "age in years", "age at death", "age at death years", "expired age years"},
        "postmortem_interval_as_recorded": {"pmi", "pmi hours", "postmortem interval", "post mortem interval", "postmortem interval hours", "post mortem interval hours"},
        "rna_quality_as_recorded": {"rin", "rna integrity number", "rna integrity", "rna quality"},
        "batch_as_recorded": {"batch", "batch id", "array batch", "processing batch"},
        "technical_replicate_as_recorded": {"technical replicate", "technical replicate id", "replicate"},
    }
    sample["field_evidence"] = {}
    for field, keys in field_keys.items():
        sample[field], sample["field_evidence"][field] = _first_field(characteristics, keys)
    sample["age_value"], sample["age_units"] = _numeric_with_units(
        sample["age_as_recorded"], sample["field_evidence"]["age_as_recorded"])
    sample["age_lower_bound"] = None
    sample["age_upper_bound"] = None
    sample["age_is_censored"] = False
    sample["age_censoring_operator"] = None
    censored_age = re.fullmatch(r"\s*(?:(>=?|<=?)\s*)?([0-9]+(?:\.[0-9]+)?)\s*(\+)?\s*([A-Za-z.]*)\s*", sample["age_as_recorded"])
    if censored_age and (censored_age.group(1) or censored_age.group(3)):
        operator = censored_age.group(1) or "+"
        sample["age_upper_bound" if operator.startswith("<") else "age_lower_bound"] = float(censored_age.group(2))
        sample["age_is_censored"] = True
        sample["age_censoring_operator"] = operator
        sample["age_value"] = None
    stage = _evidence_for(characteristics, {"developmental stage"})
    if sample["age_units"] in {"days", "months"} and any(_canonical(item["value"]) == "adult" for item in stage):
        issues.append(_issue("age_unit_conflict", "Recorded age %r conflicts with explicit adult developmental stage; retain the source value and resolve before age adjustment." % sample["age_as_recorded"], [sample["sample_accession"]]))
    if sample["age_as_recorded"] != "unknown" and sample["age_units"] == "unknown":
        issues.append(_issue("age_units_unknown", "Age is recorded without interpretable explicit units; no unit has been assumed.", [sample["sample_accession"]]))
    sample["brain_region_mapping_rule"] = "explicit_characteristic" if sample["brain_region"] != "unknown" else "unknown"
    source_regions = {
        'GSE36980': {'Frontal cortex', 'Temporal cortex', 'Hippocampus'},
        'GSE118553': {'Temporal_Cortex', 'Entorhinal_Cortex', 'Frontal_Cortex', 'Cerebellum'},
        'GSE109887': {'brain, middle temporal gyrus'},
    }
    if (sample['dataset'] in source_regions and sample['brain_region'] == 'unknown'
            and sample['tissue'] in source_regions[sample['dataset']]):
        sample['brain_region'] = ('middle temporal gyrus' if sample['dataset'] == 'GSE109887'
                                  else sample['tissue'])
        sample['brain_region_mapping_rule'] = sample['dataset'] + '_explicit_tissue_region_v1'
        sample['field_evidence']['brain_region'] = list(sample['field_evidence']['tissue'])
    if (sample["dataset"] == "GSE132903" and sample["brain_region"] == "unknown"
            and sample["tissue"] == "middle temporal gyrus"
            and "middle temporal gyrus" in design.lower()):
        sample["brain_region"] = "middle temporal gyrus"
        sample["brain_region_mapping_rule"] = "GSE132903_explicit_tissue_and_official_design_v1"
        sample["field_evidence"]["brain_region"] = sample["field_evidence"]["tissue"] + [
            {"key": "Series_overall_design", "value": design, "original": design}]
    sample["postmortem_interval_value"], sample["postmortem_interval_units"] = _numeric_with_units(
        sample["postmortem_interval_as_recorded"], sample["field_evidence"]["postmortem_interval_as_recorded"])
    sample["pathology_as_recorded"] = [item for item in characteristics if any(
        term in _canonical(item["key"]) for term in ("braak", "cerad", "patholog", "plaque", "tangle"))]
    sample["inclusion_decision"] = "not_assessed"
    sample["inclusion_reason"] = "Descriptive inventory only; biological inclusion criteria have not been applied."


def audit_samples(samples):
    """Return duplicate, repeated-measure, and donor-consistency warnings."""
    issues = []
    counts = Counter((item["dataset"], item["sample_accession"]) for item in samples)
    for (dataset, accession), count in counts.items():
        if count > 1:
            issues.append(_issue("duplicate_sample", "%s contains %s copies of %s." % (dataset, count, accession),
                                 [accession], "error"))
    donors = defaultdict(list)
    for item in samples:
        if item.get("donor_id", "unknown") != "unknown":
            donors[(item.get("donor_namespace", item["dataset"]), item["donor_id"])].append(item)
    for (namespace, donor), records in donors.items():
        if len(records) > 1:
            ids = [item["sample_accession"] for item in records]
            issues.append(_issue("repeated_measures", "%s donor %s has multiple sample records; do not treat them as independent people." % (namespace, donor), ids, "info"))
            for field in ("diagnosis", "sex_as_recorded", "age_as_recorded"):
                values = {str(item.get(field, "unknown")) for item in records
                          if item.get(field, "unknown") != "unknown"}
                if len(values) > 1:
                    issues.append(_issue("inconsistent_donor_metadata", "%s donor %s has inconsistent %s: %s." % (namespace, donor, field, sorted(values)), ids))
            regions = defaultdict(list)
            for item in records:
                if item.get('brain_region', 'unknown') != 'unknown':
                    regions[item['brain_region']].append(item['sample_accession'])
            for region, region_ids in regions.items():
                if len(region_ids) > 1:
                    issues.append(_issue('repeated_donor_region',
                        '%s donor %s has %s arrays labeled %s; review assay/source QC before treating these as distinct biological measurements. This does not identify which array to exclude.' %
                        (namespace, donor, len(region_ids), region), region_ids))
    return issues


def check_split_leakage(samples, split_by_sample):
    """Detect known donor identities assigned to multiple evaluation splits.

    Unknown donor identities cannot establish leakage-free splitting. The caller
    must handle that limitation before evaluating a predictive model.
    """
    donors = defaultdict(list)
    for sample in samples:
        if sample.get("donor_id", "unknown") != "unknown":
            split = split_by_sample.get(sample["sample_accession"])
            if split is not None:
                donors[(sample.get("donor_namespace", sample["dataset"]), sample["donor_id"])].append((sample["sample_accession"], split))
    issues = []
    for (namespace, donor), assignments in donors.items():
        if len({split for _, split in assignments}) > 1:
            issues.append(_issue("donor_split_leakage", "%s donor %s spans evaluation splits." % (namespace, donor),
                                 [accession for accession, _ in assignments], "error"))
    if any(sample.get("donor_id", "unknown") == "unknown" for sample in samples):
        issues.append(_issue("split_independence_unverified", "At least one donor identity is unknown; absence of detected leakage does not establish independent splits."))
    return issues


def inspect_matrix(path, accession=None, max_expanded_bytes=2_000_000_000):
    """Inspect one real or synthetic series matrix, retaining source metadata.

    Compressed bytes are hashed and original metadata is retained per sample.
    Decompressed content is streamed, bounded, and never written to disk.
    """
    path = Path(path)
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    source_hash = digest.hexdigest()
    metadata = defaultdict(list)
    series = defaultdict(list)
    matrix = {"feature_count": 0, "sample_count": 0, "finite_value_count": 0,
              "missing_value_count": 0, "non_numeric_value_count": 0,
              "minimum": None, "maximum": None, "data_scale": "unverified",
              "duplicate_feature_count": 0}
    issues = []
    feature_ids = set()
    header = None
    in_table = False
    saw_end = False
    expanded_bytes = 0
    opener = gzip.open if path.suffix == ".gz" else open
    try:
        with opener(path, "rb") as source:
            line_no = 0
            while True:
                # Bound readline itself: a compressed single-line payload must
                # not allocate its entire expanded size before limit checks.
                raw = source.readline(min(8 * 1024 * 1024 + 1,
                                          max_expanded_bytes - expanded_bytes + 1))
                if not raw:
                    break
                line_no += 1
                expanded_bytes += len(raw)
                if expanded_bytes > max_expanded_bytes:
                    raise InspectionError("Expanded input exceeds configured byte limit.")
                if len(raw) > 8 * 1024 * 1024:
                    raise InspectionError("Line exceeds the 8 MB metadata/matrix safety limit.")
                try:
                    line = raw.decode("utf-8-sig" if line_no == 1 else "utf-8").rstrip("\r\n")
                except UnicodeDecodeError as error:
                    raise InspectionError("Input is not UTF-8 text at line %s." % line_no) from error
                if not line:
                    continue
                try:
                    cells = next(csv.reader([line], delimiter="\t", strict=True))
                except csv.Error as error:
                    raise InspectionError("Malformed tab-delimited line %s: %s" % (line_no, error)) from error
                key = cells[0]
                if key == "!series_matrix_table_begin":
                    if in_table or header is not None:
                        raise InspectionError("Multiple expression tables are not supported.")
                    in_table = True
                    continue
                if key == "!series_matrix_table_end":
                    in_table = False
                    saw_end = True
                    continue
                if key.startswith("!Sample_"):
                    metadata[key[len("!Sample_"):]].append(cells[1:])
                elif key.startswith("!Series_"):
                    series[key[len("!Series_"):]].append(cells[1:])
                elif in_table:
                    if header is None:
                        if key != "ID_REF":
                            raise InspectionError("Expression table must begin with ID_REF.")
                        header = cells[1:]
                        matrix["sample_count"] = len(header)
                    else:
                        if len(cells) != len(header) + 1:
                            raise InspectionError("Matrix row %s has %s values; expected %s." % (line_no, len(cells) - 1, len(header)))
                        matrix["feature_count"] += 1
                        if key in feature_ids:
                            matrix["duplicate_feature_count"] += 1
                        feature_ids.add(key)
                        for value in cells[1:]:
                            if value.strip().lower() in MISSING:
                                matrix["missing_value_count"] += 1
                                continue
                            try:
                                number = float(value)
                            except ValueError:
                                matrix["non_numeric_value_count"] += 1
                                continue
                            if not math.isfinite(number):
                                matrix["missing_value_count"] += 1
                                continue
                            matrix["finite_value_count"] += 1
                            matrix["minimum"] = number if matrix["minimum"] is None else min(matrix["minimum"], number)
                            matrix["maximum"] = number if matrix["maximum"] is None else max(matrix["maximum"], number)
    except (OSError, EOFError) as error:
        raise InspectionError("Could not read compressed/text matrix: %s" % error) from error
    if not metadata.get("geo_accession") or len(metadata["geo_accession"]) != 1:
        raise InspectionError("Expected exactly one !Sample_geo_accession row.")
    accessions = metadata["geo_accession"][0]
    if not accessions or any(not re.fullmatch(r"GSM[0-9]+", item) for item in accessions):
        raise InspectionError("Invalid or empty GEO sample accessions.")
    for field, rows in metadata.items():
        if any(len(row) != len(accessions) for row in rows):
            raise InspectionError("Sample metadata field %s has inconsistent column count." % field)
    if header is not None and header != accessions:
        raise InspectionError("Matrix column identities/order differ from sample metadata.")
    if in_table or (header is not None and not saw_end):
        raise InspectionError("Expression table lacks end marker.")
    if header is None:
        issues.append(_issue("expression_table_absent", "No processed expression table was present; metadata remains inspectable."))
    if matrix["non_numeric_value_count"]:
        issues.append(_issue("non_numeric_expression_values", "Expression table contains nonnumeric values."))
    record_accessions = [value for row in series.get("geo_accession", []) for value in row]
    if accession and record_accessions and accession not in record_accessions:
        raise InspectionError("Requested accession does not match !Series_geo_accession.")
    accession = accession or (record_accessions[0] if record_accessions else "unknown")
    samples = []
    for index, sample_id in enumerate(accessions):
        sample = {"dataset": accession, "sample_accession": sample_id,
                  "source_file": str(path), "source_sha256": source_hash,
                  "assay": "; ".join(value for row in series.get("type", []) for value in row) or "unknown",
                  "original_fields": {field: [row[index] for row in rows]
                                      for field, rows in metadata.items()}}
        _normalize_sample(sample, issues, series)
        samples.append(sample)
    issues.extend(audit_samples(samples))
    region_forms = defaultdict(set)
    for sample in samples:
        if sample["brain_region"] != "unknown":
            folded = re.sub(r"[^a-z0-9]", "", sample["brain_region"].lower())
            region_forms[folded].add(sample["brain_region"])
    for forms in region_forms.values():
        if len(forms) > 1:
            issues.append(_issue("region_label_format_variants", "Brain-region strings differ only in case/separators: %s. Values are retained separately pending an explicit harmonization rule." % sorted(forms)))
    known_donors = {sample["donor_id"] for sample in samples if sample["donor_id"] != "unknown"}
    unknown_donor_samples = sum(sample["donor_id"] == "unknown" for sample in samples)
    if unknown_donor_samples:
        issues.append(_issue("donor_identity_unknown", "%s samples lack an unambiguous explicit donor identifier; total donor count and donor-level independence are unknown." % unknown_donor_samples))
    fields = ("diagnosis", "donor_id", "tissue", "brain_region", "cell_compartment",
              "sex_as_recorded", "age_as_recorded", "postmortem_interval_as_recorded",
              "rna_quality_as_recorded", "batch_as_recorded")
    missingness = {field: sum(sample[field] == "unknown" for sample in samples) for field in fields}
    summary = {
        "sample_count": len(samples), "observed_known_donor_ids": len(known_donors),
        "samples_with_unknown_donor": unknown_donor_samples,
        "total_donor_count": None if unknown_donor_samples else len(known_donors),
        "diagnosis_counts": dict(Counter(sample["diagnosis"] for sample in samples)),
        "brain_region_counts": dict(Counter(sample["brain_region"] for sample in samples)),
        "missingness_counts": missingness,
        "age_units_counts": dict(Counter(sample["age_units"] for sample in samples)),
        "censored_age_sample_count": sum(sample["age_is_censored"] for sample in samples),
        "age_range_by_units": {},
        "age_range_by_diagnosis_and_units": {},
        "diagnosis_by_brain_region_counts": dict(Counter(
            "%s | %s" % (sample["diagnosis"], sample["brain_region"]) for sample in samples)),
    }
    for units in sorted({sample["age_units"] for sample in samples}):
        ages = [sample["age_value"] for sample in samples if sample["age_units"] == units and sample["age_value"] is not None]
        if ages:
            summary["age_range_by_units"][units] = {"minimum": min(ages), "maximum": max(ages), "count": len(ages)}
    for diagnosis in sorted({sample["diagnosis"] for sample in samples}):
        summary["age_range_by_diagnosis_and_units"][diagnosis] = {}
        for units in sorted({sample["age_units"] for sample in samples}):
            ages = [sample["age_value"] for sample in samples
                    if sample["diagnosis"] == diagnosis and sample["age_units"] == units
                    and sample["age_value"] is not None]
            if ages:
                summary["age_range_by_diagnosis_and_units"][diagnosis][units] = {
                    "minimum": min(ages), "maximum": max(ages), "count": len(ages)}
    return {"dataset": accession, "source_file": str(path), "source_sha256": source_hash,
            "source_bytes": path.stat().st_size, "expanded_bytes_read": expanded_bytes,
            "original_series_metadata": dict(series), "summary": summary,
            "matrix": matrix, "samples": samples, "issues": issues}


def inspect_files(paths, max_expanded_bytes=2_000_000_000):
    return [inspect_matrix(path, max_expanded_bytes=max_expanded_bytes) for path in paths]


def write_inventory(results, output_dir, metadata_report_path=None):
    """Write reproducible JSON/CSV inventory plus an honest descriptive report."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "sample_inventory.json"
    csv_path = output_dir / "samples.csv"
    report_path = Path(metadata_report_path) if metadata_report_path is not None else output_dir / "metadata_quality.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    samples = [sample for result in results for sample in result["samples"]]
    json_path.write_text(json.dumps({"datasets": results, "cross_file_issues": audit_samples(samples)}, indent=2, ensure_ascii=False) + "\n")
    scalar_fields = ["dataset", "sample_accession", "source_file", "source_sha256", "original_label",
                     "source_name", "diagnosis", "original_diagnosis", "diagnosis_mapping_rule", "diagnosis_evidence",
                     "donor_id", "donor_namespace", "donor_identity_scope", "donor_evidence", "tissue", "brain_region",
                     "cell_compartment", "assay", "platform", "age_as_recorded", "age_value", "age_units", "age_lower_bound", "age_upper_bound", "age_is_censored", "age_censoring_operator", "brain_region_mapping_rule", "sex_as_recorded",
                     "postmortem_interval_as_recorded", "postmortem_interval_value", "postmortem_interval_units",
                     "rna_quality_as_recorded", "batch_as_recorded", "technical_replicate_as_recorded",
                     "pathology_as_recorded", "inclusion_decision", "inclusion_reason", "field_evidence", "original_fields"]
    with csv_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=scalar_fields, extrasaction="ignore")
        writer.writeheader()
        for sample in samples:
            writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
                             for key, value in sample.items() if key in scalar_fields})
    lines = ["# Inspected metadata quality", "", "Generated from the actual files named below. No biological effect has been estimated.", "",
             "Sample counts are not donor counts. Dataset accessions are not evidence of cohort independence.", "",
             "| Dataset | Samples | Explicit donor IDs observed | Total donor count | Matrix features | Expression range |", "|---|---:|---:|---|---:|---|"]
    for result in results:
        summary, matrix = result["summary"], result["matrix"]
        donor_count = "unknown" if summary["total_donor_count"] is None else str(summary["total_donor_count"])
        lines.append("| %s | %s | %s | %s | %s | %s to %s (scale unverified) |" % (
            result["dataset"], summary["sample_count"], summary["observed_known_donor_ids"], donor_count,
            matrix["feature_count"], matrix["minimum"], matrix["maximum"]))
    for result in results:
        lines.extend(["", "## " + result["dataset"], "", "Source: `%s` (%s bytes); SHA-256 `%s`." % (result["source_file"], result["source_bytes"], result["source_sha256"]), "",
                      "Diagnosis composition: `%s`. Brain-region composition: `%s`." % (json.dumps(result["summary"]["diagnosis_counts"]), json.dumps(result["summary"]["brain_region_counts"])), "",
                      "Age ranges by explicitly recorded units (unknown units remain unknown): `%s`." % json.dumps(result["summary"]["age_range_by_units"]), "",
                      "Age ranges by diagnosis and units: `%s`. Range overlap is descriptive and does not establish comparable age distributions." % json.dumps(result["summary"]["age_range_by_diagnosis_and_units"]), "",
                      "Censored ages (for example, `90+`) are preserved as lower bounds and excluded from exact-age ranges: %s samples." % result["summary"]["censored_age_sample_count"], "",
                      "| Field | Missing/unknown samples |", "|---|---:|"])
        for field, count in result["summary"]["missingness_counts"].items():
            lines.append("| %s | %s |" % (field, count))
        lines.extend(["", "Recorded issues:", ""])
        if result["issues"]:
            for issue in result["issues"]:
                lines.append("- **%s**: %s" % (issue["code"], issue["message"]))
        else:
            lines.append("- No parser/audit issues detected; this is not a completeness or scientific-validity guarantee.")
    lines.extend(["", "## Limits", "", "Original sample fields and characteristic strings are retained in JSON and CSV. Normalized diagnosis uses exact supported explicit characteristic labels, plus accession-specific mappings gated on retained official design statements: GSE132903 defines ND as non-demented controls; GSE48350 defines its AD/indiv title labels. These mappings retain their source evidence and are not generalized to other datasets. Titles are never used to infer donor identity. Age units are not assumed and censored ages are not assigned exact values. Donor identifiers are scoped to their dataset. Cross-dataset overlap, data scale, probe mapping, batch effects, and analysis inclusion rules require source-level review before disease comparisons. No samples have been automatically included in a biological analysis.", ""])
    report_path.write_text("\n".join(lines))
    return {"json": str(json_path), "csv": str(csv_path), "report": str(report_path)}
