# Pashaei 2025: reproduction and metadata-sensitivity plan

Plan date: **2026-11-08 America/Los_Angeles**. This is the current evaluation
plan, edited for public presentation after R0. An immutable pre-fit snapshot was
saved with R0; its hash remains in the [public checkpoint](../reports/public/R0_checkpoint.json). Current execution
results are in the [progress report](../reports/pashaei_2025/progress.md).
This is an exploratory data-curation evaluation with a reproduction/robustness
case study, not a registered biological hypothesis or a claim that the paper is wrong.

Target: Pashaei, Pashaei and Aydin, *Biomarker Identification for Alzheimer's
Disease Using a Multi-Filter Gene Selection Approach*, DOI
[10.3390/ijms26051816](https://doi.org/10.3390/ijms26051816).
The [methods audit](../reports/pashaei_2025_methods_audit.md) records the exact
reported checkpoints, sources, reading limits, and unresolved implementation details.

## Questions and boundaries

**Scope clarification, 2026-11-08:** recorded after R0 and before any curation
variant. The objective is to evaluate the data-curation tool; unrelated
prediction optimization is outside the research scope.
The original R0 and its immutable pre-fit plan snapshot remain unchanged.

1. Does the tool correctly identify data-curation issues and preserve their evidence?
2. Can enough of the published workflow be reconstructed to keep a comparison fixed?
3. What consequences follow from source-verified curation decisions prompted by the tool?

The first question is primary. Reconstruction supports a fair downstream case
study; a changed gene list or AUC alone does not validate the tool. Unrelated
classifier/feature-ranking development, hyperparameter searches and new biological
discovery projects are out of scope. Investigate baseline ambiguities only as needed
for the curation comparison; if they cannot be resolved, record the limitation or
choose a better-documented case study rather than optimize the reconstruction.

Keep baseline reconstruction and reviewed curation variants in separate configurations,
outputs, and decision records. Preserve raw matrices, source metadata and hashes.
All work remains free, local and CPU-friendly under AGENTS.md's existing limits.
This analysis plan does not require raw sequencing, imaging, paid services or
expanded download limits. Raw and sample-level data remain local. Public sharing
covers code, methods and selected aggregate reports; the target implementation
and historical settings remain unavailable.

## Analysis units, labels and eligibility

- Inventory unit: a GEO sample/array. Report published array totals separately
  from verified donor counts. Keep explicit donor identities scoped to their source
  unless a reviewed cross-study relationship supports a common namespace.
- Biological unit: donor when established. Never invent unique donors for unknown
  identities, treat repeated regions as independent people, or call distinct GEO
  accessions independent cohorts without evidence.
- Retain explicit AD/control source labels for the paper's comparison. Asymptomatic
  AD is a distinct source category, not an automatic control or corrupted sample.
  Record its eligibility separately. Do not force current GEO counts to match the
  published totals by guessing exclusions.
- Freeze an accession-level and sample-level inclusion table, including original
  label, normalized label/rule, brain region, compartment, source-QC status and
  reason for any exclusion, before numerical fitting.
- Audit source QC and sample lineage in development **and** evaluation datasets.
  In particular, resolve which GSE118553 release/sample subset the target used and
  compare it with the original source's QC/exclusion records. Discovery of an
  excluded source sample is a review lead, not proof it was misused by the target.

## Phase A: source and environment gate

Complete these before fitting:

1. Acquire the six target datasets and relevant annotation tables from verified
   official records; retain each retrieval URL, UTC timestamp, bytes, SHA-256 and
   available version/HTTP information. Record selected files rather than assuming
   every deposited file belongs in the published analysis.
2. Reconcile observed sample/feature counts with the target's tables and original
   source QC. Identify stale annotations, multimap/blank gene identifiers, duplicates,
   source-defined omitted samples and processing differences without altering inputs.
3. Establish each processed matrix's scale and transformation from source evidence.
   Do not add log2 transformations merely to approach a reported result or apply a
   single heuristic transformation to incompatible datasets.
4. Use an isolated R/Bioconductor environment and the established limma workflow
   for numerical fitting; preserve its session/package versions. R was absent at
   the initial environment inspection. Do not substitute a handwritten test to
   claim faithful limma reproduction.
5. Resolve or enumerate the probe annotation release, feature universe, filtering,
   duplicate-symbol/tie rules, model design, contrast, missing-value handling and
   moderation settings. Obtain author code/settings if available. Any unresolved
   choice must remain explicit; label a run a reconstruction rather than an exact
   reproduction when its numerical inputs/settings cannot be matched.

## Phase B: smallest executable numerical checkpoint

Begin with **one development dataset**. The initial candidate was GSE48350; before
any numerical fitting, the pilot was switched to **GSE132903** because its provided
lumi VST/quantile-processed matrix is documented and uses one brain region. GSE48350
has unresolved ratio-scale/transform choices and explicit multiregion control-donor
dependence. This switch was made for input interpretability, not numerical agreement.
Freeze matrix hash, sample inclusion and probe mapping before fitting.

Pilot reconstruction R0 (frozen before fitting): use all 195 explicit AD/control
arrays (97 AD, 98 control), the provided processed values without further transform,
an unadjusted two-group limma model, AD minus control, default non-robust/non-trend
eBayes moderation, and BH correction over all tested probe rows. Use limma3.56.2.
Map using the acquired current GPL10558 full GEO table, retain only unambiguous
single-symbol mappings, then select the lowest adjusted-p probe per symbol, breaking
ties by raw p then probe ID. This mapping release/ambiguity policy and model defaults
are **explicit reconstruction assumptions**, not confirmed author settings. Missing
donor identities and absent covariates remain limitations. Report source/current
mapping coverage and compare against 11,773 reported genes without tuning choices.

The first output is a complete per-probe and per-gene result table plus a checkpoint
comparison against the target, not a novel biomarker panel. The exact paper-like
design is unresolved. If an array-level `AD versus control` computation is used to
reconstruct a published output, label it a **historical numerical reconstruction**:
it must not be presented as valid donor-level inference when dependence is unresolved.
Do not silently improve its model and still call it the unmodified baseline.

For every implemented design record:

- Included/excluded sample IDs and reasons; AD/control arrays and known/unknown donors.
- Original expression scale, any transformation and justification; no pooled matrices.
- Exact design matrix, reference group, contrast direction and estimability/rank.
- Limma calls/settings, tested feature universe and multiple-testing family.
- Annotation version; sequence of probe-level testing, symbol conversion/collapse
  and adjusted-p-value calculation. Keep ambiguous multi-symbol mappings visible.
- Per-feature effect estimate, standard error where supported, test statistic,
  raw p value, adjusted p value, direction and mapping evidence.

Compare counts and gene identities to available published intermediates. If only
counts are available, say that agreement cannot verify identity-level reproduction.
Do not tune filters, annotations or designs to obtain a desired count. Investigate
and record discrepancies before moving to additional datasets.

## Phase C: published-workflow baseline B0

Once Phase B's implementation and uncertainties are frozen, expand only as needed
for a selected, source-verified curation finding's downstream comparison. If that
comparison requires all five development datasets, reconstruct their fixed baseline
and common-gene/direction outputs using the audit's checkpoint table. There is no
independent obligation to complete the entire published pipeline. Record mismatches
as results; agreement is not a mandatory condition of completion.

Network, feature-ranking, aggregation and classifier stages are conditional on
being necessary for that same selected curation comparison and on earlier stages
being interpretable. They require recovered network/version settings, pooled-data harmonization,
RF/DISR settings, classifier definitions and random seeds. Do not concatenate
different platforms, tissue compartments or scales as an unexamined default.
If source evidence requires an unsafe or scientifically uninterpretable step, stop
that stage with a precise reproduction gap rather than endorse it as valid inference.

The baseline retains the published method as its target. A baseline setting change
used to resolve reproduction ambiguity is not itself evidence of a curation benefit.
Any later restriction, mapping correction or necessary evaluation change must be
a separately declared consequence of a source-verified tool finding. General
methodological improvement is not an independent objective.

## Phase D: reviewed variants, frozen before new performance results

These are candidate **curation-linked** variants, not instructions to apply all
changes. Each activation must record this chain:

**tool finding → source verification → curation decision → downstream consequence**.

Retain the finding ID/source hash, reviewed evidence, affected samples or features,
decision and comparison specification. A warning alone is not an exclusion rule.
Freeze each variant before examining its changed gene-selection or prediction
results. Keep the reconstructed workflow otherwise fixed; document any unavoidable
change needed to honor a verified data constraint. Start one change at a time.

| Variant family | Evidence and activation gate | Intended comparison and interpretation |
|---|---|---|
| V-label: metadata interpretation | Review source labels/units/region aliases. Preserve ambiguous values. An age or region change only affects a numerical pipeline if that field is actually used. | Inventory accuracy and changed inclusion/design decisions. A metadata-only correction may leave expression results unchanged. |
| V-source-QC: source exclusions | Recover the original study's sample-level QC/exclusion list and demonstrate its relationship to current files and B0 inclusion. | Repeat B0 after the specifically justified exclusions; report which arrays/donors and class balance changed. Do not equate every author exclusion or audit flag with a confirmed error. |
| V-donor: repeated measurements/lineage | Tool identifies explicit donor/replicate relationships; source review supports the relationship and a consequential inclusion/split constraint. Unknown identifiers are not duplicates. | Implement only the grouping/replicate-handling change needed to honor that constraint. Declare a necessary model/split change separately; do not compare model families for a better score. Incomplete grouping remains unresolved. |
| V-region/compartment | Tool identifies a source-verified compatibility or eligibility issue and reviewed metadata support a defined restriction. | Apply the declared curation restriction and rerun the otherwise fixed workflow. Report changed population/estimand; no standalone region-discovery or model-adjustment study. |
| V-age/covariates | Tool identifies a source-verified label/unit/censoring problem affecting an existing inclusion rule or analysis input. Do not change 85 days to 85 years by assumption. | Correct only supported inputs or eligibility decisions. A field unused by the workflow may have no numerical effect. No new age/covariate model search merely to alter results. |
| V-probe/scale | Tool identifies an evidenced mapping/processing inconsistency; source review supports a specified correction. Distinguish this from unresolved author-method choices. | Apply the declared correction, preserve ambiguous features and measure mapping/gene-list consequences under the fixed workflow. No annotation/transform search for a favorable count or AUC. |

For any activated variant rerun all affected upstream steps and downstream selection.
Refitting only a classifier on the original 50 genes answers a different, narrower
question and must be labeled separately. Preserve an immutable B0 output.

## Evaluation policy

- The target's GSE109887 performance has already been inspected in the paper. It is
  a reproduction benchmark, not an untouched test set for our research decisions.
- Fix the published 50-gene logistic-regression comparison as the named checkpoint;
  report the paper's other panel/classifier results as additional published targets,
  not a menu for choosing our most favorable revised result.
- Never choose corrections or exclusions using testing-set performance. New
  classifier families, feature-ranking methods and hyperparameter optimization
  are outside this project's current scope. If the existing workflow's fitting or
  selection must be rerun after a curation change, preserve its fixed settings and
  honor verified donor/cohort constraints in all affected evaluation steps.
- No better-predictor/generalization claim is an objective of this case study.
  Any later such claim would additionally require suitable independent evaluation
  and reviewed lineage; a changed benchmark AUC is insufficient.
- Use the same valid evaluation samples for paired comparisons where feasible.
  If evaluation membership or estimand changes, report that separately; an AUC
  difference on a different population is not solely a model improvement.

Primary endpoints are correctness of tool findings, evidence/uncertainty retention,
missed/false flags against reviewed cases, and comparison with an explicit existing
curation workflow. Reconstruction agreement/gaps establish the case study's limits.
Changed eligibility, gene lists/directions or AUC are secondary measures of curation
consequences, not a target to maximize. Report
uncertainty using established methods and the supported independence unit; unknown
donors prevent treating a sample-level interval as established donor-level uncertainty.
Report all activated variants and results, including lower or unchanged performance.

The tool's correctness needs a source-reviewed reference set of valid/invalid/unknown
findings, comparison with an explicit existing workflow, and missed/false-flag counts.
The downstream rerun does not replace that evaluation or establish broad usefulness.

## Outputs and stopping rules

Expected first deliverables: source/version manifest; frozen sample-inclusion and
annotation mapping tables; resolved/unresolved method decisions; a limited limma
checkpoint table (if prerequisites pass); and a discrepancy log. Detailed per-sample
and numerical tables belong under ignored `data/processed/`; aggregate reports and
code may be tracked. Success does not require a higher AUC, more significant genes
or a new biological finding. Correct warnings, supported decisions and honest
unresolved cases can be useful even when downstream results are unchanged.

Stop the first numerical stage after a documented one-dataset checkpoint or its
exact blockers. Do not spend the session reverse-engineering every classifier.
Continue acquisition, source reconciliation and audit work while author details
or runtime dependencies are unavailable. Update STATUS/DECISIONS at the parent level.

Sources reviewed on 2026-11-08: target paper sections/tables as described in the
methods audit; original GSE118553 QC source and official GEO metadata. This plan
contains proposed decisions, not executed tests/downloads or reproduced findings.
