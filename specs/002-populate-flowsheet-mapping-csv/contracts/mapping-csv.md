# Contract: Mapping CSV file format

Consumers: UCSD Epic analysts (spreadsheet), `utils/fork_questionnaire_for_extract.py`.

## Encoding

- UTF-8, no BOM. CRLF line endings; every line terminated.
- Comma-separated; a cell is double-quoted only if it contains a comma, quote, or newline.
  Labels are written without commas, so no quoting is expected.

## Header (line 1, exact)

```text
CNICS NAME,RECORD NAME (UCSD Epic),LOINC code,FHIR ID - UAT,FHIR ID - Prod
```

## Rows

```text
CIRG-PHQ9,,,,                                             <- separator
Little interest or pleasure,PHQ9_INTEREST,44250-9,teN3…,tFN1…   <- mapped item row
CIRG-CNICS-AUDIT,,,,                                      <- separator
Drinking frequency,,AUDIT-0,,                             <- listed item row
CIRG-PC-PTSD-5,,,,
Traumatic event ever,,/102011-4,,                         <- leading slash kept
```

(Labels above are illustrative.)

## Reader obligations

- Locate columns by header name, not position. Extra columns are ignored.
- A row with a blank `LOINC code` is a separator: never a mapping, never warned about.
- `LOINC code` is matched case-insensitively against the item identifier.
- A row with a blank FHIR ID is a known gap: warn, do not fail, do not invent a value.

## Writer obligations (CNICS)

- Never edit `RECORD NAME (UCSD Epic)`, `FHIR ID - UAT`, or `FHIR ID - Prod` except to paste
  values supplied by UCSD.
- Keep a Questionnaire's rows contiguous under its separator, in item order.
- Do not change a `LOINC code` value once shared with UCSD; relabelling `CNICS NAME` is safe.
