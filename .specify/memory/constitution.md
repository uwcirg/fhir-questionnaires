<!--
SYNC IMPACT REPORT
Version change: (initial template) → 1.0.0
Modified principles: N/A (initial ratification)
Added sections:
  - Core Principles (I–V, all focused on $extract enablement)
  - Extraction Metadata Standards
  - Development Workflow
  - Governance
Removed sections: N/A
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no edits required (Constitution Check section
    already references the constitution file dynamically)
  - .specify/templates/spec-template.md ✅ no edits required (no constitution-specific content)
  - .specify/templates/tasks-template.md ✅ no edits required (no constitution-specific content)
  - README.md ⚠ intentionally NOT updated; user requested that general Questionnaire
    structural guidance remain in README and out of scope for this constitution
Deferred items:
  - TODO(UAT_VS_PROD_REPRESENTATION): the concrete mechanism for representing both UAT
    and production flowsheet IDs inside the Questionnaire JSON (two code.coding entries
    differentiated by system, an environment extension, separate output files, etc.) has
    not been chosen. Captured as a constraint in Principle III, not yet a concrete rule.
-->

# FHIR Questionnaires Constitution

This constitution governs one specific concern in this repository: enabling the
HAPI `$extract` operation on `QuestionnaireResponse` resources so that the
resulting `Observation` resources can be written to Epic as flowsheet rows. It
does NOT yet codify general Questionnaire-authoring conventions; those remain
in `README.md` until a future amendment.

## Core Principles

### I. Observation-Based $extract Targeting Epic Flowsheets

In-scope Questionnaires MUST be modified so that HAPI's `$extract` operation
produces one FHIR `Observation` per relevant `QuestionnaireResponse.item`. The
generated Observation shape is fixed:

- `resourceType` MUST be `"Observation"`.
- `category[0].coding[0]` MUST be
  `{ system: "http://hl7.org/fhir/observation-category", code: "vital-signs" }`.
- `code.coding[0].system` MUST be
  `http://open.epic.com/FHIR/StructureDefinition/observation-flowsheet-id`, and
  `code.coding[0].code` MUST be the Epic flowsheet ID for that `linkId`.
- `subject.reference` MUST resolve to the Patient referenced by the
  QuestionnaireResponse.
- `effectiveDateTime` MUST be derived from the QuestionnaireResponse's authored
  timestamp (or an equivalent recorded time).
- `valueCodeableConcept.coding[].display` MUST carry the answer's display text
  for choice/text answers; non-choice answers use the corresponding `value[x]`
  expected by Epic for that flowsheet row.

**Rationale**: Epic ingests these Observations as flowsheet rows. Any deviation
from this shape breaks downstream ingestion. Changes to this shape are MAJOR
amendments.

### II. JSONPath in HAPI; CQL Out of Scope

`$extract` runs in HAPI. Where extraction logic is required, it MUST be
expressed in JSONPath. CQL MUST NOT be introduced. If a concrete requirement
arises that cannot be satisfied in JSONPath, the constitution MUST be amended
(MAJOR bump) before CQL is added.

**Rationale**: The team has no current CQL toolchain or fluency, and so far no
extraction logic beyond direct mapping is anticipated. Constraining the
expression language keeps the surface small and reviewable.

### III. CSV Is the Source of Truth for Flowsheet IDs

The mapping from `(Questionnaire.code, Questionnaire.item.linkId)` to Epic
flowsheet IDs lives in a CSV checked into this repository. Each row pairs an
in-scope `linkId` with its UAT flowsheet ID and its production flowsheet ID.

Tooling that injects flowsheet IDs into Questionnaire JSON MUST read from this
CSV and MUST tolerate a sparsely populated CSV: a missing row, a missing UAT
ID, or a missing production ID is NOT a fatal error. Tooling MUST emit a
clear, per-item WARNING in those cases so the gap is visible to reviewers, and
MUST proceed with whatever IDs are available. Tooling MUST NOT invent or guess
flowsheet IDs to fill a gap.

Questionnaire JSON MUST NOT embed a flowsheet ID without a representation that
unambiguously labels it as UAT or production. Hardcoding a single ID without
that disambiguation is forbidden because it conflates the two environments.

> TODO(UAT_VS_PROD_REPRESENTATION): the concrete encoding inside the
> Questionnaire (e.g., two `code.coding` entries with distinct `system` URLs
> per environment, an environment-tagging extension, environment-specific
> output files, etc.) is not yet chosen. Until it is, tooling SHOULD pick one
> explicit representation and surface its choice in its own output so that
> reviewers can verify it.

**Rationale**: Two environments need two IDs, and confusing them sends test
data into production flowsheets or vice versa. Centralizing the mapping in CSV
keeps the JSON reviewable and makes the source of truth obvious.

### IV. Score Items Are Extracted; Their FHIRPath Is Not Touched

Items whose `linkId` contains the substring `SCORE` and that carry the
`http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-calculatedExpression`
extension are computed upstream by the form filler. These items MUST be
included in `$extract` output, because Epic wants the score on the flowsheet.

Extraction tooling MUST NOT modify, delete, or rewrite the
`calculatedExpression` FHIRPath on those items; that expression is owned by the
form filler. Tooling MAY only add the metadata required for `$extract` (e.g.,
flowsheet-ID coding) alongside the existing extension.

**Rationale**: The score is a clinically meaningful flowsheet value, but the
expression that produces it is an upstream concern. Mixing the two
responsibilities risks breaking working forms.

### V. Idempotent, Minimal-Diff Modifications

Any tool that adds `$extract` metadata to a Questionnaire MUST be idempotent:
re-running it on an already-modified Questionnaire MUST NOT duplicate entries,
reorder unrelated fields, or alter content outside the metadata it owns. The
resulting diff MUST be small enough for a subject-matter expert to verify
against the CSV by reading.

**Rationale**: These Questionnaires are reviewed by clinical and informatics
staff. Noisy diffs hide real changes and erode trust in the tooling.

## Extraction Metadata Standards

- The CSV described in Principle III MUST live in this repository (path TBD).
  Its schema MUST include at minimum:
  `questionnaire_code`, `link_id`, `flowsheet_id_uat`, `flowsheet_id_prod`.
  Additional columns are permitted.
- `$extract` enablement is performed one Questionnaire at a time. Tooling MUST
  accept a Questionnaire `id` as a parameter and operate on a single file. Bulk
  modifications MUST be expressed as a loop over single-Questionnaire runs so
  that failures are isolated and reviewable.
- Questionnaires that are deprecated — files under `deprecated/`, files matching
  `*.deprecated.json`, or Questionnaires whose `status` is `retired` — are OUT
  OF SCOPE for `$extract` enablement and MUST be skipped by tooling.
- Display-only items (`item.type` = `"display"`) and items without an answer
  value in the QuestionnaireResponse contract are OUT OF SCOPE for extraction.

## Development Workflow

- A PR that enables `$extract` for a Questionnaire MUST include: the modified
  Questionnaire JSON, any CSV updates it depends on, and a description that
  links each modified `linkId` to its CSV row(s).
- Reviewers MUST verify the diff against the CSV before approving. Tooling
  SHOULD make this a near-mechanical check.
- Changes to the Observation shape (Principle I), the choice of expression
  language (Principle II), or the CSV schema (Principle III) MUST be raised as
  constitution amendments before code that depends on them lands.

## Governance

- Amendments require a PR that updates this file, refreshes the Sync Impact
  Report at the top, and bumps the version per the rules below.
- Versioning follows semantic versioning:
  - **MAJOR**: backward-incompatible changes — e.g., switching expression
    language, altering the Observation shape, removing or redefining a
    principle.
  - **MINOR**: additive changes — e.g., a new principle or a materially
    expanded section.
  - **PATCH**: clarifications, wording fixes, non-semantic refinements.
- Compliance review: every PR that touches Questionnaire JSON for `$extract`
  enablement MUST be checked against these principles before merge. Tooling
  changes that would violate a principle MUST be paired with the corresponding
  amendment in the same PR.
- This constitution supersedes ad-hoc conventions for `$extract` work. It does
  not override the general Questionnaire-authoring guidance in `README.md`;
  those scopes are kept separate by design.

**Version**: 1.0.0 | **Ratified**: 2026-05-04 | **Last Amended**: 2026-05-04
