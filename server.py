import os
from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)  # ✅ Add this line
UPLOAD_FOLDER = 'recordings'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return "✅ SOS Multi-File Audio Server Running"

@app.route('/upload/<name>', methods=['POST'])
def upload_audio(name):
    if not request.data:
        return "No audio data received", 400

    safe_name = secure_filename(name)
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f"{safe_name}_{timestamp}.mp3"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    with open(filepath, 'wb') as f:
        f.write(request.data)

    return f"Saved as {filename}", 200

@app.route('/audio/<filename>', methods=['GET'])
def stream_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, mimetype='audio/mpeg')

@app.route('/list', methods=['GET'])
def list_all_files():
    """List all files in recordings folder"""
    files = sorted(os.listdir(UPLOAD_FOLDER))
    return jsonify(files)

@app.route('/list/<name>', methods=['GET'])
def list_files_by_name(name):
    """List all versions for a given name"""
    safe_name = secure_filename(name)
    matched = sorted(f for f in os.listdir(UPLOAD_FOLDER) if f.startswith(safe_name))
    return jsonify(matched)

@app.route('/names', methods=['GET'])
def list_unique_names():
    """List all unique names (X12345, X54321, etc.)"""
    files = os.listdir(UPLOAD_FOLDER)
    base_names = set(f.split('_')[0] for f in files if f.endswith('.mp3'))
    return jsonify(sorted(base_names))

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, threaded=True)
