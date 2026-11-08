# GSE118553 source-study QC: evidence and sample crosswalk

Reviewed 2026-11-08. This is a descriptive source audit for the Pashaei 2025
reconstruction, not a disease-effect analysis or a sample-exclusion decision.

## Result

The original GSE118553 study has public analysis scripts, but the inspected
release contains neither an exclusion manifest nor its input phenotype object.
The public GEO matrix permits exact identification of repeated **recorded
individual × brain-region** groups. It does not supply the RIN and probe-detection
values used by the original script to choose a retained sample. Consequently,
the original 54 removed sample IDs have **not** been recovered. No sample has
been excluded by this audit.

The correct source paper is Patel et al., *Transcriptomic analysis of probable
asymptomatic and symptomatic alzheimer brains*, Brain, Behavior, and Immunity
80 (2019), 644–656, DOI
[10.1016/j.bbi.2019.05.009](https://doi.org/10.1016/j.bbi.2019.05.009),
[PMID 31063847](https://pubmed.ncbi.nlm.nih.gov/31063847/).

## Published reference and observed GEO counts

The full version of record was retrieved from the official
[UCL repository record](https://discovery.ucl.ac.uk/id/eprint/10074994/).
Its results section reports 401 arrays from 112 brains, with 48 duplicate,
four outlier and two sex-discrepancy exclusions, leaving 347 arrays from
111 brains. Table 1 was both extracted and visually inspected on PDF page 4
(printed page 647). The following post-QC counts are from that table; totals
are calculated here.

| Brain region | Control | AsymAD | AD |
|---|---:|---:|---:|
| Entorhinal cortex | 16 | 28 | 34 |
| Temporal cortex | 24 | 28 | 45 |
| Frontal cortex | 21 | 32 | 38 |
| Cerebellum | 18 | 27 | 36 |
| Total arrays | **79** | **115** | **153** |

Supplementary Table 2 is described as per-sample phenotype information, but its
file has not been retrieved. The official publisher article page returned
HTTP 403. A Crossref-listed publisher XML endpoint returned only 1,945 bytes
of bibliographic metadata, without supplement links or full article text.
No supplement filename was guessed or downloaded.

The actual acquired GEO series matrix was independently inspected using
`gzip` and `csv` from the Python standard library. Its original `individual`
and `tissue` characteristics, rather than chip-name conventions, define the
groups below.

| Measurement | Observed |
|---|---:|
| Array/sample columns | 401 |
| Explicit recorded individual labels | 112 |
| AD / control / AsymAD arrays | 167 / 100 / 134 |
| Distinct individual × region groups | 352 |
| Groups with repeated records | 48 |
| Repeated group sizes | 47 pairs; one triple |
| Arrays in repeated groups | 97 |
| Arrays beyond one per group | 49 |
| Repeated groups by AD / control / AsymAD | 11 / 19 / 18 |

Age, recorded gender and disease-state values agree within each repeated group.
One control donor-region group has three arrays. This establishes a repeated
recorded individual/region label, not which specimen should be retained.
Specimen-level identifiers and the detailed crosswalk remain local.

There is a useful mismatch to resolve: the published post-QC table contains
16 entorhinal controls, while the public metadata contains only 15 distinct
individual × region groups in that category. Selecting one public record per
group cannot recreate that table. The release's instruction to remove only
one ranked record from each repeated group could leave two records in a triple,
but its unavailable `Study_ID` input has not been crosswalked to GEO's
`individual` values. That is a possible explanation, not a verified history.

Pashaei 2025 Table 4's GSE118553 binary count, 167 AD + 100 controls = 267,
equals the unfiltered public GEO diagnosis counts. The original source table's
post-QC binary total is 232. These are concrete count differences; they do
**not** establish which GSMs Pashaei used or prove that its authors omitted QC.

## What the public source code actually provides

The source paper links
[Zenodo DOI 10.5281/zenodo.1400644](https://doi.org/10.5281/zenodo.1400644).
The retrieved metadata identifies `hamelpatel/MRC-LBB v1.0.0`, published
2018-08-20, with a single 47,545-byte archive. The release corresponds to
[commit 37dea9d39f5d11479803991d1fbcb4a0370a2c42](https://github.com/hamelpatel/MRC-LBB/tree/37dea9d39f5d11479803991d1fbcb4a0370a2c42).
Both the versioned GitHub tree and current root listing contain seven R scripts
and a README, without phenotype tables or sample manifests. This is **Patel's
source-study code**, not the still-requested Pashaei 2025 implementation.

Static review of `1.Preprocess_data.R` found:

| Lines | Evidence |
|---|---|
| 65–78 | Loads `mrc_brains.eset_bg_log2_rsn_combat_adj.RData`, then obtains expression and phenotype objects. The archive does not contain this input. |
| 111–142 | Identifies repeated `Study_ID × Brain_Region` groups. Comments identify phenotype columns 6 and 43 as RIN and detected-probe count; it sorts descending and adds **the second-ranked row only** to the removal list. No GSM removal list is hardcoded. |
| 146–305 | Uses massiR Y-probe-based predictions, compares them with recorded gender, then removes samples for study IDs whose samples all disagree. Actual choices depend on input objects absent from the release. |
| 1098–1169 | Performs iterative WGCNA connectivity-based outlier removal within tissue × diagnosis groups. The actual function calls use threshold **−3**, despite nearby comments mentioning −2. |
| 1285–1347 | Maps using `illuminaHumanv4.db`; after ambiguity handling, selects among repeated Entrez identifiers using highest mean expression. This is different from Pashaei's reported smallest-adjusted-P probe rule. |
| 1362–1388 | Writes `MRC-LBB_expression_table_QCd.txt`, `MRC-LBB_phenotype.txt` and `MRC-LBB_processing.Rdata`. None is distributed in the inspected release. |

See the
[versioned preprocessing script](https://github.com/hamelpatel/MRC-LBB/blob/37dea9d39f5d11479803991d1fbcb4a0370a2c42/1.Preprocess_data.R).
No downloaded R code was executed. Its ZIP was inspected in memory with
`zipfile`: 263,085 total uncompressed bytes, no absolute/traversal/symlink
entries, and bounded entry-count and expansion checks. No archive extraction
was needed.

## Local evidence and provenance

All downloaded sources and derived crosswalks are ignored project data under
`data/raw/pashaei_sources/`; no core inventory or normalized sample table was
changed. The bounded `alzresearch.acquisition.download` API recorded exact
URLs, retrieval UTC, bytes, SHA-256 and HTTP metadata in each download's
`.provenance.json` sidecar. Downloads used caps no larger than the project's
250 MB/file and 2 GB total limits; individual discovery requests used smaller
caps and no retries.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `zenodo_1400644.json` | 3,751 | `9f746e4351d4bc2065b7e45002aaceb2b7eeb96bab767ddbd8da973447ed96ee` |
| `MRC-LBB-v1.0.0.zip` | 47,545 | `8745b4c74584bfc2cd0be3cab97866b9b3852f6cd4476bbeb92c63f9ba2ff6a7` |
| `Patel_2019_GSE118553.pdf` | 2,552,103 | `0ad0345e132a2e181ade3cbd42fdff36ec8623d0e9d597e8ab7fad5e3766264d` |
| `GSE118553_same_individual_region_groups.csv` | 42,360 | `0bdcb069b72f518a3d33882df474596d75c3234e0b64340caa5cb22a628f4187` |

The derived CSV has all 401 GSMs, original title/individual/region/diagnosis/
age/gender values, group size, and `source_removed_sample_known=unknown`.
Its input is `data/raw/GSE118553/GSE118553_series_matrix.txt.gz`, 149,479,055
bytes, SHA-256
`2b039a1c0edb9f2adb7034ecdf26d824b235b826370df102b9327f5e3095432b`.
`Patel_2019_GSE118553_extracted.txt` and `Patel_2019_table1.png` preserve the
text extraction and inspected table rendering.

Additional verified request URLs:

- [Zenodo metadata](https://zenodo.org/api/records/1400644)
- [Exact archive link from that metadata](https://zenodo.org/api/records/1400644/files/hamelpatel/MRC-LBB-v1.0.0.zip/content)
- [Versioned GitHub tree](https://api.github.com/repos/hamelpatel/MRC-LBB/git/trees/v1.0.0?recursive=1)
- [Current GitHub file listing](https://api.github.com/repos/hamelpatel/MRC-LBB/contents/)
- [Crossref record](https://api.crossref.org/works/10.1016/j.bbi.2019.05.009)
- [PubMed XML](https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=31063847&retmode=xml)

The retrieved PubMed XML was checked for the exact PMID and title. It contains
no `CommentsCorrections` entries and no retraction/correction publication type;
Crossref has no `update-to` field. This is a visible-record check on the review
date, not a guarantee that no notice exists elsewhere. PubMed's web rendering
was incomplete, and bioRxiv/publisher web requests were inaccessible.

Verification used static ZIP reads, standard-library metadata counting,
bundled `pypdf` text extraction and `pdftoppm` rendering of page 4. No disease
model, inferential test or author-code execution was performed for this audit.

## Consequence for reconstruction

Preserve a Pashaei-count reconstruction as a separately labelled attempted
reproduction. Before calling a variant **source-QC-faithful**, recover a public
retained-sample phenotype table or exact exclusion manifest and crosswalk it
to GSMs; RIN/detection inputs and the original study-ID relation would resolve
the current ambiguity. Any one-per-individual/region rule chosen without those
inputs must be reported as our sensitivity analysis with an explicit selection
rule. Donor-grouped evaluation is also necessary across different regions of
the same recorded individual, independently of technical-repeat choices.
