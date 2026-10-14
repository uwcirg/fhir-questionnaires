# fhir-questionnaires Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-10-13

## Active Technologies
- Python 3.11 (matches `python3` 3.11.2 on the box and the existing `utils/*.py`) + Python standard library only — `csv`, `json`, `pathlib`. No third-party packages. (002-populate-flowsheet-mapping-csv)
- Filesystem. One CSV under `deploy-specific/mapping-input/`; 19 Questionnaire JSON files at the repo root are read-only inputs. (002-populate-flowsheet-mapping-csv)
- Python 3.11 (matches `python3` 3.11.2 on the box and the existing `utils/*.py`) + Python standard library only — `argparse`, `copy`, `csv`, `json`, `pathlib`, `sys` (all already imported by the tool). No third-party packages. (003-flowsheet-record-id)
- Filesystem. Input: one CSV under `deploy-specific/mapping-input/` and one source Questionnaire JSON per run. Output: one JSON file each under `deploy-specific/ucsd-uat/` and `deploy-specific/ucsd-prod/`. (003-flowsheet-record-id)

- Python 3.11 (matches `python3` 3.11.2 on the box and the existing `utils/*.py`) + Python standard library only — `json`, `csv`, `argparse`, `pathlib`, `sys`. No third-party packages, consistent with `utils/remove_item_extensions.py` and `utils/remove_option_prefix.py`. (001-add-extract-metadata)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11 (matches `python3` 3.11.2 on the box and the existing `utils/*.py`): Follow standard conventions

## Recent Changes
- 003-flowsheet-record-id: Added Python 3.11 (matches `python3` 3.11.2 on the box and the existing `utils/*.py`) + Python standard library only — `argparse`, `copy`, `csv`, `json`, `pathlib`, `sys` (all already imported by the tool). No third-party packages.
- 002-populate-flowsheet-mapping-csv: Added Python 3.11 (matches `python3` 3.11.2 on the box and the existing `utils/*.py`) + Python standard library only — `csv`, `json`, `pathlib`. No third-party packages.

- 001-add-extract-metadata: Added Python 3.11 (matches `python3` 3.11.2 on the box and the existing `utils/*.py`) + Python standard library only — `json`, `csv`, `argparse`, `pathlib`, `sys`. No third-party packages, consistent with `utils/remove_item_extensions.py` and `utils/remove_option_prefix.py`.

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
