# Phase 0 Research: Fork a Questionnaire Into Per-Environment `$extract` Outputs

All findings were grounded by inspecting real repo data (`CIRG-PHQ-9.json` and
`deploy-specific/mapping-input/CNICS PRO UCSD flowsheet FHIR IDs.csv`).

## R1. Where is an item's LOINC code, for the CSV join?

**Decision**: Read the LOINC code from `item.code[].code`. Fall back to the `linkId` (strip a
single leading `/`) only when `item.code` is absent. Match case-insensitively on the exact
string against the CSV `LOINC code` column.

**Rationale**: In `CIRG-PHQ-9.json` every answerable item carries
`"code": [{"code": "44250-9", "display": "..."}]` — note there is **no `system`** on the
coding, so a strict `system == "http://loinc.org"` filter finds nothing. The same LOINC value
is also embedded in `linkId` as `/44250-9`. Using `item.code[].code` is the most direct and
survives linkId scheme changes; the linkId fallback covers items that omit `code`.

**Alternatives considered**:
- *Require `system == http://loinc.org`* — rejected: the repo's items don't set it; would match nothing.
- *Parse linkId only* — rejected as primary: couples matching to a naming convention; kept as fallback.

## R2. Confirmed mapping behavior against real data (PHQ-9 × CSV)

**Decision**: The tool must handle all three mismatch directions; the PHQ-9/CSV pair exercises each.

**Findings** (item LOINCs vs CSV `LOINC code` column):
- Matched both ways: `44250-9, 44255-8, 44259-0, 44254-1, 44251-7, 44258-2, 44252-5, 44253-3, 44260-8, 44261-6`.
- Item with **no** CSV record: `69722-7` → warn "item LOINC not in CSV", skip.
- CSV records matching **no** item: `55758-7` (UC R FM PHQ2 TOTAL), `69723-5` → warn "CSV record unmatched", skip.
- `44261-6` matches a CSV record **but is the score item** (see R4) → excluded from extraction; warn "matched CSV record skipped — maps to a score item".

**Rationale**: Confirms FR-008 bidirectional warnings and FR-007 score exclusion are real, not hypothetical, on the canonical instrument.

## R3. What `$extract` metadata does HAPI need, and how to encode exactly one flowsheet code?

**Decision**: Per in-scope item, add the SDC observation-extraction metadata so HAPI emits one
Observation per answer:
- Mark the item for extraction with the SDC `sdc-questionnaire-observationExtract` boolean
  extension (`http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-observationExtract`, `valueBoolean: true`).
- Provide the flowsheet code as a coding with `system =
  http://open.epic.com/FHIR/StructureDefinition/observation-flowsheet-id` and `code =` the
  environment's flowsheet FHIR ID, so the extracted `Observation.code.coding` carries **exactly
  one flowsheet coding** for that environment.
- Ensure the extracted Observation lands `category = vital-signs`, `subject` from the QR, and
  `effectiveDateTime` from the QR authored time (root-level observation-link metadata as HAPI
  requires).

**Open validation**: The precise extension wiring HAPI honors (and whether the flowsheet coding
is placed on `item.code` vs. a dedicated extract-code extension) is confirmed against the HAPI
server that runs `$extract`, per the spec's Assumptions — that server is the authority on
sufficiency (Constitution Principle I). The tool surfaces exactly what it wrote so a reviewer
can confirm against HAPI behavior.

**Exactly-one-flowsheet guarantee**: Because each output is single-environment, the tool writes
only that environment's one flowsheet coding per item. The fork — not multi-coding — is what
keeps every Observation to a single flowsheet, satisfying the target EMR constraint.

**Alternatives considered**:
- *Single dual-coded file (UAT + prod codings)* — rejected by Constitution Principle IV / the EMR's "no more than one flowsheet coded" limit.
- *CQL-based extraction* — rejected by Principle II.

## R4. Identifying computed score items to exclude

**Decision**: Treat an item as a computed score (out of scope) when it carries an
`sdc-questionnaire-calculatedExpression` extension
(`http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-calculatedExpression`).
Leave such items byte-for-byte unchanged in both outputs even if their LOINC matches the CSV.

**Rationale**: In `CIRG-PHQ-9.json` the total-score item `/44261-6` (`type: decimal`) is the
only item with `calculatedExpression`; it is exactly the "score, not individual response" the
EMRs don't want. Keying on the extension is precise and matches Constitution Principle I.

**Alternatives considered**:
- *Substring `SCORE` in linkId* — rejected: PHQ-9's score linkId is `/44261-6`, no "SCORE" token; brittle across instruments.
- *`type == decimal`* — rejected: not all decimals are scores.

## R5. Byte-stable, idempotent serialization

**Decision**: Parse with `json.load` (preserves insertion order in 3.7+). Re-run the tool only
on the same source input, not on its own output. Serialize with `json.dump(..., indent=2,
ensure_ascii=False)` followed by a trailing newline, **after** matching the source file's
observed style (indent width and `ensure_ascii`). Only mutate the items the tool owns; never
reorder unrelated keys. An idempotency test asserts a second run yields a byte-identical file.

**Rationale**: Constitution Principle V demands re-runs produce byte-identical output and diffs a
clinician can read. Detecting and reproducing the source's formatting avoids whole-file churn.

**Alternatives considered**:
- *`sort_keys=True`* — rejected: reorders existing keys, producing huge diffs.
- *In-place editing of the source file* — rejected: outputs are separate per-environment artifacts; source stays untouched.

## R6. Deprecated / invalid input handling

**Decision**: Before processing, refuse and exit non-zero (no output written) when: the file is
under `deprecated/`, matches `*.deprecated.json`, or has `status == "retired"` (deprecated →
skip); or the JSON is malformed / `resourceType != "Questionnaire"`; or the CSV is missing any
of `RECORD NAME`, `LOINC code`, `FHIR ID - UAT`, `FHIR ID - Prod`. Each message names the file
and the specific reason.

**Rationale**: Constitution "Extraction Metadata Standards" + spec FR-011. The repo contains
`CIRG-CNICS-ASSIST.deprecated.json`, so the `*.deprecated.json` guard is exercised by real data.

## Resolved unknowns

No `NEEDS CLARIFICATION` markers remain. The only item deferred to runtime validation (R3, exact
HAPI extension wiring) is explicitly delegated to the HAPI consumer by the spec's Assumptions and
does not block design or implementation.
