# Data Model: Code Per-Environment Questionnaires With the Flowsheet Record ID

Nothing is persisted beyond files. These are the in-memory shapes the fork tool works
with and the file shapes it reads and writes. Changes from feature 001/002 are marked
**(changed)**.

## 1. Mapping CSV (input)

`deploy-specific/mapping-input/CNICS PRO UCSD flowsheet FHIR IDs.csv` — not edited by this
feature. Format contract: [contracts/mapping-csv.md](./contracts/mapping-csv.md).

| Column | Read by the tool | Notes |
|--------|------------------|-------|
| `CNICS NAME` | no | Label; holds the `Questionnaire.id` on separator rows. |
| `RECORD NAME (UCSD Epic)` | yes (warnings only) | Required column. |
| `LOINC code` | yes — join key | Required column. Blank → row skipped (separator). |
| `Flowsheet Record ID` **(changed)** | yes | Required column. Replaces `FHIR ID - UAT` and `FHIR ID - Prod`. Blank until UCSD supplies it. |

## 2. Mapping record (in memory) **(changed)**

One per CSV row with a non-blank `LOINC code`.

| Field | Source | Rule |
|-------|--------|------|
| `loinc` | `LOINC code` | Trimmed; matched case-insensitively. |
| `record_name` | `RECORD NAME (UCSD Epic)` | Trimmed; may be blank. |
| `record_id` | `Flowsheet Record ID` | Trimmed; may be blank. Replaces the former `uat` and `prod` fields. |

**Index**: `loinc.lower()` → record, for identifiers whose rows agree.
**Conflicts**: `loinc.lower()` → rows, when two or more rows for the identifier have
different `record_id` values. Conflicting identifiers are never in the index.

## 3. Environment **(changed)**

| Key | Flowsheet `system` | Default output directory |
|-----|--------------------|--------------------------|
| `uat` | `urn:oid:1.2.840.114350.1.13.136.3.7.2.707679` | `deploy-specific/ucsd-uat/` |
| `prod` | `urn:oid:1.2.840.114350.1.13.136.2.7.2.707679` | `deploy-specific/ucsd-prod/` |

The `system` values are held in one mapping in the tool (`FLOWSHEET_SYSTEMS`). An
environment no longer selects a CSV column.

## 4. Item resolution (unchanged outcomes)

Each Questionnaire item resolves to exactly one outcome:

| Outcome | Condition | Effect on outputs |
|---------|-----------|-------------------|
| `display` / `group` | `item.type` is `display` / `group` | Unchanged, silent. |
| `score` | carries `sdc-questionnaire-calculatedExpression` | Unchanged; warned if a row matches. |
| `no_loinc` | no `item.code[].code` and no usable `linkId` | Unchanged; warned. |
| `conflict` | identifier is in Conflicts | Unchanged; warned. |
| `unmapped_item` | identifier not in Index | Unchanged; warned. |
| `mapped` | identifier in Index | See below. |

For a `mapped` item **(changed)**:

- `record_id` non-blank → the item gets extract metadata in **both** outputs.
- `record_id` blank → the item is unchanged in **both** outputs; one warning.

There is no longer a state in which an item is coded in one output and not the other.

## 5. Extract metadata written to a mapped item **(changed)**

```json
{
  "linkId": "44250-9",
  "extension": [
    { "url": "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-observationExtract",
      "valueBoolean": true }
  ],
  "code": [
    { "code": "44250-9", "display": "Little interest or pleasure in doing things" },
    { "system": "<FLOWSHEET_SYSTEMS[env]>", "code": "3025" }
  ]
}
```

- The `observationExtract` extension is unchanged.
- The flowsheet coding is appended after any existing codings. Its `code` is the
  `record_id` (identical in both outputs); its `system` is the environment's.
- Not added if a coding with that environment's `system` is already present.
- Never written: a flowsheet FHIR ID, or
  `http://open.epic.com/FHIR/StructureDefinition/observation-flowsheet-id`.

The root `sdc-questionnaire-observationExtractCategory` extension (`vital-signs`) is
unchanged: added once to any output in which at least one item was coded.

## 6. Per-environment Questionnaire (output)

`<env dir>/<source file name>`, serialized as today (`indent=2`, `ensure_ascii=False`,
trailing newline, source key order).

**Invariant (new)**: for one source Questionnaire, the UAT and production files are
byte-identical once every occurrence of one environment's `system` is replaced by the
other's.

## 7. Warnings

| Event | Message | Count |
|-------|---------|-------|
| Mapped item, blank record ID **(changed)** | `WARNING: loinc=<id> has no Flowsheet Record ID; omitted from both outputs` | 1 per item (was 2) |
| All others | unchanged from `specs/001-add-extract-metadata/contracts/cli.md` | unchanged |

## 8. Validation rules → requirements

| Rule | Requirement |
|------|-------------|
| Missing any required column → fatal, no output | FR-002 |
| Old-layout CSV (no `Flowsheet Record ID`) → fatal, no output | FR-002 |
| Same `code` in both outputs; `system` by environment | FR-003, FR-004 |
| No FHIR ID / old system emitted | FR-005 |
| Outputs differ only in `system` | FR-006 |
| Blank record ID → one warning, no coding, exit 0 | FR-007 |
| Differing record IDs for one identifier → conflict | FR-008 |
