# Alzheimer’s research data curation

Independent research into the reliability of public gene-expression data used in
Alzheimer’s studies, with a focus on research software and reproducible curation.

**Research question:** can an evidence-preserving audit make consequential metadata,
donor-relationship and gene-annotation uncertainties easier to identify and review
before a dataset is reused?

I’m building a local tool that records where each source came from, retains original
labels alongside documented interpretations, and flags unresolved issues for source
review. A [published Alzheimer’s analysis](https://www.mdpi.com/1422-0067/26/5/1816)
provides a bounded case study for evaluating the consequences of verified curation
decisions. Tool validation is in progress; this is not a completed study or a
validated clinical tool.

Start with the [current status](docs/STATUS.md),
[case-study progress](reports/pashaei_2025/progress.md), and
[prospective evaluation plan](plans/pashaei_2025_reproduction.md).

## Work completed

As of **2026-11-08**:

- Acquired and inspected six processed public GEO datasets containing **1,168
  expression arrays**, plus four full platform annotation tables. Sources, retrieval
  times, file sizes and SHA-256 hashes are recorded.
- Implemented checks for missing or conflicting metadata, repeated donor and
  brain-region records, ambiguous gene mappings, and known donor overlap across
  evaluation splits. Original values and unresolved fields are retained.
- Reconciled source-backed diagnosis labels with the case study’s reported class
  totals: 956 development and 78 testing arrays. A further 134 AsymAD arrays remain
  a separate source-defined group.
- Completed one planned numerical reconstruction using R 4.3.3 and the paper’s named
  limma version, 3.56.2, with preserved inputs, assumptions and outputs.
- Recorded **72 passing offline software tests**, plus separate checks of numerical
  implementation details. These checks do not establish scientific correctness or
  independently validate the tool’s usefulness.

The six datasets are GSE48350, GSE5281, GSE132903, GSE36980, GSE118553 and
GSE109887. Array counts are measurements, **not established independent participant
counts**. Donor identities and relationships between cohorts remain incomplete.

## Initial reconstruction and its limits

The GSE132903 pilot used 195 arrays and tested 42,179 probes. It produced **15,685
significant mapped genes**, compared with the paper’s **11,773**. This is an
unresolved reconstruction gap. The historical annotation release and full model
specification are not confirmed; matching a package version does not reproduce an
entire analysis environment.

The run does not establish improved prediction, new biomarkers or an error in the
published paper. No classifier evaluation or source-QC-faithful corrected analysis
has been completed. The tool has not yet been benchmarked against independently
reviewed reference answers or an existing curation workflow.

The [progress report](reports/pashaei_2025/progress.md) separates published targets,
observed data, reconstruction assumptions and unresolved evidence.

## Quick start

The acquisition, metadata inspection and offline tests require **Python 3.9 or
later** and use the standard library. Run commands from the repository root:

```sh
python3 -m venv .venv
.venv/bin/python scripts/run_tests.py
```

Tests use synthetic fixtures and do not download research data. The optional reader
for the historical XLS supplement is installed separately:

```sh
.venv/bin/python -m pip install -r requirements-optional.txt
```

This pins `xlrd==2.0.2`; see the
[official xlrd documentation](https://xlrd.readthedocs.io/en/latest/).
The numerical reconstruction additionally requires a project-local R runtime and
limma; it is separate from the Python quick start.

## Data acquisition and inspection

Discovery uses official NCBI records and directory listings to locate actual file
links. Preview prints the proposed transfers and configured limits before matrices
are downloaded:

```sh
.venv/bin/python scripts/project.py discover
.venv/bin/python scripts/project.py preview
.venv/bin/python scripts/project.py acquire
.venv/bin/python scripts/project.py inspect
.venv/bin/python scripts/project.py platforms
.venv/bin/python scripts/project.py platform-inspect
```

The default configuration, `configs/project.json`, covers the original three seed
datasets. Use `--config configs/pashaei_2025.json` with the main workflow for the
six-dataset case study. `inventory` is an alias for the same inspected inventory and
quality-report generation as `inspect`; it does not run a biological analysis.
Inspection verifies saved provenance and hashes without fetching missing files.

Defaults are **250 MB per file**, **2 GB total project data**, a **2 GB streamed
expansion ceiling**, and sequential downloads. The downloader enforces limits while
streaming, bounds retries and timeouts, validates content, and completes files by
atomic rename. Reuse requires matching provenance, source, size and hash; a local
snapshot does not establish that its remote source is unchanged.

Additional case-study commands are:

```sh
.venv/bin/python scripts/pashaei_sample_checkpoint.py
.venv/bin/python scripts/acquire_platform_tables.py
.venv/bin/python scripts/pashaei_mapping_checkpoint.py
.venv/bin/python scripts/run_pashaei_checkpoint.py
```

The final command requires the project-local R runtime and all preceding inputs.
Completed numerical runs are protected from overwrite. See the
[progress report](reports/pashaei_2025/progress.md) for the recorded command order,
actual outcomes and remaining prerequisites.

## Repository contents

- `src/alzresearch/`: bounded acquisition, metadata inspection, provenance checks
  and gene-mapping inspection.
- `scripts/` and `tests/`: workflow entry points and offline synthetic test cases.
- `configs/`: seed and case-study acquisition settings.
- `docs/`, `plans/` and selected `reports/`: research methods, evaluation plans
  and aggregate findings, with completed work distinguished from proposals.
- [`reports/public/`](reports/public/README.md): curated source provenance, mapping
  coverage and numerical checkpoints. Detailed `registry/` records remain local.

Downloaded expression matrices, sample-level inventories, detailed numerical
outputs, local environments and credentials are kept outside Git. The repository
shares research software and documentation rather than redistributing the data.
Source records identify the official datasets used for local acquisition.

## Next experiment

Validate a small set of tool findings against reviewed source evidence and an
existing curation workflow. Each downstream comparison should follow a documented
chain: tool finding → source verification → curation decision → analysis rerun,
with the remaining reconstruction held fixed where possible. Required source-QC
inputs must be recovered before applying source-faithful sample exclusions.

The current objective is to evaluate the curation tool. Classifier optimization,
feature-ranking searches and biological-discovery claims are outside this scope.
