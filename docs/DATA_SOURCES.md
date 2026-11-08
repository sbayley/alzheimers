# Sources and evidence log

Search date: **2026-11-07 America/Los_Angeles**. Retrieval may have a 2026-11-08 UTC timestamp. This is a targeted feasibility search, not a systematic review. Aggregate counts and provenance belong in `reports/dataset_inventory.json` and `reports/metadata_quality.md`. Sample-level fields and source evidence are kept locally in the ignored `data/processed/sample_inventory.json` and `data/processed/samples.csv`; published counts below are distinguished from those local observations.

## Seed records

| Source | Verified source description | Relevant files and limits |
| --- | --- | --- |
| [GSE48350 official GEO record](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE48350) | GPL570 expression arrays; postmortem bulk brain from four regions; source lists 253 samples. Young controls are present. Record says controls are also in GSE11882 and cases with multiple regions were preferred. | Series Matrix / SOFT / MINiML available; processed data are in sample tables. RAW TAR about 1.2 GB is excluded. Exact selected filenames and bytes must come from the official directory listing and acquisition manifest. |
| [GSE5281 official GEO record](https://ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE5281) | GPL570 expression arrays; laser-capture neuronal compartment from six regions; source lists 161 samples. These are not equivalent to bulk tissue on the same platform. | Series Matrix and `GSE5281_sample_characteristics.xls` (83.5 KB listed). RAW TAR about 965.9 MB is excluded. |
| [GSE132903 official GEO record](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE132903) | GPL10558 Illumina HumanHT-12 v4 bulk middle temporal gyrus BA21; source lists 195 samples, 97 AD and 98 non-demented. | Series Matrix; normalized XLSX about 103.1 MB; non-normalized TXT.GZ about 14.0 MB. Do not substitute non-normalized values for processed values without an explicit analysis plan. |

Direct web-reader requests to GEO encountered an NCBI browser-check page; official indexed records initially exposed these details. The acquisition process subsequently retrieved the full series-level SOFT text records and official matrix-directory listings: `data/raw/<accession>/series_record.soft.txt` and `matrix_directory.html`. Their hashes, retrieval times, exact URLs and parsed source fields are preserved in `registry/dataset_manifest.json`. That local evidence is stronger than the initial search excerpt. It remains separate from a full-paper review.

Actual completed transfers: GSE48350 processed matrix **60,194,969 bytes**; GSE5281 matrix **35,937,055 bytes**; GSE132903 matrix **41,956,695 bytes**; GSE5281 sample-characteristics XLS **85,504 bytes**. These four files total **138,174,223 bytes**, excluding source snapshots and provenance sidecars. The alternative GSE132903 normalized XLSX, non-normalized file and raw archives were not acquired. File transfer and format checks do not by themselves establish analytical usability.

The first official GPL570/GPL10558 SOFT requests exceeded an extra
**2,000,000-byte discovery-record cap**. On the owner's requested retry, platform
requests used the existing **250,000,000-byte normal file ceiling** and both
succeeded: GPL570 **6,144,861 bytes**, GPL10558 **3,691,132 bytes**. Original failures
are retained in each manifest record's `previous_attempts`; new transfers and
hashes are in `registry/platform_acquisition_run.json`. Local sources are
`data/raw/platforms/GPL570.soft.txt` and `GPL10558.soft.txt` with provenance sidecars.
The full downloaded brief responses were inspected; neither contains a probe/gene
annotation table. Declared feature totals in metadata are not observed annotation
rows. See `reports/platform_inventory.json` and `reports/platform_metadata.md`.

The local parser inspected **609 arrays** (253 / 161 / 195 respectively), agreeing with the series records. These are not 609 established independent people. The current metadata review finds explicit GSE48350 individual fields for controls but lacks equivalent verified AD-donor fields; the total donor count remains unknown. The GSE5281 XLS has 161 sample rows plus a header and no reviewed person-level donor identifier. GSE132903 includes **11 right-censored `90+` ages**; these must not be silently converted to exact age 90. See the generated quality report for final mapping details and missingness.

## Original publications and reading scope

| Publication | What was inspected this session | Use and remaining work |
| --- | --- | --- |
| [Liang et al. 2008, DOI 10.1073/pnas.0709259105, PMC2393743](https://pmc.ncbi.nlm.nih.gov/articles/PMC2393743/) | Open full-text record; abstract, results and relevant tissue/methods sections. | A specific energy-metabolism result in posterior-cingulate neurons is a potential replay target. Recover the exact probe/gene list, original model and sample exclusions before calling anything a replication. |
| [Berchtold et al. 2013, PMID 23273601](https://pubmed.ncbi.nlm.nih.gov/23273601/) | PubMed abstract and visible figure captions. PMC full text was blocked by browser check. | Paper reports a selected synaptic-gene analysis across aging/AD and multiple regions. Its reported case count must not be substituted for unique donor counts in the entire GEO release. Full methods and supplements remain to inspect. |
| [Piras et al. 2019, PMID 31256118 / DOI 10.3233/JAD-181113](https://pubmed.ncbi.nlm.nih.gov/31256118/) | GEO description and publication identity; publisher DOI request failed and PubMed text was incomplete. | Original methods, supplements, donor links and validation-cohort independence remain unverified. No claim of full-paper review. |

Visible correction/retraction check: searched each of the three DOIs with `correction retraction`; inspected the accessible Liang article for linked notices / the string `Errat`. No correction or retraction notice was visible in the material retrieved. This limited check is **not** evidence of absence; recheck publisher/Crossmark and PubMed linked notices before selecting a biological claim for replication. It does not certify papers or secondary reuse studies.

## Cohort relationships

`registry/cohort_relationships.json` records relationship status separately from expression compatibility. GSE48350/GSE11882 share controls according to the GEO record. All three seed-pair donor relationships remain `unknown`: different GSM identifiers, different dates or matching platform labels cannot establish independence. Shared investigators or brain-bank networks would be a lead for checking donor records, not proof of overlap. Within-series sampling of multiple brain regions makes donor-level linkage essential.

## Additional primary sources searched

- [AD Knowledge Portal access policy](https://help.adknowledgeportal.org/apd/access-data): public browsing; Synapse registration for public downloads; additional approval for individual-level human data. No account was created and no controlled access was requested.
- [Agora resource documentation](https://help.adknowledgeportal.org/apd/agora-resources) and [RNA evidence methods](https://help.adknowledgeportal.org/apd/rna-expression-data-and-methods): curated results for target evidence, with explicit cohort/region/model documentation. Agora evidence is not an independent new participant cohort.
- [SEA-AD official data page](https://brain-map.org/consortia/sea-ad/our-data), [AWS open-data registry](https://registry.opendata.aws/allen-sea-ad-atlas/), and [Allen multiregion release description](https://github.com/AllenInstitute/abc_atlas_access/blob/main/descriptions/SEA-AD-Multiregion-10X.md): open processed resources and small donor metadata; current release size constrains feasible work.
- [NIAGADS open access](https://www.niagads.org/open-access/) and [current dataset catalog](https://dss.niagads.org/datasets/): resource- and file-specific access status, rather than assuming the entire repository is unrestricted.
- [GWAS Catalog GCST90027158](https://www.ebi.ac.uk/gwas/studies/GCST90027158): browser-readable page was an unpopulated application shell; the listed FTP directory could not be opened through the web reader. Actual file size, current terms and anonymous transfer remain unverified in this session.
- [GEOquery](https://www.bioconductor.org/packages/release/bioc/html/GEOquery.html), [MetaSRA](https://metasra.platformx.wisc.edu/supportpages/about.html), [MetaSRA pipeline](https://github.com/deweylab/MetaSRA-pipeline), [healthyControlsPresenceChecker](https://www.bioconductor.org/packages/release/data/experiment/html/healthyControlsPresenceChecker.html), [limma](https://bioconductor.org/packages/release/bioc/html/limma.html): existing acquisition, annotation, label checking and statistical workflows. Their existence prevents treating generic parsing, metadata normalization or differential expression as a new contribution by themselves.

Representative exact searches: `site.ncbi.nlm.nih.gov/geo "GSE48350" "Overall design"`; analogous GSE5281/GSE132903 searches; `SEA AD data access AWS Allen brain map`; `site.help.adknowledgeportal.org agora download data`; `MetaSRA metadata normalization source repository`; `site.bioconductor.org healthyControlsPresenceChecker`; each original DOI plus `correction retraction`. Search coverage and reading scope are incomplete.

## 2026-11-08 reproduction follow-up

All six Pashaei 2025 matrices are now acquired, including GSE36980, GSE118553 and
GSE109887. Complete `view=full` official SOFT tables were acquired for GPL570,
GPL6244, GPL10558 and GPL10904; those are separate files from the earlier brief
metadata responses. Exact transfers/annotation versions and observed table counts
are summarized in [public source provenance](../reports/public/data_provenance.json).
Detailed source-record manifests remain local. Current-GEO mapping is an
explicit reconstruction assumption, not confirmed target-author annotation.

The target [paper](https://doi.org/10.3390/ijms26051816) provides reported sample
and gene-count checkpoints. [Methods review](../reports/pashaei_2025_methods_audit.md)
records available details and unresolved choices. The
[source-QC review](../reports/pashaei_2025_source_qc.md) documents retrieval of the
original GSE118553 study and static inspection of its public scripts; no source
author code was executed. The target implementation remains unavailable.
Actual numerical results and provenance are separate from these
source claims in the [progress report](../reports/pashaei_2025/progress.md).
