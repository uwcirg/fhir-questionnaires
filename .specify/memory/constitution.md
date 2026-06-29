<!--
SYNC IMPACT REPORT
Version change: 1.0.0 → 2.0.0 (MAJOR — backward-incompatible principle redefinitions)
Modified principles:
  - I. "Observation-Based $extract Targeting Epic Flowsheets"
       → "One Observation Per Individual Response, Exactly One Flowsheet Code"
       (added the hard rule that each Observation carries exactly ONE flowsheet code;
        added that computed score items are excluded)
  - III. "CSV Is the Source of Truth for Flowsheet IDs"
       → "CSV Maps LOINC Codes to Per-Environment Flowsheet IDs"
       (join key changed from (questionnaire_code, link_id) to the item's LOINC code
        matched against the CSV "LOINC code" column; warnings made bidirectional)
  - IV. REDEFINED: "Score Items Are Extracted; Their FHIRPath Is Not Touched"
       → "Fork Each Questionnaire Into Per-Environment Outputs"
       (the prior rule that score items MUST be extracted is REMOVED/REVERSED; the new
        Principle IV codifies forking one source Questionnaire into separate UAT and
        production Questionnaires, resolving the former TODO)
Added sections: N/A (section headings unchanged)
Removed sections:
  - TODO(UAT_VS_PROD_REPRESENTATION) deferred item — now resolved: the chosen
    representation is two separate output Questionnaire files (one per environment),
    each carrying a single flowsheet code per item.
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no edits required (Constitution Check
    references the constitution file dynamically)
  - .specify/templates/spec-template.md ✅ no edits required (no constitution-specific content)
  - .specify/templates/tasks-template.md ✅ no edits required (no constitution-specific content)
  - specs/001-add-extract-metadata/spec.md ⚠ PENDING — that spec describes a single-file,
    dual-environment, score-extracting tool keyed on linkId; it now conflicts with
    Principles I, III, and IV. Re-run /speckit.specify (or /speckit.clarify) to align it:
    fork-into-two-files, LOINC-keyed mapping, scores excluded, one flowsheet code per Observation.
  - README.md ⚠ intentionally NOT updated; general Questionnaire-authoring guidance
    remains out of scope for this constitution.
Deferred items: none.
-->

# FHIR Questionnaires Constitution

This constitution governs one specific concern in this repository: enabling the
HAPI `$extract` operation on `QuestionnaireResponse` resources so that the
resulting `Observation` resources can be written to a target EMR's flowsheet
rows. Because the target UAT and production systems use different flowsheet
FHIR IDs and cannot accept an Observation coded with more than one flowsheet,
a Questionnaire that is enabled for `$extract` is forked into one output
Questionnaire per environment. This constitution does NOT codify general
Questionnaire-authoring conventions; those remain in `README.md` until a future
amendment.

## Core Principles

### I. One Observation Per Individual Response, Exactly One Flowsheet Code

In-scope Questionnaires MUST be modified so that HAPI's `$extract` operation
produces one FHIR `Observation` per answered, individual-response
`QuestionnaireResponse.item`. The generated Observation shape is fixed:

- `resourceType` MUST be `"Observation"`.
- `category[0].coding[0]` MUST be
  `{ system: "http://hl7.org/fhir/observation-category", code: "vital-signs" }`.
- `code.coding` MUST contain **exactly one** flowsheet coding. Its `system`
  MUST be
  `http://open.epic.com/FHIR/StructureDefinition/observation-flowsheet-id`, and
  its `code` MUST be the flowsheet FHIR ID for that item **in the single
  environment the output Questionnaire targets** (UAT or production, never
  both).
- `subject.reference` MUST resolve to the Patient referenced by the
  QuestionnaireResponse.
- `effectiveDateTime` MUST be derived from the QuestionnaireResponse's authored
  timestamp (or an equivalent recorded time).
- `valueCodeableConcept.coding[].display` MUST carry the answer's display text
  for choice/text answers; non-choice answers use the corresponding `value[x]`
  expected by the target EMR for that flowsheet row.

Computed **score** items (those whose value is calculated by the form filler,
e.g. a total whose `linkId` carries an
`sdc-questionnaire-calculatedExpression`) are OUT OF SCOPE: only individual
responses are reported as Observations. See Principle IV's exclusion rules.

**Rationale**: The target EMR ingests these Observations as flowsheet rows, and
the UAT and production systems reject any Observation coded with more than one
flowsheet. Emitting exactly one flowsheet code per Observation — and one output
Questionnaire per environment — is what keeps ingestion working. Any deviation
from this shape, including adding a second flowsheet code, breaks downstream
ingestion. Changes to this shape are MAJOR amendments.

### II. JSONPath in HAPI; CQL Out of Scope

`$extract` runs in HAPI. Where extraction logic is required, it MUST be
expressed in JSONPath. CQL MUST NOT be introduced. If a concrete requirement
arises that cannot be satisfied in JSONPath, the constitution MUST be amended
(MAJOR bump) before CQL is added.

**Rationale**: The team has no current CQL toolchain or fluency, and so far no
extraction logic beyond direct mapping is anticipated. Constraining the
expression language keeps the surface small and reviewable.

### III. CSV Maps LOINC Codes to Per-Environment Flowsheet IDs

The mapping from a Questionnaire item to its UAT and production flowsheet FHIR
IDs lives in a CSV checked into this repository at
`deploy-specific/mapping-input/`. The CSV's columns are `RECORD NAME`,
`LOINC code`, `FHIR ID - UAT`, and `FHIR ID - Prod`. The **`LOINC code`
column** is the join key: each Questionnaire item is matched to a CSV row by
its LOINC code, and the row supplies that item's UAT and production flowsheet
FHIR IDs.

Tooling that injects flowsheet IDs into Questionnaire JSON MUST read from this
CSV and MUST tolerate imperfect mappings. Specifically:

- If a CSV record's `LOINC code` does not match any item in the Questionnaire,
  the tool MUST emit a WARNING naming the unmatched record and proceed to the
  next mapping.
- If a Questionnaire item has no matching CSV record (or the matched record is
  missing the UAT or production FHIR ID), the tool MUST emit a WARNING naming
  the item and what was missing, and proceed.

Neither condition is a fatal error. Tooling MUST NOT invent or guess flowsheet
IDs to fill a gap.

**Rationale**: Two environments need two IDs, and confusing them sends test
data into production flowsheets or vice versa. Keying on the LOINC code keeps
the mapping legible to clinical reviewers (LOINC is the shared vocabulary
between the instrument and the flowsheet), and centralizing it in CSV makes the
source of truth obvious. Surfacing gaps without failing the whole run lets the
team make incremental progress on partially-mapped instruments.

### IV. Fork Each Questionnaire Into Per-Environment Outputs

A Questionnaire enabled for `$extract` MUST be forked into **two** output
Questionnaires — one targeting the UAT system and one targeting production —
rather than encoding both environments' flowsheet IDs in a single file. The UAT
output MUST carry only `FHIR ID - UAT` values; the production output MUST carry
only `FHIR ID - Prod` values. This is what guarantees the single-flowsheet-code
rule of Principle I.

- UAT outputs MUST be written under `deploy-specific/ucsd-uat/`.
- Production outputs MUST be written under `deploy-specific/ucsd-prod/`.
- The source Questionnaire in the repository (e.g. `CIRG-PHQ-9.json`) is the
  input; the two per-environment files are generated artifacts derived from it.

Items that are OUT OF SCOPE and MUST NOT receive flowsheet metadata in either
output:

- Computed **score** items (per Principle I) — only individual responses are
  reported.
- Display-only items (`item.type` = `"display"`).
- Items whose LOINC code has no matching CSV record (per Principle III).

Score items and any other content the tool does not own MUST be left
byte-for-byte unchanged in the outputs, including any
`sdc-questionnaire-calculatedExpression` they carry.

**Rationale**: The target UAT and production systems use different flowsheet
FHIR IDs and cannot receive an Observation coded with more than one flowsheet.
Forking into two single-environment files is the representation that satisfies
that constraint cleanly, keeps each file reviewable against one column of the
CSV, and removes any ambiguity about which environment an ID belongs to.

### V. Idempotent, Minimal-Diff Modifications

Any tool that produces these per-environment Questionnaires MUST be idempotent:
re-running it on the same inputs MUST produce byte-identical outputs — no
duplicated entries, no reordered unrelated fields, no whitespace churn, and no
changes outside the metadata the tool owns. The resulting diff MUST be small
enough for a subject-matter expert to verify against the relevant CSV column by
reading.

**Rationale**: These Questionnaires are reviewed by clinical and informatics
staff. Noisy diffs hide real changes and erode trust in the tooling.

## Extraction Metadata Standards

- The mapping CSV described in Principle III MUST live under
  `deploy-specific/mapping-input/` and MUST include at minimum the columns
  `RECORD NAME`, `LOINC code`, `FHIR ID - UAT`, and `FHIR ID - Prod`.
  Additional columns are permitted and ignored.
- Per-environment outputs MUST be written under `deploy-specific/ucsd-uat/`
  (UAT) and `deploy-specific/ucsd-prod/` (production).
- `$extract` enablement is performed one source Questionnaire at a time.
  Tooling MUST accept a Questionnaire file as a parameter and operate on that
  single file, emitting its two environment outputs. Bulk modifications MUST be
  expressed as a loop over single-Questionnaire runs so that failures are
  isolated and reviewable.
- Questionnaires that are deprecated — files under `deprecated/`, files matching
  `*.deprecated.json`, or Questionnaires whose `status` is `retired` — are OUT
  OF SCOPE for `$extract` enablement and MUST be skipped by tooling.
- Display-only items (`item.type` = `"display"`), computed score items, and
  items whose LOINC code is absent from the CSV are OUT OF SCOPE for
  extraction.

## Development Workflow

- A PR that enables `$extract` for a Questionnaire MUST include: the two
  generated per-environment Questionnaire JSON files, any CSV updates they
  depend on, and a description that links each mapped item to its CSV record by
  LOINC code.
- Reviewers MUST verify each output against the corresponding CSV column
  (`FHIR ID - UAT` for the UAT file, `FHIR ID - Prod` for the production file)
  before approving. Tooling SHOULD make this a near-mechanical check.
- Changes to the Observation shape (Principle I), the single-flowsheet-code
  rule (Principle I), the choice of expression language (Principle II), the CSV
  schema or join key (Principle III), or the per-environment fork (Principle IV)
  MUST be raised as constitution amendments before code that depends on them
  lands.

## Governance

- Amendments require a PR that updates this file, refreshes the Sync Impact
  Report at the top, and bumps the version per the rules below.
- Versioning follows semantic versioning:
  - **MAJOR**: backward-incompatible changes — e.g., switching expression
    language, altering the Observation shape, changing the mapping join key,
    removing or redefining a principle.
  - **MINOR**: additive changes — e.g., a new principle or a materially
    expanded section.
  - **PATCH**: clarifications, wording fixes, non-semantic refinements.
- Compliance review: every PR that produces or updates per-environment
  Questionnaire JSON for `$extract` enablement MUST be checked against these
  principles before merge. Tooling changes that would violate a principle MUST
  be paired with the corresponding amendment in the same PR.
- This constitution supersedes ad-hoc conventions for `$extract` work. It does
  not override the general Questionnaire-authoring guidance in `README.md`;
  those scopes are kept separate by design.

**Version**: 2.0.0 | **Ratified**: 2026-05-04 | **Last Amended**: 2026-06-29
