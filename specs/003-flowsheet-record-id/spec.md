# Feature Specification: Code Per-Environment Questionnaires With the Flowsheet Record ID

**Feature Branch**: `003-flowsheet-record-id`
**Created**: 2026-10-13
**Status**: Draft
**Input**: User description: "update fork tool and tests to use flowsheet record ID"

## Background

Constitution v4.0.0 corrected a misunderstanding: writing to Epic does not require
the flowsheet FHIR ID. Each Epic deployment mints its own FHIR ID for a flowsheet,
whereas the flowsheet record ID is the same across a healthcare organization's
deployments. Observations are therefore coded with the record ID, qualified by a
`system` that differs between UAT and production.

The mapping file already reflects this (one `Flowsheet Record ID` column in place of
the two FHIR ID columns). The fork tool, its tests, and the checked-in PHQ-9 outputs
still follow the old scheme, so the tool cannot read the current mapping file and the
automated checks fail. This feature brings them into line.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate per-environment Questionnaires coded with the record ID (Priority: P1)

A CNICS developer runs the fork tool on a source Questionnaire with the current
mapping file and gets a UAT Questionnaire and a production Questionnaire. In both,
each mapped item carries one flowsheet coding whose code is the item's flowsheet
record ID. The UAT file uses the UAT system; the production file uses the production
system. Nothing else differs between the two files.

**Why this priority**: Today the tool rejects the current mapping file outright, so no
per-environment Questionnaire can be produced at all. This story restores the tool's
only purpose under the corrected coding scheme.

**Independent Test**: Run the tool on `CIRG-PHQ-9.json` with the checked-in mapping
file and inspect the two outputs: the nine PHQ-9 response items that match a mapping
row each carry their record ID (e.g. `3025` for "Little interest or pleasure") under
the right system for that file, and comparing the two files shows differences only in
the system value.

**Acceptance Scenarios**:

1. **Given** the current four-column mapping file and `CIRG-PHQ-9.json`, **When** the
   tool is run, **Then** it completes successfully and writes one UAT and one
   production Questionnaire.
2. **Given** the item with identifier `44250-9` mapped to record ID `3025`, **When**
   the UAT output is inspected, **Then** that item has exactly one flowsheet coding,
   with code `3025` and system `urn:oid:1.2.840.114350.1.13.136.3.7.2.707679`.
3. **Given** the same item, **When** the production output is inspected, **Then** its
   flowsheet coding has code `3025` and system
   `urn:oid:1.2.840.114350.1.13.136.2.7.2.707679`.
4. **Given** both outputs, **When** they are compared, **Then** the only differences
   are the flowsheet coding system values.
5. **Given** either output, **When** it is searched, **Then** it contains no flowsheet
   FHIR ID and no coding under
   `http://open.epic.com/FHIR/StructureDefinition/observation-flowsheet-id`.
6. **Given** the PHQ-9 computed total (`44261-6`), which has a record ID in the
   mapping file, **When** the outputs are inspected, **Then** that item carries no
   flowsheet coding and is unchanged from the source, as before.
7. **Given** unchanged inputs, **When** the tool is run a second time, **Then** both
   outputs are byte-identical to the first run.

---

### User Story 2 - Mapping gaps are reported in record-ID terms (Priority: P2)

A CNICS developer runs the tool on a Questionnaire whose items UCSD has not yet
supplied record IDs for (true of every Questionnaire except PHQ-9 today). The run
succeeds, and the warnings say plainly which items lack a flowsheet record ID. Because
one record ID serves both environments, each gap is reported once, not once per
environment.

**Why this priority**: 19 of the 20 mapped Questionnaires are still waiting on UCSD.
Clear, non-duplicated gap reporting is what lets the team track that hand-off, but it
is secondary to producing correct output for the items that are mapped.

**Independent Test**: Run the tool on `CIRG-CNICS-AUDIT.json` with the checked-in
mapping file: the run succeeds, every listed item is reported once as lacking a
flowsheet record ID, and neither output contains any flowsheet coding.

**Acceptance Scenarios**:

1. **Given** an item whose mapping row has a blank `Flowsheet Record ID`, **When** the
   tool is run, **Then** exactly one warning names the item and states that its
   flowsheet record ID is missing, and the item is left unchanged in both outputs.
2. **Given** a mapping file that lacks the `Flowsheet Record ID` column (for example a
   file still in the old two-FHIR-ID layout), **When** the tool is run, **Then** it
   stops with an error naming the missing column and writes no output.
3. **Given** a mapping file with the same identifier on two rows carrying different
   record IDs, **When** the tool is run, **Then** a warning reports the conflict and
   the item is left unchanged in both outputs.
4. **Given** a mapping file with extra columns beyond the required ones, **When** the
   tool is run, **Then** the extra columns are ignored.
5. **Given** any mapping gap, **When** the tool is run, **Then** no record ID is
   invented and the run still completes successfully.

---

### User Story 3 - Checked-in artifacts and automated checks match the new scheme (Priority: P3)

A reviewer opening the repository finds the deployed PHQ-9 Questionnaires for UAT and
production coded with record IDs, and the automated checks passing against the current
mapping file. A reviewer can verify each PHQ-9 output by reading it against the single
`Flowsheet Record ID` column.

**Why this priority**: These are the artifacts actually delivered to UCSD and the
safety net for future changes, but they follow mechanically once Stories 1 and 2 hold.

**Independent Test**: Run the full automated check suite and confirm zero failures;
regenerate the PHQ-9 outputs and confirm they are identical to the checked-in files.

**Acceptance Scenarios**:

1. **Given** the repository after this feature, **When** the automated checks are run,
   **Then** all pass.
2. **Given** the checked-in UAT and production PHQ-9 Questionnaires, **When** the tool
   is re-run on `CIRG-PHQ-9.json`, **Then** the outputs are byte-identical to the
   checked-in files.
3. **Given** the checks that validate the mapping file, **When** they run, **Then**
   they require exactly the four columns `CNICS NAME`, `RECORD NAME (UCSD Epic)`,
   `LOINC code`, `Flowsheet Record ID`, and pin the twelve site-supplied PHQ-9 rows
   (record name, identifier, record ID) against accidental change.
4. **Given** the tool's usage text and the repository README, **When** read, **Then**
   they describe the record-ID scheme and no longer say the tool is out of date.

---

### Edge Cases

- A source item already carries a coding under the target environment's flowsheet
  system: the tool does not add a second one.
- A source item already carries other codings (e.g. its LOINC coding): they are kept,
  and the flowsheet coding is added alongside them.
- A record ID cell contains surrounding whitespace: it is trimmed before use.
- A Questionnaire in which no item has a record ID: both outputs are written with no
  extraction metadata at all (no per-item flags, no category declaration).
- A mapping row matches no item in the Questionnaire being forked (every other
  Questionnaire's rows, in practice): it is reported exactly as it is today.
- Separator rows (blank identifier) are skipped and never treated as mappings.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The tool MUST read each item's flowsheet identifier from the mapping
  file's `Flowsheet Record ID` column, matching items to rows by the `LOINC code`
  column as it does today.
- **FR-002**: The tool MUST require the columns `RECORD NAME (UCSD Epic)`,
  `LOINC code`, and `Flowsheet Record ID`; if any is absent it MUST stop with an error
  naming the missing column(s) and write no output. It MUST NOT require or read the
  former `FHIR ID - UAT` and `FHIR ID - Prod` columns.
- **FR-003**: For every in-scope mapped item, each output MUST carry exactly one
  flowsheet coding whose code is the item's flowsheet record ID, identical in the UAT
  and production outputs.
- **FR-004**: The flowsheet coding's system MUST be
  `urn:oid:1.2.840.114350.1.13.136.3.7.2.707679` in the UAT output and
  `urn:oid:1.2.840.114350.1.13.136.2.7.2.707679` in the production output. These two
  values MUST be defined in exactly one place, keyed by environment.
- **FR-005**: The tool MUST NOT emit any flowsheet FHIR ID or any coding under
  `http://open.epic.com/FHIR/StructureDefinition/observation-flowsheet-id`.
- **FR-006**: The UAT and production outputs for one source Questionnaire MUST differ
  only in the flowsheet coding system values.
- **FR-007**: When a matched row's `Flowsheet Record ID` is blank, the tool MUST emit
  one warning naming the item and the missing record ID, leave the item unchanged in
  both outputs, and continue. It MUST NOT invent a value.
- **FR-008**: When one identifier appears on multiple rows with differing record IDs,
  the tool MUST warn of the conflict and leave the item unchanged in both outputs.
- **FR-009**: All behaviour not concerned with which identifier and system are written
  MUST be preserved: which items are in or out of scope, the per-item extraction flag,
  the `vital-signs` category declaration, input guards (deprecated, retired, invalid
  input), warnings for unmatched rows and unmapped items, exit status, output
  locations, and byte-stable idempotent output.
- **FR-010**: The checked-in UAT and production PHQ-9 Questionnaires MUST be
  regenerated so that they are exactly what the updated tool produces from
  `CIRG-PHQ-9.json` and the checked-in mapping file.
- **FR-011**: The automated checks for the tool MUST assert the record-ID scheme: the
  correct code and per-environment system on mapped items, absence of the old system
  and FHIR IDs, a single warning per missing record ID, the missing-column error, and
  that the two outputs differ only in system.
- **FR-012**: The automated checks for the mapping file MUST assert the four-column
  layout and pin the twelve site-supplied PHQ-9 rows, including their record IDs.
- **FR-013**: The tool's usage text and the README entry for the tool MUST describe the
  record-ID scheme; the README note that the tool is out of date MUST be removed.

### Key Entities

- **Mapping row**: one reportable Questionnaire item — brief label, Epic record name,
  identifier (join key), and flowsheet record ID. The record ID is blank until UCSD
  supplies it and is valid for both environments.
- **Flowsheet coding**: the single coding added to a mapped item — a code (the record
  ID) and a system (determined by the target environment).
- **Environment**: UAT or production. Each has a fixed flowsheet system value and an
  output location; it no longer has its own identifier per item.
- **Per-environment Questionnaire**: a generated copy of a source Questionnaire for
  one environment, carrying flowsheet codings for that environment only.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Running the tool on `CIRG-PHQ-9.json` with the checked-in mapping file
  succeeds and yields 9 items carrying a flowsheet coding in each output — the same 9
  items as before this feature — every one matching its row's record ID.
- **SC-002**: 100% of flowsheet codings in UAT outputs use the UAT system and 100% in
  production outputs use the production system; zero occurrences of the old system or
  of any flowsheet FHIR ID remain in generated or checked-in outputs.
- **SC-003**: Comparing the UAT and production output of any Questionnaire shows
  differences on flowsheet system values only.
- **SC-004**: The automated check suite goes from 34 failures to 0, with no check
  removed without an equivalent replacement.
- **SC-005**: For a Questionnaire with N listed items lacking a record ID, the run
  reports exactly N missing-record-ID warnings (previously 2N).
- **SC-006**: A reviewer can confirm a PHQ-9 output's 9 flowsheet codes against one
  mapping-file column in under 5 minutes.
- **SC-007**: Re-running the tool on unchanged inputs changes zero bytes in either
  output.

## Assumptions

- Constitution v4.0.0 is authoritative for the coding scheme, the two system values,
  and the retention of the UAT/production fork.
- The mapping file is already in its final four-column form and is not edited by this
  feature. Its file name (which still says "FHIR IDs") is left as is.
- Two tool deviations carried over from constitution v3.1.0 are OUT OF SCOPE and stay
  open for a later feature: (a) the tool strips the leading `/` from `CIRG-PC-PTSD-5`
  identifiers, so it cannot match that Questionnaire's rows; (b) the tool excludes
  every computed score, whereas the constitution excludes only `CIRG-PHQ9` scores and
  "internal" items. Neither affects any output today, because PHQ-9 is the only
  Questionnaire with record IDs supplied.
- The set of PHQ-9 items that receive a flowsheet coding does not change (9 items). A
  pre-existing mismatch is left as found and reported by the tool's existing warnings:
  the mapping file lists "Functional difficulty" as `69723-5`, while `CIRG-PHQ-9.json`
  carries that question as `69722-7`, so it is not mapped. Resolving it means changing
  a site-supplied row or the Questionnaire and is outside this feature.
- Only the PHQ-9 per-environment outputs exist in the repository, so only they need
  regenerating.
- Historical feature documents under `specs/001-*` and `specs/002-*` are records of
  past work and are not rewritten.
- The downstream consumer that was built against flowsheet FHIR IDs
  (`188-fishmouth-notify`) lives outside this repository and is updated separately.
- The command-line interface (arguments, defaults, output locations) is unchanged.
