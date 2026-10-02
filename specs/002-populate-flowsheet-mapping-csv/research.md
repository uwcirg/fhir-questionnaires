# Research: Populate Flowsheet Mapping CSV

All findings below were taken from the repository on 2026-10-02.

## R1. How the rows get produced

- **Decision**: Author the rows once during implementation and commit only the CSV plus a
  validation test. Identifiers, order, and exclusions are derived mechanically from the
  Questionnaires with a throwaway script; the `CNICS NAME` labels are written by hand.
- **Rationale**: After this feature the CSV is edited by UCSD (record names, FHIR IDs) and
  labels may be reworded. A committed generator would either overwrite those edits or need
  merge logic that is larger than the problem. The durable need is *checking* the file, and
  a test does that on every run.
- **Alternatives considered**: (a) Committed generator script with a labels lookup file —
  rejected: second source of truth for labels, and risk of clobbering UCSD's cells. (b) Pure
  hand-editing with no test — rejected: 213 rows across 19 files is too many to verify by eye.

## R2. Which items get a row

- **Decision**: An item gets a row unless `type` is `display` or `group`, or its `text`
  contains the word "internal" (case-insensitive).
- **Findings**: All 19 Questionnaires are `status: active`, and none has nested items or
  group items, so every item is top-level. Totals: 213 rows; 14 items excluded as internal;
  display items excluded in 11 Questionnaires.
- **Internal items found (no row)**: `AUDIT-Q0-score`, `AUDIT-Q1-Q2-score`,
  `AUDIT-C-complete`, `AUDIT-last-7-any-answers`, `AUDIT-last-7-complete`,
  `HIV-STIGMA-SCORE-NUM-ANSWERED`, `MINI-complete`, `MINI-num-answered`,
  `MINI-score-ignoring-skipped`, `SEXUAL-RISK-SCORE-ONE-PARTNER`,
  `SEXUAL-RISK-SCORE-MULTIPLE-PARTNERS`, `SEXUAL-RISK-SCORE-UNPROTECTED-ANAL`,
  `SEXUAL-RISK-SCORE-UNPROTECTED-ORAL`, `SEXUAL-RISK-SCORE-UNPROTECTED-VAGINAL`.
- **Rationale**: Every one of the 14 uses the word "internal" ("internal item", "internal
  scoring"), so a plain substring test reproduces the spec's rule with no false hits.
- **Computed items that do get a row (38)**: they do not describe themselves as internal.
  Two look like helper values rather than results and are worth a glance during review:
  `AUDIT-complete` ("AUDIT questionnaire complete") and `AUDIT-qnr-to-report` ("Which CNICS
  AUDIT score to display"). They are included because the rule is the item's own text.
- **Sliders included** (itemControl does not exclude): `ARV-9`, `EUROQOL-5`,
  `SEXUAL-RISK-15`, `SEXUAL-RISK-37`.

Rows per Questionnaire: ARV 13, ASSIST 22, ASSIST-OD 3, ASSIST-Polysub 5, AUDIT 17,
EUROQOL 11, EXCHANGE-SEX 5, FINANCIAL 3, FOOD 5, FROP-Com 4, HIV-STIGMA 6, HOUSING 2,
IPV4 7, MAPSS-SF 5, MINI 15, SEXUAL-RISK 48, Smoking 12, Symptoms 22, PC-PTSD-5 8.

## R3. Identifier format

- **Decision**: `LOINC code` = `linkId` exactly as authored.
- **Rationale**: Among the 19, only `CIRG-PC-PTSD-5` has slash-prefixed linkIds
  (`/102011-4` … `/102017-1`), and the constitution keeps those slashes. So "strip one
  leading slash, except PC-PTSD-5" and "copy as authored" give the same result for this
  feature. No linkId is repeated across the 19 Questionnaires or collides with a PHQ-9 row.

## R4. Labels (`CNICS NAME`)

- **Decision**: Hand-written, at most 60 characters, no commas, unique within a section,
  prefixed with nothing (the separator row already names the instrument).
- **Rationale**: Item text is often a full sentence; several items share text (`ARV-0` and
  `ARV-1` are both "Are you currently taking any HIV medications?"; `AUDIT-2-male` vs
  `AUDIT-2-not-male`), so labels need a distinguishing word. Avoiding commas keeps the file
  free of quoted cells, which is easier on spreadsheet round-trips.
- **Special cases**: every one of the 213 items has text. Among existing PHQ-9 rows,
  `55758-7` (PHQ-2 total) and `69723-5` have no item in `CIRG-PHQ-9.json`; they are labelled
  from their Epic record names.

## R5. File format

- **Decision**: UTF-8 without BOM, CRLF line endings (as today), every line terminated,
  minimal quoting, exactly five cells per row. Separator rows are `<Questionnaire.id>,,,,`.
- **Findings**: The current file uses CRLF and has no terminator after its last line.
  Appending requires adding one; terminating every line is the conventional form.
- **Section order**: `CIRG-PHQ9` first, then the order given in spec FR-003.
- **PHQ-9 row order**: existing order kept as is (values and sequence untouched), which
  takes precedence over "item order" for these pre-existing, site-mapped rows.

## R6. Fork-tool compatibility

- **Decision**: Change only the record-name column constant and lookup in
  `utils/fork_questionnaire_for_extract.py`, the header string in
  `tests/test_fork_warnings.py`, and `tests/fixtures/csv-missing-column.csv`.
- **Findings**: The tool reads the CSV with a header-keyed reader, so the new leading column
  needs no change. It already skips rows whose `LOINC code` is blank, so separator rows are
  ignored. It already falls back to `linkId` when an item has no `code`, so the new rows
  match their items. Baseline check: regenerating PHQ-9 today reproduces both checked-in
  outputs byte-for-byte, and all 17 tests pass.
- **Alternatives considered**: accepting both old and new header names — rejected: the
  constitution names one schema, and there is one CSV.

## R7. Known consequences left for the follow-up tool feature

1. **Warning volume.** The tool warns once per CSV record that matches no item in the
   Questionnaire being forked (constitution Principle III requires this). With a
   20-Questionnaire file, a PHQ-9 run will print about 213 additional "matched no item"
   warnings. Output files are unaffected. The fix — compare only against the section whose
   separator equals the Questionnaire's id — changes tool behaviour and the wording of
   Principle III, so it belongs in the follow-up.
2. **PC-PTSD-5 matching.** The tool strips the leading `/` and prefers `item.code`, so it
   will not match the slash-prefixed rows.
3. **Computed totals.** The tool skips every item with a `calculatedExpression`.
4. **Pre-existing PHQ-9 mismatch (not caused by this feature).** The Questionnaire item is
   `69722-7`; the CSV row `PHQ9_FUNCTIONAL` is `69723-5`. They never match, so that item is
   not extracted today. Left unchanged here because existing rows must be retained as is;
   needs a decision from the team.
