
import json
import os
import sys

def main(file_path):
    # Read the content of the file to analyze its structure
    with open(file_path, 'r') as file:
        content = file.read()

    # Split the content by empty lines to isolate each question
    questions_raw = content.strip().split('\n\n')

    # Initialize an empty FHIR Questionnaire R4 JSON object
    fhir_questionnaire = {
        "resourceType": "Questionnaire",
        "status": "active",
        "item": []
    }

    # Loop through each question to populate the items
    for question_raw in questions_raw:
        lines = question_raw.strip().split('\n')
        question_text = lines[0]
        link_id = lines[1].replace("item.linkId: ", "")
        
        # Initialize an item
        item = {
            "linkId": link_id,
            "text": question_text,
            "type": "choice" if len(lines) > 2 else "string"
        }
        
        # Check for answer options and populate them if they exist
        if len(lines) > 2:
            answer_options = lines[2:]
            item["answerOption"] = []
            for idx, option in enumerate(answer_options):
                answer_option = {
                    "valueCoding": {
                        "code": f"{link_id}-{idx}",
                        "display": option
                    }
                }
                item["answerOption"].append(answer_option)
        
        # Add the item to the Questionnaire
        fhir_questionnaire["item"].append(item)

    # Serialize the JSON object to a string
    fhir_questionnaire_str = json.dumps(fhir_questionnaire, indent=4)
    
    # Save the JSON object to a new file in the same directory as the source text file
    output_file_path = os.path.join(os.path.dirname(file_path), 'FHIR_Questionnaire_R4.json')
    with open(output_file_path, 'w') as file:
        file.write(fhir_questionnaire_str)

    print(f"Generated FHIR Questionnaire R4 JSON saved to: {output_file_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <path_to_source_text_file>")
    else:
        main(sys.argv[1])
