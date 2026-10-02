<!--
SYNC IMPACT REPORT
Version change: 2.1.0 → 3.0.0 (MAJOR — the mapping CSV's required columns change
  (`RECORD NAME` renamed, `CNICS NAME` added) and the join key is redefined from "the
  item's LOINC code" to "the item's linkId"; Governance classes both as MAJOR)
  Also redefines extraction scope: computed scores/totals are now extracted for every
  Questionnaire except CIRG-PHQ9. Folded into 3.0.0 because 3.0.0 was never committed.
Modified principles:
  - I. "One Observation Per Individual Response, Exactly One Flowsheet Code" →
       "One Observation Per Reported Item, Exactly One Flowsheet Code". Computed items
       (calculatedExpression) are in scope, except those of Questionnaires whose scores
       the target EMR computes itself (CIRG-PHQ9 only) and "internal" items.
  - III. "CSV Maps LOINC Codes to Per-Environment Flowsheet IDs" →
         "CSV Maps Questionnaire Items to Per-Environment Flowsheet IDs".
         Columns are now `CNICS NAME`, `RECORD NAME (UCSD Epic)`, `LOINC code`,
         `FHIR ID - UAT`, `FHIR ID - Prod`. `LOINC code` is copied from item.linkId.
         Added separator rows labelled with Questionnaire.id, the rules for which items
         get a row (no display headers, no "internal" items, no itemControl items), and
         column ownership (site supplies record name and FHIR IDs; blank until then).
  - IV. exclusion list and the byte-for-byte rule follow Principle I's new computed-item
         rule; calculatedExpression is never modified.
Added sections: N/A
Removed sections: N/A
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no edits required (Constitution Check
    references the constitution file dynamically)
  - .specify/templates/spec-template.md ✅ no edits required
  - .specify/templates/tasks-template.md ✅ no edits required
  - README.md ✅ no edits required (Tooling note does not name CSV columns)
  - deploy-specific/mapping-input/CNICS PRO UCSD flowsheet FHIR IDs.csv ⚠ pending —
    still has the v2 header and only PHQ-9 rows
  - utils/fork_questionnaire_for_extract.py ⚠ pending — REQUIRED_CSV_COLUMNS and the
    record_name lookup still use `RECORD NAME`; must change with the CSV header. It also
    skips every computed score item; it must now skip them only for CIRG-PHQ9 (plus
    "internal" items)
  - tests/test_fork_scores.py ⚠ pending — asserts scores are always skipped
  - tests/test_fork_warnings.py, tests/fixtures/csv-missing-column.csv ⚠ pending — same
  - specs/001-add-extract-metadata/{spec,data-model,research,tasks}.md ⚠ pending — cite
    the v2 column name and LOINC-only join key
Deferred items:
  - TODO(ITEMCONTROL_EXCLUSION): every PHQ-9 response item carries the itemControl
    extension yet is already mapped. Principle III retains those rows; confirm whether
    the exclusion is meant for all itemControl items (e.g. the ARV-9 slider) or only
    display/help ones.
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

### I. One Observation Per Reported Item, Exactly One Flowsheet Code

In-scope Questionnaires MUST be modified so that HAPI's `$extract` operation
produces one FHIR `Observation` per answered, reported
`QuestionnaireResponse.item` — each individual response and, except where the
"Computed items" rule below excludes them, each computed score or total. The
shape of the Observation delivered to the
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
  for choice/text answers; non-choice answers and computed items use the
  corresponding `value[x]` expected by the target EMR for that flowsheet row.

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

**Computed items**: Items whose value is calculated by the form filler (those
carrying an `sdc-questionnaire-calculatedExpression`, e.g. a score or total)
are IN SCOPE and reported as Observations like any individual response, with
two exceptions:

- Computed items of a Questionnaire whose scores the target EMR calculates
  itself are OUT OF SCOPE. Today that is `CIRG-PHQ9` only: UCSD's Epic already
  computes the PHQ-9 totals from the individual responses. Adding a
  Questionnaire to, or removing one from, this list is a constitution
  amendment.
- Computed items whose `text` states that they are "internal" items (e.g.
  `AUDIT-Q0-score`) are OUT OF SCOPE for every Questionnaire.

See Principle IV's exclusion rules.

**Rationale**: The target EMR ingests these Observations as flowsheet rows, and
the UAT and production systems reject any Observation coded with more than one
flowsheet. Emitting exactly one flowsheet code per Observation — and one output
Questionnaire per environment — is what keeps ingestion working. Any deviation
from this shape, including adding a second flowsheet code, breaks downstream
ingestion. Changes to this shape are MAJOR amendments. Totals are sent for
every instrument except PHQ-9 because the target EMR has no capacity to compute
them for those instruments; sending a PHQ-9 total would duplicate the one Epic
already derives. The category is applied
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

### III. CSV Maps Questionnaire Items to Per-Environment Flowsheet IDs

The mapping from a Questionnaire item to its UAT and production flowsheet FHIR
IDs lives in a CSV checked into this repository at
`deploy-specific/mapping-input/`. The CSV's columns are, in order:

1. `CNICS NAME` — a very brief human-friendly label for the item, derived from
   `Questionnaire.item[].text`. Maintained by this team.
2. `RECORD NAME (UCSD Epic)` — the name of the Epic flowsheet record at the
   target site. Supplied by the target site; this team MUST NOT invent it.
3. `LOINC code` — the **join key**. It MUST hold the item's identifier copied
   from `Questionnaire.item[].linkId` (a single leading `/` removed). For
   LOINC-based instruments (e.g. PHQ-9) that identifier is the LOINC code; for
   instruments whose items carry no LOINC code (e.g. `AUDIT-1`) it is the
   `linkId` as authored. The column name is retained for continuity.
4. `FHIR ID - UAT` and 5. `FHIR ID - Prod` — the flowsheet FHIR IDs. Supplied
   by the target site once it has created the flowsheets; blank until then.

Each Questionnaire item is matched to a CSV row by the `LOINC code` column, and
the row supplies that item's UAT and production flowsheet FHIR IDs.

**Separator rows**: Each Questionnaire's rows MUST be preceded by a separator
row whose `CNICS NAME` cell is the `Questionnaire.id` (e.g. `CIRG-CNICS-AUDIT`)
and whose other cells are blank. Tooling MUST skip any row whose `LOINC code`
cell is blank, so separator rows are never treated as mappings.

**Which items get a row**: When a Questionnaire is added to the CSV, every item
at any nesting depth gets one row, EXCEPT:

- display-only headers (`item.type` = `"display"`, e.g. `AUDIT-header`);
- items whose `text` states that they are "internal" items (e.g.
  `AUDIT-Q0-score`);
- items carrying the
  `http://hl7.org/fhir/StructureDefinition/questionnaire-itemControl`
  extension.

Rows that already exist with site-supplied values (the PHQ-9 rows) MUST be
retained as they are; these exclusions govern rows added for a Questionnaire,
not the removal of rows the target site has already mapped. Having a CSV row
does not by itself put an item in scope for extraction — Principle IV's
exclusions still apply (the PHQ-9 score rows are mapped but not extracted).

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
data into production flowsheets or vice versa. The CSV is also the worksheet
exchanged with the target site: this team lists the items it will send
(`CNICS NAME`, `LOINC code`), and the site answers with the flowsheet it built
for each (`RECORD NAME (UCSD Epic)`, the two FHIR IDs). Keying on the item's
`linkId` gives every item a stable key whether or not the instrument is
LOINC-coded, and where it is, the key is the LOINC code clinical reviewers
already know. Separator rows keep a many-instrument file readable. Surfacing
gaps without failing the whole run lets the team make incremental progress on
partially-mapped instruments.

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

- Computed items that Principle I excludes: those of a Questionnaire whose
  scores the target EMR calculates itself (`CIRG-PHQ9`), and "internal" items.
- Display-only items (`item.type` = `"display"`).
- Items with no matching CSV record (per Principle III).

Excluded items and any other content the tool does not own MUST be left
byte-for-byte unchanged in the outputs. For every computed item, in scope or
not, the `sdc-questionnaire-calculatedExpression` it carries MUST be left
unchanged.

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
  `CNICS NAME`, `RECORD NAME (UCSD Epic)`, `LOINC code`, `FHIR ID - UAT`, and
  `FHIR ID - Prod`. Additional columns are permitted and ignored.
- Rows for one Questionnaire MUST be contiguous, in the Questionnaire's item
  order, under that Questionnaire's separator row.
- `RECORD NAME (UCSD Epic)`, `FHIR ID - UAT`, and `FHIR ID - Prod` MUST be left
  blank for items the target site has not yet built flowsheets for.
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
- Display-only items (`item.type` = `"display"`), the computed items excluded
  by Principle I, and items whose `LOINC code` value is absent from the CSV are OUT OF SCOPE for
  extraction.

## Development Workflow

- A PR that enables `$extract` for a Questionnaire MUST include: the two
  generated per-environment Questionnaire JSON files, any CSV updates they
  depend on, and a description that links each mapped item to its CSV record by
  its `LOINC code` value.
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

**Version**: 3.0.0 | **Ratified**: 2026-05-04 | **Last Amended**: 2026-10-02
