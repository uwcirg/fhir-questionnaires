# Implementation Plan: Populate Flowsheet Mapping CSV for CNICS Questionnaires

**Branch**: `002-populate-flowsheet-mapping-csv` | **Date**: 2026-10-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-populate-flowsheet-mapping-csv/spec.md`

## Summary

Restructure `deploy-specific/mapping-input/CNICS PRO UCSD flowsheet FHIR IDs.csv` into the
five-column worksheet defined by constitution v3.1.0 and add one section per Questionnaire:
the 12 existing PHQ-9 rows under a `CIRG-PHQ9` separator, then 19 new sections holding 213
item rows (label + identifier, UCSD-owned cells blank). The rows are authored once — the
`CNICS NAME` labels are human judgments — and the result is locked in by a new pytest module
that re-derives the expected rows from the 19 source Questionnaires and checks every spec
requirement. The fork tool gets the one change it needs to keep reading the file: the
record-name column is looked up under its new header. PHQ-9 per-environment outputs must
regenerate byte-identically.

## Technical Context

**Language/Version**: Python 3.11 (matches `python3` 3.11.2 on the box and the existing `utils/*.py`)
**Primary Dependencies**: Python standard library only — `csv`, `json`, `pathlib`. No third-party packages.
**Storage**: Filesystem. One CSV under `deploy-specific/mapping-input/`; 19 Questionnaire JSON files at the repo root are read-only inputs.
**Testing**: pytest (already configured via `pytest.ini`; 17 tests passing before this feature). One new module, `tests/test_mapping_csv.py`; existing fixtures/tests updated for the renamed column.
**Target Platform**: Local, run from the repo root on Linux/macOS. The CSV is opened by UCSD analysts in a spreadsheet application.
**Project Type**: Data file + single-file CLI tool (`utils/fork_questionnaire_for_extract.py`), no package structure.
**Performance Goals**: Not a concern — 20 Questionnaires, 246 CSV lines.
**Constraints**: Existing PHQ-9 values unchanged; PHQ-9 per-environment outputs byte-identical; five cells in every row; CRLF line endings kept; no fabricated record names or FHIR IDs; source Questionnaires untouched.
**Scale/Scope**: 1 header + 20 separator rows + 12 existing PHQ-9 rows + 213 new item rows = 246 lines.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution v3.1.0.

| Principle | Gate | How this plan satisfies it |
|-----------|------|----------------------------|
| **I. One Observation per reported item, exactly one flowsheet code** | Computed totals reported except CIRG-PHQ9 and "internal" items | The CSV lists computed items for the 19 Questionnaires (38 of the 213 rows) and omits the 14 "internal" ones. No Observation shape is touched. The tool still skips every computed item at fork time; that pre-existing gap is tracked for a follow-up feature and has no effect while FHIR IDs are blank. |
| **II. JSONPath in HAPI; no CQL** | No CQL introduced | No extraction logic is added. |
| **III. CSV maps items to per-env IDs** | Column set and order; `LOINC code` from linkId; PC-PTSD-5 keeps `/`; separator rows; row exclusions; site-owned cells blank; no guessing | Header becomes `CNICS NAME,RECORD NAME (UCSD Epic),LOINC code,FHIR ID - UAT,FHIR ID - Prod`. Each section starts with a separator row (id in `CNICS NAME`, rest blank). One row per item except display, "internal", and group items; itemControl does not exclude. PC-PTSD-5 identifiers written with their leading `/`. Record name and FHIR IDs left blank for all new rows. Tool already skips blank-`LOINC code` rows and already warns in both directions. |
| **IV. Fork into per-environment outputs** | Outputs unchanged for PHQ-9 | No new per-environment files are generated. PHQ-9 outputs are regenerated only to prove they are byte-identical. |
| **V. Idempotent, minimal-diff** | Tool change minimal | Tool diff is limited to the column-name constant and its one lookup (plus docstring). Existing PHQ-9 CSV rows keep their order and values; each gains only a leading label cell. |
| **Extraction Metadata Standards** | Min. columns; rows contiguous under separator in item order; blank site cells | Enforced by `tests/test_mapping_csv.py`. Deprecated files (`CIRG-CNICS-ASSIST.deprecated.json`) are never read. |
| **Development Workflow** | PR carries CSV + what depends on it | PR contains the CSV, the tool/test rename, and the new validation test. |

**Known gap, not a violation of this feature**: the tool strips the leading `/` from every
linkId, so it cannot yet match `CIRG-PC-PTSD-5` rows (Principle III), and it skips all
computed items (Principle I). Both are spec-declared out of scope and were flagged ⚠ pending
in the v3.1.0 Sync Impact Report. See research R7.

**Result**: PASS. Complexity Tracking not required.

**Post-design re-check**: PASS — the data model and contract add nothing beyond the gates above.

## Project Structure

### Documentation (this feature)

```text
specs/002-populate-flowsheet-mapping-csv/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── mapping-csv.md   # Phase 1 output — the CSV file-format contract
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit.tasks — not created here)
```

### Source Code (repository root)

```text
deploy-specific/mapping-input/
└── CNICS PRO UCSD flowsheet FHIR IDs.csv   # MODIFIED: new header, 20 sections

utils/
└── fork_questionnaire_for_extract.py       # MODIFIED: RECORD NAME → RECORD NAME (UCSD Epic)

tests/
├── test_mapping_csv.py                     # NEW: validates the CSV against the Questionnaires
├── test_fork_warnings.py                   # MODIFIED: header string in _write_csv
└── fixtures/csv-missing-column.csv         # MODIFIED: header uses the new column names

CIRG-CNICS-*.json, CIRG-PC-PTSD-5.json      # READ ONLY (19 files)
deploy-specific/ucsd-uat/CIRG-PHQ-9.json    # UNCHANGED (regeneration must be a no-op)
deploy-specific/ucsd-prod/CIRG-PHQ-9.json   # UNCHANGED
```

**Structure Decision**: No new directories. The deliverable is the CSV itself; the only new
code is one test module beside the existing `tests/test_fork_*.py`. No row-generating script
is committed (research R1).

## Complexity Tracking

No violations.
