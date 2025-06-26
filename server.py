import os
from flask import Flask, Response, request
from queue import Queue
from threading import Lock

app = Flask(__name__)

audio_queue = Queue()
queue_lock = Lock()

@app.route('/')
def index():
    return "SOS Audio Streaming Server is Running"

@app.route('/audio', methods=['GET'])
def audio_feed():
    def stream():
        while True:
            chunk = audio_queue.get()
            if chunk:
                yield chunk

    return Response(stream(), mimetype='audio/mpeg')

@app.route('/upload', methods=['POST'])
def receive_audio():
    chunk = request.data
    if chunk:
        with queue_lock:
            audio_queue.put(chunk)
        return "Chunk received", 200
    return "No data", 400

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, threaded=True)
