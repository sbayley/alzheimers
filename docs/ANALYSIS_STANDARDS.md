# Analysis standards

The first session is a descriptive feasibility and metadata audit. No disease
effect tests, trained models, causal claims, or treatment claims are authorized
by a successful file download alone.

The 2026-11-08 authorized follow-up has a separate prospective
`plans/pashaei_2025_reproduction.md`. Its R0 pilot is a historical numerical
reconstruction with documented assumptions, not a validated donor-level finding
or a corrected/optimized biomarker model. Keep that baseline separate from
subsequent source-reviewed sensitivity variants.

Preserve original fields and provenance. Report array/sample counts separately
from donor counts; unknown identity is not evidence of unique donors. Every
normalization needs an explicit mapping rule and supporting original field.
Keep ambiguous labels unresolved and document inclusion decisions.

Before biological tests, complete plans/first_analysis.md with the question,
analysis unit, published target if any, outcome, exclusions, covariates,
missingness handling, contrasts, uncertainty, multiple testing, and sensitivities.
An analysis drafted after looking at outcomes is exploratory, not prespecified.

Do not merge bulk tissue and laser-captured neurons, incompatible array platforms,
or differently normalized scales without a scientifically justified method.
Check donor repeats and cohort lineage before validation or cross-study pooling.
Avoid donor-level leakage and fit preprocessing inside training folds.

Use established statistical workflows (for example justified Bioconductor methods
for arrays), not handwritten significance tests. Preserve source results and
differentiate reproducing code, replicating an association, and extending a study.
Record visible corrections/retractions and limitations in source coverage.
