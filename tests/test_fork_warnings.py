"""User Story 2 tests: surface mapping gaps without inventing data.

Covers cli.md cases 3 (bidirectional gaps), 7 (no fabrication), and the
conflicting-CSV-rows case (FR-009). Gaps warn but never change the exit code.
"""

import json

EPIC_FLOWSHEET_SYSTEM = (
    "http://open.epic.com/FHIR/StructureDefinition/observation-flowsheet-id"
)


def _flowsheet_codes(item):
    return [
        c.get("code")
        for c in item.get("code", [])
        if c.get("system") == EPIC_FLOWSHEET_SYSTEM
    ]


def _write_questionnaire(path, items):
    path.write_text(
        json.dumps(
            {"resourceType": "Questionnaire", "id": "test", "status": "draft", "item": items}
        )
    )
    return path


def _write_csv(path, rows, header="RECORD NAME,LOINC code,FHIR ID - UAT,FHIR ID - Prod"):
    path.write_text(header + "\n" + "\n".join(rows) + "\n")
    return path


# --- T016: bidirectional gaps (cli.md case 3; FR-008) -----------------------


def test_bidirectional_gap_warnings(tool, phq9_copy, repo_csv, out_dirs, capsys):
    uat_dir, prod_dir = out_dirs
    rc = tool.run(str(phq9_copy), str(repo_csv), str(uat_dir), str(prod_dir))
    err = capsys.readouterr().err
    assert rc == 0

    # Item-only LOINC 69722-7: exactly one "no CSV record" warning.
    item_only = [ln for ln in err.splitlines() if "69722-7" in ln and "no CSV record" in ln]
    assert len(item_only) == 1

    # CSV-only LOINCs 55758-7 and 69723-5: exactly one "matched no item" each.
    for loinc in ("55758-7", "69723-5"):
        csv_only = [
            ln for ln in err.splitlines() if loinc in ln and "matched no item" in ln
        ]
        assert len(csv_only) == 1, loinc

    # Mapped items are still written despite the gaps.
    uat = json.load(open(uat_dir / "CIRG-PHQ-9.json", encoding="utf-8"))
    assert _flowsheet_codes(uat["item"][0]) != []


# --- T017: no fabrication (cli.md case 7; FR-007) ---------------------------


def test_missing_prod_id_not_fabricated(tool, tmp_path, out_dirs, capsys):
    uat_dir, prod_dir = out_dirs
    q = _write_questionnaire(
        tmp_path / "q.json",
        [{"linkId": "/44250-9", "type": "choice", "code": [{"code": "44250-9"}]}],
    )
    # Prod ID intentionally blank.
    csv_path = _write_csv(tmp_path / "map.csv", ["PHQ9_INTEREST,44250-9,UAT-ID,"])

    rc = tool.run(str(q), str(csv_path), str(uat_dir), str(prod_dir))
    err = capsys.readouterr().err
    assert rc == 0

    uat = json.load(open(uat_dir / "q.json", encoding="utf-8"))
    prod = json.load(open(prod_dir / "q.json", encoding="utf-8"))

    # UAT carries its ID; prod omits the flowsheet metadata entirely (no invented value).
    assert _flowsheet_codes(uat["item"][0]) == ["UAT-ID"]
    assert _flowsheet_codes(prod["item"][0]) == []

    # A warning names the missing prod ID.
    assert any(
        "44250-9" in ln and "FHIR ID - Prod" in ln for ln in err.splitlines()
    )


# --- T018: conflicting CSV rows (FR-009) ------------------------------------


def test_conflicting_csv_rows_leave_item_unmodified(tool, tmp_path, out_dirs, capsys):
    uat_dir, prod_dir = out_dirs
    q = _write_questionnaire(
        tmp_path / "q.json",
        [{"linkId": "/44250-9", "type": "choice", "code": [{"code": "44250-9"}]}],
    )
    csv_path = _write_csv(
        tmp_path / "map.csv",
        [
            "PHQ9_INTEREST_A,44250-9,UAT-A,PROD-A",
            "PHQ9_INTEREST_B,44250-9,UAT-B,PROD-B",
        ],
    )

    rc = tool.run(str(q), str(csv_path), str(uat_dir), str(prod_dir))
    err = capsys.readouterr().err
    assert rc == 0

    uat = json.load(open(uat_dir / "q.json", encoding="utf-8"))
    prod = json.load(open(prod_dir / "q.json", encoding="utf-8"))

    # Conflicting LOINC → item left unmodified in both outputs.
    assert _flowsheet_codes(uat["item"][0]) == []
    assert _flowsheet_codes(prod["item"][0]) == []

    # A warning names the conflict.
    assert any(
        "44250-9" in ln and "conflicting" in ln.lower() for ln in err.splitlines()
    )
