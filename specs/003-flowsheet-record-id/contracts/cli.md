# CLI Contract: `fork_questionnaire_for_extract.py` (constitution v4.0.0)

Supersedes `specs/001-add-extract-metadata/contracts/cli.md`. The tool's external interface
is its command line, exit code, output files, and stderr warnings.

## Invocation (unchanged)

```bash
python3 utils/fork_questionnaire_for_extract.py <questionnaire.json> [--csv <path>] \
    [--uat-dir <path>] [--prod-dir <path>]
```

| Arg | Required | Default | Meaning |
|-----|----------|---------|---------|
| `questionnaire` (positional) | yes | — | Path to one source Questionnaire JSON. Exactly one per run. |
| `--csv` | no | `deploy-specific/mapping-input/CNICS PRO UCSD flowsheet FHIR IDs.csv` | Flowsheet mapping CSV ([format](./mapping-csv.md)). |
| `--uat-dir` | no | `deploy-specific/ucsd-uat` | Output directory for the UAT Questionnaire. |
| `--prod-dir` | no | `deploy-specific/ucsd-prod` | Output directory for the production Questionnaire. |

## Outputs

- **UAT file**: `<uat-dir>/<basename(questionnaire)>`
- **Prod file**: `<prod-dir>/<basename(questionnaire)>`

Each mapped, in-scope item carries exactly one flowsheet coding:

| | UAT file | Prod file |
|---|----------|-----------|
| `code` | the row's `Flowsheet Record ID` | the same value |
| `system` | `urn:oid:1.2.840.114350.1.13.136.3.7.2.707679` | `urn:oid:1.2.840.114350.1.13.136.2.7.2.707679` |

- The two files differ only in those `system` values.
- Neither file contains a flowsheet FHIR ID or a coding under
  `http://open.epic.com/FHIR/StructureDefinition/observation-flowsheet-id`.
- Both are written only on a non-fatal run. Existing files are overwritten idempotently.

## Exit codes (unchanged)

| Code | When |
|------|------|
| `0` | Run completed. Gaps/conflicts may have been warned; both outputs were written. |
| non-zero | Fatal: positional arg count ≠ 1; input not valid JSON; `resourceType != "Questionnaire"`; input is deprecated (`deprecated/` path, `*.deprecated.json`, or `status == "retired"`); CSV missing a required column (`RECORD NAME (UCSD Epic)`, `LOINC code`, `Flowsheet Record ID`); output directory unwritable. No output is written. |

A CSV in the former layout (`FHIR ID - UAT` / `FHIR ID - Prod`, no `Flowsheet Record ID`)
is a missing-column fatal error.

## stderr (warnings — never fatal)

| Event | Message shape | Status |
|-------|---------------|--------|
| Item identifier not in CSV | `WARNING: item linkId=69722-7 loinc=69722-7 has no CSV record; skipped` | unchanged |
| Item has no identifier | `WARNING: item linkId=... has no LOINC code; skipped` | unchanged |
| Matched row has no record ID | `WARNING: loinc=AUDIT-0 has no Flowsheet Record ID; omitted from both outputs` | **changed** — one line per item, was one per environment |
| Item is a score | `WARNING: loinc=44261-6 is a computed score (calculatedExpression); excluded from extraction` | unchanged |
| CSV record matched no item | `WARNING: CSV record "UC R FM PHQ2 TOTAL" loinc=55758-7 matched no item; skipped` | unchanged |
| Conflicting CSV rows | `WARNING: loinc=X has conflicting CSV rows (...); item left unmodified` | unchanged shape; conflict = differing record IDs |

## Contract test cases

1. **Happy path**: PHQ-9 + repo CSV → exit 0, two files; item `44250-9` carries code `3025`
   under the UAT system in the UAT file and under the prod system in the prod file; 9 items
   coded in each.
2. **One-flowsheet invariant**: no item in either output has more than one coding under
   that file's flowsheet system, and none under the other environment's.
3. **Differ only in system**: substituting one system URI for the other makes the two
   files byte-identical; without substitution they differ.
4. **Old scheme absent**: neither output contains `observation-flowsheet-id`.
5. **Bidirectional gaps**: `69722-7` (item-only) and `55758-7` / `69723-5` (CSV-only) each
   produce exactly one warning; exit 0; mapped items still written.
6. **Score exclusion**: `44261-6` gets no extract metadata in either output and equals the
   source item; a warning is emitted.
7. **Idempotency**: a second run yields byte-identical UAT and prod files.
8. **Checked-in outputs**: a run on `CIRG-PHQ-9.json` reproduces
   `deploy-specific/ucsd-{uat,prod}/CIRG-PHQ-9.json` byte for byte.
9. **No fabrication**: a row with a blank record ID → item uncoded in both outputs,
   exactly one warning, exit 0.
10. **Listed-but-unbuilt Questionnaire**: `CIRG-CNICS-AUDIT.json` + repo CSV → exit 0, both
    files written, one missing-record-ID warning per listed item, no flowsheet coding and no
    category extension in either file; separator rows never reported.
11. **Conflict**: two rows, same identifier, different record IDs → item uncoded in both
    outputs, conflict warning.
12. **Missing column**: CSV without `Flowsheet Record ID` (including an old-layout CSV) →
    non-zero exit naming the column, no output.
13. **Tolerant reading**: extra CSV columns ignored; whitespace around a record ID trimmed;
    an item already carrying the environment's flowsheet coding is not given a second.
14. **Deprecated/invalid input**: unchanged from feature 001.
