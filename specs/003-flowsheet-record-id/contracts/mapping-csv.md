# Contract: Mapping CSV file format (constitution v4.0.0)

Supersedes `specs/002-populate-flowsheet-mapping-csv/contracts/mapping-csv.md`.

Consumers: UCSD Epic analysts (spreadsheet), `utils/fork_questionnaire_for_extract.py`,
`tests/test_mapping_csv.py`.

## Encoding

- UTF-8, no BOM. CRLF line endings; every line terminated.
- Comma-separated; a cell is double-quoted only if it contains a comma, quote, or newline.
  Labels are written without commas, so no quoting is expected.

## Header (line 1, exact)

```text
CNICS NAME,RECORD NAME (UCSD Epic),LOINC code,Flowsheet Record ID
```

## Rows

Every row has exactly four cells.

```text
CIRG-PHQ9,,,                                         <- separator
Little interest or pleasure,PHQ9_INTEREST,44250-9,3025    <- mapped item row
CIRG-CNICS-AUDIT,,,                                  <- separator
Drinking frequency,,AUDIT-0,                         <- listed item row, not yet built
CIRG-PC-PTSD-5,,,
Traumatic event ever,,/102011-4,                     <- leading slash kept
```

(Labels other than the PHQ-9 one are illustrative.)

## Cell rules

- `Flowsheet Record ID` holds the Epic flowsheet record ID. One value serves both the UAT
  and production systems.
- The file MUST NOT contain flowsheet FHIR IDs or coding `system` values.
- `RECORD NAME (UCSD Epic)` and `Flowsheet Record ID` are blank until UCSD supplies them.

## Reader obligations

- Locate columns by header name, not position. Extra columns are ignored.
- `RECORD NAME (UCSD Epic)`, `LOINC code` and `Flowsheet Record ID` are required; if any is
  absent the reader stops with an error naming it.
- A row with a blank `LOINC code` is a separator: never a mapping, never warned about.
- `LOINC code` is matched case-insensitively against the item identifier.
- A row with a blank `Flowsheet Record ID` is a known gap: warn once, do not fail, do not
  invent a value.

## Writer obligations (CNICS)

- Never edit `RECORD NAME (UCSD Epic)` or `Flowsheet Record ID` except to paste values
  supplied by UCSD.
- Keep a Questionnaire's rows contiguous under its separator, in item order.
- Do not change a `LOINC code` value once shared with UCSD; relabelling `CNICS NAME` is safe.

## Pinned content

The twelve site-supplied PHQ-9 rows (record name, identifier, record ID) are pinned by
`tests/test_mapping_csv.py`:

| Record name | Identifier | Record ID |
|-------------|------------|-----------|
| `PHQ9_INTEREST` | `44250-9` | `3025` |
| `PHQ9_DEPRESSED` | `44255-8` | `3026` |
| `UC R FM PHQ2 TOTAL` | `55758-7` | `6733` |
| `PHQ9_SLEEP` | `44259-0` | `3027` |
| `PHQ9_ENERGY` | `44254-1` | `3028` |
| `PHQ9_APPETITE` | `44251-7` | `3029` |
| `PHQ9_FAILURE` | `44258-2` | `3030` |
| `PHQ9_CONCENTRATION` | `44252-5` | `3031` |
| `PHQ9_MOVEMENT` | `44253-3` | `3032` |
| `PHQ9_SUICIDE` | `44260-8` | `3033` |
| `PHQ9_FUNCTIONAL` | `69723-5` | `3036` |
| `PHQ9_SUMMARY_SCORE_FMLA` | `44261-6` | `3035` |
