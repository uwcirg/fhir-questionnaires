# Implementation Plan: Code Per-Environment Questionnaires With the Flowsheet Record ID

**Branch**: `003-flowsheet-record-id` | **Date**: 2026-10-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-flowsheet-record-id/spec.md`

## Summary

Bring `utils/fork_questionnaire_for_extract.py`, its tests, and the two checked-in PHQ-9
outputs into line with constitution v4.0.0. The tool reads one `Flowsheet Record ID` column
instead of two FHIR ID columns, writes that ID as the flowsheet coding's `code` in both
outputs, and takes the coding's `system` from a single per-environment mapping (UAT and
production OIDs). A blank record ID is warned about once per item rather than once per
environment. The tests are rewritten to assert the new scheme — including a byte-level check
that the two outputs differ only in `system` — and the mapping-file tests move to the
four-column layout. The CLI, item scoping, input guards, serialization and all other
warnings are unchanged. The suite goes from 34 failures to 0.

## Technical Context

**Language/Version**: Python 3.11 (matches `python3` 3.11.2 on the box and the existing `utils/*.py`)
**Primary Dependencies**: Python standard library only — `argparse`, `copy`, `csv`, `json`, `pathlib`, `sys` (all already imported by the tool). No third-party packages.
**Storage**: Filesystem. Input: one CSV under `deploy-specific/mapping-input/` and one source Questionnaire JSON per run. Output: one JSON file each under `deploy-specific/ucsd-uat/` and `deploy-specific/ucsd-prod/`.
**Testing**: pytest via `pytest.ini`. 69 tests today, 34 failing because the CSV is ahead of the code. Existing modules are updated in place; no new test module.
**Target Platform**: Local, run from the repo root on Linux/macOS.
**Project Type**: Single-file CLI tool plus generated data files; no package structure.
**Performance Goals**: Not a concern — one Questionnaire and a 246-line CSV per run.
**Constraints**: CLI unchanged; byte-stable idempotent output; UAT and production outputs differ only in `system`; no fabricated IDs; mapping CSV and source Questionnaires not edited; the set of PHQ-9 items coded (9) unchanged.
**Scale/Scope**: 1 tool (~525 lines; roughly 40 lines change), 6 test files + 1 fixture, 2 regenerated JSON outputs, 1 README sentence.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution v4.0.0.

| Principle | Gate | How this plan satisfies it |
|-----------|------|----------------------------|
| **I. One Observation per reported item, exactly one flowsheet code** | `code` = flowsheet record ID; `system` = the target environment's OID; no FHIR ID, no `observation-flowsheet-id` system; `vital-signs` category declared | The coding is built from the row's record ID and `FLOWSHEET_SYSTEMS[env]` (research R2). The old system constant is deleted. The duplicate guard keeps the coding to one per item (R3). Category declaration untouched. Tests assert each point. |
| **II. JSONPath in HAPI; no CQL** | No CQL introduced | No extraction logic is added. |
| **III. CSV maps items to flowsheet record IDs** | Read `Flowsheet Record ID`; join on `LOINC code`; skip blank-identifier rows; warn in both directions; warn on blank record ID; never guess; CSV holds no `system` values | Required columns become record name, `LOINC code`, `Flowsheet Record ID` (R1). Blank record ID → one warning, no coding (R4). Unmatched-row and unmapped-item warnings unchanged. System values live in the tool, not the CSV. |
| **IV. Fork into per-environment outputs** | Two outputs; same `code`, environment's `system`; no other difference; excluded items byte-for-byte unchanged | `build_environment_output` is still called once per environment and differs only in the system passed in. A byte-level test proves the outputs differ only in `system` (R7). Scores, display, group and unmapped items are not touched. |
| **V. Idempotent, minimal-diff** | Byte-identical re-runs; reviewable diff | Serializer unchanged. Regenerated PHQ-9 outputs change only the `system` and `code` lines of 9 codings (R9). Existing idempotency and checked-in-output tests are kept. |
| **Extraction Metadata Standards** | Min. columns; system values defined in exactly one place, keyed by environment; one Questionnaire per run; deprecated inputs skipped | `FLOWSHEET_SYSTEMS` is the single definition. CLI and guards unchanged. `tests/test_mapping_csv.py` enforces the four-column file. |
| **Development Workflow** | PR carries the generated outputs with what they depend on; outputs verifiable against the CSV column and the environment's system | PR contains the tool, tests, and both regenerated PHQ-9 files. `quickstart.md` gives the reviewer's check. |

**Known gaps, not violations introduced by this feature**: the tool strips the leading `/`
from every `linkId`, so it cannot match `CIRG-PC-PTSD-5` rows (Principle III), and it skips
every computed item rather than only `CIRG-PHQ9` scores and "internal" items (Principle I).
Both predate this feature, are declared out of scope in the spec, remain ⚠ pending in the
constitution's Sync Impact Report, and cannot affect any output while only PHQ-9 rows carry
record IDs (research R11).

**Result**: PASS. Complexity Tracking not required.

**Post-design re-check**: PASS — the data model and contracts add nothing beyond the gates
above; the design removes a state (an item coded in one environment but not the other)
rather than adding one.

## Project Structure

### Documentation (this feature)

```text
specs/003-flowsheet-record-id/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── cli.md           # Phase 1 output — tool CLI, outputs, warnings, test cases
│   └── mapping-csv.md   # Phase 1 output — four-column CSV format
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit.tasks — not created here)
```

### Source Code (repository root)

```text
utils/
└── fork_questionnaire_for_extract.py       # MODIFIED: record-ID column, FLOWSHEET_SYSTEMS,
                                            #   single missing-ID warning, docstrings/help

tests/
├── conftest.py                             # MODIFIED: flowsheet system literals
├── test_fork_core.py                       # MODIFIED: record ID + per-env system; new
│                                           #   differ-only-in-system and old-scheme-absent tests
├── test_fork_warnings.py                   # MODIFIED: 3-column test CSVs; one warning per gap;
│                                           #   trim / extra-column / pre-coded-item cases
├── test_fork_scores.py                     # MODIFIED: checks both new systems
├── test_fork_guards.py                     # MODIFIED: names `Flowsheet Record ID`; old-layout CSV
├── test_mapping_csv.py                     # MODIFIED: four columns; PHQ-9 record IDs pinned
└── fixtures/csv-missing-column.csv         # MODIFIED: record-ID column absent

deploy-specific/ucsd-uat/CIRG-PHQ-9.json    # REGENERATED
deploy-specific/ucsd-prod/CIRG-PHQ-9.json   # REGENERATED
README.md                                   # MODIFIED: drop the "tool needs updating" note

deploy-specific/mapping-input/CNICS PRO UCSD flowsheet FHIR IDs.csv   # READ ONLY
CIRG-PHQ-9.json and the other source Questionnaires                  # READ ONLY
```

**Structure Decision**: No new files or directories outside `specs/`. The change is confined
to the existing tool and the tests beside it. (The `src/` / `tests/` tree in `CLAUDE.md` is
template boilerplate; the repository's real layout is `utils/` + `tests/`.)

## Implementation Outline

Order matters only where noted; detail is for `/speckit.tasks`.

1. **Tests first** (research R6–R8): add the system literals to `conftest.py`; rewrite the
   fork tests and fixture against the record-ID scheme; update `test_mapping_csv.py` to four
   columns. The mapping-file tests pass immediately (the CSV is already correct); the fork
   tests fail until step 2.
2. **Tool** (R1–R5): constants, `load_csv_index`, `inject_extract_metadata`,
   `build_environment_output`, `report_gaps`, docstrings and help text.
3. **Regenerate** the two PHQ-9 outputs (R9) — must follow step 2; confirm the diff is 9
   codings per file and nothing else.
4. **Docs** (R10): README sentence.
5. **Verify** with `quickstart.md`: full suite green, outputs differ only in `system`,
   second run is a no-op.

## Complexity Tracking

No violations.
