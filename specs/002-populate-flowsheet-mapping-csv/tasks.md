---
description: "Task list for populating the flowsheet mapping CSV"
---

# Tasks: Populate Flowsheet Mapping CSV for CNICS Questionnaires

**Input**: Design documents from `/specs/002-populate-flowsheet-mapping-csv/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/mapping-csv.md, quickstart.md

**Tests**: Included. The plan makes `tests/test_mapping_csv.py` the durable check on the CSV
(research R1), so test tasks are part of each story.

**Organization**: Tasks are grouped by user story. All CSV-editing tasks touch the same file
and are therefore sequential, never `[P]`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1, US2, US3 (from spec.md)

## Conventions used below

- **CSV** = `deploy-specific/mapping-input/CNICS PRO UCSD flowsheet FHIR IDs.csv`
- **TOOL** = `utils/fork_questionnaire_for_extract.py`
- **Header** = `CNICS NAME,RECORD NAME (UCSD Epic),LOINC code,FHIR ID - UAT,FHIR ID - Prod`
- **Section** = a separator row `<Questionnaire.id>,,,,` followed by that Questionnaire's
  item rows, each `<label>,,<linkId>,,`
- **Reportable item** = a `Questionnaire.item` whose `type` is neither `display` nor `group`
  and whose `text` does not contain "internal" (case-insensitive). itemControl and
  calculatedExpression extensions do not affect this (data-model.md).
- **Label rules** (research R4): written by hand from the item's `text`; ≤ 60 characters; no
  commas; non-empty; unique within the section; no instrument-name prefix.
- **File format** (contracts/mapping-csv.md): UTF-8 no BOM, CRLF on every line including the
  last, exactly five cells per row. Never run a tool that rewrites line endings.
- `linkId` is copied exactly as authored (PC-PTSD-5 keeps its leading `/`).
- Never read `CIRG-CNICS-ASSIST.deprecated.json` or anything under `deprecated/`.
- Do not `git commit`; the user commits.

---

## Phase 1: Setup

**Purpose**: Record the baseline that later phases must preserve

- [ ] T001 Run `python3 -m pytest -q` from the repo root and confirm 17 tests pass; then run `python3 utils/fork_questionnaire_for_extract.py CIRG-PHQ-9.json --uat-dir <scratch>/u --prod-dir <scratch>/p` and confirm both outputs are byte-identical (`cmp`) to `deploy-specific/ucsd-uat/CIRG-PHQ-9.json` and `deploy-specific/ucsd-prod/CIRG-PHQ-9.json`. Stop and report if either check fails.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Move the CSV and its one reader to the new five-column header together, so the
tool is never left unable to read the file

**⚠️ CRITICAL**: T002–T005 must land together; the test suite is red in between

- [ ] T002 In the CSV, replace the header line with the Header above and prefix each of the 12 existing PHQ-9 rows with an empty first cell (a leading `,`), leaving their four existing values and their order untouched; terminate every line, including the last, with CRLF
- [ ] T003 [P] In `utils/fork_questionnaire_for_extract.py`, change `"RECORD NAME"` to `"RECORD NAME (UCSD Epic)"` in `REQUIRED_CSV_COLUMNS` and in the `row.get(...)` lookup inside `load_csv_index`, and update any docstring/usage text that names the old column; make no other change
- [ ] T004 [P] In `tests/test_fork_warnings.py`, change the default `header` argument of `_write_csv` to `"RECORD NAME (UCSD Epic),LOINC code,FHIR ID - UAT,FHIR ID - Prod"`
- [ ] T005 [P] In `tests/fixtures/csv-missing-column.csv`, change the header to `RECORD NAME (UCSD Epic),LOINC code,FHIR ID - UAT` so it is still missing exactly the `FHIR ID - Prod` column
- [ ] T006 Run `python3 -m pytest -q` (17 pass) and repeat the T001 PHQ-9 regeneration `cmp` check (byte-identical)

**Checkpoint**: Five-column file, tool and existing tests green, PHQ-9 outputs unchanged

---

## Phase 3: User Story 1 - UCSD receives a complete worksheet of items (Priority: P1) 🎯 MVP

**Goal**: The CSV lists every reportable item of the 19 Questionnaires (213 rows), each with
a label and identifier and blank UCSD-owned cells

**Independent Test**: `python3 -m pytest tests/test_mapping_csv.py -q` passes the US1 tests;
for any one Questionnaire, its section's `LOINC code` values equal its reportable items'
linkIds in order

### Tests for User Story 1 ⚠️ write first, confirm they FAIL before T008

- [ ] T007 [US1] Create `tests/test_mapping_csv.py` with: (a) a module constant `NEW_QUESTIONNAIRES` listing, in this order, `(id, filename)` for `CIRG-CNICS-ARV`, `-ASSIST`, `-ASSIST-OD`, `-ASSIST-Polysub`, `-AUDIT`, `-EUROQOL`, `-EXCHANGE-SEX`, `-FINANCIAL`, `-FOOD`, `-FROP-Com`, `-HIV-STIGMA`, `-HOUSING`, `-IPV4`, `-MAPSS-SF`, `-MINI`, `-SEXUAL-RISK`, `-Smoking`, `-Symptoms` (files `CIRG-CNICS-<name>.json`) and `CIRG-PC-PTSD-5` (`CIRG-PC-PTSD-5.json`); (b) a helper `reportable_link_ids(path)` that walks items at any depth and applies the Reportable-item rule; (c) a helper `load_sections()` that reads the CSV with `csv.reader` (`newline=""`, `utf-8`) and returns the header plus an ordered mapping of separator id → list of 5-cell rows, treating a row with a blank third cell as a separator; (d) a test parametrized over `NEW_QUESTIONNAIRES` asserting the file's `id` matches, the section exists, and its third-column values equal `reportable_link_ids` exactly and in order (FR-006/007/008/009); (e) a parametrized test asserting every row in those sections has blank cells 2, 4, 5 (FR-011) and a first cell that is non-empty, ≤ 60 characters, comma-free and unique within the section (FR-010, SC-006); (f) a test asserting the four slider ids `ARV-9`, `EUROQOL-5`, `SEXUAL-RISK-15`, `SEXUAL-RISK-37` and the total `AUDIT-score` are present, and `AUDIT-header` and `AUDIT-Q0-score` are absent; (g) a test asserting the 19 sections hold 213 item rows in total. Reuse `REPO_ROOT`/`REPO_CSV` from `tests/conftest.py`.

### Implementation for User Story 1

Each task appends one Section to the end of the CSV (see Conventions). Expected item-row
counts are from research R2; after each task the matching parametrized case in T007 passes.

- [ ] T008 [US1] Append the `CIRG-CNICS-ARV` section (13 rows; includes slider `ARV-9`; `ARV-0` and `ARV-1` share the same text and need distinguishable labels) from `CIRG-CNICS-ARV.json` to the CSV
- [ ] T009 [US1] Append the `CIRG-CNICS-ASSIST` section (22 rows) from `CIRG-CNICS-ASSIST.json` to the CSV
- [ ] T010 [US1] Append the `CIRG-CNICS-ASSIST-OD` section (3 rows) from `CIRG-CNICS-ASSIST-OD.json` to the CSV
- [ ] T011 [US1] Append the `CIRG-CNICS-ASSIST-Polysub` section (5 rows) from `CIRG-CNICS-ASSIST-Polysub.json` to the CSV
- [ ] T012 [US1] Append the `CIRG-CNICS-AUDIT` section (17 rows; 5 internal items omitted; `AUDIT-2-male` and `AUDIT-2-not-male` need distinguishable labels) from `CIRG-CNICS-AUDIT.json` to the CSV
- [ ] T013 [US1] Append the `CIRG-CNICS-EUROQOL` section (11 rows; includes slider `EUROQOL-5`; the five `EUROQOL-SCORE-*` rows need labels distinct from their question rows) from `CIRG-CNICS-EUROQOL.json` to the CSV
- [ ] T014 [US1] Append the `CIRG-CNICS-EXCHANGE-SEX` section (5 rows) from `CIRG-CNICS-EXCHANGE-SEX.json` to the CSV
- [ ] T015 [US1] Append the `CIRG-CNICS-FINANCIAL` section (3 rows) from `CIRG-CNICS-FINANCIAL.json` to the CSV
- [ ] T016 [US1] Append the `CIRG-CNICS-FOOD` section (5 rows) from `CIRG-CNICS-FOOD.json` to the CSV
- [ ] T017 [US1] Append the `CIRG-CNICS-FROP-Com` section (4 rows) from `CIRG-CNICS-FROP-Com.json` to the CSV
- [ ] T018 [US1] Append the `CIRG-CNICS-HIV-STIGMA` section (6 rows; 1 internal item omitted) from `CIRG-CNICS-HIV-STIGMA.json` to the CSV
- [ ] T019 [US1] Append the `CIRG-CNICS-HOUSING` section (2 rows) from `CIRG-CNICS-HOUSING.json` to the CSV
- [ ] T020 [US1] Append the `CIRG-CNICS-IPV4` section (7 rows) from `CIRG-CNICS-IPV4.json` to the CSV
- [ ] T021 [US1] Append the `CIRG-CNICS-MAPSS-SF` section (5 rows) from `CIRG-CNICS-MAPSS-SF.json` to the CSV
- [ ] T022 [US1] Append the `CIRG-CNICS-MINI` section (15 rows; 3 internal items omitted) from `CIRG-CNICS-MINI.json` to the CSV
- [ ] T023 [US1] Append the `CIRG-CNICS-SEXUAL-RISK` section (48 rows; 5 internal items omitted; includes sliders `SEXUAL-RISK-15` and `SEXUAL-RISK-37`) from `CIRG-CNICS-SEXUAL-RISK.json` to the CSV
- [ ] T024 [US1] Append the `CIRG-CNICS-Smoking` section (12 rows) from `CIRG-CNICS-Smoking.json` to the CSV
- [ ] T025 [US1] Append the `CIRG-CNICS-Symptoms` section (22 rows) from `CIRG-CNICS-Symptoms.json` to the CSV
- [ ] T026 [US1] Append the `CIRG-PC-PTSD-5` section (8 rows; identifiers keep their leading `/`, e.g. `/102011-4`) from `CIRG-PC-PTSD-5.json` to the CSV
- [ ] T027 [US1] Run `python3 -m pytest tests/test_mapping_csv.py -q`; all US1 tests pass and the total is 213 item rows

**Checkpoint**: The worksheet content UCSD needs is complete (MVP)

---

## Phase 4: User Story 2 - The file is navigable by Questionnaire (Priority: P2)

**Goal**: Exactly 20 separator rows, one per Questionnaire id, in the agreed order, with the
existing PHQ-9 rows under `CIRG-PHQ9`

**Independent Test**: Reading the first column top to bottom shows the 20 ids from
data-model.md "Section" in that order, each once

### Tests for User Story 2 ⚠️ write first, confirm the PHQ-9 cases FAIL before T029

- [ ] T028 [US2] In `tests/test_mapping_csv.py`, add: a test that the header equals the Header exactly (FR-001/002); a test that the separator ids, in file order, equal `["CIRG-PHQ9"]` followed by the ids in `NEW_QUESTIONNAIRES` with no duplicates and no extras (FR-003/004/005, SC-001); a test that the first data line of the file is the `CIRG-PHQ9` separator (no item row precedes a separator); a test that every separator row's cells 2–5 are blank; and a test that `json.load(CIRG-PHQ-9.json)["id"] == "CIRG-PHQ9"`

### Implementation for User Story 2

- [ ] T029 [US2] In the CSV, insert the separator row `CIRG-PHQ9,,,,` as line 2, immediately after the header and before the first PHQ-9 row
- [ ] T030 [US2] Run `python3 -m pytest tests/test_mapping_csv.py -q`; US1 and US2 tests pass

**Checkpoint**: 20 sections, each findable by its id

---

## Phase 5: User Story 3 - Existing PHQ-9 mapping keeps working (Priority: P3)

**Goal**: PHQ-9 rows are labelled but otherwise untouched, the file is structurally sound for
any reader, and the fork tool handles the 20-section file

**Independent Test**: Regenerated PHQ-9 UAT/prod Questionnaires are byte-identical to the
checked-in ones; a fork run on a new Questionnaire exits 0

### Tests for User Story 3 ⚠️ write first, confirm the label case FAILS before T033

- [ ] T031 [P] [US3] In `tests/test_mapping_csv.py`, add: a module constant `PHQ9_ROWS` holding the 12 original `(record name, LOINC code, UAT id, Prod id)` tuples copied from `git show HEAD:"deploy-specific/mapping-input/CNICS PRO UCSD flowsheet FHIR IDs.csv"`, and a test that cells 2–5 of the `CIRG-PHQ9` section equal them exactly and in order (FR-012, SC-004); a test that each PHQ-9 row's first cell is non-empty, ≤ 60 characters, comma-free and unique in the section; a test that every row in the file has exactly five cells (FR-014); a test that non-blank third-column values are unique across the whole file, compared case-insensitively (FR-013); and a test that the raw bytes have no BOM, contain no `\n` not preceded by `\r`, and end with `\r\n`
- [ ] T032 [P] [US3] In `tests/test_fork_core.py`, add two tests using the existing `tool`, `repo_csv` and `out_dirs` fixtures: (1) forking a temp copy of `CIRG-PHQ-9.json` with the repo CSV yields files byte-identical to `deploy-specific/ucsd-uat/CIRG-PHQ-9.json` and `deploy-specific/ucsd-prod/CIRG-PHQ-9.json` (FR-015); (2) forking a temp copy of `CIRG-CNICS-AUDIT.json` returns 0, writes both files, stderr names `AUDIT-0` as lacking `FHIR ID - UAT` and `FHIR ID - Prod`, and stderr never mentions any separator id from the CSV as a record (US3 scenario 3)

### Implementation for User Story 3

- [ ] T033 [US3] In the CSV, fill the first cell of each of the 12 PHQ-9 rows with a label per the Label rules, taken from the matching item's `text` in `CIRG-PHQ-9.json` (e.g. `44250-9` → "Little interest or pleasure"); for `55758-7` and `69723-5`, which have no item in that file, derive the label from the Epic record name ("PHQ-2 total score", "Functional difficulty"); change nothing else in those rows
- [ ] T034 [US3] Run `python3 -m pytest -q`; every test in the suite passes
- [ ] T035 [US3] Run `python3 utils/fork_questionnaire_for_extract.py CIRG-PHQ-9.json` with default output directories and confirm `git status --short deploy-specific/ucsd-uat deploy-specific/ucsd-prod` prints nothing

**Checkpoint**: All three stories complete

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T036 [P] In `README.md`, extend the Tooling bullet for `utils/fork_questionnaire_for_extract.py` with one or two sentences: the mapping CSV now has the five columns in the Header, one section per Questionnaire under a separator row, UCSD fills the record name and FHIR ID columns, and `tests/test_mapping_csv.py` validates it
- [ ] T037 [P] In `specs/001-add-extract-metadata/quickstart.md`, add a one-line note at the top that the CSV schema was superseded by constitution v3.1.0 and feature 002 (new column names; many "matched no item" warnings are expected per run), leaving the rest of the feature 001 documents unchanged
- [ ] T038 Walk through `specs/002-populate-flowsheet-mapping-csv/quickstart.md` steps 1–3 and confirm each behaves as described; confirm `git status --short` shows no change to any `CIRG-*.json` at the repo root or under `deploy-specific/ucsd-*` (FR-016)
- [ ] T039 Report to the user for review: the final row counts per section; the two helper-looking computed rows `AUDIT-complete` and `AUDIT-qnr-to-report` (research R2); the pre-existing `69722-7` vs `69723-5` PHQ-9 mismatch (research R7.4); and the follow-up tool work still owed (research R7.1–R7.3)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001)**: none
- **Foundational (T002–T006)**: after Setup; blocks every story
- **US1 (T007–T027)**: after Foundational
- **US2 (T028–T030)**: after Foundational; its order test only goes fully green once US1's
  sections exist
- **US3 (T031–T035)**: after Foundational; T032's AUDIT case needs T012; T031's uniqueness
  and five-cell tests cover whatever sections exist
- **Polish (T036–T039)**: after all stories

### Within Each User Story

- Test task first, confirm it fails, then the CSV edits, then the run task
- T008–T026 are strictly sequential (same file, append order = section order)

### Parallel Opportunities

- T003, T004, T005 (three different files) alongside T002
- T031 and T032 (different test files)
- T036 and T037 (different docs)
- Nothing else: the CSV is a single file

## Parallel Example: Foundational

```text
Task: "T003 rename the record-name column in utils/fork_questionnaire_for_extract.py"
Task: "T004 update _write_csv header in tests/test_fork_warnings.py"
Task: "T005 update header in tests/fixtures/csv-missing-column.csv"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. T001, then T002–T006
2. T007–T027
3. **Stop and validate**: the 19 sections are complete and could be sent to UCSD

### Incremental Delivery

1. Foundational → file readable in its new shape, PHQ-9 safe
2. US1 → UCSD's build list (MVP)
3. US2 → PHQ-9 separator and ordering guarantees
4. US3 → PHQ-9 labels, structural tests, tool regression tests
5. Polish → docs and review notes

## Notes

- Derive each section's identifiers and order with a throwaway script in the scratchpad if
  helpful; do not commit a generator (research R1)
- Labels are judgments: prefer the clinical concept over the question wording, and add a
  qualifier (timeframe, sex, "score", "interpretation") when two items would otherwise collide
- UCSD-owned cells stay blank; never invent a record name or FHIR ID
