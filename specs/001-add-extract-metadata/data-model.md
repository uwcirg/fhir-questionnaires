# Phase 1 Data Model: Fork a Questionnaire Into Per-Environment `$extract` Outputs

The tool is stateless: it transforms inputs into two output files plus a warning stream. The
"entities" below are the in-memory shapes and the on-disk artifacts, not a database.

## Entities

### 1. Source Questionnaire (input)
- **What**: A FHIR R4 `Questionnaire` resource as JSON at the repo root (e.g. `CIRG-PHQ-9.json`).
- **Key fields read**:
  - `resourceType` (MUST equal `"Questionnaire"`)
  - `status` (if `"retired"` → reject)
  - `item[]` (recursive tree). For each item: `linkId`, `type`, `code[]`, `extension[]`,
    `answerOption[]`, nested `item[]`.
- **Derived per item**:
  - `loinc` — from `item.code[].code`, else `linkId` with one leading `/` stripped (R1).
  - `is_score` — true if the item carries an `sdc-questionnaire-calculatedExpression` extension (R4).
  - `is_display` — `type == "display"`.
  - `is_answerable` — has an answerable `type` (not `display`/`group`) and a usable answer encoding.
- **Validation**: malformed JSON or non-Questionnaire → fatal (FR-011).

### 2. Flowsheet-ID CSV record (input)
- **What**: One row of `deploy-specific/mapping-input/CNICS PRO UCSD flowsheet FHIR IDs.csv`.
- **Fields**: `RECORD NAME` (descriptive, not used for matching), `LOINC code` (join key),
  `FHIR ID - UAT`, `FHIR ID - Prod`.
- **Validation**: any required column missing → fatal before any output (FR-011). A blank
  `FHIR ID - UAT` or `FHIR ID - Prod` is allowed (sparse) and produces a per-environment gap warning.
- **Index built**: `loinc -> {uat, prod, record_name}`. A LOINC appearing twice with
  **conflicting** IDs is recorded as a conflict (FR-009), not collapsed.

### 3. Mapping outcome (in-memory, per item)
Resolved by joining item `loinc` against the CSV index. Exactly one outcome per in-scope item:

| Outcome | Condition | Effect |
|---------|-----------|--------|
| `mapped` | LOINC found, env ID present | Inject extract metadata with that env's flowsheet ID |
| `missing_env_id` | LOINC found, that env's ID blank | No metadata in that env's output; warn |
| `unmapped_item` | LOINC not in CSV | No metadata; warn |
| `no_loinc` | item has no derivable LOINC | No metadata; warn |
| `score` | item `is_score` | Skip; item left unchanged; warn if it also matched a CSV record |
| `display` / `group` | not answerable | Skip silently (display) / recurse (group) |
| `conflict` | LOINC has conflicting CSV rows | Skip item in both outputs; warn naming the rows |

CSV records whose LOINC matched no item → `unmatched_record` warning (FR-008), one per record.

### 4. Extract metadata (what gets injected, per mapped item, per environment)
Added so HAPI `$extract` emits one Observation (see research R3) coded with **exactly one**
flowsheet coding for that environment:
- SDC `observationExtract` boolean extension (`...sdc-questionnaire-observationExtract`, `true`).
- Flowsheet coding: `system =
  http://open.epic.com/FHIR/StructureDefinition/observation-flowsheet-id`,
  `code =` `FHIR ID - UAT` (UAT output) or `FHIR ID - Prod` (prod output).
- Resulting Observation: `category[0].coding[0] = {system:
  http://hl7.org/fhir/observation-category, code: vital-signs}`, `subject` from QR,
  `effectiveDateTime` from QR authored time.
- **Owned scope**: the tool only adds/updates these elements; all other item content is preserved.

#### Example: extracted downstream Observation (UAT)

This is the Observation HAPI `$extract` should emit for the PHQ-9 first item
(LOINC `44250-9`, "Little interest or pleasure in doing things") answered "Not at all", using
the **UAT** flowsheet FHIR ID `teN3kKw8NMBIF9ZU7Nd-9pQ0` from the CSV. The production output's
Observation is identical except `code.coding[0].code` is the `FHIR ID - Prod` value
(`tFN1y-XuXVcZBVua5Shx3hA0`). Note the single flowsheet coding (Constitution Principle I).

```json
{
  "resourceType": "Observation",
  "category": [
    {
      "coding": [
        { "system": "http://hl7.org/fhir/observation-category", "code": "vital-signs" }
      ]
    }
  ],
  "code": {
    "coding": [
      {
        "system": "http://open.epic.com/FHIR/StructureDefinition/observation-flowsheet-id",
        "code": "teN3kKw8NMBIF9ZU7Nd-9pQ0"
      }
    ]
  },
  "subject": { "reference": "Patient/<patient FHIR ID>" },
  "effectiveDateTime": "2026-01-28T19:57:00Z",
  "valueCodeableConcept": {
    "coding": [
      { "display": "Not at all" }
    ]
  }
}
```

### 5. UAT Questionnaire & Production Questionnaire (outputs)
- **Where**: `deploy-specific/ucsd-uat/<source-filename>` and
  `deploy-specific/ucsd-prod/<source-filename>`.
- **Difference**: identical except UAT carries only `FHIR ID - UAT` flowsheet codes and prod
  only `FHIR ID - Prod`.
- **Invariant**: no Observation in either output is coded with more than one flowsheet (FR-005).
- **Serialization**: byte-stable, idempotent (research R5); re-running on the same source yields
  byte-identical files.

### 6. Run report (output)
- **What**: human-readable warnings to stderr, one line per gap/conflict/skip, each naming the
  LOINC and/or record and what was missing.
- **Exit code**: non-zero only on fatal input errors (entity 1/2 validation); gaps alone → exit 0.

## Relationships

```text
Source Questionnaire ──(item.loinc)──┐
                                     ├──> Mapping outcome ──> Extract metadata ──┬──> UAT Questionnaire
Flowsheet CSV ──(LOINC code index)───┘                                           └──> Prod Questionnaire
        │                                                                              (one flowsheet code each)
        └──(records with no item)──> unmatched_record warnings ─────────────────> Run report
```
