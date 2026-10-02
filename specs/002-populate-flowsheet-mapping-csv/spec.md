# Feature Specification: Populate Flowsheet Mapping CSV for CNICS Questionnaires

**Feature Branch**: `002-populate-flowsheet-mapping-csv`
**Created**: 2026-10-02
**Status**: Draft
**Input**: User description: "Per the latest edit to the constitution, we need to read from some of these Questionnaires and extract data related to downstream SDC $extract and Epic consumption, to add the information to `deploy-specific/mapping-input/CNICS PRO UCSD flowsheet FHIR IDs.csv`. The pattern has been established there with CIRG-PHQ-9.json. Do this for 19 further Questionnaires; add a separator row per Questionnaire labelled with its Questionnaire.id; add a leading `CNICS NAME` column with a very brief human-friendly label based on item text; rename `RECORD NAME` to `RECORD NAME (UCSD Epic)`; populate `LOINC code` from item linkId; leave the FHIR ID columns blank; exclude display-only headers, 'internal' items, and items with the questionnaire-itemControl extension."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - UCSD receives a complete worksheet of items to build flowsheets for (Priority: P1)

The CNICS team hands UCSD's Epic team one mapping file that lists every item CNICS
will report for 19 additional Questionnaires. For each item UCSD sees a short,
readable name and the identifier CNICS will send. UCSD uses the file as its build
list: it creates a flowsheet row per listed item, then fills in the Epic record name
and the UAT and production flowsheet IDs.

**Why this priority**: UCSD cannot create flowsheets until it knows which items are
coming. Nothing downstream (ID entry, per-environment Questionnaires, extraction) can
start without this list.

**Independent Test**: Open the mapping file and, for any one of the 19 Questionnaires,
compare its section against that Questionnaire: every reportable item appears exactly
once with a label and identifier, no excluded item appears, and the three UCSD-owned
cells are blank.

**Acceptance Scenarios**:

1. **Given** the Questionnaire `CIRG-CNICS-AUDIT`, **When** the mapping file is
   reviewed, **Then** it contains a section for that Questionnaire with one row per
   reportable item (e.g. `AUDIT-0`, `AUDIT-1`, `AUDIT-score`), each with a brief label
   and the item's identifier.
2. **Given** an item that is a display-only header (e.g. `AUDIT-header`), **When** the
   mapping file is reviewed, **Then** no row exists for it.
3. **Given** an item whose text states it is an internal item (e.g. `AUDIT-Q0-score`),
   **When** the mapping file is reviewed, **Then** no row exists for it.
4. **Given** a slider-style question carrying the questionnaire-itemControl extension
   (e.g. `ARV-9`), **When** the mapping file is reviewed, **Then** a row exists for it
   like any other question.
5. **Given** a computed total that is not marked internal (e.g. `AUDIT-score`), **When**
   the mapping file is reviewed, **Then** a row exists for it, because CNICS reports
   totals for these Questionnaires.
6. **Given** any row added for the 19 Questionnaires, **When** it is reviewed, **Then**
   its Epic record name, UAT ID, and production ID cells are blank.

---

### User Story 2 - The file is navigable by Questionnaire (Priority: P2)

A reviewer at CNICS or UCSD scrolling a file of over 200 rows can tell at a glance
which Questionnaire each row belongs to, because every Questionnaire's rows sit
together under a separator row carrying that Questionnaire's id.

**Why this priority**: The content is usable without separators, but a flat list of
200+ rows across 20 instruments is error-prone to review and to fill in.

**Independent Test**: Read the first column top to bottom: 20 separator rows appear,
each naming one Questionnaire id, each followed only by that Questionnaire's rows.

**Acceptance Scenarios**:

1. **Given** the mapping file, **When** a reviewer looks for `CIRG-CNICS-FOOD`,
   **Then** they find one separator row labelled `CIRG-CNICS-FOOD` whose other cells
   are blank, followed by that Questionnaire's rows in the order the items appear in
   the Questionnaire.
2. **Given** the existing PHQ-9 rows, **When** the file is reviewed, **Then** they sit
   under a separator row labelled `CIRG-PHQ9`.

---

### User Story 3 - Existing PHQ-9 mapping keeps working (Priority: P3)

A CNICS developer regenerates the per-environment PHQ-9 Questionnaires from the
restructured mapping file and gets exactly the files that are already deployed.

**Why this priority**: PHQ-9 is the only instrument live today. Restructuring the file
must not disturb it, but it is a guard on existing behaviour rather than new value.

**Independent Test**: Regenerate the UAT and production PHQ-9 Questionnaires from the
updated mapping file and compare them with the currently checked-in ones.

**Acceptance Scenarios**:

1. **Given** the updated mapping file, **When** the PHQ-9 per-environment
   Questionnaires are regenerated, **Then** they are identical to the checked-in ones.
2. **Given** the existing PHQ-9 rows, **When** the file is reviewed, **Then** each
   keeps its original Epic record name, identifier, UAT ID, and production ID, now
   under the renamed record-name column, and has gained a brief label.
3. **Given** the updated mapping file, **When** per-environment Questionnaires are
   generated for one of the 19 new Questionnaires, **Then** the run completes, reports
   each item as awaiting its flowsheet IDs, and treats no separator row as a mapping.

---

### Edge Cases

- **Item with no text** (e.g. a computed item lacking display text): the label is
  derived from the item's identifier and its role in the Questionnaire; the label cell
  is never left blank.
- **Identifiers with a leading slash** (`CIRG-PC-PTSD-5`, e.g. `/102011-4`): the slash
  is kept. Many stored responses to this Questionnaire already use that form, so it is
  the identifier CNICS will send. This is the one exception to the no-slash rule.
- **Same question text on two items** (e.g. `ARV-0` and `ARV-1`, or the sex-specific
  `AUDIT-2-male` / `AUDIT-2-not-male`): labels must still be distinguishable from one
  another within the Questionnaire.
- **Labels containing commas or quotes**: the file must remain a well-formed table
  with five cells in every row.
- **Existing PHQ-9 row with no corresponding Questionnaire item** (the PHQ-2 total,
  `55758-7`): the row is retained and labelled from its Epic record name.
- **Nested items**: items at any depth are considered; the same inclusion and
  exclusion rules apply.
- **Grouping-only items** (containers that hold other items and take no answer): no
  row, since nothing is reported for them.
- **Similarly named superseded files** (e.g. `CIRG-CNICS-ASSIST.deprecated.json`):
  never used as a source.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The mapping file MUST have exactly these columns, in this order:
  `CNICS NAME`, `RECORD NAME (UCSD Epic)`, `LOINC code`, `FHIR ID - UAT`,
  `FHIR ID - Prod`.
- **FR-002**: The former `RECORD NAME` column MUST be renamed to
  `RECORD NAME (UCSD Epic)` with its existing values unchanged.
- **FR-003**: The mapping file MUST contain a section for each of these Questionnaire
  ids: `CIRG-PHQ9` (existing rows), `CIRG-CNICS-ARV`, `CIRG-CNICS-ASSIST`,
  `CIRG-CNICS-ASSIST-OD`, `CIRG-CNICS-ASSIST-Polysub`, `CIRG-CNICS-AUDIT`,
  `CIRG-CNICS-EUROQOL`, `CIRG-CNICS-EXCHANGE-SEX`, `CIRG-CNICS-FINANCIAL`,
  `CIRG-CNICS-FOOD`, `CIRG-CNICS-FROP-Com`, `CIRG-CNICS-HIV-STIGMA`,
  `CIRG-CNICS-HOUSING`, `CIRG-CNICS-IPV4`, `CIRG-CNICS-MAPSS-SF`, `CIRG-CNICS-MINI`,
  `CIRG-CNICS-SEXUAL-RISK`, `CIRG-CNICS-Smoking`, `CIRG-CNICS-Symptoms`,
  `CIRG-PC-PTSD-5`.
- **FR-004**: Each section MUST begin with a separator row whose `CNICS NAME` cell is
  the Questionnaire's id and whose other four cells are blank.
- **FR-005**: Sections MUST appear with `CIRG-PHQ9` first, then in the order listed in
  FR-003; within a section, rows MUST follow the order of items in the Questionnaire.
- **FR-006**: For each of the 19 newly added Questionnaires, the section MUST contain
  exactly one row for every item, at any nesting depth, that is not excluded by
  FR-007.
- **FR-007**: No row MUST be added for an item that is: (a) a display-only header;
  (b) described in its own text as an "internal" item; or (c) a grouping-only
  container. The presence of the
  `http://hl7.org/fhir/StructureDefinition/questionnaire-itemControl` extension MUST
  NOT by itself exclude an item: answerable items that carry it (the slider questions
  `ARV-9`, `EUROQOL-5`, `SEXUAL-RISK-15`, `SEXUAL-RISK-37`) MUST have a row.
- **FR-008**: Computed scores and totals that are not excluded by FR-007 MUST have a
  row, in line with the constitution's rule that totals are reported for every
  Questionnaire except PHQ-9.
- **FR-009**: Each item row's `LOINC code` cell MUST be the item's identifier (its
  linkId) copied exactly as authored. For `CIRG-PC-PTSD-5` this includes the leading
  `/` (e.g. `/102011-4`); the other 18 Questionnaires' identifiers have no leading
  slash.
- **FR-010**: Each item row's `CNICS NAME` cell MUST be a very brief human-friendly
  label derived from the item's text, MUST be non-empty, and MUST be unique within its
  Questionnaire's section.
- **FR-011**: For rows added for the 19 Questionnaires, the `RECORD NAME (UCSD Epic)`,
  `FHIR ID - UAT`, and `FHIR ID - Prod` cells MUST be blank.
- **FR-012**: Every existing PHQ-9 row MUST be retained with its record name,
  identifier, UAT ID, and production ID unchanged, and MUST gain a `CNICS NAME` label.
- **FR-013**: No `LOINC code` value may appear on more than one row of the file.
- **FR-014**: Every row, including separator rows, MUST have exactly five cells, and
  the file MUST open cleanly as a table in a spreadsheet application.
- **FR-015**: The existing process that generates per-environment Questionnaires MUST
  accept the restructured file: it MUST read the renamed record-name column, MUST
  ignore separator rows, and MUST produce PHQ-9 outputs identical to those currently
  checked in.
- **FR-016**: The 19 source Questionnaires MUST NOT be modified by this feature.

### Key Entities

- **Mapping file**: The single worksheet exchanged between CNICS and UCSD. One header
  row, then sections. CNICS owns the label and identifier columns; UCSD owns the Epic
  record name and the two flowsheet ID columns.
- **Questionnaire section**: A separator row naming a Questionnaire id, followed by
  that Questionnaire's item rows.
- **Item row**: One reportable Questionnaire item — brief label, identifier, and (once
  UCSD supplies them) Epic record name, UAT flowsheet ID, production flowsheet ID.
- **Reportable item**: A Questionnaire item that takes a patient's answer or holds a
  computed score/total, and is not a display header, an internal item, or a grouping
  container.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 20 Questionnaire ids appear as separator rows, each exactly once.
- **SC-002**: For each of the 19 added Questionnaires, 100% of reportable items have
  exactly one row and 0 excluded items have a row (approximately 213 item rows in
  total across the 19).
- **SC-003**: 100% of item rows have a non-empty label and a non-empty identifier;
  100% of the rows added by this feature have blank UCSD-owned cells.
- **SC-004**: All 12 existing PHQ-9 rows retain their original four values, and the
  regenerated PHQ-9 UAT and production Questionnaires show zero differences from the
  checked-in versions.
- **SC-005**: A reviewer can locate any named Questionnaire's rows in the file in
  under 30 seconds without searching by item identifier.
- **SC-006**: A UCSD analyst can tell what each row measures from its label alone,
  without opening the Questionnaire; labels are short enough to read in a default-width
  spreadsheet column (target: 60 characters or fewer).

## Assumptions

- **itemControl does not exclude an item.** The original request listed the
  itemControl extension as an exclusion; that was clarified on 2026-10-02: slider
  questions carrying it are reported and get rows. Display-only items that carry it
  are still excluded, as display-only items.
- **PC-PTSD-5 identifiers keep their leading slash** (clarified 2026-10-02) because
  existing stored responses use that form. PHQ-9 rows remain without a slash, as
  already recorded.
- **"Internal" is recognised from the item's text**, i.e. the text says the item is an
  internal item. Computed items that do not say so are treated as reportable.
- **Source files** are the active Questionnaire files at the repository root whose
  `id` matches the list in FR-003; deprecated variants are ignored.
- **Labels are CNICS-authored judgments**, not verbatim text; they may be revised
  later without affecting matching, because matching uses the identifier column only.
- **The column keeps the name `LOINC code`** even though most added identifiers are
  not LOINC codes (constitution v3.0.0, Principle III).
- **Out of scope**: obtaining Epic record names or flowsheet IDs from UCSD; generating
  or committing per-environment Questionnaires for the 19 Questionnaires; changing the
  generation process so that computed totals are actually extracted for non-PHQ-9
  Questionnaires (required by constitution v3.0.0, to be handled as its own feature
  before IDs arrive — confirmed out of scope 2026-10-02); making the generation
  process match the slash-prefixed `CIRG-PC-PTSD-5` rows; updating the feature 001
  documents that cite the old column name.
- **Dependency**: constitution v3.1.0 defines the column set, separator rows,
  identifier rule (including the `CIRG-PC-PTSD-5` slash exception), and the items
  that get no row.
