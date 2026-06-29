"""User Story 1 core tests (cli.md cases 1, 2, 5) plus edge cases (T026)."""

import json

EPIC_FLOWSHEET_SYSTEM = (
    "http://open.epic.com/FHIR/StructureDefinition/observation-flowsheet-id"
)
SDC_OBSERVATION_EXTRACT = (
    "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-observationExtract"
)

# PHQ-9 first item: LOINC 44250-9 (PHQ9_INTEREST) from the repo CSV.
UAT_INTEREST = "teN3kKw8NMBIF9ZU7Nd-9pQ0"
PROD_INTEREST = "tFN1y-XuXVcZBVua5Shx3hA0"


def _flowsheet_codes(item):
    return [
        c.get("code")
        for c in item.get("code", [])
        if c.get("system") == EPIC_FLOWSHEET_SYSTEM
    ]


def _iter_items(items):
    for item in items or []:
        yield item
        yield from _iter_items(item.get("item"))


def _run(tool, phq9_copy, repo_csv, out_dirs):
    uat_dir, prod_dir = out_dirs
    rc = tool.run(str(phq9_copy), str(repo_csv), str(uat_dir), str(prod_dir))
    uat = json.load(open(uat_dir / "CIRG-PHQ-9.json", encoding="utf-8"))
    prod = json.load(open(prod_dir / "CIRG-PHQ-9.json", encoding="utf-8"))
    return rc, uat, prod


# --- T009: happy-path contract (cli.md case 1) ------------------------------


def test_happy_path_two_files_env_correct(tool, phq9_copy, repo_csv, out_dirs):
    rc, uat, prod = _run(tool, phq9_copy, repo_csv, out_dirs)
    assert rc == 0

    uat_first = uat["item"][0]
    prod_first = prod["item"][0]
    assert uat_first["linkId"] == "/44250-9"

    # Each mapped item carries its env's flowsheet coding with the Epic system.
    assert _flowsheet_codes(uat_first) == [UAT_INTEREST]
    assert _flowsheet_codes(prod_first) == [PROD_INTEREST]

    # And the observationExtract extension is present on mapped items.
    assert any(
        e.get("url") == SDC_OBSERVATION_EXTRACT and e.get("valueBoolean") is True
        for e in uat_first.get("extension", [])
    )


def test_uat_file_has_no_prod_ids_and_vice_versa(tool, phq9_copy, repo_csv, out_dirs):
    _, uat, prod = _run(tool, phq9_copy, repo_csv, out_dirs)
    uat_text = json.dumps(uat)
    prod_text = json.dumps(prod)
    # Production ID for PHQ9_INTEREST must not appear in the UAT file, and vice versa.
    assert PROD_INTEREST not in uat_text
    assert UAT_INTEREST not in prod_text


# --- T010: one-flowsheet invariant (cli.md case 2) --------------------------


def test_no_item_has_more_than_one_flowsheet_coding(tool, phq9_copy, repo_csv, out_dirs):
    _, uat, prod = _run(tool, phq9_copy, repo_csv, out_dirs)
    for doc in (uat, prod):
        for item in _iter_items(doc["item"]):
            assert len(_flowsheet_codes(item)) <= 1


# --- T011: idempotency (cli.md case 5) --------------------------------------


def test_idempotent_byte_identical_rerun(tool, phq9_copy, repo_csv, out_dirs):
    uat_dir, prod_dir = out_dirs
    tool.run(str(phq9_copy), str(repo_csv), str(uat_dir), str(prod_dir))
    first_uat = (uat_dir / "CIRG-PHQ-9.json").read_bytes()
    first_prod = (prod_dir / "CIRG-PHQ-9.json").read_bytes()

    tool.run(str(phq9_copy), str(repo_csv), str(uat_dir), str(prod_dir))
    assert (uat_dir / "CIRG-PHQ-9.json").read_bytes() == first_uat
    assert (prod_dir / "CIRG-PHQ-9.json").read_bytes() == first_prod


# --- T026: edge cases — group/display untouched, no-LOINC item -------------


def test_display_and_score_items_get_no_flowsheet(tool, phq9_copy, repo_csv, out_dirs):
    _, uat, prod = _run(tool, phq9_copy, repo_csv, out_dirs)
    for doc in (uat, prod):
        for item in _iter_items(doc["item"]):
            if item.get("type") == "display":
                assert _flowsheet_codes(item) == []


def test_no_loinc_item_unchanged(tool):
    # An answerable item with neither code nor a LOINC-bearing linkId resolves to
    # no_loinc and is never annotated.
    item = {"linkId": "free-text", "type": "string"}
    assert tool.extract_loinc(item) == "free-text"  # linkId fallback (no leading slash)
    item2 = {"type": "string"}
    assert tool.extract_loinc(item2) is None
    outcome, _ = tool.resolve_item(item2, {}, {})
    assert outcome == "no_loinc"
