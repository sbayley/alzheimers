# Public research snapshots

These files are curated aggregate snapshots of an exploratory Alzheimer's data-curation project. They document the acquired inputs and completed checkpoints; they do not establish biological validity, an exact reproduction of the target paper, or a validated curation tool.

- [Data provenance](data_provenance.json) records six processed expression matrices and four full platform annotation records: exact requested and final URLs, retrieval times, relative local paths, bytes, SHA-256, and available Last-Modified/ETag values. Absent headers are explicit nulls. The public snapshot omits copied series metadata, contact fields, sample lists and response cookies.
- [R0 checkpoint](R0_checkpoint.json) preserves the recorded numerical summary and input/output hashes for the first GSE132903 reconstruction. Only machine-specific repository-root prefixes were removed from command arguments. The 15,685 significant mapped genes versus 11,773 reported in the target paper remain an unresolved reproduction gap.
- [Mapping summary](mapping_summary.json) reports aggregate coverage and ambiguity counts under the acquired GEO annotations. It omits feature-level assignments and sample/donor identifiers. The historical annotation release used by the target authors remains unconfirmed.

Original acquisition logs, detailed inventories, frozen run inputs, numerical tables and local execution records remain intact in the research workspace and are excluded from Git. Relative paths describe that workspace's layout; the underlying datasets and runtime are not bundled. The plan hash in R0 identifies the pre-fit snapshot retained with the original run, which may differ from the subsequently clarified plan in this repository. Publication did not rerun the statistical analysis.

## Re-acquiring the data

From the repository root, after creating the Python environment described in the main README:

```sh
.venv/bin/python scripts/project.py discover --config configs/pashaei_2025.json
.venv/bin/python scripts/project.py preview --config configs/pashaei_2025.json
.venv/bin/python scripts/project.py acquire --config configs/pashaei_2025.json
.venv/bin/python scripts/project.py inventory --config configs/pashaei_2025.json
.venv/bin/python scripts/acquire_platform_tables.py
```

Discovery and acquisition use official NCBI endpoints and the configured storage, request and expansion limits. Their detailed local records remain ignored. Remote data or annotations may change: compare newly recorded hashes with this snapshot before interpreting a rerun as using the same inputs. These commands acquire and inspect data; they do not recreate the project-local R runtime or perform the numerical reconstruction.
