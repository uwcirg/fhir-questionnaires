"""User Story 3 test: exclude computed score items (cli.md case 4; FR-007, SC-007).

The PHQ-9 total-score item /44261-6 carries a calculatedExpression extension. It
must receive no extract metadata in either output and stay byte-identical to the
source item; a warning notes its matched CSV record was skipped as a score.
"""

import json

EPIC_FLOWSHEET_SYSTEM = (
    "http://open.epic.com/FHIR/StructureDefinition/observation-flowsheet-id"
)


def _find(items, link_id):
    for item in items or []:
        if item.get("linkId") == link_id:
            return item
        found = _find(item.get("item"), link_id)
        if found is not None:
            return found
    return None


def test_score_item_excluded_and_unchanged(tool, phq9_copy, repo_csv, out_dirs, capsys):
    uat_dir, prod_dir = out_dirs
    rc = tool.run(str(phq9_copy), str(repo_csv), str(uat_dir), str(prod_dir))
    err = capsys.readouterr().err
    assert rc == 0

    source = json.load(open(phq9_copy, encoding="utf-8"))
    uat = json.load(open(uat_dir / "CIRG-PHQ-9.json", encoding="utf-8"))
    prod = json.load(open(prod_dir / "CIRG-PHQ-9.json", encoding="utf-8"))

    src_score = _find(source["item"], "/44261-6")
    assert src_score is not None

    for doc in (uat, prod):
        out_score = _find(doc["item"], "/44261-6")
        # No flowsheet coding was added...
        assert not any(
            c.get("system") == EPIC_FLOWSHEET_SYSTEM for c in out_score.get("code", [])
        )
        # ...and the item is byte-identical to the source item.
        assert out_score == src_score

    # A warning notes the score exclusion (LOINC 44261-6 matched a CSV record).
    assert any(
        "44261-6" in ln and "score" in ln.lower() for ln in err.splitlines()
    )
