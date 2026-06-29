"""User Story 1 guard tests (cli.md case 6; spec US1 scenario 3).

Each invalid input must exit non-zero, name the reason on stderr, and write no
output files.
"""

import json


def _assert_no_output(out_dirs):
    uat_dir, prod_dir = out_dirs
    assert not (uat_dir / "x.json").exists()
    # The directories should not even contain output for the bad input.
    for d in (uat_dir, prod_dir):
        if d.exists():
            assert list(d.glob("*.json")) == []


def test_deprecated_suffix_rejected(tool, repo_csv, out_dirs, tmp_path, capsys):
    uat_dir, prod_dir = out_dirs
    bad = tmp_path / "CIRG-CNICS-ASSIST.deprecated.json"
    bad.write_text(json.dumps({"resourceType": "Questionnaire", "status": "draft"}))
    rc = tool.run(str(bad), str(repo_csv), str(uat_dir), str(prod_dir))
    assert rc != 0
    assert "deprecated" in capsys.readouterr().err.lower()
    _assert_no_output(out_dirs)


def test_deprecated_directory_rejected(tool, repo_csv, out_dirs, tmp_path, capsys):
    uat_dir, prod_dir = out_dirs
    dep_dir = tmp_path / "deprecated"
    dep_dir.mkdir()
    bad = dep_dir / "PHQ-9.json"
    bad.write_text(json.dumps({"resourceType": "Questionnaire", "status": "draft"}))
    rc = tool.run(str(bad), str(repo_csv), str(uat_dir), str(prod_dir))
    assert rc != 0
    assert "deprecated" in capsys.readouterr().err.lower()
    _assert_no_output(out_dirs)


def test_retired_status_rejected(tool, repo_csv, out_dirs, fixtures_dir, capsys):
    uat_dir, prod_dir = out_dirs
    bad = fixtures_dir / "retired-questionnaire.json"
    rc = tool.run(str(bad), str(repo_csv), str(uat_dir), str(prod_dir))
    assert rc != 0
    assert "retired" in capsys.readouterr().err.lower()
    _assert_no_output(out_dirs)


def test_non_questionnaire_rejected(tool, repo_csv, out_dirs, fixtures_dir, capsys):
    uat_dir, prod_dir = out_dirs
    bad = fixtures_dir / "not-a-questionnaire.json"
    rc = tool.run(str(bad), str(repo_csv), str(uat_dir), str(prod_dir))
    assert rc != 0
    err = capsys.readouterr().err
    assert "Questionnaire" in err
    _assert_no_output(out_dirs)


def test_malformed_json_rejected(tool, repo_csv, out_dirs, tmp_path, capsys):
    uat_dir, prod_dir = out_dirs
    bad = tmp_path / "broken.json"
    bad.write_text("{ not valid json ")
    rc = tool.run(str(bad), str(repo_csv), str(uat_dir), str(prod_dir))
    assert rc != 0
    assert "json" in capsys.readouterr().err.lower()
    _assert_no_output(out_dirs)


def test_csv_missing_column_rejected(tool, phq9_copy, out_dirs, fixtures_dir, capsys):
    uat_dir, prod_dir = out_dirs
    bad_csv = fixtures_dir / "csv-missing-column.csv"
    rc = tool.run(str(phq9_copy), str(bad_csv), str(uat_dir), str(prod_dir))
    assert rc != 0
    err = capsys.readouterr().err
    assert "FHIR ID - Prod" in err  # the missing column is named
    _assert_no_output(out_dirs)
