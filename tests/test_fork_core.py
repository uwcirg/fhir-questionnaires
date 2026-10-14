"""User Story 1 core tests (cli.md cases 1, 2, 5) plus edge cases (T026)."""

import csv
import json
import shutil

from .conftest import (
    OLD_FLOWSHEET_SYSTEM,
    PROD_FLOWSHEET_SYSTEM,
    REPO_ROOT,
    UAT_FLOWSHEET_SYSTEM,
)

SDC_OBSERVATION_EXTRACT = (
    "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-observationExtract"
)
SDC_OBSERVATION_EXTRACT_CATEGORY = (
    "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-observationExtractCategory"
)

# The PHQ-9 items the tool codes, linkId -> Flowsheet Record ID from the repo CSV.
# Not coded: 69722-7 (no CSV row) and 44261-6 (computed score).
PHQ9_RECORD_IDS = {
    "44250-9": "3025",
    "44255-8": "3026",
    "44259-0": "3027",
    "44254-1": "3028",
    "44251-7": "3029",
    "44258-2": "3030",
    "44252-5": "3031",
    "44253-3": "3032",
    "44260-8": "3033",
}


def _flowsheet_codes(item, system):
    return [
        c.get("code") for c in item.get("code", []) if c.get("system") == system
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
    assert uat_first["linkId"] == "44250-9"

    # Each mapped item carries the same record ID under its env's flowsheet system.
    assert _flowsheet_codes(uat_first, UAT_FLOWSHEET_SYSTEM) == ["3025"]
    assert _flowsheet_codes(prod_first, PROD_FLOWSHEET_SYSTEM) == ["3025"]

    # And the observationExtract extension is present on mapped items.
    assert any(
        e.get("url") == SDC_OBSERVATION_EXTRACT and e.get("valueBoolean") is True
        for e in uat_first.get("extension", [])
    )


def test_each_file_carries_only_its_own_system(tool, phq9_copy, repo_csv, out_dirs):
    _, uat, prod = _run(tool, phq9_copy, repo_csv, out_dirs)
    # The production system must not appear in the UAT file, and vice versa.
    assert PROD_FLOWSHEET_SYSTEM not in json.dumps(uat)
    assert UAT_FLOWSHEET_SYSTEM not in json.dumps(prod)


def test_outputs_differ_only_in_system(tool, phq9_copy, repo_csv, out_dirs):
    uat_dir, prod_dir = out_dirs
    _run(tool, phq9_copy, repo_csv, out_dirs)
    uat_text = (uat_dir / "CIRG-PHQ-9.json").read_text(encoding="utf-8")
    prod_text = (prod_dir / "CIRG-PHQ-9.json").read_text(encoding="utf-8")
    assert uat_text != prod_text
    assert prod_text.replace(PROD_FLOWSHEET_SYSTEM, UAT_FLOWSHEET_SYSTEM) == uat_text


def test_old_scheme_absent(tool, phq9_copy, repo_csv, out_dirs):
    _, uat, prod = _run(tool, phq9_copy, repo_csv, out_dirs)
    for doc in (uat, prod):
        assert OLD_FLOWSHEET_SYSTEM not in json.dumps(doc)


def test_phq9_mapped_items_carry_their_record_ids(tool, phq9_copy, repo_csv, out_dirs):
    _, uat, prod = _run(tool, phq9_copy, repo_csv, out_dirs)
    for doc, system in ((uat, UAT_FLOWSHEET_SYSTEM), (prod, PROD_FLOWSHEET_SYSTEM)):
        coded = {}
        for item in _iter_items(doc["item"]):
            codes = _flowsheet_codes(item, system)
            if codes:
                assert len(codes) == 1, item["linkId"]
                coded[item["linkId"]] = codes[0]
        assert coded == PHQ9_RECORD_IDS


def test_root_observation_extract_category_present(tool, phq9_copy, repo_csv, out_dirs):
    # HAPI's $extract needs the root observationExtractCategory to set
    # Observation.category; both env outputs must declare it exactly once (vital-signs).
    _, uat, prod = _run(tool, phq9_copy, repo_csv, out_dirs)
    for doc in (uat, prod):
        cats = [
            e
            for e in doc.get("extension", [])
            if e.get("url") == SDC_OBSERVATION_EXTRACT_CATEGORY
        ]
        assert len(cats) == 1
        coding = cats[0]["valueCodeableConcept"]["coding"][0]
        assert coding["system"] == "http://hl7.org/fhir/observation-category"
        assert coding["code"] == "vital-signs"


# --- T010: one-flowsheet invariant (cli.md case 2) --------------------------


def test_no_item_has_more_than_one_flowsheet_coding(tool, phq9_copy, repo_csv, out_dirs):
    _, uat, prod = _run(tool, phq9_copy, repo_csv, out_dirs)
    for doc, system in ((uat, UAT_FLOWSHEET_SYSTEM), (prod, PROD_FLOWSHEET_SYSTEM)):
        for item in _iter_items(doc["item"]):
            assert len(_flowsheet_codes(item, system)) <= 1


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
    for doc, system in ((uat, UAT_FLOWSHEET_SYSTEM), (prod, PROD_FLOWSHEET_SYSTEM)):
        for item in _iter_items(doc["item"]):
            if item.get("type") == "display":
                assert _flowsheet_codes(item, system) == []


def test_no_loinc_item_unchanged(tool):
    # An answerable item with neither code nor a LOINC-bearing linkId resolves to
    # no_loinc and is never annotated.
    item = {"linkId": "free-text", "type": "string"}
    assert tool.extract_loinc(item) == "free-text"  # linkId fallback (no leading slash)
    item2 = {"type": "string"}
    assert tool.extract_loinc(item2) is None
    outcome, _ = tool.resolve_item(item2, {}, {})
    assert outcome == "no_loinc"


# --- repo CSV with one section per Questionnaire (feature 002) --------------


def test_phq9_outputs_match_checked_in_files(tool, phq9_copy, repo_csv, out_dirs):
    uat_dir, prod_dir = out_dirs
    rc = tool.run(str(phq9_copy), str(repo_csv), str(uat_dir), str(prod_dir))
    assert rc == 0
    deployed = REPO_ROOT / "deploy-specific"
    assert (uat_dir / "CIRG-PHQ-9.json").read_bytes() == (
        deployed / "ucsd-uat" / "CIRG-PHQ-9.json"
    ).read_bytes()
    assert (prod_dir / "CIRG-PHQ-9.json").read_bytes() == (
        deployed / "ucsd-prod" / "CIRG-PHQ-9.json"
    ).read_bytes()


def test_fork_listed_but_unmapped_questionnaire(tool, tmp_path, repo_csv, out_dirs, capsys):
    uat_dir, prod_dir = out_dirs
    source = tmp_path / "CIRG-CNICS-AUDIT.json"
    shutil.copy(REPO_ROOT / "CIRG-CNICS-AUDIT.json", source)

    rc = tool.run(str(source), str(repo_csv), str(uat_dir), str(prod_dir))
    err_lines = capsys.readouterr().err.splitlines()
    assert rc == 0
    assert (uat_dir / "CIRG-CNICS-AUDIT.json").exists()
    assert (prod_dir / "CIRG-CNICS-AUDIT.json").exists()

    # A listed row with blank FHIR IDs is a known gap, reported per environment.
    for column in ("FHIR ID - UAT", "FHIR ID - Prod"):
        assert any("loinc=AUDIT-0 " in ln and column in ln for ln in err_lines), column

    # Separator rows are never treated as records.
    with open(repo_csv, encoding="utf-8", newline="") as f:
        separators = [row[0] for row in list(csv.reader(f))[1:] if not row[2].strip()]
    assert separators
    for separator in separators:
        assert not any(
            'CSV record "%s"' % separator in ln or ln.endswith("loinc=%s" % separator)
            for ln in err_lines
        ), separator
