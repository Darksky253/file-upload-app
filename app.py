from flask import Flask, request, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename

# Flask alkalmazás inicializálása
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'  # Lokális mappa feltöltött fájlokhoz
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


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


# Fájlok feltöltése helyi mappába
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    files = request.files.getlist('file')  # Több fájl kezelése
    uploaded_files = []

    for file in files:
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # Fájl mentése a lokális mappába
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        uploaded_files.append({"filename": filename})

    return jsonify({"message": "Files uploaded successfully", "files": uploaded_files})


# Lokális fájlok böngészése
@app.route('/browse', methods=['GET'])
def browse_files():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    if not files:
        return '<h1>No files found</h1>'

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
@app.route('/files/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


# Flask szerver indítása
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
