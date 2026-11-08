# First descriptive analysis plan

Status: written before disease-effect testing; no disease-effect tests are planned
in the first session. This is an exploratory feasibility audit, not a registered
biological hypothesis.

Question: Which acquired processed GEO datasets have enough explicit metadata and
compatible design to support a small, reproducible follow-up, and what would
prevent valid inference?

Unit: a GEO sample/array for inventory purposes. Donor-level summaries are allowed
only when explicit donor identifiers and their meaning are verified. Sample
counts must never be relabeled as participant counts.

Outcomes: acquisition success, matrix shape and observed numeric range, diagnosis
and region composition, field missingness, age ranges/overlap if supported, explicit
donor repeat counts, source-linked cohort relations, and documented exclusions.

Inclusion: public processed matrix files discovered from official records and
listings, within configured limits and passing content/provenance checks. Preserve
every sample in the inventory; mark unknown/ambiguous diagnosis and donor identity.
No sample is yet included in disease-effect analysis.

Covariates to assess: age/units, sex as recorded, region, tissue/cell compartment,
platform and processing, postmortem interval, RNA integrity, batch, pathology.
Do not impute undocumented values. Stratify missingness by dataset/diagnosis when
the diagnosis is explicit. Do not fit a disease model in this session.

Sensitivities to scope: age-compatible controls; one region and compartment;
explicit versus unresolved diagnosis; verified donor independence; probe mapping
ambiguity; scale and normalization compatibility. A specific biological follow-up
requires an amended plan with an exact source result and validated analysis unit.

Failure conditions: unknown donor lineage, unavailable covariates, incompatible
measurement/compartment, too few compatible samples, or inaccessible data. These
are valid audit findings, not reasons to invent values or relax evidence standards.
