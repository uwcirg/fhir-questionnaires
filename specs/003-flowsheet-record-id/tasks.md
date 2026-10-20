---
description: "Task list for coding per-environment Questionnaires with the flowsheet record ID"
---

# Tasks: Code Per-Environment Questionnaires With the Flowsheet Record ID

**Input**: Design documents from `/specs/003-flowsheet-record-id/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md, contracts/mapping-csv.md, quickstart.md

**Tests**: Included. The spec requires them (FR-011, FR-012, SC-004). Within each story the
test tasks come first and must be seen to fail (or, where noted, pass) before moving on.

**Organization**: Tasks are grouped by user story. Tasks that touch the same file are
sequential, never `[P]`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1, US2, US3 (from spec.md)

## Conventions used below

- **TOOL** = `utils/fork_questionnaire_for_extract.py`
- **CSV** = `deploy-specific/mapping-input/CNICS PRO UCSD flowsheet FHIR IDs.csv` —
  READ ONLY in this feature. Never edit it.
- **UAT system** = `urn:oid:1.2.840.114350.1.13.136.3.7.2.707679`
- **PROD system** = `urn:oid:1.2.840.114350.1.13.136.2.7.2.707679`
- **OLD system** = `http://open.epic.com/FHIR/StructureDefinition/observation-flowsheet-id`
- **PHQ-9 mapped set** = the 9 items the tool codes, with their record IDs:
  `44250-9`→`3025`, `44255-8`→`3026`, `44259-0`→`3027`, `44254-1`→`3028`, `44251-7`→`3029`,
  `44258-2`→`3030`, `44252-5`→`3031`, `44253-3`→`3032`, `44260-8`→`3033`.
  Not coded: `69722-7` (no CSV row; the CSV has `69723-5`) and `44261-6` (computed score).
- **Scratch** = a temporary directory outside the repo; never write test outputs into
  `deploy-specific/` except in T018.
- Out of scope — do NOT change: the leading-`/` stripping in `extract_loinc`, the
  `is_score` exclusion, the source Questionnaires, the CSV, anything under `specs/001-*` or
  `specs/002-*`.
- Python 3.11, standard library only. Match the existing style of the file being edited
  (`%`-formatting, docstring conventions, section-comment banners).
- Do not `git commit`; the user commits.

---

## Phase 1: Setup

**Purpose**: Record the baseline this feature starts from

- [X] T001 Run `python3 -m pytest -q` from the repo root and confirm `34 failed, 35 passed`; then run `python3 utils/fork_questionnaire_for_extract.py CIRG-PHQ-9.json --uat-dir <Scratch>/u --prod-dir <Scratch>/p` and confirm it exits non-zero with `ERROR: CSV … is missing required column(s): FHIR ID - UAT, FHIR ID - Prod` and writes nothing. Stop and report if the baseline differs.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared test constants every story's tests import (research R6)

- [X] T002 In `tests/conftest.py`, add three module-level string constants after `FIXTURES`: `UAT_FLOWSHEET_SYSTEM` (the UAT system), `PROD_FLOWSHEET_SYSTEM` (the PROD system) and `OLD_FLOWSHEET_SYSTEM` (the OLD system), written as literals with a one-line comment that they are deliberately independent of the tool's own constants; change nothing else in the file

**Checkpoint**: `python3 -m pytest -q` still reports `34 failed, 35 passed`

---

## Phase 3: User Story 1 - Generate per-environment Questionnaires coded with the record ID (Priority: P1) 🎯 MVP

**Goal**: The tool reads `Flowsheet Record ID` from the CSV and writes it as the flowsheet
coding's `code` in both outputs, under the UAT system in the UAT file and the PROD system
in the production file; the outputs differ in nothing else.

**Independent Test**: `python3 utils/fork_questionnaire_for_extract.py CIRG-PHQ-9.json --uat-dir <Scratch>/u --prod-dir <Scratch>/p` exits 0; `diff <Scratch>/u/CIRG-PHQ-9.json <Scratch>/p/CIRG-PHQ-9.json` shows exactly 9 changed lines, all `system` values; `grep -c observation-flowsheet-id` on either file prints `0`.

### Tests for User Story 1 ⚠️ write first, see them fail

- [X] T003 [US1] Rewrite the record-ID assertions in `tests/test_fork_core.py` (contracts/cli.md cases 1–4, 7): (a) delete the local `EPIC_FLOWSHEET_SYSTEM`, `UAT_INTEREST` and `PROD_INTEREST` constants and import `UAT_FLOWSHEET_SYSTEM`, `PROD_FLOWSHEET_SYSTEM`, `OLD_FLOWSHEET_SYSTEM` from `.conftest` alongside `REPO_ROOT`; add a module constant `PHQ9_RECORD_IDS` holding the PHQ-9 mapped set as a dict linkId→record ID; (b) change `_flowsheet_codes(item)` to `_flowsheet_codes(item, system)` filtering on the given system; (c) in `test_happy_path_two_files_env_correct` assert `_flowsheet_codes(uat_first, UAT_FLOWSHEET_SYSTEM) == ["3025"]` and `_flowsheet_codes(prod_first, PROD_FLOWSHEET_SYSTEM) == ["3025"]`, keeping the `observationExtract` assertion; (d) replace `test_uat_file_has_no_prod_ids_and_vice_versa` with `test_each_file_carries_only_its_own_system`: `PROD_FLOWSHEET_SYSTEM` does not occur in the UAT file's text and `UAT_FLOWSHEET_SYSTEM` does not occur in the production file's text; (e) in `test_no_item_has_more_than_one_flowsheet_coding` and `test_display_and_score_items_get_no_flowsheet` pass the file's own system (UAT for `uat`, PROD for `prod`); (f) add `test_outputs_differ_only_in_system`: read both output files as text, assert they are not equal, and assert `prod_text.replace(PROD_FLOWSHEET_SYSTEM, UAT_FLOWSHEET_SYSTEM) == uat_text` (research R7); (g) add `test_old_scheme_absent`: neither output's text contains `OLD_FLOWSHEET_SYSTEM`; (h) add `test_phq9_mapped_items_carry_their_record_ids`: for each output, the dict {linkId: code} over all items having a coding under that file's system equals `PHQ9_RECORD_IDS` (exactly 9 entries). Leave `test_root_observation_extract_category_present`, `test_idempotent_byte_identical_rerun`, `test_no_loinc_item_unchanged`, `test_phq9_outputs_match_checked_in_files` and `test_fork_listed_but_unmapped_questionnaire` untouched in this task
- [X] T004 [P] [US1] In `tests/test_fork_scores.py`, delete the local `EPIC_FLOWSHEET_SYSTEM`, import `UAT_FLOWSHEET_SYSTEM`, `PROD_FLOWSHEET_SYSTEM`, `OLD_FLOWSHEET_SYSTEM` from `.conftest`, and change the "no flowsheet coding was added" assertion so that, for both outputs, the `44261-6` item has no coding whose `system` is any of those three; keep the equals-source and warning assertions (cli.md case 6)
- [X] T005 [US1] Run `python3 -m pytest tests/test_fork_core.py tests/test_fork_scores.py -q` and confirm the tests touched in T003–T004 fail because the tool rejects the CSV (missing-column error); if any of them passes, the test is not exercising the new scheme — fix it before continuing

### Implementation for User Story 1

- [X] T006 [US1] In `utils/fork_questionnaire_for_extract.py` constants block: delete `EPIC_FLOWSHEET_SYSTEM`; add `FLOWSHEET_SYSTEMS = {"uat": <UAT system>, "prod": <PROD system>}` with a comment that the flowsheet record ID is the same in both environments and only its coding system differs (constitution v4.0.0, Principle I); set `REQUIRED_CSV_COLUMNS` to `["RECORD NAME (UCSD Epic)", "LOINC code", "Flowsheet Record ID"]`; delete `ENV_COLUMNS` and its comment (research R1, R2)
- [X] T007 [US1] In `load_csv_index` in `utils/fork_questionnaire_for_extract.py`: build each record as `{"loinc", "record_name", "record_id"}` with `record_id = (row.get("Flowsheet Record ID") or "").strip()`; detect conflicts with `{r["record_id"] for r in rows}` having more than one member; build each index entry as `{"record_id", "record_name", "loinc"}`; update the docstring's description of `index`, `conflicts` and `records` to match (research R1, R5; data-model §2)
- [X] T008 [US1] In `utils/fork_questionnaire_for_extract.py`: change `inject_extract_metadata(item, flowsheet_id)` to `inject_extract_metadata(item, system, record_id)`, appending `{"system": system, "code": record_id}` only when no existing coding has that `system`; in `build_environment_output` read `record_id = detail["record"].get("record_id")`, skip the item when it is blank, and call `inject_extract_metadata(item, FLOWSHEET_SYSTEMS[env], record_id)`; update both docstrings (research R2, R3; data-model §5)
- [X] T009 [US1] In `report_gaps` in `utils/fork_questionnaire_for_extract.py`, replace the per-environment loop in the `mapped` branch with a single check: when `record.get("record_id")` is blank, call `warn("loinc=%s has no Flowsheet Record ID; omitted from both outputs" % loinc)` once (research R4; data-model §7). This removes the last use of `ENV_COLUMNS`; confirm with `grep -n 'ENV_COLUMNS\|EPIC_FLOWSHEET_SYSTEM\|"uat"\]\|"prod"\]\|FHIR ID' utils/fork_questionnaire_for_extract.py` that only docstring/help mentions remain (those are handled in T017)
- [X] T010 [US1] Run `python3 -m pytest tests/test_fork_core.py tests/test_fork_scores.py -q`; every test must pass except exactly two that are expected to stay red until later tasks: `test_phq9_outputs_match_checked_in_files` (fixed by T018) and `test_fork_listed_but_unmapped_questionnaire` (fixed by T014). Then perform this story's Independent Test in Scratch

**Checkpoint**: The tool produces correct record-ID outputs for PHQ-9. Checked-in outputs and gap tests are not yet updated.

---

## Phase 4: User Story 2 - Mapping gaps are reported in record-ID terms (Priority: P2)

**Goal**: A blank record ID is reported once per item; a CSV without the
`Flowsheet Record ID` column is rejected; conflicting rows are detected on the record ID;
nothing is invented.

**Independent Test**: `python3 utils/fork_questionnaire_for_extract.py CIRG-CNICS-AUDIT.json --uat-dir <Scratch>/u --prod-dir <Scratch>/p 2><Scratch>/err` exits 0; `grep -c 'has no Flowsheet Record ID; omitted from both outputs' <Scratch>/err` equals the number of AUDIT item rows in the CSV; neither output contains `urn:oid:1.2.840.114350`.

**Note**: The tool behaviour for this story was necessarily implemented in T007 and T009,
because the record's shape cannot change piecemeal. This phase adds the tests that pin it;
T015 fixes the tool if any of them fails.

### Tests for User Story 2

- [ ] T011 [P] [US2] Replace the contents of `tests/fixtures/csv-missing-column.csv` with a header `RECORD NAME (UCSD Epic),LOINC code` and one row `PHQ9_INTEREST,44250-9`, so it is missing exactly the `Flowsheet Record ID` column
- [ ] T012 [US2] In `tests/test_fork_guards.py` (cli.md case 12): in `test_csv_missing_column_rejected` assert `"Flowsheet Record ID" in err` instead of `"FHIR ID - Prod"`; add `test_old_layout_csv_rejected(tool, phq9_copy, out_dirs, tmp_path, capsys)` that writes a CSV with header `CNICS NAME,RECORD NAME (UCSD Epic),LOINC code,FHIR ID - UAT,FHIR ID - Prod` and one PHQ-9 row carrying two FHIR-ID-like strings, runs the tool, and asserts non-zero exit, `"Flowsheet Record ID"` in stderr, and `_assert_no_output(out_dirs)`
- [ ] T013 [P] [US2] Update `tests/test_fork_warnings.py` (cli.md cases 5, 9, 11, 13): (a) delete the local `EPIC_FLOWSHEET_SYSTEM`, import `UAT_FLOWSHEET_SYSTEM` and `PROD_FLOWSHEET_SYSTEM` from `.conftest`, and change `_flowsheet_codes(item)` to `_flowsheet_codes(item, system)`; (b) change the `_write_csv` default header to `RECORD NAME (UCSD Epic),LOINC code,Flowsheet Record ID`; (c) in `test_bidirectional_gap_warnings` pass `UAT_FLOWSHEET_SYSTEM` to the final assertion; (d) replace `test_missing_prod_id_not_fabricated` with `test_missing_record_id_not_fabricated`: CSV row `PHQ9_INTEREST,44250-9,` (blank record ID) → exit 0, no coding under the UAT system in the UAT output and none under the PROD system in the production output, the item in each output equals the source item, and exactly one stderr line contains both `44250-9` and `Flowsheet Record ID`; (e) in `test_conflicting_csv_rows_leave_item_unmodified` use rows `PHQ9_INTEREST_A,44250-9,3025` and `PHQ9_INTEREST_B,44250-9,9999` and pass each file's own system; (f) add `test_record_id_whitespace_trimmed`: row `PHQ9_INTEREST,44250-9,  3025  ` → both outputs carry code `"3025"`; (g) add `test_extra_csv_columns_ignored`: header `CNICS NAME,RECORD NAME (UCSD Epic),LOINC code,Flowsheet Record ID,NOTES` with row `Interest,PHQ9_INTEREST,44250-9,3025,anything` → exit 0 and both outputs carry code `"3025"`; (h) add `test_item_already_coded_is_not_coded_twice`: source item whose `code` already contains `{"system": UAT_FLOWSHEET_SYSTEM, "code": "3025"}`, CSV row with record ID `3025` → the UAT output has exactly one coding under the UAT system and the production output has exactly one under the PROD system
- [ ] T014 [US2] In `test_fork_listed_but_unmapped_questionnaire` in `tests/test_fork_core.py` (cli.md case 10): replace the per-column loop with an assertion that exactly one stderr line contains both `loinc=AUDIT-0 ` and `Flowsheet Record ID`; add assertions that neither output file's text contains `UAT_FLOWSHEET_SYSTEM` or `PROD_FLOWSHEET_SYSTEM` and that neither parsed output has a root extension whose `url` is `SDC_OBSERVATION_EXTRACT_CATEGORY`; update the comment above it ("blank record ID is a known gap, reported once"); keep the separator-row assertions unchanged

### Implementation for User Story 2

- [ ] T015 [US2] Run `python3 -m pytest tests/test_fork_guards.py tests/test_fork_warnings.py tests/test_fork_core.py tests/test_fork_scores.py -q`; everything must pass except `test_phq9_outputs_match_checked_in_files` (fixed by T018). If any other test fails, correct `utils/fork_questionnaire_for_extract.py` (not the test) so its behaviour matches contracts/cli.md, then re-run. Then perform this story's Independent Test in Scratch

**Checkpoint**: Gap reporting is pinned by tests; one warning per missing record ID.

---

## Phase 5: User Story 3 - Checked-in artifacts and automated checks match the new scheme (Priority: P3)

**Goal**: The deployed PHQ-9 outputs are coded with record IDs, the mapping-file tests
assert the four-column layout, the docs describe the scheme, and the whole suite is green.

**Independent Test**: `python3 -m pytest -q` reports 0 failed; `python3 utils/fork_questionnaire_for_extract.py CIRG-PHQ-9.json` followed by `git diff --stat deploy-specific/` shows no change beyond the one made in T018.

### Tests for User Story 3

- [ ] T016 [P] [US3] Update `tests/test_mapping_csv.py` to the four-column layout (contracts/mapping-csv.md): (a) `HEADER` = `["CNICS NAME", "RECORD NAME (UCSD Epic)", "LOINC code", "Flowsheet Record ID"]`; (b) `PHQ9_ROWS` becomes twelve `(record name, identifier, record ID)` triples exactly as tabled under "Pinned content" in `specs/003-flowsheet-record-id/contracts/mapping-csv.md`, and its comment says `(record name, LOINC code, Flowsheet Record ID)`; (c) in `test_new_section_rows_have_labels_and_blank_site_cells` assert `[row[1], row[3]] == ["", ""]`; (d) in `test_first_data_row_is_phq9_separator` expect `[PHQ9_ID, "", "", ""]`; (e) in `test_separator_rows_have_only_the_id` expect `row[1:] == ["", "", ""]`; (f) in `test_phq9_rows_unchanged` compare `tuple(row[1:4])`; (g) rename `test_every_row_has_five_cells` to `test_every_row_has_four_cells` and assert `len(row) == 4`; (h) in the module docstring say "flowsheet record IDs" instead of "FHIR IDs" and point at `specs/003-flowsheet-record-id/contracts`. Then run `python3 -m pytest tests/test_mapping_csv.py -q` and confirm all tests in the file pass with no change to the CSV. (This task depends on nothing else and may be done at any point after T001.)

### Implementation for User Story 3

- [ ] T017 [US3] Update the prose in `utils/fork_questionnaire_for_extract.py` (research R10): module docstring (the two output bullets say each file carries the flowsheet record ID under that environment's `system`; "diff each file against a single CSV column" stays true; "flowsheet-ID CSV" → "flowsheet mapping CSV"), the `build_environment_output` docstring, the argparse `description` ("…per-environment $extract outputs (same flowsheet record ID, UAT or production system)") and the `--csv` help ("Flowsheet mapping CSV path"). No behaviour change; `grep -n 'FHIR ID -' utils/fork_questionnaire_for_extract.py` must print nothing (the `DEFAULT_CSV` file name legitimately still contains "FHIR IDs")
- [ ] T018 [US3] Regenerate the checked-in outputs by running `python3 utils/fork_questionnaire_for_extract.py CIRG-PHQ-9.json` from the repo root (default directories). Verify with `git diff --stat deploy-specific/ucsd-uat deploy-specific/ucsd-prod` that each file shows 18 insertions and 18 deletions, and with `git diff deploy-specific/ucsd-uat deploy-specific/ucsd-prod | grep '^[-+] ' | grep -v '"system"\|"code"'` that no other line changed; verify `grep -c observation-flowsheet-id` prints `0` for both files and `diff deploy-specific/ucsd-uat/CIRG-PHQ-9.json deploy-specific/ucsd-prod/CIRG-PHQ-9.json | grep -c '^<'` prints `9` (research R9). Stop and report if the diff touches anything else
- [ ] T019 [P] [US3] In `README.md`, in the `utils/fork_questionnaire_for_extract.py` bullet, delete the parenthetical sentence beginning "(As of constitution v4.0.0 the tool itself still needs updating" through its closing parenthesis; change nothing else in the bullet
- [ ] T020 [US3] Run `python3 -m pytest -q` and confirm 0 failed (76 tests if T003–T016 were written exactly as listed; never fewer than 69). Run the tool on `CIRG-PHQ-9.json` a second time and confirm `git status --short deploy-specific/` shows no change beyond T018's

**Checkpoint**: All user stories complete; suite green; checked-in outputs match the tool.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T021 Walk through `specs/003-flowsheet-record-id/quickstart.md` steps 1–4 exactly as written (writing step 4's outputs to Scratch) and confirm every stated expectation holds; correct quickstart.md if an expectation is wrong
- [ ] T022 [P] Sweep for leftovers: `grep -rn 'FHIR ID - \|observation-flowsheet-id\|EPIC_FLOWSHEET_SYSTEM' utils tests deploy-specific/ucsd-uat deploy-specific/ucsd-prod README.md` may match only (a) the `OLD_FLOWSHEET_SYSTEM` literal in `tests/conftest.py` and (b) the old-layout header string inside `test_old_layout_csv_rejected` in `tests/test_fork_guards.py`; remove anything else
- [ ] T023 Audit SC-004: list test names with `python3 -m pytest --collect-only -q` and compare against the baseline test names (read them with `git show HEAD:tests/<file>` for tracked files) to confirm every removed or renamed test (`test_uat_file_has_no_prod_ids_and_vice_versa`, `test_missing_prod_id_not_fabricated`, `test_every_row_has_five_cells`) has the replacement named in T003, T013 and T016; report the before/after counts

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001)** → **Foundational (T002)** → user stories
- **US1 (T003–T010)**: needs T002. Blocks US2's verification (T015) and US3's regeneration (T018)
- **US2 (T011–T015)**: test tasks need T002; T014 needs T003 (same file); T015 needs T006–T009
- **US3 (T016–T020)**: T016 is independent; T017 needs T009 (same file); T018 needs T006–T009; T020 needs everything before it
- **Polish (T021–T023)**: after T020

### Why the stories are not fully independent

The tool's mapping record changes shape once (T006–T009); reading, writing and gap
reporting all depend on that shape, so it lands in US1. US2 and US3 then add tests,
artifacts and docs on top. US1 alone is a usable MVP: the tool works with the current CSV.

### Within Each User Story

- Tests are written before the implementation they cover and observed failing (US1), or
  observed passing against behaviour already implemented (US2 — see its note)
- T006 → T007 → T008 → T009 are sequential: one file, and the tool does not import cleanly
  until all four are done

### Parallel Opportunities

- T004 alongside T003 (different files)
- T011 and T013 alongside T012 (different files); T014 after T003
- T016 at any time after T001; T019 alongside T017/T018

---

## Parallel Example: User Story 2

```text
Task: "T011 Replace tests/fixtures/csv-missing-column.csv"
Task: "T012 Update tests/test_fork_guards.py"
Task: "T013 Update tests/test_fork_warnings.py"
# then, alone (shares a file with T003):
Task: "T014 Update test_fork_listed_but_unmapped_questionnaire in tests/test_fork_core.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. T001–T002: baseline and shared constants
2. T003–T010: tests, then the tool
3. **STOP and VALIDATE**: US1 Independent Test — correct PHQ-9 outputs in Scratch

### Incremental Delivery

1. US1 → the tool can read the current CSV and emits record-ID codings
2. US2 → gap reporting pinned (one warning per item, missing-column guard, conflicts)
3. US3 → checked-in PHQ-9 outputs regenerated, mapping-file tests and docs updated, suite green
4. Polish → quickstart walk-through, leftover sweep, SC-004 audit

A PR should carry all three stories: the suite is not fully green until T020.

---

## Notes

- Expected red tests between checkpoints are named in T010 and T015; any other failure is
  a defect to fix before moving on
- `tests/test_mapping_csv.py` is untracked in git; T016 edits it in place and T023 has no
  `HEAD` version to compare it against — use the pre-edit file contents instead
- After this feature the constitution's Sync Impact Report still lists the tool, tests and
  PHQ-9 outputs as ⚠ pending; refreshing that report is a constitution edit and is left to
  the maintainer
- Do not `git commit`; the user commits
