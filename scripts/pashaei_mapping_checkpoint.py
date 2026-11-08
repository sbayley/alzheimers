#!/usr/bin/env python3
"""Offline current-GEO mapping coverage; no expression analysis or model fitting."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from alzresearch.gene_mapping import (inspect_platform_mapping, inspect_matrix_feature_ids,
                                     matched_mapping_rows, write_mapping_csv)
from alzresearch.workflow import save_json


DATASET_PLATFORMS = {
    "GSE132903": "GPL10558", "GSE118553": "GPL10558", "GSE48350": "GPL570",
    "GSE5281": "GPL570", "GSE36980": "GPL6244", "GSE109887": "GPL10904",
}


def main():
    config = json.loads((ROOT / "configs/project.json").read_text())
    limits = config["limits"]
    registry = json.loads((ROOT / "registry/pashaei_2025_annotation_acquisition.json").read_text())
    records = {record["accession"]: record for record in registry["platforms"]}
    report_path = ROOT / "reports/pashaei_2025/mapping_checkpoint.json"
    report = {"generated_utc": datetime.now(timezone.utc).isoformat(),
              "interpretation": "Current official GEO table mapping reconstruction, not confirmed author annotation. No DE analysis or expression export performed.",
              "platforms": [], "datasets": [], "errors": []}
    # Illumina platform first so the one-region GSE132903 pilot is ready earliest.
    for platform in ("GPL10558", "GPL570", "GPL6244", "GPL10904"):
        try:
            mapping = inspect_platform_mapping(ROOT / "data/raw/platforms" / (platform + ".full.soft.txt"),
                platform, project_root=ROOT, expected_url=records[platform]["url"],
                max_bytes=limits["max_file_bytes"])
            union_features = []
            for accession, assigned in DATASET_PLATFORMS.items():
                if assigned != platform:
                    continue
                matrix = inspect_matrix_feature_ids(ROOT / "data/raw" / accession / (accession + "_series_matrix.txt.gz"),
                    accession, project_root=ROOT, max_file_bytes=limits["max_file_bytes"],
                    max_expanded_bytes=limits["max_expanded_bytes"])
                rows = list(matched_mapping_rows(mapping, matrix.pop("feature_ids")))
                union_features.extend(row["feature_id"] for row in rows)
                status_counts = Counter(row["status"] for row in rows)
                symbols = [row["unique_symbol"] for row in rows if row["status"] == "unique"]
                matrix.update(platform=platform, mapping_status_counts=dict(status_counts),
                    distinct_unique_source_symbols=len(set(symbols)),
                    probes_per_unique_symbol=dict(Counter(Counter(symbols).values())),
                    unique_mapping_fraction=status_counts["unique"] / len(rows) if rows else None)
                report["datasets"].append(matrix)
            output = ROOT / "data/processed/pashaei_2025/mappings" / (platform + ".csv")
            write_mapping_csv(output, matched_mapping_rows(mapping, union_features))
            summary = {key: value for key, value in mapping.items() if key != "mappings"}
            summary["mapping_csv"] = str(output.relative_to(ROOT))
            summary["exported_feature_rows"] = len(set(union_features))
            report["platforms"].append(summary)
            print(json.dumps({"platform": platform, "mapping_csv": str(output),
                              "mapping_counts": summary["mapping_status_counts"]}), flush=True)
        except Exception as error:
            report["errors"].append({"platform": platform,
                "error": type(error).__name__ + ": " + str(error)})
            print(json.dumps(report["errors"][-1]), flush=True)
        save_json(report_path, report)
    print(json.dumps({"report": str(report_path), "errors": len(report["errors"])}), flush=True)
    if report["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
