import re
import os
import random
import string
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
from werkzeug.utils import secure_filename
from faker import Faker

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER_ORIGINAL = 'uploads/original'
UPLOAD_FOLDER_MASKED = 'uploads/masked'
app.config['UPLOAD_FOLDER_ORIGINAL'] = UPLOAD_FOLDER_ORIGINAL
app.config['UPLOAD_FOLDER_MASKED'] = UPLOAD_FOLDER_MASKED

os.makedirs(UPLOAD_FOLDER_ORIGINAL, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_MASKED, exist_ok=True)

ALLOWED_EXTENSIONS = {'csv', 'xlsx'}

# Initialize Faker
fake = Faker()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def sanitize_filename(filename):
    return secure_filename(filename)

def mask_email(email):
    local, domain = email.split("@")
    local_masked = local[0] + '*' * (len(local) - 2) + local[-1] if len(local) > 2 else '*' * len(local)
    return f"{local_masked}@{domain}"

def mask_phone(phone):
    return re.sub(r'\d', '*', phone[:-2]) + phone[-2:]

def mask_text(value):
    """
    Mask general text data (e.g., names, addresses) partially.
    Only show first and last character, replace the middle part with asterisks.
    """
    if len(value) > 2:
        return value[0] + '*' * (len(value) - 2) + value[-1]
    else:
        return '*' * len(value)

def mask_numeric(value):
    """
    Mask numeric data (e.g., phone numbers, IC numbers) by keeping only the first and last digits visible.
    """
    num_str = str(int(value))  # Convert to string to handle the digits properly
    if len(num_str) > 2:
        return num_str[0] + '*' * (len(num_str) - 2) + num_str[-1]
    else:
        return '*' * len(num_str)

def anonymize_name_or_address(value, column_name=None):
    """
    Anonymize name and address-related data by using Faker to generate random fake data.
    """
    if column_name:
        # Check if it's a name or address column (case insensitive)
        if 'name' in column_name.lower():
            return fake.name()  # Generate a fake name
        elif 'address' in column_name.lower():
            return fake.address()  # Generate a fake address
    return value

def mask_data(value, column_name=None):
    """
    Mask data based on the type of value and column name.
    Apply appropriate masking logic for text and numeric data.
    """
    if isinstance(value, str):
        value = value.strip()

        # Check if the column is a name or address column (you can adjust these checks as needed)
        if column_name and ('name' in column_name.lower() or 'address' in column_name.lower()):
            return anonymize_name_or_address(value, column_name)

        if re.match(r"[^@]+@[^@]+\.[^@]+", value):  # Detect email
            return mask_email(value)
        elif re.match(r'\d{10,}', value):  # Detect phone numbers
            return mask_phone(value)
        else:
            return mask_text(value)  # Generic text masking
    elif isinstance(value, (int, float)):
        return mask_numeric(value)  # Mask numeric data
    return value

@app.route("/detect_columns", methods=["POST"])
def detect_columns():
    file = request.files.get("file")
    if not file or not allowed_file(file.filename):
        return jsonify({"error": "No file uploaded or file format not supported"}), 400

    input_path = os.path.join(UPLOAD_FOLDER_ORIGINAL, sanitize_filename(file.filename))
    file.save(input_path)

    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(input_path)
        elif file.filename.endswith('.xlsx'):
            df = pd.read_excel(input_path)

        columns = df.columns.tolist()
        return jsonify({"columns": columns})
    except Exception as e:
        return jsonify({"error": f"Failed to process the file. Error: {str(e)}"}), 500

@app.route("/mask_data", methods=["POST"])
def mask_data_route():
    file = request.files.get("file")
    columns_to_mask = request.form.get("columns")

    if not file or not columns_to_mask:
        return jsonify({"error": "No file uploaded or columns selected for masking."}), 400

    try:
        columns_to_mask = json.loads(columns_to_mask)
        input_path = os.path.join(UPLOAD_FOLDER_ORIGINAL, sanitize_filename(file.filename))
        file.save(input_path)

        if file.filename.endswith('.csv'):
            df = pd.read_csv(input_path)
        elif file.filename.endswith('.xlsx'):
            df = pd.read_excel(input_path)

        for column in columns_to_mask:
            if column in df.columns:
                df[column] = df[column].apply(lambda x: mask_data(x, column))
            else:
                print(f"Warning: Column {column} not found in DataFrame.")

        masked_file_path = os.path.join(UPLOAD_FOLDER_MASKED, f"masked_{sanitize_filename(file.filename)}")
        if file.filename.endswith('.csv'):
            df.to_csv(masked_file_path, index=False)
        elif file.filename.endswith('.xlsx'):
            df.to_excel(masked_file_path, index=False)

        return jsonify({"file_path": f"/{masked_file_path.replace(os.sep, '/')}"}), 200
    except Exception as e:
        return jsonify({"error": f"Error masking data. {str(e)}"}), 500

@app.route("/uploads/masked/<filename>")
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER_MASKED, filename)

if __name__ == "__main__":
    app.run(debug=True)
























































