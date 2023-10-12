# fhir-questionnaires
A repository of FHIR Questionnaires in json format. This is intended to be a definitive source which we populate FHIR repositories from. Even if we know of a FHIR Questionnaire elsewhere, we'll need to bring them to this repository so we can add/edit a subset of fields as described below.

# Process for creating these
1. Search for the Questionnaire first at the [NLM forms builder](https://lhcformbuilder.nlm.nih.gov/) and then at LOINC (NLM includes many of the LOINC Questionaires).
   1. We want the FHIR "R4" (current) version. If a particular questionnaire is only available as an earlier version of FHIR (eg DSTU2, or STU3), we'll probably want to start there and adapt it to the R4 format.
   1. If we've already have a non-FHIR implementation of the questionnaire in one of our systems (eg dhair2, DCW), compare verbiage, scoring, with what's found. We generally need to retain whatever verbiage we've been using historically, but confirm on a case-by-case basis w/ research staff.
1. If we don't find an existing FHIR Questionnaire, here are the alternatives:
   1. Copy existing similar qnr from our repo
      1. Example: CIRG-PainTracker-STOP (very brief qnr, 4 yes/no questions)
   1. Create one de novo w/ help from a script (see chatgpt script) - makes sense for something like PainTracker TRT - fairly long, all codings novel.
      1. Example: CIRG-PainTracker-TRT

# Fields and how we use them
- "id"
   - usage: this is how we refer to the questionnaire in code, CarePlans, etc.
   - REQUIRED 1..1 (same as standard), and we need it to be a known & reliable value (not assigned by the FHIR server) - that part is not per standard.
   - QuestionnaireResponse.questionnaire points at this via eg "Questionnaire/CIRG-PHQ-4"
   - example: "CIRG-PHQ-4"
   - Our profile: add the above info
- "title"
   - usage: human friendly.
   - REQUIRED (1..1). THIS IS A CHANGE FROM THE STANDARD, which says 0..1. Add this to our profile.
   - example: "Everyday Cognition - Participant Self Report Form [ECog]"
   - In our [questionnaire filler](https://github.com/uwcirg/asbi-screening-app), this is used for the page's <head><title>.
- "description"
   = REQUIRED (1..1). This is in contrast to spec (0..1).
   - Per spec: "Natural language description of the questionnaire"; [Markdown w/out HTML](https://build.fhir.org/datatypes.html#markdown).
   - 2023-10-12 Moving forward we'll use this for descriptive text to displayed to non-lay users (eg in the summary report).
     - We'll use Markdown w/out HTML, and we expect that the front-end may convert that to html (and indeed we'll include e.g. links to references here).
     - This may include `<-- HTML style comments -->` for internal notes that we don't want rendered (hopefully a lib like showdown.js will interpret those as HTML comments, so they won't be displayed...).
   - Contrast this with item[0]._text.extension (see below).
- "code"
   - usage: uniquely identify the questionnaire according to some system, eg at LOINC. Not our canonical reference (see "id"). See https://github.com/uwcirg/fhir-questionnaires/pull/2/files#r974579864
- "name"
   - Standard says 0..1; computer friendly.
   - Do we use this anywhere Amy? I see that it's populated for the DCW Questionnaires.
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
     - Note that this is not used for computed mappings back *to* the non-FHIR source (eg dhair2); that source maps in this direction (eg dhair2's question.fhir_linkId)). 
     - If we identify a FHIR resource for the Questionnaire that's established in the community (usually loinc), then we'll use its values for these. Otherwise, use whatever is easy... a pattern like 'CIRG-[project eg "PainTracker"]-[our question ID], eg [this PainTracker body diagram question](https://github.com/uwcirg/fhir-questionnaires/blob/main/CIRG-PainTracker-Location-Body-Diagram.json#L17)' is good, but sometimes not easy (hard to scale).
  - item[n].type
     - example: "choice", "decimal", "string", "display"
     - REQUIRED.
     - Note: we ignore other directives eg item.extension.valueCodeableConcept.coding.code "drop-down".  
  - item[n].answerOption[n]
    - item.answerOption[n].valueCoding
      - code: QuestionnaireResponse refers to this
        - This is not used for computed mappings back *to* the non-FHIR source (eg dhair2); that source maps in this direction (eg dhair2's options.fhir_code).
        - If we identify a FHIR resource for the Questionnaire that's established in the community (usually loinc), then we'll use its values for these. Otherwise, use whatever is easy... a pattern like option.id from dhair2 eg [this PainTracker body diagram question](https://github.com/uwcirg/fhir-questionnaires/blob/main/CIRG-PainTracker-Location-Body-Diagram.json#L17)' is good, but sometimes not easy (hard to scale).
      - display: the text displayed for the option.
    - item.answerOption[n].extension
      - "url": "http://hl7.org/fhir/StructureDefinition/ordinalValue"
        - almost always valueDecimal; rarely valueString (example [here](https://github.com/uwcirg/asbi-screening-app/blob/master/src/fhir/1_Questionnaire-C-IDAS.json)).
      - "url": "http://hl7.org/fhir/StructureDefinition/questionnaire-optionPrefix" I see this is nearly always populated, but Amy do you use this at all? Seems redundant w/ ordinalValue (just above).
  - item[n]._text.extension where item[n].type = "display"
    - XTHML displayed...
      - ... during the questionnaire, usually instructions.
      - ... sometimes in the [summary report](https://github.com/uwcirg/patient-summary) "about" pop-up, but as of 2023-10-12 we are moving to `description` for that.
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
