# fhir-questionnaires
A repository of FHIR Questionnaires in json format. This is intended to be a definitive source which we populate FHIR repositories from.

# Process for creating these
1. Search for the Questionnaire first at the [NLM forms builder](https://lhcformbuilder.nlm.nih.gov/) and then at LOINC (NLM includes many of the LOINC Questionaires).
2. If we've already have a non-FHIR implementation of the questionnaire in one of our systems (eg dhair2, DCW), compare verbiage, scoring, with what's found. We generally need to retain whatever verbiage we've been using historically, but confirm on a case-by-case basis w/ research staff.
3. Even if we find a FHIR Questionnaire elsewhere, we'll need to bring them to this repository so we can add/edit a small number of fields as described below.

# Fields and how we use them
- "id"
   - usage: this is how we refer to the questionnaire in code, CarePlans, etc.
   - REQUIRED (same as standard), and we need it to be a known & reliable value (not assigned by the FHIR server) - that part is not per standard.
   - example: "CIRG-PHQ9"
   - Our profile: add the above info
- "title"
   - usage: human friendly.
   - REQUIRED (1..1). THIS IS A CHANGE FROM THE STANDARD, which says 0..1. Add this to our profile.
   - example: "Everyday Cognition - Participant Self Report Form [ECog]"
   - In our [questionnaire filler](https://github.com/uwcirg/asbi-screening-app), this is used for the page's <head><title>.
- "description"
   - Spec says: "Natural language description of the questionnaire", 0..1, Markdown.
   - Contrast this with item[0]._text.extension (see below), which we use to describe the questionnaire in XHTML for rendering on web pages.
   - Amy do you use this anywhere? It seems not (I don't see it in the questionnaire filler's DCW Questionnaires, at least), but I may be missing something. If you're not using it, then I'll reserve it for descriptive text that we don't intend to render. 
- "code"
   - usage: uniquely identify the questionnaire according to some system, eg at LOINC. Not our canonical reference (see "id"). See https://github.com/uwcirg/fhir-questionnaires/pull/2/files#r974579864
- "name"
   - Standard says 0..1; computer friendly.
   - Do we use this anywhere Amy? I see that it's populated for the DCW Questionnaires.
- "linkId"
   - usage: QuestionnaireResponse will refer to this
   - REQUIRED (1..1), same as standard.
- "status"
   - REQUIRED (1..1), same as standard.
   - Default for us: "active"
   - We don't read this for anything, and have populated it inconsistently.
- "item"[n]
  - item[n].text - used in the UI.
  - item[n].code.display - ignore, same as item.text but from external source. No need to remove, often too laborious.
  - item[n].linkId
     - REQUIRED.
     - QuestionnaireResponse refers to this.
     - If we identify a FHIR resource for the Questionnaire that's established in the community, then we'll use its values for these. Otherwise, use a pattern like 'CIRG-[project eg "PainTracker"]-[our question ID], eg [this PainTracker body diagram question](https://github.com/uwcirg/fhir-questionnaires/blob/main/CIRG-PainTracker-Location-Body-Diagram.json#L17)'. Note that this is not used for computed mappings, that's done from the source of the QuestionnaireResponse (eg dhair2's question.fhir_linkId)).
  - item[n].type
     - example: "choice", "decimal", "string", "display"
     - REQUIRED.
     - Note: we ignore other directives eg item.extension.valueCodeableConcept.coding.code "drop-down".  
  - item[n].answerOption[n]
    - item.answerOption[n].valueCoding
      - code: QuestionnaireResponse refers to this
        - If we identify a FHIR resource for the Questionnaire that's established in the community, then we'll use its values for these. Otherwise, use eg option.id from dhair2 eg [this PainTracker body diagram question](https://github.com/uwcirg/fhir-questionnaires/blob/main/CIRG-PainTracker-Location-Body-Diagram.json#L17)'. Note that this is not used for computed mappings, that's done from the source of the QuestionnaireResponse (eg dhair2's options.fhir_code).
      - display: the text displayed for the option.
    - item.answerOption[n].extension
      - "url": "http://hl7.org/fhir/StructureDefinition/ordinalValue"
        - almost always valueDecimal; rarely valueString (example [here](https://github.com/uwcirg/asbi-screening-app/blob/master/src/fhir/1_Questionnaire-C-IDAS.json)).
      - "url": "http://hl7.org/fhir/StructureDefinition/questionnaire-optionPrefix" I see this is nearly always populated, but Amy do you use this at all? Seems redundant w/ ordinalValue (just above).
  - item[n]._text.extension where item[n].type = "display"
    - XTHML displayed...
      - ... during the questionnaire, usually instructions.
      - ... in the [summary report](https://github.com/uwcirg/patient-summary) "about" pop-up.
      - Not a question (does not have an answerOption[]).
      - Usually at item[0] (the screener gives it its own page in this case)
      - Sometimes later as instructions for a specific question item
      - Examples of both in [MINICOG in the questionnaire filler](https://github.com/uwcirg/asbi-screening-app/blob/master/src/fhir/1_Questionnaire-MINICOG.json).
    - "url": "http://hl7.org/fhir/StructureDefinition/rendering-xhtml"
    - "valueString": XTHML
    - Examples
      - CIRG-PC-PTSD-5.json
      - CIRG-PHQ-4.json
      - 1_Questionnaire-USAUDIT.json (screener app)
  - item[n]."extension"."valueCoding"
    - We sometimes use this to indicate that an item is a score [here](https://github.com/uwcirg/fhir-questionnaires/pull/2/files#diff-66fd6a93556a044e8ffa3a290dac3e49b37b29b60c0cdddfb2645fe5cea49ae2R582)
    - Amy do you read this for anything?
  - item[n]."enableWhen"
    - Amy you're not using this for anything, are you? I see it for the DCW Audit questionnaires, but we don't use those...

**We'll continue to curate this as need be**
