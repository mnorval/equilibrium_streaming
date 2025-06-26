import os
import io
import threading
from flask import Flask, request, jsonify, send_from_directory, Response
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Manual CORS headers
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

UPLOAD_FOLDER = 'recordings'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Dictionary to store active streams
active_streams = {}
stream_lock = threading.Lock()

class StreamBuffer:
    def __init__(self, name):
        self.name = name
        self.buffer = io.BytesIO()
        self.listeners = []
        self.is_active = True
        self.lock = threading.Lock()
        
    def write_chunk(self, data):
        with self.lock:
            if self.is_active:
                self.buffer.write(data)
                # Notify all listeners
                for listener in self.listeners[:]:  # Copy list to avoid modification issues
                    try:
                        listener.put(data)
                    except:
                        self.listeners.remove(listener)
    
    def add_listener(self, queue):
        with self.lock:
            if self.is_active:
                self.listeners.append(queue)
                return True
        return False
    
    def stop_stream(self):
        with self.lock:
            self.is_active = False
            # Save the complete buffer to file
            if self.buffer.tell() > 0:
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                filename = f"{self.name}_{timestamp}.mp3"
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                
                self.buffer.seek(0)
                with open(filepath, 'wb') as f:
                    f.write(self.buffer.read())
                print(f"[STREAM] Saved stream to {filename}")
                return filename
            return None

@app.route('/')
def index():
    return "✅ SOS Real-time Streaming Server Running"

@app.route('/stream/start/<name>', methods=['POST'])
def start_stream(name):
    """Start a new stream"""
    safe_name = secure_filename(name)
    
    with stream_lock:
        if safe_name in active_streams:
            return f"Stream {safe_name} already active", 409
        
        active_streams[safe_name] = StreamBuffer(safe_name)
        print(f"[STREAM] Started stream: {safe_name}")
    
    return f"Stream {safe_name} started", 200

@app.route('/stream/data/<name>', methods=['POST'])
def stream_data(name):
    """Receive streaming audio data"""
    safe_name = secure_filename(name)
    
    if safe_name not in active_streams:
        return f"Stream {safe_name} not found", 404
    
    if not request.data:
        return "No audio data received", 400
    
    stream_buffer = active_streams[safe_name]
    stream_buffer.write_chunk(request.data)
    
    return "OK", 200

@app.route('/stream/stop/<name>', methods=['POST'])
def stop_stream(name):
    """Stop a stream and save the file"""
    safe_name = secure_filename(name)
    
    with stream_lock:
        if safe_name not in active_streams:
            return f"Stream {safe_name} not found", 404
        
        stream_buffer = active_streams[safe_name]
        filename = stream_buffer.stop_stream()
        del active_streams[safe_name]
        
        print(f"[STREAM] Stopped stream: {safe_name}")
        
        if filename:
            return f"Stream stopped and saved as {filename}", 200
        else:
            return f"Stream stopped (no data to save)", 200

@app.route('/stream/listen/<name>')
def listen_stream(name):
    """Listen to live stream"""
    safe_name = secure_filename(name)
    
    if safe_name not in active_streams:
        return f"Stream {safe_name} not found", 404
    
    import queue
    listener_queue = queue.Queue()
    
    stream_buffer = active_streams[safe_name]
    if not stream_buffer.add_listener(listener_queue):
        return "Stream no longer active", 410
    
    def generate():
        try:
            while stream_buffer.is_active:
                try:
                    # Wait for new data with timeout
                    data = listener_queue.get(timeout=1.0)
                    yield data
                except queue.Empty:
                    # Send keepalive or check if stream is still active
                    if not stream_buffer.is_active:
                        break
                    continue
        except:
            pass
        finally:
            # Remove listener when done
            with stream_buffer.lock:
                if listener_queue in stream_buffer.listeners:
                    stream_buffer.listeners.remove(listener_queue)
    
    return Response(generate(), 
                   mimetype='audio/mpeg',
                   headers={
                       'Cache-Control': 'no-cache',
                       'Connection': 'keep-alive'
                   })

@app.route('/streams', methods=['GET'])
def list_active_streams():
    """List currently active streams"""
    with stream_lock:
        streams = list(active_streams.keys())
    return jsonify(streams)

# Existing endpoints for saved files
@app.route('/audio/<filename>', methods=['GET'])
def stream_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, mimetype='audio/mpeg')

@app.route('/list', methods=['GET'])
def list_all_files():
    """List all saved files in recordings folder"""
    try:
        files = sorted([f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.mp3')])
        print(f"[DEBUG] Found {len(files)} files: {files}")
        return jsonify(files)
    except Exception as e:
        print(f"[ERROR] Error listing files: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/list/<name>', methods=['GET'])
def list_files_by_name(name):
    """List all versions for a given name"""
    safe_name = secure_filename(name)
    matched = sorted(f for f in os.listdir(UPLOAD_FOLDER) if f.startswith(safe_name))
    return jsonify(matched)

@app.route('/names', methods=['GET'])
def list_unique_names():
    """List all unique names"""
    files = os.listdir(UPLOAD_FOLDER)
    base_names = set(f.split('_')[0] for f in files if f.endswith('.mp3'))
    return jsonify(sorted(base_names))

# Legacy upload endpoint for compatibility
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

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, threaded=True)
