# Quickstart: forking a Questionnaire with flowsheet record IDs

Run from the repository root. Supersedes the output-checking steps in
`specs/001-add-extract-metadata/quickstart.md`.

## 1. Run the checks

```bash
python3 -m pytest
```

Expect zero failures (34 failed before this feature).

## 2. Fork PHQ-9

```bash
python3 utils/fork_questionnaire_for_extract.py CIRG-PHQ-9.json
```

Writes `deploy-specific/ucsd-uat/CIRG-PHQ-9.json` and
`deploy-specific/ucsd-prod/CIRG-PHQ-9.json`. Expect on stderr one `has no CSV record`
warning for `69722-7`, one score warning for `44261-6`, and a `matched no item` warning for
each row that belongs to another Questionnaire.

## 3. Verify the outputs

The two files differ only in the flowsheet `system` (9 lines):

```bash
diff deploy-specific/ucsd-uat/CIRG-PHQ-9.json deploy-specific/ucsd-prod/CIRG-PHQ-9.json
```

Every changed pair reads `…136.3.7.2.707679` (UAT) against `…136.2.7.2.707679` (prod).

The old scheme is gone (expect `0` for both files):

```bash
grep -c 'observation-flowsheet-id' deploy-specific/ucsd-uat/CIRG-PHQ-9.json \
    deploy-specific/ucsd-prod/CIRG-PHQ-9.json
```

Check the codes against the CSV's `Flowsheet Record ID` column — each of the 9 mapped
items shows its record ID directly beneath the system line:

```bash
grep -A1 'urn:oid:1.2.840.114350' deploy-specific/ucsd-uat/CIRG-PHQ-9.json
```

A second run changes nothing:

```bash
python3 utils/fork_questionnaire_for_extract.py CIRG-PHQ-9.json 2>/dev/null
git status --short deploy-specific/ucsd-uat deploy-specific/ucsd-prod
```

(After the regenerated files are committed, expect no output from `git status`.)

## 4. Fork a Questionnaire UCSD has not built yet

```bash
python3 utils/fork_questionnaire_for_extract.py CIRG-CNICS-AUDIT.json \
    --uat-dir /tmp/fork-check/uat --prod-dir /tmp/fork-check/prod
```

Exit code 0. One `has no Flowsheet Record ID; omitted from both outputs` warning per
listed AUDIT item, and neither output contains a flowsheet coding.

## When UCSD returns values

Paste the record name and the flowsheet record ID into the matching CSV rows — one ID per
item, good for both environments. Re-run step 2 for that Questionnaire and commit the two
generated files with the CSV.

## Not covered by this feature

- `CIRG-PC-PTSD-5` rows are not matched yet (the tool strips the leading `/`).
- Computed scores are excluded for every Questionnaire, not only `CIRG-PHQ9`.
- PHQ-9 "Functional difficulty" is `69722-7` in the Questionnaire but `69723-5` in the CSV,
  so it is not mapped.
