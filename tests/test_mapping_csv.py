"""Validate the flowsheet mapping CSV against the source Questionnaires.

The CSV is authored by hand (labels) and later edited by UCSD (record names,
FHIR IDs), so there is no generator to re-run. These tests are the durable
check: they re-derive each section's expected rows from its Questionnaire and
enforce the file format in ``specs/002-populate-flowsheet-mapping-csv/contracts``.
"""

import csv
import json

import pytest

from .conftest import REPO_CSV, REPO_ROOT

HEADER = [
    "CNICS NAME",
    "RECORD NAME (UCSD Epic)",
    "LOINC code",
    "FHIR ID - UAT",
    "FHIR ID - Prod",
]

PHQ9_ID = "CIRG-PHQ9"

# (Questionnaire.id, file name), in CSV section order after CIRG-PHQ9.
NEW_QUESTIONNAIRES = [
    ("CIRG-CNICS-ARV", "CIRG-CNICS-ARV.json"),
    ("CIRG-CNICS-ASSIST", "CIRG-CNICS-ASSIST.json"),
    ("CIRG-CNICS-ASSIST-OD", "CIRG-CNICS-ASSIST-OD.json"),
    ("CIRG-CNICS-ASSIST-Polysub", "CIRG-CNICS-ASSIST-Polysub.json"),
    ("CIRG-CNICS-AUDIT", "CIRG-CNICS-AUDIT.json"),
    ("CIRG-CNICS-EUROQOL", "CIRG-CNICS-EUROQOL.json"),
    ("CIRG-CNICS-EXCHANGE-SEX", "CIRG-CNICS-EXCHANGE-SEX.json"),
    ("CIRG-CNICS-FINANCIAL", "CIRG-CNICS-FINANCIAL.json"),
    ("CIRG-CNICS-FOOD", "CIRG-CNICS-FOOD.json"),
    ("CIRG-CNICS-FROP-Com", "CIRG-CNICS-FROP-Com.json"),
    ("CIRG-CNICS-HIV-STIGMA", "CIRG-CNICS-HIV-STIGMA.json"),
    ("CIRG-CNICS-HOUSING", "CIRG-CNICS-HOUSING.json"),
    ("CIRG-CNICS-IPV4", "CIRG-CNICS-IPV4.json"),
    ("CIRG-CNICS-MAPSS-SF", "CIRG-CNICS-MAPSS-SF.json"),
    ("CIRG-CNICS-MINI", "CIRG-CNICS-MINI.json"),
    ("CIRG-CNICS-SEXUAL-RISK", "CIRG-CNICS-SEXUAL-RISK.json"),
    ("CIRG-CNICS-Smoking", "CIRG-CNICS-Smoking.json"),
    ("CIRG-CNICS-Symptoms", "CIRG-CNICS-Symptoms.json"),
    ("CIRG-PC-PTSD-5", "CIRG-PC-PTSD-5.json"),
]
NEW_IDS = [qid for qid, _ in NEW_QUESTIONNAIRES]

# The 12 PHQ-9 rows as they stood before this file gained sections:
# (record name, LOINC code, FHIR ID - UAT, FHIR ID - Prod). Site-supplied; must not change.
PHQ9_ROWS = [
    ("PHQ9_INTEREST", "44250-9", "teN3kKw8NMBIF9ZU7Nd-9pQ0", "tFN1y-XuXVcZBVua5Shx3hA0"),
    ("PHQ9_DEPRESSED", "44255-8", "tnU0icMggWEcRhksuu4hJ3A0", "tgAEmGWuKOH90pDSRw12lMw0"),
    ("UC R FM PHQ2 TOTAL", "55758-7", "tcspRW.3lXOnl6nYHXrx3Rg0", "tOtfy1njyE8TLwJknfz1D6Q0"),
    ("PHQ9_SLEEP", "44259-0", "tKyPjZXsY.fwUg8kQpgnrGg0", "typS9O2qDI0m.HMK.UCuU9Q0"),
    ("PHQ9_ENERGY", "44254-1", "t9ed6G2pi.iZGhA9T0KKSXQ0", "tQlxHdYutrpw.q9oN8UTWIw0"),
    ("PHQ9_APPETITE", "44251-7", "tUvwUAzzAo2GM-83FWMNMBA0", "tatJ03AeDkOmJkhqVq5nPuA0"),
    ("PHQ9_FAILURE", "44258-2", "t0-c.j3CMZhmoM0Qd8ZtPmA0", "tjuTfQDPPGDzFJOBye4CUQA0"),
    ("PHQ9_CONCENTRATION", "44252-5", "tbX6Ca3KWexbQqjSTR.gb5w0", "th5JnOCvgEo6wFNMYttQ1hA0"),
    ("PHQ9_MOVEMENT", "44253-3", "tags.2ubhSPRHJcPwj9A-9A0", "tUanlOhZVjhrnccxjKKNlPQ0"),
    ("PHQ9_SUICIDE", "44260-8", "tcfuT6l6w588Qqjcx6cXqxw0", "tlj.UZxepQkWIO1YvyNgSgQ0"),
    ("PHQ9_FUNCTIONAL", "69723-5", "tdYjwfyJvuW4IRAhjwoPFeA0", "tSIy3PqqDUIyqyAVOqq9oVA0"),
    (
        "PHQ9_SUMMARY_SCORE_FMLA",
        "44261-6",
        "tAcMJ6d9AZFqpzWcp-YjG6Q0",
        "tWcTJEKrsz8gtUzQPsnGOmA0",
    ),
]

MAX_LABEL_LENGTH = 60


def _iter_items(items):
    for item in items or []:
        yield item
        yield from _iter_items(item.get("item"))


def reportable_link_ids(path):
    """linkIds of the items that get a CSV row, in Questionnaire order.

    An item is reportable unless it is a display or group item, or its text
    says it is "internal". itemControl and calculatedExpression do not matter.
    """
    with open(path, encoding="utf-8") as f:
        questionnaire = json.load(f)
    return [
        item["linkId"]
        for item in _iter_items(questionnaire.get("item"))
        if item.get("type") not in ("display", "group")
        and "internal" not in (item.get("text") or "").lower()
    ]


def read_rows():
    """Every CSV row as a list of cells, header first."""
    with open(REPO_CSV, encoding="utf-8", newline="") as f:
        return list(csv.reader(f))


def load_sections():
    """Return ``(header, sections, separator_ids, orphans)``.

    ``sections`` maps separator id -> its item rows in file order;
    ``separator_ids`` lists every separator as encountered (duplicates kept);
    ``orphans`` holds item rows that precede the first separator. A row whose
    third cell is blank is a separator.
    """
    rows = read_rows()
    header, body = rows[0], rows[1:]
    sections = {}
    separator_ids = []
    orphans = []
    current = None
    for row in body:
        if len(row) < 3 or not row[2].strip():
            current = row[0] if row else ""
            separator_ids.append(current)
            sections.setdefault(current, [])
        elif current is None:
            orphans.append(row)
        else:
            sections[current].append(row)
    return header, sections, separator_ids, orphans


def _assert_labels_ok(rows):
    labels = [row[0] for row in rows]
    for label in labels:
        assert label.strip(), "blank CNICS NAME"
        assert label == label.strip(), label
        assert len(label) <= MAX_LABEL_LENGTH, label
        assert "," not in label, label
    assert len(set(labels)) == len(labels), "CNICS NAME repeated within a section"


# --- US1: every reportable item of the 19 Questionnaires is listed ----------


@pytest.mark.parametrize("qid,filename", NEW_QUESTIONNAIRES, ids=NEW_IDS)
def test_section_lists_reportable_items_in_order(qid, filename):
    path = REPO_ROOT / filename
    with open(path, encoding="utf-8") as f:
        assert json.load(f)["id"] == qid

    _, sections, _, _ = load_sections()
    assert qid in sections, "no separator row for %s" % qid
    assert [row[2] for row in sections[qid]] == reportable_link_ids(path)


@pytest.mark.parametrize("qid", NEW_IDS)
def test_new_section_rows_have_labels_and_blank_site_cells(qid):
    _, sections, _, _ = load_sections()
    rows = sections.get(qid, [])
    assert rows, "no rows for %s" % qid
    for row in rows:
        assert [row[1], row[3], row[4]] == ["", "", ""], row
    _assert_labels_ok(rows)


def test_sliders_and_totals_listed_display_and_internal_omitted():
    _, sections, _, _ = load_sections()
    listed = {row[2] for rows in sections.values() for row in rows}
    for link_id in ("ARV-9", "EUROQOL-5", "SEXUAL-RISK-15", "SEXUAL-RISK-37", "AUDIT-score"):
        assert link_id in listed, link_id
    for link_id in ("AUDIT-header", "AUDIT-Q0-score"):
        assert link_id not in listed, link_id


def test_new_sections_total_213_item_rows():
    _, sections, _, _ = load_sections()
    assert sum(len(sections.get(qid, [])) for qid in NEW_IDS) == 213


# --- US2: navigable by Questionnaire ----------------------------------------


def test_header_is_exact():
    header, _, _, _ = load_sections()
    assert header == HEADER


def test_separators_are_the_20_ids_in_order():
    _, _, separator_ids, _ = load_sections()
    assert separator_ids == [PHQ9_ID] + NEW_IDS


def test_first_data_row_is_phq9_separator():
    _, _, _, orphans = load_sections()
    assert orphans == []
    assert read_rows()[1] == [PHQ9_ID, "", "", "", ""]


def test_separator_rows_have_only_the_id():
    for row in read_rows()[1:]:
        if not row[2].strip():
            assert row[0].strip()
            assert row[1:] == ["", "", "", ""], row


def test_phq9_separator_matches_questionnaire_id():
    with open(REPO_ROOT / "CIRG-PHQ-9.json", encoding="utf-8") as f:
        assert json.load(f)["id"] == PHQ9_ID


# --- US3: PHQ-9 rows untouched, file structurally sound ---------------------


def test_phq9_rows_unchanged():
    _, sections, _, _ = load_sections()
    assert [tuple(row[1:5]) for row in sections.get(PHQ9_ID, [])] == PHQ9_ROWS


def test_phq9_rows_have_labels():
    _, sections, _, _ = load_sections()
    rows = sections.get(PHQ9_ID, [])
    assert len(rows) == len(PHQ9_ROWS)
    _assert_labels_ok(rows)


def test_every_row_has_five_cells():
    for number, row in enumerate(read_rows(), start=1):
        assert len(row) == 5, "line %d: %r" % (number, row)


def test_identifiers_unique_across_file():
    identifiers = [row[2].strip().lower() for row in read_rows()[1:] if row[2].strip()]
    duplicates = sorted({i for i in identifiers if identifiers.count(i) > 1})
    assert duplicates == []


def test_encoding_and_line_endings():
    raw = REPO_CSV.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), "file has a BOM"
    raw.decode("utf-8")
    assert raw.endswith(b"\r\n"), "last line is not terminated with CRLF"
    assert raw.count(b"\n") == raw.count(b"\r\n"), "bare LF line ending"
