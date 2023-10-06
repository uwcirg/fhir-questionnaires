# fhir-questionnaires
A repository of FHIR Questionnaires in json format. This is intended to be a temporary repository so we can refine them prior to committing them to FHIR repositories.

# Fields and how we use them
- "id"
   - usage: this is how we refer to the questionnaire in code, CarePlans, etc.
   - REQUIRED, and we need it to be a known & reliable value (not assigned by the FHIR server)
   - example: "CIRG-PHQ9"
   - Our profile: add the above info
- "title"
   - usage: human friendly.
   - REQUIRED (1..1). THIS IS A CHANGE FROM THE STANDARD, which says 0..1. Add this to our profile.
   - example: "Everyday Cognition - Participant Self Report Form [ECog]"
   - In DCW, this is used for the page's <head><title> (in [one case](https://github.com/uwcirg/asbi-screening-app/blob/master/src/fhir/1_Questionnaire-CarePartner.json), the project title is included, which isn't good - NBD since that questionnaire is unlikely to be used elsewhere).
- "description"
   - usage: A sentence or two description of the questionnaire. This may be presented in the questionnaire user interface on a page prior to the questionnaire, and/or included in reports. 
   - format: markdown (per spec)
   - REQUIRED (1..1). THIS IS A CHANGE FROM THE STANDARD, which says 0..1. Add this to our profile? 
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
  - item[n]._text.extension
    - XTHML displayed...
      - ... during the questionnaire, usually instructions.
      - ... in the [summary report](https://github.com/uwcirg/patient-summary) "about" pop-up.
      - Not a question (does not have an answerOption[]).
      - Usually at item[0] (the screener gives it its own page in this case)
      - Sometimes later as instructions for a specific question item
      - Examples of both in [MINICOG in the questionnaire filler]([https://github.com/uwcirg/asbi-screening-app](https://github.com/uwcirg/asbi-screening-app/blob/master/src/fhir/1_Questionnaire-MINICOG.json))).
    - "url": "http://hl7.org/fhir/StructureDefinition/rendering-xhtml"
    - "valueString": XTHML
    - Examples
      - CIRG-PC-PTSD-5.json
      - CIRG-PHQ-4.json
      - 1_Questionnaire-USAUDIT.json (screener app)

**We'll continue to curate this as need be**
