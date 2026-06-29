# Feature Specification: Fork a FHIR Questionnaire Into Per-Environment `$extract` Outputs

**Feature Branch**: `001-add-extract-metadata`  
**Created**: 2026-05-04  
**Last Updated**: 2026-06-29  
**Status**: Draft  
**Input**: User description: "A python script (in /utils) which reads a FHIR Questionnaire
and a CSV mapping each item's LOINC code to UAT and production flowsheet FHIR IDs, and
outputs two new Questionnaires — one for the UAT EMR and one for production — each carrying
a single flowsheet code per item, so a server can run `$extract` on QuestionnaireResponse."
Revised 2026-06-29 to align with Constitution v2.0.0.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fork one Questionnaire into UAT and production outputs (Priority: P1)

An informaticist has a FHIR Questionnaire JSON file in this repository (e.g.,
`CIRG-PHQ-9.json`) and the CSV at
`deploy-specific/mapping-input/CNICS PRO UCSD flowsheet FHIR IDs.csv` that maps
each in-scope item's LOINC code to its UAT and production flowsheet FHIR IDs.
They run a single command, naming the Questionnaire and the CSV, and get back
**two** new Questionnaire JSON files — one written under
`deploy-specific/ucsd-uat/` carrying only UAT flowsheet IDs, and one under
`deploy-specific/ucsd-prod/` carrying only production flowsheet IDs. Each output
carries the metadata that HAPI's `$extract` operation needs to emit one
Observation per answered individual-response item, where each Observation is
coded with exactly one flowsheet ID.

**Why this priority**: This is the entire reason the tool exists. The target UAT
and production systems use different flowsheet FHIR IDs and cannot accept an
Observation coded with more than one flowsheet, so a single dual-coded file is
not usable. Without the fork, no Questionnaire in this repo can populate either
environment's flowsheets via `$extract`. Every other story is a refinement of
this one.

**Independent Test**: Pick one Questionnaire and the CSV. Run the tool. Confirm
two files are produced, one per environment directory; that each output's
in-scope items carry the flowsheet ID from the matching CSV column for that
environment (`FHIR ID - UAT` in the UAT file, `FHIR ID - Prod` in the prod
file); and that, when each file is posted with a matching
`QuestionnaireResponse` to a HAPI server, it produces Observations whose
`code.coding` carries exactly one flowsheet code, whose `category` is
`vital-signs`, and whose `subject` and `effectiveDateTime` come from the
QuestionnaireResponse.

**Acceptance Scenarios**:

1. **Given** a Questionnaire whose in-scope items carry LOINC codes that appear
   in the CSV `LOINC code` column with both a UAT and a production FHIR ID,
   **When** the tool is run on that Questionnaire, **Then** two output
   Questionnaires are written — one under `deploy-specific/ucsd-uat/` and one
   under `deploy-specific/ucsd-prod/` — and each matched item carries the
   metadata required for `$extract` to produce one Observation conforming to
   Constitution Principle I (vital-signs category; exactly one
   `code.coding` flowsheet entry whose `code` is that environment's flowsheet
   FHIR ID; subject from QR; effectiveDateTime from QR authored time; answer
   carried in `valueCodeableConcept.coding[].display` for choice/text answers
   and the appropriate `value[x]` for non-choice answers).
2. **Given** any in-scope item, **When** the tool produces the two outputs,
   **Then** the UAT output contains only `FHIR ID - UAT` values and the
   production output contains only `FHIR ID - Prod` values, and neither output
   contains an Observation coded with more than one flowsheet.
3. **Given** a Questionnaire whose `status` is `retired`, or a file living
   under `deprecated/`, or a filename matching `*.deprecated.json`, **When**
   the tool is run on that file, **Then** the tool refuses to produce outputs
   and exits with a clear message naming the rule that excluded it.
4. **Given** a Questionnaire JSON with display-only items (`item.type` =
   `"display"`) interleaved with answerable items, **When** the tool is run,
   **Then** the display-only items receive no flowsheet metadata in either
   output and only answerable individual-response items are mapped.
5. **Given** the tool has already been run and its two outputs committed,
   **When** the tool is re-run on the same inputs, **Then** both outputs are
   byte-identical to the committed versions (no duplicated metadata, no
   reordered fields, no whitespace churn).

---

### User Story 2 - Surface mapping gaps without inventing data (Priority: P1)

The CSV is the source of truth for flowsheet IDs and is, in practice, sparsely
populated. The user needs to see, in a single run, exactly which mappings did
not line up — in both directions — without the tool refusing to do partial work
and without the tool guessing values to fill gaps.

**Why this priority**: Silent gap-filling is the failure mode that sends test
data into production flowsheets, which is precisely what Constitution
Principle III prevents. Equally, refusing to produce any output when the CSV is
incomplete would block the team from making incremental progress on
mostly-mapped Questionnaires.

**Independent Test**: Run the tool against a Questionnaire and a CSV in which
some CSV records' LOINC codes match no Questionnaire item, some Questionnaire
items' LOINC codes appear nowhere in the CSV, and some matched records are
missing a UAT or production FHIR ID. Confirm: (a) every mismatch is reported as
a warning naming the unmatched record or item and what was missing; (b) items
that did map were still written correctly in both outputs; (c) no fabricated IDs
appear anywhere.

**Acceptance Scenarios**:

1. **Given** a CSV record whose `LOINC code` does not match any item in the
   Questionnaire, **When** the tool runs, **Then** it emits a warning naming
   the unmatched record and proceeds to the next mapping.
2. **Given** a Questionnaire item whose LOINC code appears nowhere in the CSV,
   **When** the tool runs, **Then** no flowsheet metadata is added for that
   item in either output and the tool emits a warning naming the item.
3. **Given** a matched CSV record that has a UAT FHIR ID but no production FHIR
   ID (or vice versa), **When** the tool runs, **Then** the available ID is
   written into the corresponding environment's output, the other environment's
   output omits flowsheet metadata for that item, and a warning names the item
   and the missing ID.
4. **Given** any combination of the gaps above, **When** the tool finishes,
   **Then** it exits non-zero only if the outputs could not be written at all;
   gaps alone do not cause a non-zero exit, but every gap appears in the
   warnings.

---

### User Story 3 - Exclude computed score items (Priority: P2)

Some Questionnaires include items whose value is a computed score (e.g., a total
whose `linkId` carries an `sdc-questionnaire-calculatedExpression`). The target
EMRs only need Observations for the individual responses, not the scores. Those
score items must be left untouched in both outputs.

**Why this priority**: Constitution Principle I (and Principle IV's exclusion
list) makes scores out of scope for extraction. Emitting score Observations
would push values the EMR does not want; modifying the score items would risk
breaking working forms whose `calculatedExpression` is owned by the form filler.

**Independent Test**: Run the tool on a Questionnaire that contains at least one
computed score item (e.g., `CIRG-PHQ-9.json`). Confirm that neither output adds
flowsheet metadata to the score item and that the score item — including any
`calculatedExpression` extension — is byte-identical to the input in both
outputs.

**Acceptance Scenarios**:

1. **Given** a computed score item, **When** the tool runs, **Then** no
   flowsheet metadata is added to that item in either output and the item is
   left byte-for-byte unchanged.
2. **Given** a computed score item that nonetheless has a LOINC code present in
   the CSV, **When** the tool runs, **Then** the score item is still excluded
   from extraction and the tool emits a warning that the matched CSV record was
   skipped because it maps to a score item.

---

### Edge Cases

- A Questionnaire has nested items (groups containing items). In-scope
  answerable items at any nesting depth are mapped by their LOINC code; group
  items themselves receive no flowsheet metadata.
- A Questionnaire item carries no LOINC code at all. It cannot be matched to the
  CSV; the tool emits a warning naming the item and leaves it unmodified in both
  outputs.
- A Questionnaire item's LOINC code matches a CSV record, but the item is of a
  type for which the EMR does not accept the answer (e.g., an attachment).
  Treated as out-of-scope; the tool emits a warning rather than producing
  metadata that would fail at extract time.
- The same LOINC code appears more than once in the CSV with conflicting
  flowsheet IDs. The tool MUST NOT silently pick one; it emits a warning naming
  the LOINC code and the conflicting records, leaves that item unmodified in
  both outputs, and proceeds.
- The Questionnaire file is malformed JSON, or is JSON but is not a FHIR
  Questionnaire resource (`resourceType` != `"Questionnaire"`). The tool exits
  non-zero with a message identifying the file and the problem, without writing
  any output.
- The CSV is missing a required column (`RECORD NAME`, `LOINC code`,
  `FHIR ID - UAT`, `FHIR ID - Prod`). The tool exits non-zero before writing any
  output and names the missing column(s).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The tool MUST accept, as inputs to a single run, the path to one
  Questionnaire JSON file and the path to the flowsheet-ID CSV; it MUST NOT
  process more than one Questionnaire per invocation.
- **FR-002**: The tool MUST match each in-scope Questionnaire item to a CSV
  record by the item's **LOINC code** against the CSV's `LOINC code` column.
- **FR-003**: The tool MUST produce **two** output Questionnaires from the
  single input: one written under `deploy-specific/ucsd-uat/` carrying only
  `FHIR ID - UAT` values, and one written under `deploy-specific/ucsd-prod/`
  carrying only `FHIR ID - Prod` values.
- **FR-004**: For each in-scope item that matches a CSV record, the tool MUST
  add, in each environment output, the metadata required for HAPI's `$extract`
  to emit one Observation per answered item conforming to Constitution
  Principle I: `category[0].coding[0]` = `{ system:
  "http://hl7.org/fhir/observation-category", code: "vital-signs" }`;
  `code.coding` containing **exactly one** flowsheet coding whose `system` =
  `http://open.epic.com/FHIR/StructureDefinition/observation-flowsheet-id` and
  whose `code` = that environment's flowsheet FHIR ID for the item; `subject`
  derived from the QR's subject; `effectiveDateTime` derived from the QR's
  authored timestamp; and `valueCodeableConcept.coding[].display` (for
  choice/text answers) or the appropriate `value[x]` (for other answer types)
  carrying the answer.
- **FR-005**: No Observation produced by either output may be coded with more
  than one flowsheet. The UAT output and the production output MUST NOT share or
  cross-contaminate flowsheet IDs.
- **FR-006**: The tool MUST express any extraction logic in JSONPath. The tool
  MUST NOT introduce CQL.
- **FR-007**: The tool MUST treat as out-of-scope and add no flowsheet metadata
  for: computed **score** items; items with `item.type = "display"`; items
  whose LOINC code does not appear in the CSV; items whose answer type is not
  extractable to a flowsheet row; and items carrying no LOINC code. The tool
  MUST leave all such items byte-for-byte unchanged in both outputs. Entire
  Questionnaires that are deprecated (file under `deprecated/`, filename
  matching `*.deprecated.json`, or `Questionnaire.status = "retired"`) MUST be
  skipped without producing outputs.
- **FR-008**: For every CSV record whose `LOINC code` matches no item in the
  Questionnaire, and for every in-scope item whose LOINC code matches no CSV
  record (or matches a record missing the UAT or production ID), the tool MUST
  emit a warning naming the unmatched record or item and what is missing, and
  MUST proceed to the next mapping. The tool MUST NOT invent or guess flowsheet
  IDs.
- **FR-009**: When the same LOINC code appears in the CSV with conflicting
  flowsheet IDs, the tool MUST emit a warning naming the LOINC code and the
  conflicting records, leave that item unmodified in both outputs, and proceed.
- **FR-010**: The tool MUST be idempotent: running it again on the same inputs
  MUST produce byte-identical outputs in both environment directories. It MUST
  NOT duplicate metadata entries, reorder unrelated fields, or alter content
  outside the metadata it owns.
- **FR-011**: The tool MUST exit non-zero, without writing any output, when: the
  input file is not valid JSON; the input file is not a `Questionnaire`
  resource; or the CSV is missing any required column (`RECORD NAME`,
  `LOINC code`, `FHIR ID - UAT`, `FHIR ID - Prod`). In every such case the
  message MUST identify the file and the specific problem.
- **FR-012**: Bulk processing of multiple Questionnaires MUST be expressed by
  the user as a loop over single-Questionnaire runs of this tool, so that a
  failure on one file does not silently skip or corrupt others.

### Key Entities *(include if data involved)*

- **Questionnaire (input)**: A FHIR R4 `Questionnaire` resource stored as JSON
  in this repository. Carries a tree of `item` entries, each of which may carry
  a LOINC `code` used to join against the CSV.
- **Flowsheet-ID CSV (input)**: The repository-checked CSV at
  `deploy-specific/mapping-input/CNICS PRO UCSD flowsheet FHIR IDs.csv` with
  columns `RECORD NAME`, `LOINC code`, `FHIR ID - UAT`, `FHIR ID - Prod`. Each
  row maps one LOINC code to its UAT and production flowsheet FHIR IDs. Sparse
  population is expected and tolerated.
- **UAT Questionnaire (output)**: The input Questionnaire with per-item
  metadata carrying only `FHIR ID - UAT` flowsheet codes, written under
  `deploy-specific/ucsd-uat/`. Each in-scope item yields one Observation coded
  with a single UAT flowsheet.
- **Production Questionnaire (output)**: The same, carrying only `FHIR ID - Prod`
  flowsheet codes, written under `deploy-specific/ucsd-prod/`.
- **Run report (output)**: The set of human-readable warnings emitted during the
  run, covering every CSV record and Questionnaire item that did not map.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a Questionnaire whose CSV mapping is fully populated, a
  reviewer can confirm in under 5 minutes, by reading each output alongside the
  matching CSV column, that every in-scope item received the correct flowsheet
  ID for that environment and no other content changed.
- **SC-002**: 100% of Observations produced by either output are coded with
  exactly one flowsheet; 0% carry more than one flowsheet code.
- **SC-003**: 0% of items receive a fabricated or guessed flowsheet ID under any
  combination of CSV gaps.
- **SC-004**: Re-running the tool on the same inputs produces byte-identical
  outputs in both environment directories in 100% of cases.
- **SC-005**: For every CSV record and every in-scope item that does not map, a
  single warning naming it and what was missing appears in the run output, with
  no mismatch being silently swallowed.
- **SC-006**: When pointed at a deprecated, retired, or non-Questionnaire input,
  the tool refuses to write any output and names the rule that excluded the file
  in 100% of cases.
- **SC-007**: For a Questionnaire containing computed score items, neither
  output adds flowsheet metadata to a score item, and each score item
  (including any `calculatedExpression`) is byte-identical to the input in 100%
  of cases.

## Assumptions

- The tool is run by an informaticist or developer from the repository root, on
  demand per Questionnaire, not on a schedule and not as a server. Bulk runs are
  performed by shell loops over this tool, per the constitution's "Extraction
  Metadata Standards" section.
- The flowsheet-ID CSV lives at
  `deploy-specific/mapping-input/CNICS PRO UCSD flowsheet FHIR IDs.csv` and is
  the single source of truth for the mapping, per Constitution Principle III.
- The CSV's required columns are exactly `RECORD NAME`, `LOINC code`,
  `FHIR ID - UAT`, and `FHIR ID - Prod`. Additional columns are permitted and
  ignored. The `RECORD NAME` column is descriptive and is not used for matching.
- A Questionnaire item is matched to the CSV by a LOINC `code.coding` entry
  (system `http://loinc.org`). An item with no LOINC code cannot be matched and
  is reported as a gap.
- A "computed score item" is identified by carrying an
  `sdc-questionnaire-calculatedExpression` extension (consistent with how scores
  are computed by the form filler); such items are excluded from extraction.
- The flowsheet coding `system` remains
  `http://open.epic.com/FHIR/StructureDefinition/observation-flowsheet-id` per
  Constitution Principle I; the UAT and production environments differ only in
  the flowsheet ID `code`, supplied by the CSV's two ID columns.
- The HAPI server that will execute `$extract` is the consumer of each output
  and is the authority on whether the metadata is sufficient; this tool's
  correctness is judged against that consumer's behavior (Constitution
  Principle I), not against an internal extraction engine in this tool.
- Existing utilities under `/utils` (e.g., `remove_item_extensions.py`) are the
  precedent for how single-file Questionnaire transformations are packaged and
  invoked in this repo; the new tool is expected to fit that same shape.
