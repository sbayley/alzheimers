# Project status

Updated **2026-11-08 America/Los_Angeles**. The current objective is to evaluate a
data-curation tool for public Alzheimer’s gene-expression data. Pashaei 2025 is a
bounded downstream case study; classifier optimization and biological discovery
are outside the current scope.

## Completed

- Acquired six processed expression matrices and four full official platform tables,
  preserving exact URLs, retrieval times, sizes and SHA-256 hashes.
- Inspected **1,168 arrays**. Source-backed diagnosis selection matches the paper’s
  reported class totals: **956 development and 78 testing arrays**. The remaining
  **134 AsymAD arrays** are retained as a separate legitimate source group.
- Added checks for missing and conflicting metadata, repeated donor/region records,
  ambiguous gene mappings and known donor overlap across evaluation splits.
- Verified current-GEO mapping coverage. GSE132903 has 39,310 uniquely mapped probes,
  2,869 unmapped probes and 28,859 source symbols.
- Completed a documented GSE132903 numerical reconstruction using R 4.3.3 and
  limma 3.56.2: 195 arrays, 42,179 tested probes and **15,685 significant mapped
  genes**, compared with the paper’s **11,773**. This is an unresolved **+3,912 gap**.
- Independently checked count/collapse logic, adjusted-p ranges and five actual
  AD-minus-control coefficients. These establish implementation alignment only.
- Recorded **72 passing offline tests**, plus a separate synthetic limma functional
  check. Completed numerical outputs are preserved against overwrite.

## Findings and limits

The numerical run is a reconstruction, not an improvement or successful reproduction
claim. Current GEO mapping, an unadjusted model and documented defaults are explicit
assumptions; the historical annotation release and full author implementation remain
unavailable. Matching a package version does not reproduce an entire environment.

GSE118553 contains **48 repeated recorded donor × region groups** (47 pairs and one
triple). Its source study reports 347 post-QC arrays, including 232 AD/control arrays,
compared with 267 binary arrays in the public labels and target table. The required
quality inputs and exact retained/excluded sample list remain unavailable. These
are source-review findings, not automatic exclusions or evidence of a paper error.

Donor identities and cross-study relationships remain incomplete. Current GPL6244
annotations include **19 explicit truncated-assignment warnings**, retained as
incomplete mappings. The tool has not yet been benchmarked against independently
reviewed answers or an existing workflow. No classifier evaluation, five-way gene
intersection, corrected analysis or new biological finding is claimed.

## Next experiment

Validate a small set of tool findings against reviewed source evidence and an
explicit existing curation workflow. Trace each downstream variant through tool
finding → verification → curation decision → fixed-workflow rerun. Recover source-QC
inputs before source-faithful filtering. Preserve the original reconstruction and
resolve its ambiguities only as needed for a fair curation comparison.

The [evaluation plan](../plans/pashaei_2025_reproduction.md) defines the boundaries.

## Public evidence

- [Case-study progress](../reports/pashaei_2025/progress.md)
- [Public source provenance](../reports/public/data_provenance.json)
- [Sample-count checkpoint](../reports/pashaei_2025/sample_checkpoint.json)
- [Repeated-group checkpoint](../reports/pashaei_2025/replicate_group_checkpoint.json)
- [Mapping summary](../reports/public/mapping_summary.json)
- [Numerical checkpoint](../reports/public/R0_checkpoint.json)
- [Independent implementation checks](../reports/pashaei_2025/R0_verification.json)
- [Target methods review](../reports/pashaei_2025_methods_audit.md)
- [Source-QC review](../reports/pashaei_2025_source_qc.md)
- [Software test log](../reports/test_results.txt)
- [Research decisions](DECISIONS.md) and [source log](DATA_SOURCES.md)

Raw files, specimen-level data, detailed inventories, original execution records
and environments stay local and ignored. Curated public summaries retain the
aggregate evidence needed to review the work without redistributing those files.
