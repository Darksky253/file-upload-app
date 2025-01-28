from flask import Flask, request, jsonify, send_from_directory
import os

# Flask app inicializálása
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Feltöltési mappa létrehozása
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

# Fájlok feltöltése
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"})
    files = request.files.getlist('file')  # Több fájl támogatása
    saved_files = []
    for file in files:
        if file.filename == '':
            return jsonify({"error": "No selected file"})
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        saved_files.append(file.filename)
    return jsonify({"message": "Files uploaded successfully", "files": saved_files})

# Fájlok listázása JSON-ben
@app.route('/list-files', methods=['GET'])
def list_files():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    return jsonify({"files": files})

# Böngészhető fájlfelület
@app.route('/browse', methods=['GET'])
def browse_files():
    files = os.listdir(app.config['UPLOAD_FOLDER'])  # Mappa tartalma
    file_links = [
        f'<li><a href="/files/{file}" download>{file}</a></li>' for file in files
    ]  # Letöltési linkek generálása
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
            {''.join(file_links)}  <!-- Letöltési linkek beszúrása -->
        </ul>
    </body>
    </html>
    '''

# Fájl letöltése
@app.route('/files/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# Flask szerver indítása
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
