<!--
SYNC IMPACT REPORT
Version change: 2.0.0 → 2.1.0 (MINOR — Principle I materially expanded; the delivered
  Observation shape is unchanged, so this is not a MAJOR shape change)
Modified principles:
  - I. "One Observation Per Individual Response, Exactly One Flowsheet Code" (title
       unchanged). The fixed shape now describes the Observation delivered to the target
       EMR. Added a "Category" rule: HAPI ignores the Questionnaire's
       observationExtractCategory extension and stamps `survey`
       (cqframework/clinical-reasoning#1128), so the Questionnaire MUST still declare
       `vital-signs` and the step downstream of $extract MUST set it before delivery.
       All other shape elements are still required as emitted by HAPI's $extract.
Added sections: N/A
Removed sections: N/A
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no edits required (Constitution Check
    references the constitution file dynamically)
  - .specify/templates/spec-template.md ✅ no edits required (no constitution-specific content)
  - .specify/templates/tasks-template.md ✅ no edits required (no constitution-specific content)
  - specs/001-add-extract-metadata/spec.md ✅ already aligned (Clarifications
    Session 2026-10-02, FR-004, Assumptions)
  - specs/001-add-extract-metadata/plan.md ✅ updated (Constitution Check cites v2.1.0;
    Principle I row reflects the Category rule)
  - specs/001-add-extract-metadata/tasks.md (T013), data-model.md (entity 4 and the
    example Observation), research.md (R3) ✅ updated to the same wording
  - README.md ✅ Tooling note already records the HAPI category limitation.
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
`QuestionnaireResponse.item`. The shape of the Observation delivered to the
target EMR is fixed. Every element below MUST be present as emitted by HAPI's
`$extract`, with the single exception of `category`, which is governed by the
"Category" rule that follows the list:

- `resourceType` MUST be `"Observation"`.
- `category[0].coding[0]` MUST be
  `{ system: "http://hl7.org/fhir/observation-category", code: "vital-signs" }`
  on the Observation delivered to the target EMR.
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

**Category**: HAPI does not read the SDC
`sdc-questionnaire-observationExtractCategory` extension from the
Questionnaire and stamps `survey` on every extracted Observation
([cqframework/clinical-reasoning#1128](https://github.com/cqframework/clinical-reasoning/issues/1128)).
Therefore:

- Each output Questionnaire MUST still declare the `vital-signs` category via
  that extension, using the `system` and `code` above. This is the full extent
  of the Questionnaire's (and the forking tool's) category obligation.
- The processing step downstream of `$extract` — between HAPI and the target
  EMR — MUST set `category[0].coding[0]` to the value above before the
  Observation is delivered. An Observation MUST NOT reach the target EMR
  carrying HAPI's default `survey` category.
- The `category` HAPI itself emits is NOT a compliance criterion for a
  Questionnaire or for the forking tool.

Computed **score** items (those whose value is calculated by the form filler,
e.g. a total whose `linkId` carries an
`sdc-questionnaire-calculatedExpression`) are OUT OF SCOPE: only individual
responses are reported as Observations. See Principle IV's exclusion rules.

**Rationale**: The target EMR ingests these Observations as flowsheet rows, and
the UAT and production systems reject any Observation coded with more than one
flowsheet. Emitting exactly one flowsheet code per Observation — and one output
Questionnaire per environment — is what keeps ingestion working. Any deviation
from this shape, including adding a second flowsheet code, breaks downstream
ingestion. Changes to this shape are MAJOR amendments. The category is applied
downstream only because HAPI ignores the Questionnaire's declaration; keeping
the declaration in the Questionnaire records the intended value at its source
and lets HAPI honor it without further Questionnaire changes if that is fixed.

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

**Version**: 2.1.0 | **Ratified**: 2026-05-04 | **Last Amended**: 2026-10-02
