from flask import Flask, request, jsonify, send_file, render_template
import google.generativeai as genai
import os
import tempfile
import textwrap
import re
import pandas as pd

app = Flask(__name__, template_folder='templates', static_folder='static')

# Configure the Google API key
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', 'sssss')
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro-latest')

# Function to convert text to markdown format
def to_markdown(text):
    # Replace bullet points with empty string
    text = text.replace('•','')
    # Add indentation for block quotes
    return textwrap.indent(text, '> ', predicate=lambda _: True)

# Helper function to ensure the table format is correct
def ensure_table_format(text):
    lines = text.split('\n')
    for i in range(len(lines)):
        if re.match(r'^\|\s*\d+\s*\|', lines[i]):
            lines[i] = lines[i].replace(' | ', ' |').replace('| ', '|').replace(' |', '|').replace('| ', ' | ')
    return '\n'.join(lines)

# Helper function to create a DataFrame from the response text
# Helper function to create a DataFrame from the response text
def create_dataframe(text):
    lines = text.split('\n')
    data = []
    for line in lines:
        if line.strip() and line.startswith('|'):
            columns = [col.strip() for col in line.split('|')[1:-1]]
            data.append(columns)
    if len(data) > 1:
        df = pd.DataFrame(data[1:], columns=data[0])
    else:
        df = pd.DataFrame()
    return df

@app.route('/')
def index():
    return render_template('./index.html')

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    print("****************",data)
    prompt = data.get('prompt')
    print("#####################",prompt)
    positive_count = data.get('positiveCount', 10)
    negative_count = data.get('negativeCount', 10)

    modified_prompt = f"{prompt} Generate {positive_count} positive test cases and {negative_count} negative test cases."
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400
    

     # Add explicit instructions to the prompt
    # full_prompt = (
    #     f"Generate test cases for the following scenario in a Markdown table format "
    #     f"with columns: Test Case ID, Description, Input, Expected Result.\n\n"
    #     f"{modified_prompt}\n\n"
    #     f"You need to mention which is Positive test cases and Negative test cases:\n\n"
    #     f"## Test Cases in Markdown Table Format:\n\n"
    #     f"| Test Case ID | Description | Input | Expected Result |\n"
    #     f"|--------------|-------------|-------|-----------------|\n"
    # )

    full_prompt = (
        # f"Generate test cases for the following scenario in a Markdown table format "
        f"Add the given prompt on top of the table named it has Given Prompt:,Don't highlights the prompt.\n"
        f"with columns:Test Case ID, Description, Input, Expected Result,Test case type.\n\n"
        f"In column Test case type Generate only the test case is positive or negative.\n"
        f"{modified_prompt}\n\n"
        f"## Test Cases in Markdown Table Format:\n\n"
        f" Test Case ID | Description | Input | Expected Result |Test case type|\n"
        f"--------------|-------------|-------|-----------------|-------------|\n"
    )
    
    response_Skill = model.generate_content(full_prompt)
    response_text = response_Skill.text
    # Apply the to_markdown function
    markdown_response_text = to_markdown(response_text)
    # Ensure the table format is correct
    formatted_text = ensure_table_format(markdown_response_text)

    # Save response to a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.txt')
    # temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.ods')
    temp_file.write(formatted_text)
    temp_file_path = temp_file.name
    temp_file.close()

     # Create DataFrame and save as CSV and Excel
    df = create_dataframe(formatted_text)
    csv_file_path = tempfile.mktemp(suffix='.csv')
    excel_file_path = tempfile.mktemp(suffix='.xlsx')
    if not df.empty:
        df.to_csv(csv_file_path, index=False)
        df.to_excel(excel_file_path, index=False)
    
    return jsonify({"response": formatted_text,
                     "file_path": temp_file_path,
                     "prompt"    : prompt, 
                    "csv_file_path": csv_file_path if not df.empty else "",
                    "excel_file_path": excel_file_path if not df.empty else ""}
                    )

@app.route('/download', methods=['GET'])
def download():
    file_path = request.args.get('file_path')
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
