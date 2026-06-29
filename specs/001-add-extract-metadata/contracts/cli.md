# CLI Contract: `fork_questionnaire_for_extract.py`

The tool's external interface is its command line, exit code, output files, and stderr warnings.
This contract is the testable surface for `/speckit.tasks`.

## Invocation

```bash
python3 utils/fork_questionnaire_for_extract.py <questionnaire.json> [--csv <path>] \
    [--uat-dir <path>] [--prod-dir <path>]
```

### Arguments

| Arg | Required | Default | Meaning |
|-----|----------|---------|---------|
| `questionnaire` (positional) | yes | — | Path to one source Questionnaire JSON. Exactly one per run. |
| `--csv` | no | `deploy-specific/mapping-input/CNICS PRO UCSD flowsheet FHIR IDs.csv` | Flowsheet-ID CSV path. |
| `--uat-dir` | no | `deploy-specific/ucsd-uat` | Output directory for the UAT Questionnaire. |
| `--prod-dir` | no | `deploy-specific/ucsd-prod` | Output directory for the production Questionnaire. |

Processing more than one Questionnaire is done by the caller looping over single invocations
(Constitution: bulk = loop over single runs). The tool MUST reject more than one positional path.

## Outputs

- **UAT file**: `<uat-dir>/<basename(questionnaire)>` — carries only `FHIR ID - UAT` flowsheet codes.
- **Prod file**: `<prod-dir>/<basename(questionnaire)>` — carries only `FHIR ID - Prod` flowsheet codes.
- Both written only on a successful (non-fatal) run. Existing files are overwritten idempotently.

## Exit codes

| Code | When |
|------|------|
| `0` | Run completed. Mapping gaps/conflicts may have been warned, but both outputs were written. |
| non-zero | Fatal: positional arg count ≠ 1; input not valid JSON; `resourceType != "Questionnaire"`; input is deprecated (`deprecated/` path, `*.deprecated.json`, or `status == "retired"`); CSV missing any required column; output directory unwritable. No output files are written in these cases. |

## stderr (warnings — never fatal)

One line per event; each MUST name the LOINC and/or CSV record and what was missing:

| Event | Example message shape |
|-------|----------------------|
| Item LOINC not in CSV | `WARNING: item linkId=/69722-7 loinc=69722-7 has no CSV record; skipped` |
| Item has no LOINC | `WARNING: item linkId=... has no LOINC code; skipped` |
| Matched record missing env ID | `WARNING: loinc=44260-8 has no FHIR ID - Prod; omitted from prod output` |
| Item is a score | `WARNING: loinc=44261-6 is a computed score (calculatedExpression); excluded from extraction` |
| CSV record matched no item | `WARNING: CSV record "UC R FM PHQ2 TOTAL" loinc=55758-7 matched no item; skipped` |
| Conflicting CSV rows | `WARNING: loinc=X has conflicting CSV rows (...); item left unmodified` |

## Contract test cases (for `/speckit.tasks`)

1. **Happy path**: PHQ-9 + repo CSV → two files exist; each mapped item carries one flowsheet
   coding from the correct env column; UAT file contains no `FHIR ID - Prod` value and vice versa.
2. **One-flowsheet invariant**: no extracted Observation in either output is coded with >1 flowsheet.
3. **Bidirectional gaps**: `69722-7` (item-only) and `55758-7`/`69723-5` (CSV-only) each produce
   exactly one warning; exit code 0; mapped items still written.
4. **Score exclusion**: `/44261-6` receives no extract metadata in either output and is
   byte-identical to source; a warning is emitted.
5. **Idempotency**: running twice on the same source yields byte-identical UAT and prod files.
6. **Deprecated/invalid**: `CIRG-CNICS-ASSIST.deprecated.json`, a `status=retired` fixture, a
   non-Questionnaire JSON, and a CSV missing a column each exit non-zero with a naming message and
   write no output.
7. **No fabrication**: with a CSV row missing the prod ID, the prod output omits that item's
   flowsheet metadata rather than inventing an ID.
