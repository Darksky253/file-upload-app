from flask import Flask, request, jsonify, send_from_directory
import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Flask alkalmazás inicializálása
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'  # Lokális mappa feltöltött fájlokhoz
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Google Drive hitelesítés környezeti változóból
GOOGLE_APPLICATION_CREDENTIALS_JSON = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
if not GOOGLE_APPLICATION_CREDENTIALS_JSON:
    raise RuntimeError("The GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable is not set!")

credentials_info = json.loads(GOOGLE_APPLICATION_CREDENTIALS_JSON)
credentials = Credentials.from_service_account_info(credentials_info, scopes=['https://www.googleapis.com/auth/drive'])

# Google Drive API kapcsolat
drive_service = build('drive', 'v3', credentials=credentials)

# Google Drive mappa azonosítója (cseréld ki a sajátodra!)
DRIVE_FOLDER_ID = '1YD6rjJmPjEXsjuWudNzTIF0p-g3zuT88'


# Főoldal (feltöltési űrlap)
@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>File Upload</title>
    </head>
    <body>
        <h1>Upload Files</h1>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="file" multiple>
            <button type="submit">Upload</button>
        </form>
        <p><a href="/browse">Browse Uploaded Files</a></p>
    </body>
    </html>
    '''


# Fájlok feltöltése Google Drive-ra
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    files = request.files.getlist('file')  # Több fájl kezelése
    uploaded_files = []

    for file in files:
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # Helyi fájl mentése ideiglenesen
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Fájl feltöltése Google Drive-ra
        try:
            file_metadata = {
                'name': filename,
                'parents': [DRIVE_FOLDER_ID]
            }
            media = MediaFileUpload(filepath, resumable=True)
            uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            uploaded_files.append({"filename": filename, "id": uploaded_file.get('id')})
        except Exception as e:
            print(f"Error uploading file to Google Drive: {e}")
            return jsonify({"error": "Failed to upload file to Google Drive", "details": str(e)}), 500
        finally:
            os.remove(filepath)

    return jsonify({"message": "Files uploaded successfully to Google Drive", "files": uploaded_files})


# Fájlok listázása Google Drive mappából
@app.route('/browse', methods=['GET'])
def browse_files():
    try:
        results = drive_service.files().list(
            q=f"'{DRIVE_FOLDER_ID}' in parents",
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        items = results.get('files', [])

        if not items:
            return '<h1>No files found in the Google Drive folder</h1>'

        # Fájlok listázása HTML-ben
        html = '<h1>Uploaded Files:</h1><ul>'
        for item in items:
            file_link = f'https://drive.google.com/file/d/{item["id"]}/view'
            html += f'<li><a href="{file_link}" target="_blank">{item["name"]}</a></li>'
        html += '</ul>'
        return html
    except Exception as e:
        return jsonify({"error": "Failed to retrieve files from Google Drive", "details": str(e)}), 500


# Fájl letöltése helyi mappából
@app.route('/files/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


# Flask szerver indítása
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
