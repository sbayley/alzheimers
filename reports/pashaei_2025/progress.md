# Pashaei 2025: first reproduction checkpoint

Session: **2026-11-08 America/Los_Angeles**. Target
[DOI 10.3390/ijms26051816](https://www.mdpi.com/1422-0067/26/5/1816).
This report separates published targets, observed data, reconstruction outputs,
and remaining uncertainties. No improvement in a biomarker classifier is claimed.

## Completed

The target-author implementation, exact historical settings and intermediate
results are not available in this project.

All six processed expression matrices are acquired. Three new transfers were
GSE36980 **8,886,746 bytes**, GSE118553 **149,479,055 bytes**, and GSE109887
**17,908,567 bytes**. Four full official platform annotation records were also
acquired and checked against their declared table sizes:

| Platform | Download bytes | Observed annotation rows |
|---|---:|---:|
| GPL570 | 85,646,369 | 54,675 |
| GPL6244 | 100,752,926 | 33,297 |
| GPL10558 | 75,786,263 | 48,107 |
| GPL10904 | 896,292 | 34,695 |

Sources, hashes, HTTP/version fields and retrieval timestamps are in the
[public provenance summary](../public/data_provenance.json).
Original detailed manifests and source records remain local.
The original seed audit remains separate; new output paths use the paper namespace.

## Sample-selection checkpoint

The six matrices contain **1,168 arrays**. Exact source-backed AD/control label
selection reproduces all published class totals: **956 development arrays** and
**78 testing arrays**. GSE118553 contains a separate **134-array AsymAD group**,
which accounts for its 401 deposited versus 267 binary-comparison arrays. These
are group exclusions, not corrupted data. No source-QC exclusions were applied.

| Dataset | Selected AD | Selected controls | Published count match |
|---|---:|---:|---|
| GSE48350 | 80 | 173 | Yes |
| GSE36980 | 33 | 47 | Yes |
| GSE132903 | 97 | 98 | Yes |
| GSE118553 | 167 | 100 | Yes |
| GSE5281 | 87 | 74 | Yes |
| GSE109887, testing | 46 | 32 | Yes |

Matching counts does not establish the exact historical sample IDs, complete donor
totals, independence, or numerical reproduction. Original labels, rules and hashes
are retained in ignored detailed data. See [structured sample checkpoint](sample_checkpoint.json).

## Numerical pilot R0: observed mismatch

The [prospective plan](../../plans/pashaei_2025_reproduction.md) was frozen before
fitting. GSE132903 was selected before observing numerical results because it uses
one brain region and documented processed values. The raw/normalized processing
ambiguities and explicit multiregion dependence in GSE48350 made it a less suitable
first numerical pilot.

R0 used **native R 4.3.3**, exact **limma 3.56.2**, all 195 AD/control arrays,
the supplied processed expression values without an additional transformation,
an unadjusted AD-minus-control model, default non-trend/non-robust eBayes,
BH correction over 42,179 probe rows, and the acquired current GPL10558 symbols.
Only unambiguous single-symbol mappings were retained. Among multiple probes
for a symbol, the lowest adjusted-p probe was selected, then raw p/probe ID for ties.

| Checkpoint | Paper | R0 reconstruction |
|---|---:|---:|
| AD / control arrays | 97 / 98 | 97 / 98 |
| Significant mapped genes, reported FDR threshold 0.05 | 11,773 | **15,685** |

Additional observed R0 counts: **42,179 tested probes**, **20,222 significant probes**,
**39,310 uniquely mapped probes**, **28,859 distinct mapped source symbols**,
**8,458 positive** and **7,227 negative** selected-gene coefficients.
The total mapped-gene count differs from the paper by **+3,912**.

This run **does not reproduce the published gene count**. It is not a corrected
analysis, evidence of better prediction, a new biological finding, or proof the
paper is wrong. The paper's exact annotation database/release and model settings
remain unconfirmed. R0's current-GEO mapping, ambiguity handling and model defaults
are reconstruction assumptions. A count agreement alone would also be insufficient
to establish gene-identity agreement.

The [public checkpoint](../public/R0_checkpoint.json) contains hashed inputs
and output hashes, with machine paths normalized to repository-relative paths.
The original exact command and execution record remain local. The original pre-fit plan is copied into the
ignored run directory. Full per-probe/per-gene tables and session information are
under `data/processed/pashaei_2025/R0_GSE132903_v1/`; completed runs are protected
against accidental overwrite. The [aggregate result](../public/R0_checkpoint.json) and
[independent implementation checks](R0_verification.json) are reviewable reports.

Independent checks confirmed the row/count summaries, lowest-adjusted-p probe
selection per gene, adjusted-p ranges and five actual AD-minus-control coefficient
calculations. They verify implementation alignment, not scientific truth or exact
equivalence to the authors' unavailable implementation.

## Metadata and original-source QC findings

- GSE118553 has **48 repeated recorded donor × brain-region groups** (47 pairs
  and one triple). These are review candidates, not automatic deletions. The tool
  now distinguishes repeated regions from multiple arrays within the same region.
- The original source study reports **347 post-QC arrays**, including 153 AD and
  79 controls (232 binary arrays), versus 267 binary arrays in the deposited GEO
  labels and target paper's table. Its public preprocessing scripts are available,
  but the required phenotype/RIN inputs and retained/excluded sample manifest are
  absent from the inspected archive. Exact source-faithful removal is unresolved.
  See the [source-QC evidence review](../pashaei_2025_source_qc.md).
- Current annotations expose missing/ambiguous mappings. GPL6244 includes **19
  explicit source-truncation warnings**; partial assignments are retained without
  declaring a complete single-gene mapping. See [mapping summary](../public/mapping_summary.json).
- Many donor identities and cross-study relationships remain unknown. A zero
  detected duplicate count in a dataset with unknown donors is not evidence of
  independent participants. No array was removed merely because donor identity
  was missing.

## Verification and resources

**72 offline tests passed, 0 failed**. The runtime additionally passed a synthetic
limma functional check; the real-data R0 checks above are separate from that test
count. No classifier, five-way gene intersection, or corrected sensitivity variant
was run.

All downloaded files stayed below 250 MB. Combined project-data/runtime storage
was approximately **1.61 GB**, below the original 2 GB limit. Shared hardlinks are
counted once; **196,757,732 bytes** of redundant verified package archives were
removed after offline installation. No global R install or shell startup change was
made. The exact named limma version is matched, not the entire unknown author
environment. The original runtime installation record is preserved locally.

## Next experiment

The objective is evaluation of the data-curation tool. Validate tool findings against
source-reviewed answers and an existing curation workflow first. Any downstream
comparison must follow tool finding → verification → curation decision → fixed
workflow rerun. Preserve R0; no model-family, ranking or hyperparameter search.

For GSE118553, recover a source retained/excluded sample table or the needed QC
inputs before source-faithful filtering. A necessary grouping/split change may
implement a verified donor constraint but must be explicitly declared. Resolve
baseline ambiguities only enough to support a fair curation comparison, without
using published counts or known GSE109887 scores to choose favorable settings.

## Commands executed

```sh
.venv/bin/python scripts/project.py discover --config configs/pashaei_2025.json
.venv/bin/python scripts/project.py preview --config configs/pashaei_2025.json
.venv/bin/python scripts/project.py acquire --config configs/pashaei_2025.json
.venv/bin/python scripts/project.py inventory --config configs/pashaei_2025.json
.venv/bin/python scripts/pashaei_sample_checkpoint.py
.venv/bin/python scripts/acquire_platform_tables.py
.venv/bin/python scripts/pashaei_mapping_checkpoint.py
.venv/bin/python scripts/run_pashaei_checkpoint.py
.venv/bin/python scripts/run_tests.py > reports/test_results.txt 2>&1
```

Environment setup commands, package locks, exact sources and bounded-install checks
are documented in the preserved local runtime report. Current outputs represent completed
work; the next experiments above remain proposed.
