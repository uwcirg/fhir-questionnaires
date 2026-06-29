# Quickstart: Fork a Questionnaire for `$extract`

## Prerequisites
- Python 3.11+ (stdlib only; no `pip install` needed to run the tool).
- Run from the repository root.
- `pytest` only if you want to run the test suite.

## Fork one Questionnaire into UAT + prod outputs

```bash
python3 utils/fork_questionnaire_for_extract.py CIRG-PHQ-9.json
```

This reads `CIRG-PHQ-9.json` and the default CSV
(`deploy-specific/mapping-input/CNICS PRO UCSD flowsheet FHIR IDs.csv`) and writes:

- `deploy-specific/ucsd-uat/CIRG-PHQ-9.json`  (UAT flowsheet IDs only)
- `deploy-specific/ucsd-prod/CIRG-PHQ-9.json` (production flowsheet IDs only)

Mapping gaps print to stderr as `WARNING:` lines but do not stop the run. Example expected
warnings for PHQ-9: item `69722-7` has no CSV record; CSV records `55758-7` and `69723-5` match
no item; score item `44261-6` is excluded.

## Override paths

```bash
python3 utils/fork_questionnaire_for_extract.py CIRG-PEG.json \
    --csv "deploy-specific/mapping-input/CNICS PRO UCSD flowsheet FHIR IDs.csv" \
    --uat-dir deploy-specific/ucsd-uat \
    --prod-dir deploy-specific/ucsd-prod
```

## Bulk (loop over single runs)

```bash
for q in CIRG-PHQ-9.json CIRG-PHQ-4.json CIRG-PEG.json; do
  python3 utils/fork_questionnaire_for_extract.py "$q" || echo "FAILED: $q"
done
```

## Verify the result

```bash
# Two files were produced
ls deploy-specific/ucsd-uat/CIRG-PHQ-9.json deploy-specific/ucsd-prod/CIRG-PHQ-9.json

# UAT file carries no production IDs (and vice versa) — should print nothing
grep -F "$(awk -F, 'NR==2{print $4}' 'deploy-specific/mapping-input/CNICS PRO UCSD flowsheet FHIR IDs.csv')" \
    deploy-specific/ucsd-uat/CIRG-PHQ-9.json

# Idempotency: re-run and confirm no diff
python3 utils/fork_questionnaire_for_extract.py CIRG-PHQ-9.json
git diff --stat deploy-specific/ucsd-uat deploy-specific/ucsd-prod   # expect no changes on second run
```

## Run tests

```bash
pytest tests/test_fork_questionnaire_for_extract.py -v
```
