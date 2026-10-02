# Data Model: Flowsheet Mapping CSV

## Mapping file

`deploy-specific/mapping-input/CNICS PRO UCSD flowsheet FHIR IDs.csv`

| # | Column | Owner | Item row | Separator row |
|---|--------|-------|----------|---------------|
| 1 | `CNICS NAME` | CNICS | brief label, required, ≤ 60 chars | `Questionnaire.id` |
| 2 | `RECORD NAME (UCSD Epic)` | UCSD | blank until supplied | blank |
| 3 | `LOINC code` | CNICS | item `linkId`, required — join key | blank |
| 4 | `FHIR ID - UAT` | UCSD | blank until supplied | blank |
| 5 | `FHIR ID - Prod` | UCSD | blank until supplied | blank |

Structure: header row, then 20 **sections**. A section is one separator row followed by
that Questionnaire's item rows.

## Section

- Identified by `Questionnaire.id` (not the file name: `CIRG-PHQ-9.json` has id `CIRG-PHQ9`).
- Order: `CIRG-PHQ9`, `CIRG-CNICS-ARV`, `CIRG-CNICS-ASSIST`, `CIRG-CNICS-ASSIST-OD`,
  `CIRG-CNICS-ASSIST-Polysub`, `CIRG-CNICS-AUDIT`, `CIRG-CNICS-EUROQOL`,
  `CIRG-CNICS-EXCHANGE-SEX`, `CIRG-CNICS-FINANCIAL`, `CIRG-CNICS-FOOD`,
  `CIRG-CNICS-FROP-Com`, `CIRG-CNICS-HIV-STIGMA`, `CIRG-CNICS-HOUSING`, `CIRG-CNICS-IPV4`,
  `CIRG-CNICS-MAPSS-SF`, `CIRG-CNICS-MINI`, `CIRG-CNICS-SEXUAL-RISK`, `CIRG-CNICS-Smoking`,
  `CIRG-CNICS-Symptoms`, `CIRG-PC-PTSD-5`.
- Each id appears as a separator exactly once.

## Item row

Source: one reportable item of the section's Questionnaire.

**Reportable item** = any `Questionnaire.item` (any depth) where all hold:

- `type` is not `display`
- `type` is not `group`
- `text` does not contain "internal" (case-insensitive)

The `questionnaire-itemControl` extension and the `calculatedExpression` extension have no
bearing on whether an item is reportable.

Validation rules:

| Rule | Spec |
|------|------|
| Exactly 5 cells in every row | FR-014 |
| Header equals the five column names in order | FR-001, FR-002 |
| For each new section: set and order of `LOINC code` values = reportable items' `linkId`s in Questionnaire order | FR-005, FR-006, FR-007, FR-008, FR-009 |
| `CNICS NAME` non-empty, ≤ 60 chars, unique within its section | FR-010, SC-006 |
| New-section rows: columns 2, 4, 5 blank | FR-011 |
| `LOINC code` unique across the file (blank cells excluded) | FR-013 |
| The 12 PHQ-9 rows keep record name, identifier, UAT ID, Prod ID | FR-012 |

## State

A new item row moves through: **listed** (label + identifier; this feature) → **built**
(UCSD fills record name) → **mapped** (UCSD fills both FHIR IDs). Only PHQ-9 rows are
*mapped* today.
