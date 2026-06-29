# Implementation Plan: Fork a FHIR Questionnaire Into Per-Environment `$extract` Outputs

**Branch**: `001-add-extract-metadata` | **Date**: 2026-06-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-add-extract-metadata/spec.md`

## Summary

Build a single-purpose Python CLI in `utils/` that reads one FHIR R4 Questionnaire and the
flowsheet-ID CSV, then writes **two** derived Questionnaires — one under
`deploy-specific/ucsd-uat/` carrying only UAT flowsheet FHIR IDs and one under
`deploy-specific/ucsd-prod/` carrying only production IDs. Each in-scope individual-response
item is matched to a CSV record by its LOINC code and annotated with the SDC metadata HAPI's
`$extract` needs to emit one Observation coded with exactly one flowsheet. Computed score
items, display items, and unmapped items are skipped; every mapping gap (in either direction)
is reported as a warning without failing the run or fabricating IDs. Output must be
idempotent and byte-stable so clinical reviewers can diff each file against one CSV column.

## Technical Context

**Language/Version**: Python 3.11 (matches `python3` 3.11.2 on the box and the existing `utils/*.py`)  
**Primary Dependencies**: Python standard library only — `json`, `csv`, `argparse`, `pathlib`, `sys`. No third-party packages, consistent with `utils/remove_item_extensions.py` and `utils/remove_option_prefix.py`.  
**Storage**: Filesystem. Input Questionnaire JSON + CSV; outputs are two JSON files under `deploy-specific/ucsd-uat/` and `deploy-specific/ucsd-prod/`.  
**Testing**: pytest (new dev dependency; the repo has no test suite today). Unit tests on the mapping/extract functions plus an idempotency test that re-runs the tool on its own output.  
**Target Platform**: Local CLI, run from the repo root by an informaticist/developer on Linux/macOS.  
**Project Type**: Single CLI tool (one script under `utils/`), following the existing single-file-transform precedent in this repo.  
**Performance Goals**: Not a concern — one Questionnaire (<50 items) per run, sub-second.  
**Constraints**: Byte-identical, idempotent output (stable JSON serialization preserving key order and the source file's indentation/`ensure_ascii` style); exactly one flowsheet code per extracted Observation; no fabricated IDs; warnings to stderr, never fatal for mapping gaps.  
**Scale/Scope**: ~30 Questionnaires in the repo, processed one at a time; bulk runs are shell loops over this tool.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution v2.0.0. Each principle is satisfied by an explicit design rule:

| Principle | Gate | How this plan satisfies it |
|-----------|------|----------------------------|
| **I. One Observation per response, exactly one flowsheet code** | Extracted Observation shape fixed; one flowsheet coding; scores excluded | Tool annotates each in-scope item so HAPI emits one Observation per answer with `category=vital-signs`, exactly one flowsheet coding (system `http://open.epic.com/FHIR/StructureDefinition/observation-flowsheet-id`, code = the environment's FHIR ID). Score items get no metadata. |
| **II. JSONPath in HAPI; no CQL** | No CQL introduced | Tool only injects static SDC metadata + flowsheet codings; any extraction expression emitted is JSONPath. No CQL anywhere. |
| **III. CSV maps LOINC → per-env IDs** | Join on `LOINC code`; bidirectional warnings; no guessing | Matching is item-LOINC ↔ CSV `LOINC code` column; unmatched records and unmatched items both warn and continue; tool never invents IDs. |
| **IV. Fork into per-environment outputs** | Two files, UAT-only and prod-only IDs, correct dirs; exclusions | Two outputs written to `deploy-specific/ucsd-uat/` and `deploy-specific/ucsd-prod/`; UAT file carries only `FHIR ID - UAT`, prod only `FHIR ID - Prod`; scores/display/unmapped/no-LOINC items left byte-for-byte unchanged. |
| **V. Idempotent, minimal-diff** | Re-run → byte-identical; minimal diff | Stable serializer preserves key order + source formatting; tool mutates only the metadata it owns; idempotency covered by a test. |
| **Extraction Metadata Standards** | One Questionnaire per run; deprecated skipped; CSV under `mapping-input/` | CLI takes one Questionnaire path; refuses `deprecated/`, `*.deprecated.json`, `status=retired`; reads the CSV at `deploy-specific/mapping-input/`. |
| **Development Workflow** | PR includes both outputs + CSV; reviewable | Outputs are deterministic and diffable against a single CSV column. |

**Result**: PASS. No violations; Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/001-add-extract-metadata/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── cli.md           # Phase 1 output — CLI command contract
├── checklists/
│   └── requirements.md  # From /speckit.specify
└── tasks.md             # /speckit.tasks output (NOT created here)
```

### Source Code (repository root)

```text
utils/
└── fork_questionnaire_for_extract.py   # The CLI tool (new)

tests/
└── test_fork_questionnaire_for_extract.py   # pytest unit + idempotency tests (new)

deploy-specific/
├── mapping-input/
│   └── CNICS PRO UCSD flowsheet FHIR IDs.csv   # input CSV (exists)
├── ucsd-uat/            # UAT outputs (exists, currently empty)
└── ucsd-prod/           # production outputs (exists, currently empty)

CIRG-*.json              # source Questionnaires at repo root (inputs)
```

**Structure Decision**: Single CLI tool added to the existing `utils/` directory, matching
the established single-file-transform pattern (`remove_item_extensions.py`,
`remove_option_prefix.py`). A new top-level `tests/` directory holds pytest tests, including
fixtures derived from `CIRG-PHQ-9.json`. No package, no framework, stdlib only.

## Complexity Tracking

> No constitution violations — section intentionally empty.
