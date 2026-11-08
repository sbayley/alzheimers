# Pashaei 2025 reproduction feasibility: methods audit

Historical feasibility review. Acquisition and one numerical reconstruction are
now complete; see the [current progress report](pashaei_2025/progress.md).

Review date: **2026-11-08 America/Los_Angeles**. This is a source/methods audit,
not an executed reproduction or judgment that the target contains errors.

Target: [Pashaei et al., 2025, DOI 10.3390/ijms26051816](https://www.mdpi.com/1422-0067/26/5/1816).
Primary alternatives for locating the manuscript:
[PMC11898513](https://pmc.ncbi.nlm.nih.gov/articles/PMC11898513/) and
[Indiana University deposited publisher PDF](https://scholarworks.indianapolis.iu.edu/bitstreams/e7c28555-30c7-42a2-8eec-f3e03b581eaa/download).

## Published checkpoints to test

The following are **reported** targets, not locally reproduced results or verified
unique-person counts. The paper labels the first five as training/development data.
Values below are transcribed from Table 4 and sections 2.1–2.2; compare sample IDs
and gene identities as well as counts whenever intermediate tables become available.

| GEO accession | Paper platform | AD / control arrays | Total arrays | Reported significant genes |
|---|---|---:|---:|---:|
| GSE48350 | GPL570 | 80 / 173 | 253 | 9,010 |
| GSE36980 | GPL6244 | 33 / 47 | 80 | 4,191 |
| GSE132903 | GPL10558 | 97 / 98 | 195 | 11,773 |
| GSE118553 | GPL10558 | 167 / 100 | 267 | 6,516 |
| GSE5281 | GPL570 | 87 / 74 | 161 | 10,003 |
| GSE109887 (testing) | GPL10904 | 46 / 32 | 78 | Not a development DEG target |

Further targets: five-way intersection **803** genes; **95** consistently increased,
**522** consistently decreased and **186** variable in direction. The abstract's
50-gene logistic-regression result is AUC **0.868**. Table 2 also reports **0.871**
for 40 genes and compares 10–100 gene panels across four classifiers. Preserve
these as distinct reported checkpoints; do not choose a revised configuration by
which one yields the most favorable result.

## What is specified and what is unresolved

The retrieved methods name limma **3.56.2**, BH-adjusted FDR below **0.05**, a
lowest-adjusted-p probe choice per gene symbol, four ranking streams (RF, DISR,
degree and bottleneck), rank aggregation, and four classifiers. That outlines the
pipeline but is not an executable specification. The source points to GEO data;
no author-code link was located in the material reviewed. The exact target
implementation and historical settings remain unavailable.

| Decision needed for reproduction | Current evidence / uncertainty | Required action |
|---|---|---|
| Exact sample eligibility | The target gives class totals. Deposited sample membership and source-study QC may differ. | Freeze sample-ID lists and source category definitions; request target inclusion/exclusion list. |
| Gene/probe mapping | The methods call the package “annotation” v1.30.0 without a resolved platform-specific mapping release in our review. Blank/multi-symbol probes and tie handling are not yet established. | Acquire actual annotations with provenance; establish gene namespace/version, mapping ambiguity and tie rules. |
| Probe testing/collapse order | Lowest adjusted-p probe selection is reported, but exact filtering, tested universe and timing of symbol collapse/FDR need reconstruction. | Preserve probe-level output and explicitly record the sequence; do not tune it to match counts. |
| Processed scale/transformation | Our existing matrices span different numeric ranges and have differing source processing. A single comparable pooled scale is not established. | Verify per-dataset scale from primary processing metadata and code; no arbitrary shared transform. |
| Design/contrast/covariates | An AD/control comparison is stated; exact design formula, reference coding, age/sex/region adjustment, repeated-donor handling and default moderation settings have not been established. | Recover code/settings or mark assumptions in a labeled historical reconstruction; retain independence limitations. |
| Tissue/region/compartment handling | The public sources include multiregion bulk tissue and captured neurons. Shared platform labels do not make those observations interchangeable. | Reconcile target sample use; define any restricted/adjusted model as a separate sensitivity. |
| Pooling before RF/DISR | A combined development expression matrix is described, but harmonization, batch/scale handling and exact sample/gene ordering are unresolved. | Do not start pooled model selection until the matrix construction can be specified and audited. |
| Network/ranking reproducibility | Network releases/settings, identifiers, tie behavior, RF/DISR parameters, rank aggregation and randomness can affect results. | Record versions and recover exact settings/intermediates; do not silently replace a historical network with its latest release. |
| Classifier evaluation | The same named test dataset appears in many reported panel/classifier comparisons. Exact training, scaling and classifier settings remain unresolved. | Treat it as a published benchmark; freeze our decisions without optimizing on it. New generalization claims need suitable independent evaluation evidence. |

## Source-study QC lead: GSE118553

The official [GEO/BioProject record](https://www.ncbi.nlm.nih.gov/gds?LinkName=bioproject_gds&from_uid=486003)
lists **401 samples** and distinguishes control, asymptomatic AD and symptomatic AD.
The [original study's deposited publisher manuscript](https://discovery.ucl.ac.uk/id/eprint/10074994/7/Dobson_Transcriptomic%20analysis%20of%20probable%20asymptomatic%20and%20symptomatic%20alzheimer%20brains_VoR.pdf)
(*Transcriptomic analysis of probable asymptomatic and symptomatic Alzheimer brains*,
[DOI 10.1016/j.bbi.2019.05.009](https://doi.org/10.1016/j.bbi.2019.05.009),
PMID 31063847) reports source QC removing **48 duplicate samples, four outliers and two sex
discrepancies**, retaining **347 tissue arrays from 111 brains**. Its data-availability
section links analysis scripts at [Zenodo DOI 10.5281/zenodo.1400644](https://doi.org/10.5281/zenodo.1400644).

This is a **lead for an exact sample-ID crosswalk**, not a conclusion that the
target included known bad samples. Reconcile deposited versions, source-QC lists,
clinical categories and target eligibility. Do not subtract source exclusion
counts mechanically or label AsymAD data erroneous. The availability of source
study scripts does not establish availability of the target paper's full pipeline.

The other missing target series have official source descriptions compatible with
bounded processed-data inspection: [GSE36980](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE36980)
lists 80 multiregion arrays and [GSE109887](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE109887)
describes 78 MTG arrays. Actual transfers and current sample labels remain the
acquisition workflow's responsibility. These historical source notes preceded
the completed transfers recorded in the [progress report](pashaei_2025/progress.md).

## Smallest useful next result

First resolve a **single development dataset's** sample membership, scale and
annotation. Then use established limma in an isolated R environment to produce
a documented per-probe/per-gene checkpoint, subject to the
[prospective plan](../plans/pashaei_2025_reproduction.md). Stop with a clear method
gap if those inputs cannot be specified. Comparing a DEG count alone is weaker
than comparing the actual mapped gene list.

Further numerical checkpoints are conditional on a source-reviewed curation
finding and frozen comparison rules; they are not an independent classifier
development goal. A missing donor ID is unresolved evidence, not proof of
duplication or an instruction to exclude a sample.

## Reading scope, search record and limitations

- This project reviewed the primary manuscript's indexed abstract/results/methods
  sections 2.1–2.4 and 4.1–4.8 and tables 2/4 during the preceding methods checks.
  This follow-up rechecked indexed primary text for the intersection/direction and
  ranking stages. It is not a line-by-line executable-code review.
- Direct publisher access returned HTTP 429 during this follow-up, and direct
  university PDF access timed out in the web reader. The indexed primary manuscript
  supplied the relevant text; no claim is made that a complete fresh PDF was
  downloaded and inspected in this review.
- The original GSE118553 publisher PDF's indexed processing/results and data
  availability sections supplied its source-QC/script lead. The script archive
  itself has not been inspected or executed during this review.
- Exact searches included the DOI plus `annotation`, the paper title plus
  `803 95 522`, the title plus `4.5`, and the official GEO accessions. Primary
  GEO/NCBI records and the UCL deposited original manuscript were used for the
  sample/QC source checks. Searches were performed on 2026-11-08.
- Earlier project notice checks did not find a visible correction/retraction in
  the retrieved material. No comprehensive publisher/Crossmark/PubMed notice audit
  has been completed here; recheck linked notices before finalizing a scientific
  replication claim. No absence-of-code or absence-of-correction claim is proved
  by a failed search.

No datasets, code, models or statistical tests were downloaded/executed by this
documentation review. These files distinguish published claims, local pre-existing
audit evidence, proposed methods and unresolved reproduction details.
