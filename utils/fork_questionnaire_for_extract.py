#!/usr/bin/env python3
"""Fork one FHIR R4 Questionnaire into per-environment ``$extract`` outputs.

Given a source Questionnaire and the flowsheet-ID CSV, this tool writes **two**
derived Questionnaires:

* ``deploy-specific/ucsd-uat/<name>``  — carrying only ``FHIR ID - UAT`` flowsheet codes
* ``deploy-specific/ucsd-prod/<name>`` — carrying only ``FHIR ID - Prod`` flowsheet codes

Each in-scope, answerable item is matched to a CSV record by its LOINC code and
annotated with the SDC metadata HAPI's ``$extract`` needs to emit exactly one
Observation coded with a single flowsheet coding for that environment. Computed
score items, display/group items, unmapped items, and items with no LOINC are
left byte-for-byte unchanged. Every mapping gap (in either direction) is reported
as a ``WARNING:`` line on stderr without failing the run or fabricating IDs.

Outputs are byte-stable and idempotent so a clinical reviewer can diff each file
against a single CSV column.

Usage::

    python3 utils/fork_questionnaire_for_extract.py CIRG-PHQ-9.json

    python3 utils/fork_questionnaire_for_extract.py CIRG-PEG.json \\
        --csv "deploy-specific/mapping-input/CNICS PRO UCSD flowsheet FHIR IDs.csv" \\
        --uat-dir deploy-specific/ucsd-uat \\
        --prod-dir deploy-specific/ucsd-prod

Bulk processing is a shell loop over single invocations (Constitution: bulk =
loop over single runs).
"""

import argparse
import copy
import csv
import json
import sys
from pathlib import Path

# --- FHIR / SDC constants ---------------------------------------------------

SDC_OBSERVATION_EXTRACT = (
    "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-observationExtract"
)
SDC_CALCULATED_EXPRESSION = (
    "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-calculatedExpression"
)
SDC_OBSERVATION_EXTRACT_CATEGORY = (
    "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-observationExtractCategory"
)
EPIC_FLOWSHEET_SYSTEM = (
    "http://open.epic.com/FHIR/StructureDefinition/observation-flowsheet-id"
)
# Observation.category HAPI stamps on every extracted Observation. A PHQ-9 is a
# survey instrument, so `survey` is the correct category (matches the working
# GAD-7 questionnaire).
OBSERVATION_CATEGORY_SYSTEM = "http://terminology.hl7.org/CodeSystem/observation-category"
OBSERVATION_CATEGORY_CODE = "survey"

REQUIRED_CSV_COLUMNS = ["RECORD NAME", "LOINC code", "FHIR ID - UAT", "FHIR ID - Prod"]

# Environment key -> CSV column carrying that environment's flowsheet FHIR ID.
ENV_COLUMNS = {"uat": "FHIR ID - UAT", "prod": "FHIR ID - Prod"}

DEFAULT_CSV = "deploy-specific/mapping-input/CNICS PRO UCSD flowsheet FHIR IDs.csv"
DEFAULT_UAT_DIR = "deploy-specific/ucsd-uat"
DEFAULT_PROD_DIR = "deploy-specific/ucsd-prod"


# --- small helpers ----------------------------------------------------------


def warn(message):
    """Emit a non-fatal warning to stderr."""
    print("WARNING: " + message, file=sys.stderr)


def fatal(message):
    """Emit a fatal error to stderr and exit non-zero. No output is written."""
    print("ERROR: " + message, file=sys.stderr)
    return 1


# --- input guards (T004, research R6) ---------------------------------------


def deprecated_reason(path):
    """Return a human reason if ``path`` is a deprecated input, else ``None``.

    Path-based checks only (do not require the JSON to be parsed): the file is
    under a ``deprecated/`` directory, or its name matches ``*.deprecated.json``.
    """
    p = Path(path)
    if any(part == "deprecated" for part in p.parts):
        return "is under a deprecated/ directory"
    if p.name.endswith(".deprecated.json"):
        return "matches *.deprecated.json"
    return None


def load_questionnaire(path):
    """Load and validate the source Questionnaire.

    Returns the parsed dict on success. Raises ``ValueError`` with a
    file-naming message when the input is deprecated, not valid JSON, not a
    Questionnaire, or retired. Callers turn that into a fatal exit.
    """
    reason = deprecated_reason(path)
    if reason is not None:
        raise ValueError("input %s %s; refusing to process" % (path, reason))

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise ValueError("input %s does not exist" % path)
    except json.JSONDecodeError as exc:
        raise ValueError("input %s is not valid JSON (%s)" % (path, exc))

    if not isinstance(data, dict) or data.get("resourceType") != "Questionnaire":
        raise ValueError(
            "input %s resourceType is %r, expected \"Questionnaire\""
            % (path, data.get("resourceType") if isinstance(data, dict) else None)
        )

    if data.get("status") == "retired":
        raise ValueError("input %s has status=retired; refusing to process" % path)

    return data


# --- CSV loader & mapping index (T005, data-model entity 2) -----------------


def load_csv_index(csv_path):
    """Read the flowsheet CSV into a LOINC -> record index.

    Returns ``(index, conflicts, records)`` where:

    * ``index``     -- ``loinc_lower -> {"uat", "prod", "record_name", "loinc"}``
                       for every non-conflicting LOINC.
    * ``conflicts`` -- ``loinc_lower -> [record, ...]`` for LOINCs that appear
                       in multiple rows with conflicting env IDs (FR-009; detection
                       only — such items are skipped, never collapsed).
    * ``records``   -- list of all rows as ``{"loinc", "record_name", "uat", "prod"}``
                       in file order, for unmatched-record reporting (FR-008).

    Raises ``ValueError`` (→ fatal) if any required column is missing, before any
    output is produced.
    """
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        missing = [c for c in REQUIRED_CSV_COLUMNS if c not in fieldnames]
        if missing:
            raise ValueError(
                "CSV %s is missing required column(s): %s"
                % (csv_path, ", ".join(missing))
            )

        records = []
        for row in reader:
            loinc = (row.get("LOINC code") or "").strip()
            if not loinc:
                continue
            records.append(
                {
                    "loinc": loinc,
                    "record_name": (row.get("RECORD NAME") or "").strip(),
                    "uat": (row.get("FHIR ID - UAT") or "").strip(),
                    "prod": (row.get("FHIR ID - Prod") or "").strip(),
                }
            )

    # Group rows by lowercased LOINC; detect conflicting duplicates.
    grouped = {}
    for rec in records:
        grouped.setdefault(rec["loinc"].lower(), []).append(rec)

    index = {}
    conflicts = {}
    for key, rows in grouped.items():
        distinct = {(r["uat"], r["prod"]) for r in rows}
        if len(distinct) > 1:
            conflicts[key] = rows
            continue
        rec = rows[0]
        index[key] = {
            "uat": rec["uat"],
            "prod": rec["prod"],
            "record_name": rec["record_name"],
            "loinc": rec["loinc"],
        }

    return index, conflicts, records


# --- item walking & LOINC extraction (T006, T007) ---------------------------


def extract_loinc(item):
    """Return an item's LOINC code for the CSV join, or ``None`` (research R1).

    Primary source is ``item.code[].code``; falls back to ``linkId`` with a
    single leading ``/`` stripped. Returns ``None`` when neither yields a value.
    """
    for coding in item.get("code", []) or []:
        code = coding.get("code")
        if code:
            return str(code).strip()
    link_id = item.get("linkId")
    if isinstance(link_id, str) and link_id:
        stripped = link_id[1:] if link_id.startswith("/") else link_id
        if stripped:
            return stripped.strip()
    return None


def iter_items(items, parent=None):
    """Yield ``(item, parent)`` for every item at any nesting depth (T007)."""
    for item in items or []:
        if not isinstance(item, dict):
            continue
        yield item, parent
        if item.get("item"):
            yield from iter_items(item["item"], parent=item)


def is_score(item):
    """True if the item carries an SDC calculatedExpression extension (research R4)."""
    for ext in item.get("extension", []) or []:
        if ext.get("url") == SDC_CALCULATED_EXPRESSION:
            return True
    return False


def is_answerable(item):
    """True for items that can produce an answer (not display/group)."""
    return item.get("type") not in ("display", "group")


# --- mapping resolution (data-model entity 3) -------------------------------


def resolve_item(item, index, conflicts):
    """Classify a single item against the CSV index.

    Returns a ``(outcome, detail)`` tuple where ``outcome`` is one of:
    ``display``, ``group``, ``score``, ``no_loinc``, ``conflict``,
    ``unmapped_item``, ``mapped``. ``detail`` carries the LOINC and, for
    ``mapped``, the matched record.
    """
    item_type = item.get("type")
    if item_type == "display":
        return ("display", {})
    if item_type == "group":
        return ("group", {})

    loinc = extract_loinc(item)

    if is_score(item):
        return ("score", {"loinc": loinc})

    if loinc is None:
        return ("no_loinc", {})

    key = loinc.lower()
    if key in conflicts:
        return ("conflict", {"loinc": loinc, "rows": conflicts[key]})
    if key not in index:
        return ("unmapped_item", {"loinc": loinc})
    return ("mapped", {"loinc": loinc, "record": index[key]})


# --- extract-metadata injection (T013, data-model entity 4) -----------------


def inject_extract_metadata(item, flowsheet_id):
    """Annotate one in-scope item so HAPI ``$extract`` emits one Observation.

    Adds the SDC ``observationExtract`` boolean extension and a single flowsheet
    coding (``system`` = Epic flowsheet-id, ``code`` = the environment's FHIR ID)
    to ``item.code``. Only these owned elements are touched; all other content is
    preserved.
    """
    extensions = item.setdefault("extension", [])
    if not any(e.get("url") == SDC_OBSERVATION_EXTRACT for e in extensions):
        extensions.append({"url": SDC_OBSERVATION_EXTRACT, "valueBoolean": True})

    codings = item.setdefault("code", [])
    if not any(c.get("system") == EPIC_FLOWSHEET_SYSTEM for c in codings):
        codings.append({"system": EPIC_FLOWSHEET_SYSTEM, "code": flowsheet_id})


def ensure_root_extract_category(doc):
    """Declare the root ``observationExtractCategory`` HAPI's ``$extract`` needs.

    HAPI reads this Questionnaire-root extension to set ``Observation.category``
    on every emitted Observation; without it the operation fails even though the
    per-item ``observationExtract`` flags are present. Added once per document
    (the survey category). Idempotent: a document that already declares it is
    left unchanged. Callers add it only to documents that actually got extract
    metadata injected, so non-extract instruments stay untouched.
    """
    extensions = doc.setdefault("extension", [])
    if any(e.get("url") == SDC_OBSERVATION_EXTRACT_CATEGORY for e in extensions):
        return
    extensions.append(
        {
            "url": SDC_OBSERVATION_EXTRACT_CATEGORY,
            "valueCodeableConcept": {
                "coding": [
                    {
                        "system": OBSERVATION_CATEGORY_SYSTEM,
                        "code": OBSERVATION_CATEGORY_CODE,
                    }
                ]
            },
        }
    )


# --- warnings / run report (T019, T020, T021, T023) -------------------------


def report_gaps(source, index, conflicts, records):
    """Walk the source and emit every mapping warning exactly once (US2/US3).

    Warnings never change the exit code (FR-009): mapping gaps, conflicts, and
    score exclusions are informational. Returns the set of LOINCs (lowercased)
    that matched some item, used for ``unmatched_record`` reporting.
    """
    matched_loincs = set()

    for item, _parent in iter_items(source.get("item", [])):
        outcome, detail = resolve_item(item, index, conflicts)
        loinc = detail.get("loinc")
        link_id = item.get("linkId")

        if loinc:
            matched_loincs.add(loinc.lower())

        if outcome in ("display", "group"):
            continue

        if outcome == "score":
            # Only warn when the score item also matched a CSV record (research R4).
            if loinc and loinc.lower() in index:
                warn(
                    "loinc=%s is a computed score (calculatedExpression); "
                    "excluded from extraction" % loinc
                )
            continue

        if outcome == "no_loinc":
            warn("item linkId=%s has no LOINC code; skipped" % link_id)
            continue

        if outcome == "conflict":
            names = ", ".join(
                '"%s"' % r["record_name"] for r in detail.get("rows", [])
            )
            warn(
                "loinc=%s has conflicting CSV rows (%s); item left unmodified"
                % (loinc, names)
            )
            continue

        if outcome == "unmapped_item":
            warn(
                "item linkId=%s loinc=%s has no CSV record; skipped"
                % (link_id, loinc)
            )
            continue

        # outcome == "mapped": warn for any environment whose ID is blank.
        record = detail["record"]
        for env, column in ENV_COLUMNS.items():
            if not record.get(env):
                warn(
                    "loinc=%s has no %s; omitted from %s output"
                    % (loinc, column, env)
                )

    # CSV records whose LOINC matched no item (FR-008), one per record.
    for rec in records:
        if rec["loinc"].lower() not in matched_loincs:
            warn(
                'CSV record "%s" loinc=%s matched no item; skipped'
                % (rec["record_name"], rec["loinc"])
            )

    return matched_loincs


# --- two-document build (T014) ----------------------------------------------


def build_environment_output(source, index, conflicts, env):
    """Return a deep copy of ``source`` with only ``env``'s flowsheet IDs injected.

    ``env`` is ``"uat"`` or ``"prod"``. Mapped, answerable, non-score items whose
    record carries that environment's ID get the extract metadata; everything
    else (scores, display/group, unmapped, no-LOINC, conflicts, blank env ID) is
    left byte-for-byte unchanged. No warnings are emitted here — see
    :func:`report_gaps`.
    """
    doc = copy.deepcopy(source)
    injected_any = False
    for item, _parent in iter_items(doc.get("item", [])):
        outcome, detail = resolve_item(item, index, conflicts)
        if outcome != "mapped":
            continue
        flowsheet_id = detail["record"].get(env)
        if not flowsheet_id:
            continue  # missing env ID → never fabricate (FR-007)
        inject_extract_metadata(item, flowsheet_id)
        injected_any = True
    # Only a document that actually marks items for extraction needs the root
    # category HAPI reads; leave documents with zero extract items untouched.
    if injected_any:
        ensure_root_extract_category(doc)
    return doc


# --- byte-stable serialization (T008, research R5) --------------------------


def write_questionnaire(doc, out_dir, source_path):
    """Write ``doc`` to ``out_dir/basename(source_path)``, byte-stable (research R5).

    Uses ``indent=2, ensure_ascii=False`` plus a trailing newline, preserving the
    source key order. Creates the output directory if missing.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / Path(source_path).name
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return out_path


# --- CLI (T001, T015) -------------------------------------------------------


def build_parser():
    parser = argparse.ArgumentParser(
        prog="fork_questionnaire_for_extract.py",
        description=(
            "Fork one FHIR Questionnaire into per-environment $extract outputs "
            "(UAT-only and prod-only flowsheet IDs)."
        ),
    )
    parser.add_argument(
        "questionnaire",
        help="Path to one source Questionnaire JSON (exactly one per run).",
    )
    parser.add_argument(
        "--csv",
        default=DEFAULT_CSV,
        help="Flowsheet-ID CSV path (default: %(default)s).",
    )
    parser.add_argument(
        "--uat-dir",
        default=DEFAULT_UAT_DIR,
        help="Output directory for the UAT Questionnaire (default: %(default)s).",
    )
    parser.add_argument(
        "--prod-dir",
        default=DEFAULT_PROD_DIR,
        help="Output directory for the production Questionnaire (default: %(default)s).",
    )
    return parser


def run(questionnaire, csv_path, uat_dir, prod_dir):
    """Execute one fork. Returns an exit code (0 success, non-zero fatal).

    Wiring (T015): guards → load CSV index → report gaps → build both docs →
    write via the byte-stable serializer. Mapping gaps warn but keep exit 0.
    """
    try:
        source = load_questionnaire(questionnaire)
    except ValueError as exc:
        return fatal(str(exc))

    try:
        index, conflicts, records = load_csv_index(csv_path)
    except FileNotFoundError:
        return fatal("CSV %s does not exist" % csv_path)
    except ValueError as exc:
        return fatal(str(exc))

    # Emit all warnings once (gaps never abort the run).
    report_gaps(source, index, conflicts, records)

    # Build and write both per-environment outputs.
    uat_doc = build_environment_output(source, index, conflicts, "uat")
    prod_doc = build_environment_output(source, index, conflicts, "prod")

    try:
        uat_path = write_questionnaire(uat_doc, uat_dir, questionnaire)
        prod_path = write_questionnaire(prod_doc, prod_dir, questionnaire)
    except OSError as exc:
        return fatal("could not write output: %s" % exc)

    print("Wrote %s" % uat_path)
    print("Wrote %s" % prod_path)
    return 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    return run(args.questionnaire, args.csv, args.uat_dir, args.prod_dir)


if __name__ == "__main__":
    sys.exit(main())
