import os
from flask import Flask, Response, request, send_from_directory, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'recordings'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return "✅ Named SOS Audio Server Running"

@app.route('/upload/<name>', methods=['POST'])
def receive_audio(name):
    if not request.data:
        return "No audio data received", 400

    safe_name = secure_filename(name)
    filename = f"{safe_name}.mp3"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    # Optional: auto-versioning to prevent overwrite
    i = 1
    while os.path.exists(filepath):
        filename = f"{safe_name}_{i}.mp3"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        i += 1

    with open(filepath, 'wb') as f:
        f.write(request.data)

    return f"Saved as {filename}", 200

@app.route('/audio/<name>', methods=['GET'])
def stream_named_audio(name):
    safe_name = secure_filename(name)
    
    # Try with no suffix
    file_path = os.path.join(UPLOAD_FOLDER, f"{safe_name}.mp3")
    if os.path.exists(file_path):
        return send_from_directory(UPLOAD_FOLDER, f"{safe_name}.mp3", mimetype='audio/mpeg')

    # If not found, try suffix versions
    i = 1
    while True:
        filename = f"{safe_name}_{i}.mp3"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(file_path):
            return send_from_directory(UPLOAD_FOLDER, filename, mimetype='audio/mpeg')
        if i > 10:  # max versions to check
            break
        i += 1

    return "Audio file not found", 404

@app.route('/list', methods=['GET'])
def list_audio_files():
    files = sorted(os.listdir(UPLOAD_FOLDER))
    return jsonify(files)

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, threaded=True)
