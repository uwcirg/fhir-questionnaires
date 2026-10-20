<!--
SYNC IMPACT REPORT
Version change: 3.1.0 → 4.0.0 (MAJOR — the Observation's flowsheet coding is redefined
  and two CSV columns are replaced by one; both are backward incompatible)
Modified principles:
  - I. "One Observation Per Reported Item, Exactly One Flowsheet Code" (title unchanged).
       The flowsheet coding's `code` is now the flowsheet record ID (identical in UAT and
       production); its `system` is the target environment's OID. The flowsheet FHIR ID
       and the `observation-flowsheet-id` system are no longer used.
  - III. "CSV Maps Questionnaire Items to Per-Environment Flowsheet IDs" →
         "CSV Maps Questionnaire Items to Flowsheet Record IDs". Columns `FHIR ID - UAT`
         and `FHIR ID - Prod` are replaced by a single `Flowsheet Record ID` column.
         Join key, separator rows and row-inclusion rules are unchanged.
  - IV. "Fork Each Questionnaire Into Per-Environment Outputs" (title unchanged). The fork
        is retained, but the two outputs now differ only in the flowsheet coding's
        `system`; the `code` is the same in both.
  - V. Wording only (reviewers check one CSV column, not one per environment).
Added sections: N/A
Removed sections: N/A
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no edits required
  - .specify/templates/spec-template.md ✅ no edits required
  - .specify/templates/tasks-template.md ✅ no edits required
  - .specify/templates/commands/ ✅ directory not present
  - README.md ✅ updated (utils entry describes the four-column CSV and record-ID coding)
  - deploy-specific/mapping-input/CNICS PRO UCSD flowsheet FHIR IDs.csv ✅ already
    updated by the maintainer (four columns). File name still says "FHIR IDs"; renaming
    is optional and would touch the tool default, tests and specs.
  - utils/fork_questionnaire_for_extract.py ⚠ pending — still requires the
    `FHIR ID - UAT` / `FHIR ID - Prod` columns and emits the `observation-flowsheet-id`
    system; must read `Flowsheet Record ID` and emit the per-environment OID system.
    v3.1.0 items also still pending (strips the leading `/` for `CIRG-PC-PTSD-5`; skips
    every computed score item rather than CIRG-PHQ9 and "internal" items only).
  - tests/conftest.py, tests/test_fork_*.py, tests/test_mapping_csv.py,
    tests/fixtures/csv-missing-column.csv ⚠ pending — assert the v3 columns and system
  - deploy-specific/ucsd-uat/CIRG-PHQ-9.json, deploy-specific/ucsd-prod/CIRG-PHQ-9.json
    ⚠ pending — generated with flowsheet FHIR IDs; regenerate once the tool is updated
  - specs/001-add-extract-metadata/*, specs/002-populate-flowsheet-mapping-csv/*
    ⚠ pending — historical feature docs cite the v3 columns and coding system
  - Downstream consumer built on the `188-fishmouth-notify` branch (outside this
    repository) ⚠ pending — written against flowsheet FHIR IDs
Deferred items: none.
-->



# FHIR Questionnaires Constitution

This constitution governs one specific concern in this repository: enabling the
HAPI `$extract` operation on `QuestionnaireResponse` resources so that the
resulting `Observation` resources can be written to a target EMR's flowsheet
rows. Each Observation is coded with the item's flowsheet record ID, which is
the same in the target site's UAT and production systems; the coding `system`
that qualifies it is not. Because that `system` differs per environment and
the target systems cannot accept an Observation coded with more than one
flowsheet, a Questionnaire that is enabled for `$extract` is forked into one
output Questionnaire per environment. This constitution does NOT codify general
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
- `code.coding` MUST contain **exactly one** flowsheet coding. Its `code` MUST
  be the item's flowsheet record ID (e.g. `3025`), which is the same in every
  environment of the target site. Its `system` MUST be the flowsheet-record-ID
  system of **the single environment the output Questionnaire targets** (UAT
  or production, never both):
  - UAT/test: `urn:oid:1.2.840.114350.1.13.136.3.7.2.707679`
  - production: `urn:oid:1.2.840.114350.1.13.136.2.7.2.707679`

  The coding MUST NOT carry a flowsheet FHIR ID, and MUST NOT use the system
  `http://open.epic.com/FHIR/StructureDefinition/observation-flowsheet-id`.
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
ingestion. Changes to this shape are MAJOR amendments. The flowsheet record ID
is used rather than the flowsheet FHIR ID because every Epic deployment mints
its own FHIR ID for a given flowsheet, whereas the record ID is consistent
across the deployments of one healthcare organization. Writing to Epic does not
require the FHIR ID. The trade-off is that the record ID's `system` differs per
deployment, so the two values above are fixed here. Totals are sent for
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

### III. CSV Maps Questionnaire Items to Flowsheet Record IDs

The mapping from a Questionnaire item to its flowsheet record ID lives in a
CSV checked into this repository at `deploy-specific/mapping-input/`. The
CSV's columns are, in order:

1. `CNICS NAME` — a very brief human-friendly label for the item, derived from
   `Questionnaire.item[].text`. Maintained by this team.
2. `RECORD NAME (UCSD Epic)` — the name of the Epic flowsheet record at the
   target site. Supplied by the target site; this team MUST NOT invent it.
3. `LOINC code` — the **join key**. It MUST hold the item's identifier copied
   from `Questionnaire.item[].linkId`, with a single leading `/` removed —
   except for `CIRG-PC-PTSD-5`, whose identifiers keep their leading `/` (e.g.
   `/102011-4`) because many stored QuestionnaireResponses already use that
   form. Tooling MUST match that Questionnaire's rows with the `/` intact. For
   LOINC-based instruments (e.g. PHQ-9) that identifier is the LOINC code; for
   instruments whose items carry no LOINC code (e.g. `AUDIT-1`) it is the
   `linkId` as authored. The column name is retained for continuity.
4. `Flowsheet Record ID` — the Epic flowsheet record ID (e.g. `3025`), valid
   for both the UAT and production systems. Supplied by the target site once
   it has created the flowsheet; blank until then.

Each Questionnaire item is matched to a CSV row by the `LOINC code` column, and
the row supplies that item's flowsheet record ID. The CSV MUST NOT hold
flowsheet FHIR IDs or the per-environment `system` values; the latter are
fixed by Principle I.

**Separator rows**: Each Questionnaire's rows MUST be preceded by a separator
row whose `CNICS NAME` cell is the `Questionnaire.id` (e.g. `CIRG-CNICS-AUDIT`)
and whose other cells are blank. Tooling MUST skip any row whose `LOINC code`
cell is blank, so separator rows are never treated as mappings.

**Which items get a row**: When a Questionnaire is added to the CSV, every item
at any nesting depth gets one row, EXCEPT:

- display-only headers (`item.type` = `"display"`, e.g. `AUDIT-header`);
- items whose `text` states that they are "internal" items (e.g.
  `AUDIT-Q0-score`);
- grouping-only items (`item.type` = `"group"`), which take no answer.

The `http://hl7.org/fhir/StructureDefinition/questionnaire-itemControl`
extension does NOT by itself exclude an item: answerable items that carry it
(e.g. the `ARV-9` slider) get a row like any other.

Rows that already exist with site-supplied values (the PHQ-9 rows) MUST be
retained as they are. Having a CSV row
does not by itself put an item in scope for extraction — Principle IV's
exclusions still apply (the PHQ-9 score rows are mapped but not extracted).

Tooling that injects flowsheet record IDs into Questionnaire JSON MUST read
from this CSV and MUST tolerate imperfect mappings. Specifically:

- If a CSV record's `LOINC code` does not match any item in the Questionnaire,
  the tool MUST emit a WARNING naming the unmatched record and proceed to the
  next mapping.
- If a Questionnaire item has no matching CSV record (or the matched record's
  `Flowsheet Record ID` is blank), the tool MUST emit a WARNING naming the
  item and what was missing, and proceed.

Neither condition is a fatal error. Tooling MUST NOT invent or guess flowsheet
record IDs to fill a gap.

**Rationale**: One record ID serves both environments, so the site supplies a
single value per item and there is no per-environment column to mix up. The
CSV is also the worksheet exchanged with the target site: this team lists the
items it will send (`CNICS NAME`, `LOINC code`), and the site answers with the
flowsheet it built for each (`RECORD NAME (UCSD Epic)`, `Flowsheet Record
ID`). Keying on the item's
`linkId` gives every item a stable key whether or not the instrument is
LOINC-coded, and where it is, the key is the LOINC code clinical reviewers
already know. Separator rows keep a many-instrument file readable. Surfacing
gaps without failing the whole run lets the team make incremental progress on
partially-mapped instruments.

### IV. Fork Each Questionnaire Into Per-Environment Outputs

A Questionnaire enabled for `$extract` MUST be forked into **two** output
Questionnaires — one targeting the UAT system and one targeting production —
rather than encoding both environments' flowsheet codings in a single file.
Both outputs MUST carry the same `Flowsheet Record ID` value as each mapped
item's flowsheet `code`. The UAT output MUST carry only the UAT `system` of
Principle I; the production output MUST carry only the production `system`.
The two outputs MUST NOT differ in any other respect. This is what guarantees
the single-flowsheet-code rule of Principle I.

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

**Rationale**: The target UAT and production systems identify the same
flowsheet record ID under different `system` values and cannot receive an
Observation coded with more than one flowsheet. Forking into two
single-environment files is the representation that satisfies that constraint
cleanly, keeps each file reviewable against the CSV, and removes any ambiguity
about which environment a file is for.

### V. Idempotent, Minimal-Diff Modifications

Any tool that produces these per-environment Questionnaires MUST be idempotent:
re-running it on the same inputs MUST produce byte-identical outputs — no
duplicated entries, no reordered unrelated fields, no whitespace churn, and no
changes outside the metadata the tool owns. The resulting diff MUST be small
enough for a subject-matter expert to verify against the CSV's
`Flowsheet Record ID` column by reading.

**Rationale**: These Questionnaires are reviewed by clinical and informatics
staff. Noisy diffs hide real changes and erode trust in the tooling.

## Extraction Metadata Standards

- The mapping CSV described in Principle III MUST live under
  `deploy-specific/mapping-input/` and MUST include at minimum the columns
  `CNICS NAME`, `RECORD NAME (UCSD Epic)`, `LOINC code`, and
  `Flowsheet Record ID`. Additional columns are permitted and ignored.
- Rows for one Questionnaire MUST be contiguous, in the Questionnaire's item
  order, under that Questionnaire's separator row.
- `RECORD NAME (UCSD Epic)` and `Flowsheet Record ID` MUST be left blank for
  items the target site has not yet built flowsheets for.
- The per-environment flowsheet `system` values of Principle I MUST be defined
  in exactly one place in the tooling, keyed by environment.
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
- Reviewers MUST verify each output's flowsheet codes against the CSV's
  `Flowsheet Record ID` column, and each output's flowsheet `system` against
  the Principle I value for its environment (UAT for the UAT file, production
  for the production file), before approving. Tooling SHOULD make this a
  near-mechanical check.
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
    language, altering the Observation shape, changing the flowsheet identifier
  or its `system`, changing the mapping join key or required CSV columns,
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

**Version**: 4.0.0 | **Ratified**: 2026-05-04 | **Last Amended**: 2026-10-13
