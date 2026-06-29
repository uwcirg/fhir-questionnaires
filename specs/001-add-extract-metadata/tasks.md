---
description: "Task list for: Fork a FHIR Questionnaire Into Per-Environment $extract Outputs"
---

# Tasks: Fork a FHIR Questionnaire Into Per-Environment `$extract` Outputs

**Input**: Design documents from `/specs/001-add-extract-metadata/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md, quickstart.md

**Tests**: INCLUDED — the spec defines explicit Independent Tests per story and `contracts/cli.md`
lists 7 contract test cases (idempotency, one-flowsheet invariant, bidirectional gaps, etc.).

**Organization**: Tasks are grouped by user story. The deliverable is a single CLI tool
(`utils/fork_questionnaire_for_extract.py`), so **all implementation tasks edit that one file
and are therefore sequential** — `[P]` is used only for genuinely independent files (separate
test modules, fixtures). This is called out in Parallel Opportunities.

## Path Conventions

- Tool: `utils/fork_questionnaire_for_extract.py` (repo root `utils/`, matches existing utils)
- Tests: `tests/` at repo root, pytest; fixtures in `tests/conftest.py`
- Inputs: source `CIRG-*.json` at repo root; CSV at `deploy-specific/mapping-input/`
- Outputs: `deploy-specific/ucsd-uat/`, `deploy-specific/ucsd-prod/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project skeleton and test harness

- [ ] T001 Create the tool skeleton at `utils/fork_questionnaire_for_extract.py`: shebang, module docstring summarizing the fork behavior, `argparse` CLI (one positional `questionnaire`; optional `--csv`, `--uat-dir`, `--prod-dir` with defaults from `contracts/cli.md`), and a `main()` that parses args and returns an exit code (stub body for now).
- [ ] T002 [P] Add pytest scaffolding: create `tests/` with empty `tests/__init__.py` and a `pytest.ini` (or `[tool.pytest.ini_options]`) at repo root setting `testpaths = tests`.
- [ ] T003 [P] Create test fixtures in `tests/conftest.py`: a pytest fixture giving a tmp copy of `CIRG-PHQ-9.json`, a fixture for the repo CSV path, plus small in-repo fixture files for a `status=retired` Questionnaire, a non-Questionnaire JSON, and a CSV missing a required column (write fixture data under `tests/fixtures/`).

**Checkpoint**: `pytest` runs (collects 0 tests) and `python3 utils/fork_questionnaire_for_extract.py --help` prints usage.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Parsing, validation, mapping index, and serialization that ALL stories depend on. All edit `utils/fork_questionnaire_for_extract.py` → sequential.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T004 Implement input guards in `utils/fork_questionnaire_for_extract.py` (FR-011, research R6): reject and `sys.exit(non-zero)` with a file-naming message when the input path is under `deprecated/`, matches `*.deprecated.json`, has `status == "retired"`, is not valid JSON, or `resourceType != "Questionnaire"`. No output written on failure.
- [ ] T005 Implement the CSV loader in `utils/fork_questionnaire_for_extract.py`: read with `csv.DictReader`; validate the required columns `RECORD NAME`, `LOINC code`, `FHIR ID - UAT`, `FHIR ID - Prod` (missing any → exit non-zero naming the column, before any output); build a `loinc -> {uat, prod, record_name}` index and record duplicate-LOINC conflicts separately (data-model entity 2; FR-009 detection only).
- [ ] T006 Implement the LOINC extraction helper in `utils/fork_questionnaire_for_extract.py` (research R1): return the LOINC from `item.code[].code`, falling back to `linkId` with one leading `/` stripped; `None` if neither yields a value.
- [ ] T007 Implement the recursive item walker in `utils/fork_questionnaire_for_extract.py`: yield every item at any nesting depth with its parent context, so groups recurse and leaf items are classified (data-model entity 1).
- [ ] T008 Implement the byte-stable serializer in `utils/fork_questionnaire_for_extract.py` (research R5; Constitution Principle V): `json.dump(..., indent=2, ensure_ascii=False)` plus trailing newline, preserving source key order, writing to a given output directory using `basename(questionnaire)`; create the output dir if missing.

**Checkpoint**: Foundation ready — guards, CSV index, LOINC matching, walker, and writer exist and are unit-callable.

---

## Phase 3: User Story 1 - Fork one Questionnaire into UAT and production outputs (Priority: P1) 🎯 MVP

**Goal**: Given a Questionnaire + CSV, write two files (UAT-only and prod-only flowsheet IDs), each in-scope item annotated so HAPI `$extract` emits one Observation with exactly one flowsheet coding.

**Independent Test**: Run on `CIRG-PHQ-9.json`; confirm `deploy-specific/ucsd-uat/CIRG-PHQ-9.json` and `deploy-specific/ucsd-prod/CIRG-PHQ-9.json` exist, each mapped item carries its env's flowsheet ID, no Observation has >1 flowsheet coding, and a re-run is byte-identical.

### Tests for User Story 1

> Write these FIRST and ensure they FAIL before implementation.

- [ ] T009 [P] [US1] Happy-path contract test in `tests/test_fork_core.py` (cli.md case 1): two files produced; each mapped item carries the env-correct flowsheet coding with `system = http://open.epic.com/FHIR/StructureDefinition/observation-flowsheet-id`; UAT file contains no `FHIR ID - Prod` value and vice versa.
- [ ] T010 [P] [US1] One-flowsheet-invariant test in `tests/test_fork_core.py` (cli.md case 2): assert no item in either output yields an Observation coded with more than one flowsheet (Constitution Principle I; matches the example Observation in `data-model.md`).
- [ ] T011 [P] [US1] Idempotency test in `tests/test_fork_core.py` (cli.md case 5): running the tool twice on `CIRG-PHQ-9.json` produces byte-identical UAT and prod files.
- [ ] T012 [P] [US1] Guard tests in `tests/test_fork_guards.py` (cli.md case 6; spec US1 scenario 3): deprecated path, `*.deprecated.json`, `status=retired`, non-Questionnaire JSON, and CSV-missing-column each exit non-zero, name the reason, and write no output.

### Implementation for User Story 1

- [ ] T013 [US1] Implement per-item, per-environment extract-metadata injection in `utils/fork_questionnaire_for_extract.py` (data-model entity 4; research R3): add the SDC `observationExtract` boolean extension and the single flowsheet coding (`system` Epic flowsheet-id, `code` = the env's FHIR ID) so HAPI emits one Observation with `category=vital-signs`, subject + effectiveDateTime from the QR. Touch only owned elements.
- [ ] T014 [US1] Implement the two-document build in `utils/fork_questionnaire_for_extract.py`: deep-copy the source into a UAT doc and a prod doc, injecting only that environment's flowsheet ID per mapped in-scope item; skip `display`/`group` items (FR-003, FR-005).
- [ ] T015 [US1] Wire `main()` end-to-end in `utils/fork_questionnaire_for_extract.py`: guards → load CSV index → walk items → build both docs → write via the serializer to `--uat-dir` and `--prod-dir`; return exit 0 on success.

**Checkpoint**: MVP works — `python3 utils/fork_questionnaire_for_extract.py CIRG-PHQ-9.json` writes both files; T009–T012 pass.

---

## Phase 4: User Story 2 - Surface mapping gaps without inventing data (Priority: P1)

**Goal**: Report every mapping mismatch (both directions) and never fabricate IDs, without failing the run.

**Independent Test**: Run on PHQ-9 + repo CSV; confirm warnings for item-only LOINC `69722-7`, CSV-only LOINCs `55758-7`/`69723-5`, and any missing env ID; exit code 0; mapped items still written; no invented IDs.

### Tests for User Story 2

- [ ] T016 [P] [US2] Bidirectional-gap test in `tests/test_fork_warnings.py` (cli.md case 3; FR-008): assert exactly one warning each for item-only `69722-7` and CSV-only `55758-7`/`69723-5`, exit 0, mapped items still present in outputs.
- [ ] T017 [P] [US2] No-fabrication test in `tests/test_fork_warnings.py` (cli.md case 7; FR-007): with a CSV row missing the prod ID, the prod output omits that item's flowsheet metadata (no invented value) while UAT still carries it, and a warning names the missing ID.
- [ ] T018 [P] [US2] Conflict test in `tests/test_fork_warnings.py` (cli.md; FR-009): a LOINC with conflicting CSV rows warns naming the rows and leaves that item unmodified in both outputs; exit 0.

### Implementation for User Story 2

- [ ] T019 [US2] Implement per-item outcome classification + warnings to stderr in `utils/fork_questionnaire_for_extract.py` (data-model entity 3): `unmapped_item`, `no_loinc`, and `missing_env_id` each emit a `WARNING:` line naming the LOINC/linkId and what is missing.
- [ ] T020 [US2] Emit `unmatched_record` warnings in `utils/fork_questionnaire_for_extract.py`: after walking items, warn once per CSV record whose `LOINC code` matched no item (FR-008).
- [ ] T021 [US2] Apply conflict handling in `utils/fork_questionnaire_for_extract.py`: for conflicting-LOINC rows from T005, warn and skip the item in both outputs; ensure gaps/conflicts never change the exit code from 0 (FR-009).

**Checkpoint**: US1 + US2 both work; warning stream matches the shapes in `contracts/cli.md`.

---

## Phase 5: User Story 3 - Exclude computed score items (Priority: P2)

**Goal**: Leave computed score items untouched and out of extraction in both outputs.

**Independent Test**: Run on PHQ-9; confirm `/44261-6` receives no extract metadata in either output, is byte-identical to source, and a warning notes the matched CSV record was skipped as a score.

### Tests for User Story 3

- [ ] T022 [P] [US3] Score-exclusion test in `tests/test_fork_scores.py` (cli.md case 4; FR-007, SC-007): the `calculatedExpression` item `/44261-6` has no added flowsheet metadata in UAT or prod output and is byte-identical to the source item; a warning is emitted that the matched CSV record maps to a score.

### Implementation for User Story 3

- [ ] T023 [US3] Implement score detection + exclusion in `utils/fork_questionnaire_for_extract.py` (research R4): classify an item as a score when it carries an `sdc-questionnaire-calculatedExpression` extension; skip it (no metadata, unchanged), and if its LOINC also matched a CSV record, emit a warning that the record was skipped because it maps to a score item.

**Checkpoint**: All three stories independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T024 [P] Add a docstring/usage example block to `utils/fork_questionnaire_for_extract.py` mirroring `quickstart.md`, and a one-line pointer to the tool in `README.md`.
- [ ] T025 Run the `quickstart.md` validation end-to-end (fork PHQ-9, verify two files + idempotent re-run with `git diff --stat`) and confirm the produced UAT Observation matches the example in `data-model.md`.
- [ ] T026 [P] Add an edge-case unit test in `tests/test_fork_core.py` for nested/group items and an item with no LOINC code (data-model edge cases): group items get no metadata; no-LOINC item warns and is unchanged.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup. BLOCKS all user stories.
- **User Stories (Phase 3–5)**: All depend on Foundational. US2 and US3 layer onto US1's mapping/build logic in the same file, so in practice they proceed in priority order (US1 → US2 → US3) rather than in parallel.
- **Polish (Phase 6)**: After the desired stories are complete.

### User Story Dependencies

- **US1 (P1)**: Foundation only. MVP.
- **US2 (P1)**: Builds on US1's item-classification/build path (same file).
- **US3 (P2)**: Builds on US1's walker/build path (same file).

### Within Each User Story

- Tests written first and failing before implementation.
- Foundational helpers before story logic; build before write; story complete before next priority.

### Parallel Opportunities

- Setup: T002 and T003 are `[P]` (different files) — T001 is the tool file.
- **All Phase 2 tasks are sequential** (one file: `utils/fork_questionnaire_for_extract.py`).
- **Test tasks are `[P]` across distinct test modules** (`test_fork_core.py`, `test_fork_guards.py`, `test_fork_warnings.py`, `test_fork_scores.py`); tests within the *same* module are sequential.
- **All implementation tasks (T013–T015, T019–T021, T023) are sequential** — they edit the one tool file. Do not parallelize them.

---

## Parallel Example: User Story 1 tests

```bash
# These touch different test modules → safe to write in parallel:
Task: "Happy-path + invariant + idempotency tests in tests/test_fork_core.py"   # T009–T011 (same file, sequential within)
Task: "Guard tests in tests/test_fork_guards.py"                                 # T012 (separate file, [P])
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 Setup → 2. Phase 2 Foundational (critical) → 3. Phase 3 US1 → 4. **STOP & VALIDATE**: fork PHQ-9, confirm two files, one flowsheet code each, idempotent re-run.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. US1 → MVP (two correct per-environment files).
3. US2 → trustworthy gap reporting, no fabrication.
4. US3 → scores correctly excluded.
5. Polish → docs + quickstart validation.

---

## Notes

- `[P]` = different files, no dependency. The tool is a single file, so most implementation is intentionally sequential.
- `[Story]` labels map tasks to spec user stories for traceability.
- Verify tests fail before implementing.
- Commit after each task or logical group.
- Never fabricate flowsheet IDs; gaps warn but keep exit 0 (Constitution Principle III).
