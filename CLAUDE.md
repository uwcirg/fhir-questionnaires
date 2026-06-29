# fhir-questionnaires Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-06-29

## Active Technologies

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

- 001-add-extract-metadata: Added Python 3.11 (matches `python3` 3.11.2 on the box and the existing `utils/*.py`) + Python standard library only — `json`, `csv`, `argparse`, `pathlib`, `sys`. No third-party packages, consistent with `utils/remove_item_extensions.py` and `utils/remove_option_prefix.py`.

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
