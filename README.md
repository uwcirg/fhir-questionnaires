# fhir-questionnaires
A repository of FHIR Questionnaires in json format. This is intended to be a temporary repository so we can refine them prior to committing them to FHIR repositories.

# Fields and how we use them
- "id"
   - usage: this is how we refer to the questionnaire in code, CarePlans, etc.
   - REQUIRED.
   - example: "CIRG-PHQ9"
- "title"
   - usage: human readable.
   - REQUIRED.
   - example: "Everyday Cognition - Participant Self Report Form [ECog]"
- "description"
   - usage: A sentence or two description of the questionnaire. This may be presented in the questionnaire user interface on a page prior to the questionnaire, and/or included in reports. 
   - REQUIRED.
- "code"
   - usage: uniquely identify the questionnaire according to some system, eg at LOINC. Not our canonical reference (see "id"). See https://github.com/uwcirg/fhir-questionnaires/pull/2/files#r974579864
- "name"
   - usage: arbitrary?
- "linkId"
   - usage: QuestionnaireResponse will refer to this
   - REQUIRED.
- "status"
   - example: "active"
- "extension"."valueCoding"
   - usage: perhaps don't need this, implicit?
   - example: https://github.com/uwcirg/fhir-questionnaires/pull/2/files#diff-66fd6a93556a044e8ffa3a290dac3e49b37b29b60c0cdddfb2645fe5cea49ae2R582 
- "item"
  - item.text - used in the UI.
  - item.code.display - ignore, same as item.text but from external source. No need to remove, often too laborious.
  - item.linkId
     - usage: QuestionnaireResponse will refer to this
     - REQUIRED.
  - item.type
     - example: "choice"
     - REQUIRED.
     - Note: we ignore other directives eg item.extension.valueCodeableConcept.coding.code "drop-down".  

**We'll continue to curate this as need be**
