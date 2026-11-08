# Annotation sources for the Pashaei 2025 reconstruction

Historical source review. The four full tables have since been acquired and
inspected; see [public provenance](public/data_provenance.json) and
[mapping coverage](public/mapping_summary.json).

Research date: **2026-11-08 America/Los_Angeles**. This is a source and mapping
feasibility review, not a completed probe-to-gene mapping or a reproduction result.
No data files, packages or code were downloaded by this source review.

## Main finding

The paper describes a Bioconductor `annotation` package at version `1.30.0`, but
that description does not uniquely identify the chip annotation database, release,
identifier type or handling of one-to-many mappings. It also describes selecting
the probe with the smallest adjusted p-value when several probes correspond to a
gene. Exact mapping choices are therefore a reproduction dependency, not an
implementation detail that can safely be guessed. [Paper, section 4.2](https://www.mdpi.com/1422-0067/26/5/1816)

Until the authors clarify, label any numerical run as a **documented reconstruction**
with an explicit annotation source/version. Do not pick a mapping merely because
it produces the published 803-gene intersection. A current GEO table and a selected
Bioconductor chip database are different, defensible source choices to compare;
neither has yet been established as the authors' exact input.

## Platform-specific evidence

| Platform | Verified identifier/table structure | Implication for our datasets |
|---|---|---|
| [GPL570](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GPL570) | Affymetrix HG-U133 Plus 2.0; platform table includes `ID`, `Gene Symbol`, Entrez IDs and other fields. The official table shows that one probe can have multiple symbols separated by `///`. | GSE48350/GSE5281 probe IDs require an explicit probe-to-gene mapping rule. Preserve every mapped candidate and count ambiguity before applying any collapse rule. |
| [GPL6244](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GPL6244) | Human Gene 1.0 ST, transcript/gene version. `ID` means transcript-cluster identifier. `gene_assignment` is multipart, with accession, symbol and other components; separate assignments use `///`. The source declares 33,297 table rows and approximately 97,019 Kbytes for its full uncompressed table. | GSE36980 needs transcript-cluster mapping. A parser expecting a simple `Gene Symbol` column would be wrong for the displayed original table. A cluster can map to multiple genes. |
| [GPL10558](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GPL10558) | Illumina HumanHT-12 V4.0 probe platform. The project’s already retrieved brief record links R1 and R2 manufacturer annotation files and records an R2 update. | GSE132903/GSE118553 need identifier-specific checks: `ILMN_...` probe IDs and numeric array-address IDs are not interchangeable. Retain the key type and mapping source. |
| [GPL10904](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GPL10904) | The title explicitly identifies a **gene-symbol** platform. `ID` is an internal gene symbol and `ORF` repeats a gene symbol. The official record declares 34,695 rows and approximately 586 Kbytes for the full table. | GSE109887 may already use gene-symbol rows. Inspect the acquired matrix IDs before applying any probe mapper. Older symbol strings must not silently be replaced or collapsed. |

These table sizes are source-displayed estimates, **not measured HTTP transfer
bytes**. The downloaded matrix may contain a filtered subset of its platform, so
matrix/platform row-count differences alone do not establish an error. The table
descriptions above were read from indexed official GEO content; direct browser
opens encountered NCBI browser checks.

## Official acquisition leads

GEO's public records and [programmatic-access documentation](https://www.ncbi.nlm.nih.gov/geo/info/geo_paccess.html)
identify the official platform-file hierarchy. The platform base directories to
inspect with the project's bounded downloader are:

- `https://ftp.ncbi.nlm.nih.gov/geo/platforms/GPLnnn/GPL570/`
- `https://ftp.ncbi.nlm.nih.gov/geo/platforms/GPL6nnn/GPL6244/`
- `https://ftp.ncbi.nlm.nih.gov/geo/platforms/GPL10nnn/GPL10558/`
- `https://ftp.ncbi.nlm.nih.gov/geo/platforms/GPL10nnn/GPL10904/`

**Directory-listing verification was deferred to the acquisition workflow.** The web
reader could not open these FTP-over-HTTPS listings. No `soft/` or `annot/` file
name is asserted here as a currently listed file. Follow actual official hrefs,
record HEAD metadata when available, and enforce 250 MB/file and 2 GB project-data
limits while streaming, including unknown lengths.

Two exact supplemental file URLs are already named in the project's retrieved
GPL10558 brief source record; they are useful verified filename leads, but their
current response sizes and contents remain unverified during this review:

- [GPL10558 manufacturer R1 annotation](https://ftp.ncbi.nlm.nih.gov/geo/platforms/GPL10nnn/GPL10558/suppl/GPL10558_HumanHT-12_V4_0_R1_15002873_B.txt.gz)
- [GPL10558 manufacturer R2 annotation](https://ftp.ncbi.nlm.nih.gov/geo/platforms/GPL10nnn/GPL10558/suppl/GPL10558_HumanHT-12_V4_0_R2_15002873_B.txt.gz)

The official GEO display also supports full-record/table views. A full SOFT view
is distinct from the already acquired `view=brief` metadata-only responses. The
web reader could not fetch full SOFT query responses in this review, so no full
table transfer is recorded as successful.

GEO distinguishes original submitter records from its annotation SOFT files,
which provide updated platform annotation. That distinction matters for a
historical reproduction. [Official GEO DataSets documentation](https://ncbi.nlm.nih.gov/geo/info/datasets.html)

## Established Bioconductor options

These are verified existing resources, **not a claim that Pashaei used them**:

| Platform | Official chip database | Evidence and version caution |
|---|---|---|
| GPL570 | [hgu133plus2.db](https://bioconductor.org/packages/release/data/annotation/html/hgu133plus2.db.html) | Official package identifies the HG-U133 Plus 2.0 chip and exposes historical Bioconductor release links. Record both this package and its annotation-source metadata. |
| GPL6244 | [hugene10sttranscriptcluster.db](https://bioconductor.org/packages/release/data/annotation/html/hugene10sttranscriptcluster.db.html) | Official transcript-cluster annotation package. It is a different granularity from similarly named probeset packages. |
| GPL10558 | [illuminaHumanv4.db](https://bioconductor.org/packages/release/data/annotation/html/illuminaHumanv4.db.html) | Official HumanHT12v4 annotation resource. Check available key types and actual matrix identifiers before selection. |
| GPL10904 | No additional probe mapper selected | Source IDs are gene symbols; any alias-resolution/updated-symbol pass should be an explicit, versioned variant rather than an invisible baseline transformation. |

The official [AnnotationDbi manual](https://www.bioconductor.org/packages/release/bioc/manuals/AnnotationDbi/man/AnnotationDbi.pdf)
documents distinct key types and one-to-many results. In particular, `mapIds()`
defaults to the first returned match, while options can retain lists, mark
ambiguous results missing or filter them. A default-first result is a software
choice, not evidence that a biological mapping is unambiguous. Save the mapping
cardinality and the chosen rule.

## Decisions required before a numerical baseline

1. Acquire and hash complete official tables or explicitly selected chip-database
   sources; retain version dates and all original identifier fields.
2. Verify coverage using actual matrix IDs, not platform title alone. Report
   unmapped IDs, multi-gene assignments, duplicate symbols and controls separately.
3. Establish whether the authors adjusted p-values over probes before gene
   collapsing, or over genes after collapsing; document any reconstruction choice.
4. Specify how several probes per symbol are reduced, how ties are broken, and
   how a single probe assigned to several genes is treated. The paper's
   minimum-adjusted-p rule does not resolve all these cases.
5. Keep published-method reconstruction separate from alternative summaries such
   as averaging probes, excluding ambiguous mappings or updating aliases. For
   prediction, outcome-based gene/probe selection in a revised evaluation must
   be confined to the corresponding development data/folds.
6. Treat an initial count mismatch as a diagnostic checkpoint. Compare mapping
   versions, filtering order, identifiers and transform assumptions before drawing
   conclusions about the paper or the audit tool.

## Reading scope and remaining uncertainty

This review inspected official GEO indexed record/table descriptions, official
Bioconductor package pages and the AnnotationDbi manual. The paper's annotation
description was available in retrieved indexed methods text and prior project
source review; executable author code has not been verified. No complete mapping
table was locally inspected here, no download sizes were measured, and no
differential-expression/model result was generated. Source availability does not
establish an exact historical match or compatibility across platforms.
