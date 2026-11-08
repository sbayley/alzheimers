# Research decisions

Decisions recorded **2026-11-07–08 America/Los_Angeles**. This public summary
preserves the substantive research and implementation choices; original local
session records remain outside Git.

1. **Evaluate curation tooling.** The question is whether an evidence-preserving
   audit identifies meaningful data issues. The published analysis is a bounded
   case study, not an independent biomarker or classifier development project.
2. **Use bounded local resources.** The core acquisition and audit use Python’s
   standard library. Downloads are sequential, capped at 250 MB per file and 2 GB
   total project data. No controlled-access datasets or large raw sequencing files
   are required.
3. **Acquire from official evidence.** Discover real links from NCBI records and
   directory listings. Record source URLs, timestamps, sizes, hashes and available
   HTTP/version fields. Verified cached files preserve local snapshots; they do
   not prove the remote source remains unchanged.
4. **Preserve originals and ambiguity.** Normalize diagnosis labels only when
   explicit source definitions support them. Unknown fields remain unknown;
   censored ages retain their bounds and units. Never infer donors from accessions.
5. **Count arrays separately from donors.** Repeated regions are measurements, not
   independent people. Retain known control-cohort overlap and unknown relationships
   explicitly; distinct series accessions do not establish independence.
6. **Keep source groups distinct.** Preserve the 134 AsymAD arrays as their own
   legitimate group rather than calling them corrupt or relabeling them controls.
7. **Use the named statistical package.** The numerical reconstruction uses an
   isolated R 4.3.3 runtime and limma 3.56.2. This matches the named limma version,
   not the authors’ entire unknown analysis environment.
8. **Freeze one numerical checkpoint.** Select GSE132903 before numerical fitting
   because it uses one brain region and documented processed values. Preserve R0
   and its pre-fit snapshot rather than tune choices toward the published count.
9. **Report the discrepancy.** The 15,685-versus-11,773 mapped-gene result is an
   unresolved reconstruction gap, not improved prediction or proof of an error.
10. **Review flags before exclusions.** Repeated donor/region groups and truncated
    annotation assignments prompt source review. They do not automatically identify
    a sample to remove or a gene mapping to repair.
11. **Validate the tool before interpreting downstream changes.** Compare findings
    against reviewed evidence and an existing workflow. Each changed analysis must
    follow a verified curation decision while keeping the remaining workflow fixed
    where possible.
12. **Publish a reviewable research repository.** Share software, synthetic tests,
    methods and aggregate checkpoints. Keep expression matrices, specimen-level
    inventories, raw metadata snapshots, runtimes and local logs ignored. Curated
    provenance and numerical summaries identify their source records and any path
    normalization; original local records and frozen run outputs remain intact.
