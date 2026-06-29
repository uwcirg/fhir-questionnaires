# Feature Specification: Add `$extract` Metadata to a FHIR Questionnaire

**Feature Branch**: `001-add-extract-metadata`  
**Created**: 2026-05-04  
**Status**: Draft  
**Input**: User description: "Let's work on a spec for a new python script (in /utils) which will modify a FHIR Questionnaire to add the necessary information for a server to run $extract on QuestionnaireResponse, as described in the speckit consitution."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enable `$extract` for one Questionnaire from the CSV mapping (Priority: P1)

An informaticist has a FHIR Questionnaire JSON file in this repository (e.g.,
`CIRG-PHQ-9.json`) and a CSV that maps each in-scope `linkId` of that
Questionnaire to its UAT and production Epic flowsheet IDs. They run a single
command, naming the Questionnaire and the CSV, and get back a modified
Questionnaire JSON whose items carry the metadata that HAPI's `$extract`
operation needs to emit one Observation per answered item. The diff against the
original is small enough for a clinical reviewer to verify by reading.

**Why this priority**: This is the entire reason the tool exists. Without it,
no Questionnaire in this repo can be used to populate Epic flowsheets via
`$extract`. Every other story below is a refinement of this one.

**Independent Test**: Pick one Questionnaire and one CSV row that covers it.
Run the tool. Confirm the resulting JSON, when posted with a matching
`QuestionnaireResponse` to a HAPI server, produces Observations whose
`code.coding` carries the Epic flowsheet IDs from the CSV row, whose
`category` is `vital-signs`, and whose `subject` and `effectiveDateTime` come
from the QuestionnaireResponse.

**Acceptance Scenarios**:

1. **Given** a Questionnaire JSON whose items match `linkId` values that exist
   in the CSV with both UAT and production flowsheet IDs, **When** the tool is
   run on that Questionnaire, **Then** the output Questionnaire JSON contains,
   for each matched in-scope item, the metadata required for `$extract` to
   produce one Observation conforming to the shape mandated by Principle I of
   the constitution (vital-signs category, Epic flowsheet-ID system on
   `code.coding`, subject from QR, effectiveDateTime from QR authored time,
   answer carried in `valueCodeableConcept.coding[].display` for choice/text
   answers and the appropriate `value[x]` for non-choice answers).
2. **Given** a Questionnaire whose `status` is `retired`, or a file living
   under `deprecated/`, or a filename matching `*.deprecated.json`, **When**
   the tool is run on that file, **Then** the tool refuses to modify it and
   exits with a clear message naming the rule that excluded it.
3. **Given** a Questionnaire JSON with display-only items (`item.type` =
   `"display"`) interleaved with answerable items, **When** the tool is run,
   **Then** the display-only items are left untouched and only answerable
   items receive `$extract` metadata.
4. **Given** the tool has already been run on a Questionnaire and the output
   committed, **When** the tool is re-run on that committed output with the
   same CSV, **Then** the output is byte-identical to the input (no duplicated
   metadata, no reordered fields, no whitespace churn).

---

### User Story 2 - Surface gaps without inventing data (Priority: P1)

The CSV is the source of truth for flowsheet IDs and is, in practice, sparsely
populated: some `linkId`s have only a UAT ID, some have only a production ID,
some are missing entirely. The user needs to see exactly which items lacked
which IDs in a single run, without the tool refusing to do partial work and
without the tool guessing values to fill the gaps.

**Why this priority**: Silent gap-filling is the failure mode that sends test
data into production flowsheets, which is precisely what Principle III is
written to prevent. Equally, refusing to produce any output when the CSV is
incomplete would block the team from making incremental progress on
mostly-mapped Questionnaires.

**Independent Test**: Run the tool against a Questionnaire and a CSV in which
some matched `linkId`s have only a UAT ID, some have only a production ID,
some appear with no IDs, and some `linkId`s in the Questionnaire are absent
from the CSV altogether. Confirm: (a) every gap is reported as a per-item
warning that names the `linkId` and what was missing; (b) items that did have
IDs were still updated correctly; (c) no fabricated IDs appear anywhere in
the output.

**Acceptance Scenarios**:

1. **Given** an in-scope `linkId` whose CSV row has a UAT ID but no production
   ID, **When** the tool runs, **Then** the output Questionnaire records the
   UAT ID with an unambiguous environment label and the run emits a warning
   naming the `linkId` and the missing production ID.
2. **Given** an in-scope `linkId` that appears nowhere in the CSV, **When**
   the tool runs, **Then** no `$extract` metadata is added for that item and
   the run emits a warning naming the missing `linkId`.
3. **Given** any combination of gaps described above, **When** the tool
   finishes, **Then** the process exits with a non-zero status only if the
   Questionnaire could not be written at all; gaps alone do not cause a
   non-zero exit, but every gap appears in the run's warning output.

---

### User Story 3 - Preserve upstream-owned `SCORE` items (Priority: P2)

Some Questionnaires include items whose `linkId` contains `SCORE` and which
carry an `sdc-questionnaire-calculatedExpression` extension. Those expressions
are owned by the form filler and must not be touched, but the score itself
must still appear on the Epic flowsheet, so those items still need
`$extract` metadata.

**Why this priority**: Constitution Principle IV makes this an explicit
boundary. Implementing the rest of the tool without honoring it would silently
break working forms the first time the tool is pointed at a scored
Questionnaire (e.g., `CIRG-PHQ-9.json`).

**Independent Test**: Run the tool on a Questionnaire that contains at least
one item whose `linkId` includes `SCORE` and which carries a
`calculatedExpression` extension. Confirm the resulting item still contains
that extension, byte-identical to the input, while also carrying the new
flowsheet-ID metadata required by `$extract`.

**Acceptance Scenarios**:

1. **Given** an item whose `linkId` contains `SCORE` and which has a
   `calculatedExpression` extension, **When** the tool runs and the CSV
   provides flowsheet IDs for that `linkId`, **Then** the
   `calculatedExpression` extension is preserved unchanged and the
   flowsheet-ID metadata is added alongside it.
2. **Given** the same item, **When** the tool runs and the CSV does NOT
   provide flowsheet IDs for that `linkId`, **Then** the
   `calculatedExpression` extension is preserved unchanged and a warning is
   emitted that the score will not appear on the flowsheet until the CSV is
   filled in.

---

### Edge Cases

- A Questionnaire has nested items (groups containing items containing items).
  In-scope answerable items at any nesting depth must receive metadata; the
  group items themselves do not.
- A Questionnaire item's `linkId` matches a CSV row, but the item is of a
  type for which Epic does not accept the answer (e.g., an attachment).
  Treated as out-of-scope; emit a per-item warning rather than producing
  metadata that would fail at extract time.
- The same `linkId` appears more than once in the CSV with conflicting
  flowsheet IDs. The tool must refuse to silently pick one; it must emit an
  error that names the `linkId` and the conflicting rows and leave the item
  unmodified.
- The Questionnaire file is malformed JSON, or is JSON but is not a FHIR
  Questionnaire resource (`resourceType` != `"Questionnaire"`). The tool must
  exit non-zero with a message identifying the file and the problem, without
  writing any output.
- The CSV is missing required columns (`questionnaire_code`, `link_id`,
  `flowsheet_id_uat`, `flowsheet_id_prod`). The tool must exit non-zero
  before touching any Questionnaire and name the missing column(s).
- The Questionnaire's `code` does not appear in any
  `questionnaire_code` value in the CSV. The tool must exit non-zero with a
  message stating the Questionnaire is unmapped, rather than producing a file
  with no metadata.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The tool MUST accept, as inputs to a single run, the path to one
  Questionnaire JSON file and the path to the flowsheet-ID CSV; it MUST NOT
  process more than one Questionnaire per invocation.
- **FR-002**: The tool MUST identify which CSV rows apply to the given
  Questionnaire by matching the Questionnaire's `code` against the CSV's
  `questionnaire_code` column.
- **FR-003**: For each in-scope item in the Questionnaire whose `linkId`
  matches a CSV row, the tool MUST add the metadata required for HAPI's
  `$extract` to emit one Observation per answered item, where that
  Observation conforms to the shape defined in Constitution Principle I:
  `category[0].coding[0]` = `{ system:
  "http://hl7.org/fhir/observation-category", code: "vital-signs" }`,
  `code.coding[0].system` =
  `http://open.epic.com/FHIR/StructureDefinition/observation-flowsheet-id`,
  `code.coding[0].code` = the Epic flowsheet ID for that `linkId`, `subject`
  derived from the QR's subject, `effectiveDateTime` derived from the QR's
  authored timestamp, and `valueCodeableConcept.coding[].display` (for
  choice/text answers) or the appropriate `value[x]` (for other answer types)
  carrying the answer.
- **FR-004**: The tool MUST express any extraction logic in JSONPath. The tool
  MUST NOT introduce CQL.
- **FR-005**: The tool MUST embed flowsheet IDs in the Questionnaire in a way
  that unambiguously labels each ID as either UAT or production, so that the
  two environments cannot be confused by a downstream reader.
  [NEEDS CLARIFICATION: which concrete representation should the tool emit
  to disambiguate UAT vs production flowsheet IDs — two `code.coding` entries
  with distinct `system` URLs per environment, an environment-tagging
  extension, separate output files per environment, or another option? The
  constitution leaves this open and asks the tool to pick one explicit
  representation and surface its choice in its output.]
- **FR-006**: The tool MUST treat as out-of-scope and skip without
  modification: items with `item.type = "display"`, items whose `linkId` does
  not appear in the CSV for this Questionnaire, items whose answer type is
  not extractable to an Epic flowsheet row, and entire Questionnaires that
  are deprecated (file is under `deprecated/`, filename matches
  `*.deprecated.json`, or `Questionnaire.status = "retired"`).
- **FR-007**: For every in-scope item that does NOT receive complete metadata
  (because the CSV row is missing, or is missing the UAT ID, or is missing
  the production ID), the tool MUST emit a per-item warning that names the
  `linkId` and what is missing, and MUST proceed with whatever IDs are
  available. The tool MUST NOT invent or guess flowsheet IDs.
- **FR-008**: For items whose `linkId` contains the substring `SCORE` and
  which carry the
  `http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-calculatedExpression`
  extension, the tool MUST add `$extract` metadata alongside the existing
  extension and MUST NOT modify, delete, or rewrite the
  `calculatedExpression` FHIRPath itself.
- **FR-009**: The tool MUST be idempotent: running it a second time on its
  own output, with the same CSV, MUST produce a byte-identical file. It MUST
  NOT duplicate metadata entries, reorder unrelated fields, or alter content
  outside the metadata it owns.
- **FR-010**: The tool MUST exit non-zero, without writing output, when: the
  input file is not valid JSON; the input file is not a `Questionnaire`
  resource; the CSV is missing any required column; the Questionnaire's
  `code` is not present anywhere in the CSV; or two or more CSV rows assign
  conflicting flowsheet IDs to the same `linkId`. In every such case the
  message MUST identify the file and the specific problem.
- **FR-011**: At the end of every successful run, the tool MUST surface, in
  its own output, the choice of representation it used for UAT vs production
  flowsheet IDs (per FR-005) so a reviewer can verify it without re-reading
  the source.
- **FR-012**: Bulk processing of multiple Questionnaires MUST be expressed by
  the user as a loop over single-Questionnaire runs of this tool, so that a
  failure on one file does not silently skip or corrupt others.

### Key Entities *(include if feature involves data)*

- **Questionnaire (input)**: A FHIR R4 `Questionnaire` resource stored as
  JSON in this repository. Carries a `code` identifying the instrument and a
  tree of `item` entries each with a `linkId` and a `type`.
- **Flowsheet-ID CSV (input)**: A repository-checked CSV where each row pairs
  a `(questionnaire_code, link_id)` with that item's `flowsheet_id_uat` and
  `flowsheet_id_prod`. Sparse population is expected and tolerated.
- **Modified Questionnaire (output)**: The same `Questionnaire` resource with
  added per-item metadata sufficient for HAPI `$extract` to produce
  Observations matching the constitution's required shape. Diff vs. input is
  minimal and contains no changes outside the metadata this tool owns.
- **Run report (output)**: The set of human-readable warnings and the
  declaration of the UAT-vs-production representation used in this run,
  emitted to the user during the run.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a Questionnaire whose CSV mapping is fully populated, a
  reviewer can confirm in under 5 minutes, by reading the diff alongside the
  CSV, that every in-scope `linkId` received the correct flowsheet IDs and
  no other content changed.
- **SC-002**: 100% of in-scope items that the CSV maps with both UAT and
  production IDs receive complete `$extract` metadata in the output; 0% of
  items receive a fabricated or guessed flowsheet ID under any combination of
  CSV gaps.
- **SC-003**: Re-running the tool on its own output, with the same CSV,
  produces a byte-identical file in 100% of cases.
- **SC-004**: For any item that did not receive complete metadata, a single
  `linkId`-named warning appears in the run output identifying exactly what
  was missing, with no warning being silently swallowed.
- **SC-005**: When pointed at a deprecated, retired, or non-Questionnaire
  input, the tool refuses to write any output and names the rule that
  excluded the file in 100% of cases.
- **SC-006**: For a Questionnaire containing `SCORE` items with
  `calculatedExpression`, the `calculatedExpression` value in the output is
  byte-identical to the input in 100% of cases.

## Assumptions

- The tool is run by an informaticist or developer from the repository root,
  on demand per Questionnaire, not on a schedule and not as a server. Bulk
  runs are performed by shell loops over this tool, per the constitution's
  "Extraction Metadata Standards" section.
- The flowsheet-ID CSV lives inside this repository and is the single source
  of truth for the mapping, per Constitution Principle III. Its precise path
  is not yet fixed by the constitution, so the tool accepts the CSV path as
  an input rather than hardcoding it.
- The CSV's required columns are exactly those named by the constitution
  (`questionnaire_code`, `link_id`, `flowsheet_id_uat`, `flowsheet_id_prod`).
  Additional columns are permitted and are ignored by this tool.
- The Questionnaire `code` is a stable identifier suitable for matching the
  CSV's `questionnaire_code` column. If a Questionnaire carries multiple
  `code.coding` entries, the tool matches against any of them and treats a
  match on any entry as a match for the Questionnaire as a whole.
- The HAPI server that will execute `$extract` is the consumer of the
  modified Questionnaire and is the authority on whether the metadata is
  sufficient; this tool's correctness is judged against that consumer's
  behavior (Constitution Principle I), not against an internal extraction
  engine in this tool.
- The encoding of UAT vs production flowsheet IDs inside the Questionnaire
  is treated as an open question the constitution explicitly defers
  (`TODO(UAT_VS_PROD_REPRESENTATION)`); the answer to FR-005 above will
  determine the exact JSON shape the tool emits but does not change any
  other requirement in this spec.
- Existing utilities under `/utils` (e.g., `remove_item_extensions.py`) are
  the precedent for how single-file Questionnaire transformations are
  packaged and invoked in this repo; the new tool is expected to fit that
  same shape.
