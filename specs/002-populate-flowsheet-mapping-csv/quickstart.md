# Quickstart: verifying the mapping CSV

Run from the repository root.

## 1. Validate the file

```bash
python3 -m pytest
```

`tests/test_mapping_csv.py` re-reads the 19 Questionnaires and checks the header, the 20
separators and their order, that each section lists exactly its reportable items, labels,
blank UCSD cells, unique identifiers, and that the PHQ-9 rows are unchanged.

## 2. Confirm PHQ-9 outputs are unchanged

```bash
python3 utils/fork_questionnaire_for_extract.py CIRG-PHQ-9.json
git status --short deploy-specific/ucsd-uat deploy-specific/ucsd-prod   # expect no output
```

Expect many `matched no item` warnings on stderr — one for each row belonging to another
Questionnaire (research R7). The two output files must not change.

## 3. Eyeball it

Open the CSV in a spreadsheet: five columns, a separator row before each Questionnaire, and
for the 19 new sections only the first and third columns filled.

## Adding another Questionnaire later

1. Append a separator row with the `Questionnaire.id`.
2. Add one row per item, skipping display, group, and "internal" items: label, blank,
   `linkId`, blank, blank.
3. Add the Questionnaire's id and file to the list in `tests/test_mapping_csv.py`; run pytest.

## When UCSD returns values

Paste record names and FHIR IDs into the matching rows. Do not reorder rows or edit
`LOINC code`.
