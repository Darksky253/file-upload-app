from flask import Flask, request, jsonify, send_from_directory
import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Flask alkalmazás inicializálása
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
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

# Google Drive mappa azonosítója
DRIVE_FOLDER_ID = '<1YD6rjJmPjEXsjuWudNzTIF0p-g3zuT88>'  # Cseréld ki a saját mappa azonosítódra!


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
        return jsonify({"error": "No file part"})
    files = request.files.getlist('file')  # Több fájl kezelése
    uploaded_files = []

    for file in files:
        if file.filename == '':
            return jsonify({"error": "No selected file"})

        # Helyi fájl mentése ideiglenesen
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

        # Fájl feltöltése Google Drive-ra
        file_metadata = {
            'name': file.filename,
            'parents': [DRIVE_FOLDER_ID]
        }
        media = MediaFileUpload(filepath, resumable=True)
        uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        uploaded_files.append({"filename": file.filename, "id": uploaded_file.get('id')})

        # Helyi fájl törlése
        os.remove(filepath)

    return jsonify({"message": "Files uploaded successfully to Google Drive", "files": uploaded_files})


# Fájlok listázása JSON-ben (Google Drive mappa tartalma nem látható itt, csak feltöltési mappa)
@app.route('/list-files', methods=['GET'])
def list_files():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    return jsonify({"files": files})


# Böngészhető fájlfelület (csak helyi fájlok, Drive-ra feltöltöttek külön keresendők)
@app.route('/browse', methods=['GET'])
def browse_files():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    file_links = [
        f'<li><a href="/files/{file}" download>{file}</a></li>' for file in files
    ]
    return f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>File Browser</title>
    </head>
    <body>
        <h1>Uploaded Files</h1>
        <ul>
            {''.join(file_links)}
        </ul>
    </body>
    </html>
    '''


# Fájl letöltése helyi mappából
@app.route('/files/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


# Flask szerver indítása
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
