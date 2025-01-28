from flask import Flask, request, jsonify, send_from_directory
import os
import json
from werkzeug.utils import secure_filename
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Flask alkalmazás inicializálása
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Google Drive hitelesítés
GOOGLE_APPLICATION_CREDENTIALS_JSON = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
if not GOOGLE_APPLICATION_CREDENTIALS_JSON:
    raise RuntimeError("The GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable is not set!")

credentials_info = json.loads(GOOGLE_APPLICATION_CREDENTIALS_JSON)
credentials = Credentials.from_service_account_info(credentials_info, scopes=['https://www.googleapis.com/auth/drive'])
drive_service = build('drive', 'v3', credentials=credentials)

# Google Drive mappa azonosító
DRIVE_FOLDER_ID = '1YD6rjJmPjEXsjuWudNzTIF0p-g3zuT88'


@app.route('/')
def home():
    return '''
    <h1>Google Drive File Upload</h1>
    <form action="/upload" method="post" enctype="multipart/form-data">
        <input type="file" name="file" multiple>
        <button type="submit">Upload</button>
    </form>
    <p><a href="/browse-local">Browse Local Files</a></p>
    <p><a href="/browse-drive">Browse Google Drive Files</a></p>
    '''


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    files = request.files.getlist('file')
    uploaded_files = []

    for file in files:
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            # Fájl feltöltése Google Drive-ra
            file_metadata = {
                'name': filename,
                'parents': [DRIVE_FOLDER_ID]
            }
            media = MediaFileUpload(filepath, resumable=True)
            uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            uploaded_files.append({"filename": filename, "id": uploaded_file.get('id')})
        except Exception as e:
            return jsonify({"error": "Failed to upload file to Google Drive", "details": str(e)}), 500
        finally:
            os.remove(filepath)

    return jsonify({"message": "Files uploaded successfully", "files": uploaded_files})


@app.route('/browse-local', methods=['GET'])
def browse_local_files():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    if not files:
        return '<h1>No files found locally</h1>'

    file_links = [
        f'<li><a href="/files/{file}" download>{file}</a></li>' for file in files
    ]
    return f'''
    <h1>Local Files:</h1>
    <ul>{''.join(file_links)}</ul>
    '''


@app.route('/browse-drive', methods=['GET'])
def browse_drive_files():
    try:
        results = drive_service.files().list(
            q=f"'{DRIVE_FOLDER_ID}' in parents",
            spaces='drive',
            fields='files(id, name)').execute()
        items = results.get('files', [])

        if not items:
            return '<h1>No files found in Google Drive</h1>'

        html = '<h1>Files in Google Drive:</h1><ul>'
        for item in items:
            html += f'<li><a href="https://drive.google.com/file/d/{item["id"]}/view" target="_blank">{item["name"]}</a></li>'
        html += '</ul>'
        return html
    except Exception as e:
        return jsonify({"error": "Failed to retrieve files from Google Drive", "details": str(e)}), 500


@app.route('/files/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
