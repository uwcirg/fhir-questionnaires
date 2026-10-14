# Research: Code Per-Environment Questionnaires With the Flowsheet Record ID

No `NEEDS CLARIFICATION` items remained in the Technical Context. The decisions below
settle the design choices the spec leaves to planning. All were checked against the code
and data in the repository on 2026-10-13.

## R1 — How the tool reads the record ID

**Decision**: Replace the two per-environment CSV columns with one. `REQUIRED_CSV_COLUMNS`
becomes `RECORD NAME (UCSD Epic)`, `LOINC code`, `Flowsheet Record ID`. Each loaded record
carries a single `record_id` (trimmed) in place of `uat` / `prod`. `ENV_COLUMNS` is deleted.

**Rationale**: Constitution v4.0.0 Principle III. One value serves both environments, so a
per-environment lookup on the record no longer has anything to select.

**Alternatives considered**:
- *Keep `uat`/`prod` keys, both set to the record ID* — smallest diff, but leaves a data
  shape that implies the IDs can differ, which is the misunderstanding being removed.
- *Accept either layout (old or new)* — rejected: FR-002 says the old columns must not be
  read, and silently accepting an old file would emit FHIR IDs as record IDs.

## R2 — Where the two `system` values live

**Decision**: One module-level mapping in the tool, keyed by the environment keys already
used throughout (`"uat"`, `"prod"`):

```python
FLOWSHEET_SYSTEMS = {
    "uat": "urn:oid:1.2.840.114350.1.13.136.3.7.2.707679",
    "prod": "urn:oid:1.2.840.114350.1.13.136.2.7.2.707679",
}
```

`EPIC_FLOWSHEET_SYSTEM` is deleted. `build_environment_output(…, env)` passes
`FLOWSHEET_SYSTEMS[env]` to `inject_extract_metadata(item, system, record_id)`.

**Rationale**: FR-004 and the constitution's Extraction Metadata Standards require the
values to be defined in exactly one place, keyed by environment. They are per-environment,
not per-item, so they do not belong in the CSV (Principle III forbids it).

**Alternatives considered**:
- *CLI options `--uat-system` / `--prod-system`* — rejected: the spec fixes the CLI as
  unchanged, and the values are constitutional constants, not run-time choices.
- *A config file under `deploy-specific/`* — rejected as premature for two constants and
  one target site; revisit if a second site is added.

## R3 — Guard against a duplicate flowsheet coding

**Decision**: Keep the existing guard shape, now against the target environment's system:
add the coding only if `item.code` has no coding with `system == FLOWSHEET_SYSTEMS[env]`.

**Rationale**: Preserves the "exactly one flowsheet coding" rule and idempotency (spec edge
case: a source item that already carries the coding). Outputs are always rebuilt from the
source Questionnaire, never from a previous output, so codings under the old
`observation-flowsheet-id` system cannot be carried forward; no stripping logic is needed.

**Alternatives considered**: *Actively remove old-system codings* — rejected: no source
Questionnaire contains one (verified by grep), and deleting content the tool does not own
would breach Principle IV's "left byte-for-byte unchanged".

## R4 — Missing-record-ID warning

**Decision**: One warning per item, emitted from `report_gaps`:

```text
WARNING: loinc=AUDIT-0 has no Flowsheet Record ID; omitted from both outputs
```

**Rationale**: FR-007 / SC-005 — the gap exists once, not once per environment. The
message keeps the existing `loinc=<id> has no <column name>; omitted from …` shape so
anyone grepping logs finds it the same way, and the column name matches the CSV header.

**Alternatives considered**: *Keep two warnings for symmetry with the two outputs* —
rejected; it doubles a 213-line warning list for no information.

## R5 — Conflicting duplicate rows

**Decision**: Rows sharing a lowercased `LOINC code` conflict when their `record_id`
values differ (`len({r["record_id"] for r in rows}) > 1`). Behaviour otherwise unchanged:
warn, leave the item unmodified in both outputs.

**Rationale**: FR-008. Direct translation of the existing `(uat, prod)` tuple comparison.
`tests/test_mapping_csv.py::test_identifiers_unique_across_file` already keeps the real
file free of duplicates; the tool-level check covers ad-hoc CSVs passed with `--csv`.

## R6 — How tests reference the system values

**Decision**: Define the three URIs once, as literals, in `tests/conftest.py`
(`UAT_FLOWSHEET_SYSTEM`, `PROD_FLOWSHEET_SYSTEM`, `OLD_FLOWSHEET_SYSTEM`) and import them
in the test modules, replacing the `EPIC_FLOWSHEET_SYSTEM` constant now copy-pasted into
three files. Helpers that collect flowsheet codes take the system as an argument.

**Rationale**: Literals independent of the tool's own constants mean a typo in
`FLOWSHEET_SYSTEMS` fails a test instead of being mirrored by it. `test_fork_core.py`
already imports from `.conftest`, so the pattern exists.

**Alternatives considered**: *Assert against `tool.FLOWSHEET_SYSTEMS`* — rejected for the
reason above. *Keep one copy per test file* — rejected: two values in three files is the
kind of duplication that drifts.

## R7 — Proving "the outputs differ only in system" (FR-006)

**Decision**: A test reads both output files as text, replaces every occurrence of the
production system URI in the production file with the UAT URI, and asserts the result is
byte-identical to the UAT file. It also asserts the two files are *not* identical before
the substitution.

**Rationale**: Byte-level, so it also catches whitespace or ordering drift between the two
builds. Simpler and stricter than a structural JSON diff.

## R8 — Test changes, by file

**Decision**:

| File | Change |
|------|--------|
| `tests/conftest.py` | Add the three system literals (R6). |
| `tests/test_fork_core.py` | Happy path asserts code `3025` under the UAT system in the UAT file and the prod system in the prod file. `test_uat_file_has_no_prod_ids_and_vice_versa` → `test_each_file_carries_only_its_own_system`. New: outputs differ only in system (R7); no old system / no FHIR ID in outputs; exactly 9 PHQ-9 items coded. `test_fork_listed_but_unmapped_questionnaire` asserts exactly one `Flowsheet Record ID` warning for `AUDIT-0` and no flowsheet coding in either output. |
| `tests/test_fork_warnings.py` | `_write_csv` default header → `RECORD NAME (UCSD Epic),LOINC code,Flowsheet Record ID`. `test_missing_prod_id_not_fabricated` → `test_missing_record_id_not_fabricated` (blank record ID: neither output coded, exactly one warning). Conflict test rows carry differing record IDs. New: whitespace around a record ID is trimmed; extra CSV columns are ignored; a source item already carrying the env coding is not given a second. |
| `tests/test_fork_scores.py` | Check the score item for both new systems; otherwise unchanged. |
| `tests/test_fork_guards.py` | Missing-column test asserts `Flowsheet Record ID` is named. New: an old-layout CSV (`…,FHIR ID - UAT,FHIR ID - Prod`) is rejected the same way, with no output. |
| `tests/fixtures/csv-missing-column.csv` | Header `RECORD NAME (UCSD Epic),LOINC code` (record-ID column absent). |
| `tests/test_mapping_csv.py` | `HEADER` → four columns. `PHQ9_ROWS` → `(record name, identifier, record ID)` triples with the twelve site-supplied values. Blank-site-cell check → `[row[1], row[3]]`. Separator checks → four cells. `test_every_row_has_five_cells` → `…_four_cells`. Docstring points at this feature's contract. |

**Rationale**: FR-011, FR-012, SC-004 (every removed assertion has a record-ID
equivalent). 34 tests fail today: 8 in `test_fork_core.py`, 1 each in `test_fork_scores.py`
and `test_fork_warnings.py` (the tool rejects the CSV), and 24 in `test_mapping_csv.py`
(five-column assumptions).

**Note**: `tests/test_mapping_csv.py` is untracked in git (it was never committed with
feature 002). It is updated in place; committing it is the maintainer's call.

## R9 — Regenerating the checked-in PHQ-9 outputs

**Decision**: After the tool change, run it once with defaults on `CIRG-PHQ-9.json` to
overwrite `deploy-specific/ucsd-uat/CIRG-PHQ-9.json` and
`deploy-specific/ucsd-prod/CIRG-PHQ-9.json`. Expected diff per file: the `system` and
`code` lines of 9 codings (18 changed lines), nothing else.

**Rationale**: FR-010; `test_phq9_outputs_match_checked_in_files` then pins them. Verified
against the pre-change CSV that the tool maps 9 PHQ-9 items today: the ten response items
minus `69722-7`, which the CSV lists as `69723-5` (pre-existing mismatch, out of scope per
the spec's Assumptions). The mapped set is unchanged by this feature because every
previously mapped row has a record ID.

## R10 — Documentation touched

**Decision**: Update the tool's module docstring, the `inject_extract_metadata` /
`load_csv_index` / `build_environment_output` docstrings, and the argparse description and
`--csv` help. In `README.md`, drop the "tool itself still needs updating" sentence added
with constitution v4.0.0. `specs/001-*` and `specs/002-*` are left as historical records;
this feature's `contracts/` supersede `specs/001-add-extract-metadata/contracts/cli.md`
and `specs/002-populate-flowsheet-mapping-csv/contracts/mapping-csv.md`.

**Rationale**: FR-013 and the spec's Assumptions.

## R11 — Out-of-scope gaps confirmed still harmless

**Decision**: Leave (a) leading-`/` stripping for `CIRG-PC-PTSD-5` and (b) exclusion of
every computed score untouched.

**Rationale**: Spec Assumptions. Verified: only the 12 PHQ-9 rows have a record ID, so no
`CIRG-PC-PTSD-5` item and no non-PHQ-9 computed item could receive a coding today
regardless. Both remain flagged in the constitution's Sync Impact Report.
