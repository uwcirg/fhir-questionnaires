import json
import sys

def remove_option_prefix_extensions(data):
    """
    Recursively traverse the JSON and remove extensions of type
    'http://hl7.org/fhir/StructureDefinition/questionnaire-optionPrefix'
    from all answerOption elements.
    """
    if isinstance(data, dict):
        # If this dict has an 'answerOption' list, process it
        if 'answerOption' in data and isinstance(data['answerOption'], list):
            for option in data['answerOption']:
                if isinstance(option, dict) and 'extension' in option:
                    option['extension'] = [
                        ext for ext in option['extension']
                        if not (
                            isinstance(ext, dict) and
                            ext.get('url') == 'http://hl7.org/fhir/StructureDefinition/questionnaire-optionPrefix'
                        )
                    ]
                    # Remove 'extension' if it’s now empty
                    if not option['extension']:
                        option.pop('extension')
        
        # Recurse into all dictionary values
        for key, value in data.items():
            data[key] = remove_option_prefix_extensions(value)
    
    elif isinstance(data, list):
        # Recurse into each item in the list
        data = [remove_option_prefix_extensions(item) for item in data]

    return data


def main(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        questionnaire = json.load(f)

    cleaned = remove_option_prefix_extensions(questionnaire)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    print(f"Cleaned file written to {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python remove_option_prefix.py <input.json> <output.json>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])

