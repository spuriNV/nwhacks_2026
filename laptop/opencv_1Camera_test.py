import cv2
import threading
import time
import socket
import json
import base64
from pathlib import Path
from datetime import datetime, timezone
from flask import Flask, render_template, Response, request, jsonify
from flask_socketio import SocketIO

# ------------------------------
# YOLO Configuration
# ------------------------------
ENABLE_YOLO = True
MODEL_PATH = Path(__file__).parent / "models" / "yolo11n.pt"
CONFIDENCE_THRESHOLD = 0.75

# ------------------------------
# MongoDB Configuration
# ------------------------------
ENABLE_MONGODB = True
MONGO_SAVE_INTERVAL = 1.0  # Save detections every N seconds (avoid flooding DB)

# COCO class IDs for desired objects
ALLOWED_CLASSES = {
    0: "person",
    24: "backpack",
    26: "handbag",
    39: "bottle",
    56: "chair",
    60: "dining table",
    62: "tv",
    63: "laptop",
    67: "cell phone",
}

# ------------------------------
# Web Server Configuration
# ------------------------------
WEB_HOST = "0.0.0.0"
WEB_PORT = 5050

# ------------------------------
# Camera streams (RTP)
# ------------------------------
streams = {
    "cam1": ("rtp://0.0.0.0:5000", 5000, "CSI Cam 1"),
    "cam2": ("rtp://0.0.0.0:5002", 5002, "CSI Cam 2"),
    "cam3": ("rtp://0.0.0.0:5004", 5004, "USB Cam 3"),
}

frames = {}           # Raw frames per camera
detections = {}       # YOLO detections per camera (bounding boxes, not annotated frames)
locks = {}
detection_locks = {}
running = True

# MongoDB client
mongo_client = None
if ENABLE_MONGODB:
    try:
        from db import get_mongo_client
        mongo_client = get_mongo_client()
        print("MongoDB connected")
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        ENABLE_MONGODB = False

# Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'camera-stream-secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')


def check_port_available(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(('0.0.0.0', port))
        sock.close()
        return True, None
    except OSError as e:
        return False, str(e)


def capture_loop(cam_id, url, port, display_name):
    print(f"[{display_name}] Starting capture thread...")

    available, error = check_port_available(port)
    if not available:
        print(f"   [{display_name}] Port {port}: ALREADY IN USE - {error}")
    else:
        print(f"   [{display_name}] Port {port}: available")

    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        print(f"[{display_name}] Error: Could not open stream")
        return

    print(f"[{display_name}] Opened successfully")

    frame_count = 0
    last_status_time = time.time()

    while running:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.01)
            continue

        frame_count += 1
        with locks[cam_id]:
            frames[cam_id] = frame

        if time.time() - last_status_time > 5.0:
            print(f"   [{display_name}] Frames captured: {frame_count}")
            last_status_time = time.time()

    cap.release()
    print(f"[{display_name}] Closed")


def yolo_loop(cam_id, display_name, model):
    print(f"   [YOLO-{display_name}] Started")

    frame_count = 0
    last_fps_time = time.time()
    fps_frame_count = 0
    last_mongo_save = time.time()
    mongo_save_count = 0

    while running:
        with locks[cam_id]:
            frame = frames.get(cam_id)

        if frame is None:
            time.sleep(0.005)
            continue

        # Run YOLO inference
        results = model(
            frame,
            conf=CONFIDENCE_THRESHOLD,
            classes=list(ALLOWED_CLASSES.keys()),
            verbose=False,
        )

        # Extract detection data (not the annotated image)
        detection_data = []
        if results[0].boxes is not None:
            boxes = results[0].boxes
            for i in range(len(boxes)):
                box = boxes[i]
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                cls_name = ALLOWED_CLASSES.get(cls_id, f"class_{cls_id}")

                detection_data.append({
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "confidence": conf,
                    "class_id": cls_id,
                    "class_name": cls_name,
                })

        # Store detections for web broadcast
        with detection_locks[cam_id]:
            detections[cam_id] = detection_data

        # Save to MongoDB at configured interval
        if ENABLE_MONGODB and mongo_client and detection_data:
            if time.time() - last_mongo_save >= MONGO_SAVE_INTERVAL:
                try:
                    timestamp = datetime.now(timezone.utc)
                    mongo_docs = []
                    for det in detection_data:
                        mongo_docs.append({
                            "object_name": det["class_name"],
                            "accuracy": det["confidence"],
                            "camera_id": cam_id,
                            "bounding_box": {
                                "x1": det["x1"],
                                "y1": det["y1"],
                                "x2": det["x2"],
                                "y2": det["y2"]
                            },
                            "timestamp": timestamp
                        })
                    mongo_client.insert_yolo_detections_batch(mongo_docs)
                    mongo_save_count += len(mongo_docs)
                    last_mongo_save = time.time()
                except Exception as e:
                    print(f"   [YOLO-{display_name}] MongoDB save error: {e}")

        frame_count += 1
        fps_frame_count += 1

        elapsed = time.time() - last_fps_time
        if elapsed > 5.0:
            fps = fps_frame_count / elapsed
            print(f"   [YOLO-{display_name}] FPS: {fps:.1f}, Detections: {len(detection_data)}, Saved to DB: {mongo_save_count}")
            fps_frame_count = 0
            last_fps_time = time.time()

    print(f"[YOLO-{display_name}] Stopped")


def generate_mjpeg(cam_id):
    """Generate MJPEG stream for a camera."""
    while running:
        with locks[cam_id]:
            frame = frames.get(cam_id)

        if frame is None:
            time.sleep(0.01)
            continue

        # Encode frame as JPEG
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

        time.sleep(0.033)  # ~30 FPS


def broadcast_detections():
    """Broadcast YOLO detections to all connected clients."""
    while running:
        all_detections = {}
        for cam_id in streams.keys():
            with detection_locks[cam_id]:
                all_detections[cam_id] = detections.get(cam_id, [])

        socketio.emit('detections', all_detections)
        time.sleep(0.05)  # 20 updates per second


# ------------------------------
# Flask Routes
# ------------------------------
@app.route('/')
def index():
    return render_template('index.html', cameras=streams)


@app.route('/video/<cam_id>')
def video_feed(cam_id):
    if cam_id not in streams:
        return "Camera not found", 404
    return Response(
        generate_mjpeg(cam_id),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/detections/<cam_id>')
def get_detections(cam_id):
    if cam_id not in streams:
        return json.dumps({"error": "Camera not found"}), 404
    with detection_locks[cam_id]:
        return json.dumps(detections.get(cam_id, []))


# ------------------------------
# API Routes for Raspberry Pi
# ------------------------------
def parse_timestamp(ts_string):
    """Parse ISO format timestamp string to datetime object."""
    if not ts_string:
        return None
    try:
        # Handle ISO format with or without timezone
        if ts_string.endswith('Z'):
            ts_string = ts_string[:-1] + '+00:00'
        return datetime.fromisoformat(ts_string)
    except (ValueError, TypeError):
        return None


@app.route('/api/interaction', methods=['POST'])
def post_interaction():
    """
    Receive interaction data (button presses, vibration) from Raspberry Pi.

    Expected JSON body:
    {
        "button_id": "BTN_A",        # optional
        "num_presses": 3,            # optional, defaults to 1
        "vibration_id": "VIB_1",     # optional
        "vibration_level": 75,       # optional, 0-100
        "timestamp": "2024-01-17T12:30:00Z"  # optional, ISO format
    }
    """
    if not ENABLE_MONGODB or not mongo_client:
        return jsonify({"error": "MongoDB not connected"}), 503

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        # Parse timestamp if provided
        timestamp = parse_timestamp(data.get("timestamp"))

        # Insert interaction into MongoDB
        interaction_id = mongo_client.insert_interaction(
            button_id=data.get("button_id"),
            num_presses=data.get("num_presses"),
            vibration_id=data.get("vibration_id"),
            vibration_level=data.get("vibration_level"),
            timestamp=timestamp
        )

        print(f"[API] Received interaction: {data}")
        return jsonify({"success": True, "id": interaction_id}), 201

    except Exception as e:
        print(f"[API] Error saving interaction: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/vibration', methods=['POST'])
def post_vibration():
    """
    Simplified endpoint for vibration data only.

    Expected JSON body:
    {
        "vibration_id": "VIB_1",
        "vibration_level": 75,
        "timestamp": "2024-01-17T12:30:00Z"  # optional, ISO format
    }
    """
    if not ENABLE_MONGODB or not mongo_client:
        return jsonify({"error": "MongoDB not connected"}), 503

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        vibration_id = data.get("vibration_id", "VIB_DEFAULT")
        vibration_level = data.get("vibration_level", 0)
        timestamp = parse_timestamp(data.get("timestamp"))

        interaction_id = mongo_client.insert_interaction(
            vibration_id=vibration_id,
            vibration_level=vibration_level,
            timestamp=timestamp
        )

        print(f"[API] Received vibration: id={vibration_id}, level={vibration_level}")
        return jsonify({"success": True, "id": interaction_id}), 201

    except Exception as e:
        print(f"[API] Error saving vibration: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/button', methods=['POST'])
def post_button():
    """
    Simplified endpoint for button press data only.

    Expected JSON body:
    {
        "button_id": "BTN_A",
        "num_presses": 3,
        "timestamp": "2024-01-17T12:30:00Z"  # optional, ISO format
    }
    """
    if not ENABLE_MONGODB or not mongo_client:
        return jsonify({"error": "MongoDB not connected"}), 503

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        button_id = data.get("button_id", "BTN_DEFAULT")
        num_presses = data.get("num_presses", 1)
        timestamp = parse_timestamp(data.get("timestamp"))

        interaction_id = mongo_client.insert_interaction(
            button_id=button_id,
            num_presses=num_presses,
            timestamp=timestamp
        )

        print(f"[API] Received button press: id={button_id}, presses={num_presses}")
        return jsonify({"success": True, "id": interaction_id}), 201

    except Exception as e:
        print(f"[API] Error saving button press: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for the Pi to verify connectivity."""
    return jsonify({
        "status": "ok",
        "mongodb": ENABLE_MONGODB and mongo_client is not None,
        "yolo": ENABLE_YOLO and model is not None
    })


# ------------------------------
# Initialize YOLO
# ------------------------------
model = None
if ENABLE_YOLO:
    print("=" * 50)
    print("YOLO Setup")
    print("=" * 50)

    try:
        from ultralytics import YOLO
        import torch

        print(f"CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"GPU: {torch.cuda.get_device_name(0)}")

        if MODEL_PATH.exists():
            model = YOLO(MODEL_PATH)
        else:
            print(f"Downloading model...")
            model = YOLO("yolo11n.pt")

        model.to('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Model loaded on: {'CUDA' if torch.cuda.is_available() else 'CPU'}")

        # Warm up
        import numpy as np
        dummy = np.zeros((480, 640, 3), dtype=np.uint8)
        for _ in range(3):
            model(dummy, verbose=False)
        print("Model ready")

    except Exception as e:
        print(f"YOLO setup failed: {e}")
        ENABLE_YOLO = False


# ------------------------------
# Main
# ------------------------------
def main():
    global running

    # Create templates folder and HTML file
    templates_dir = Path(__file__).parent / "templates"
    templates_dir.mkdir(exist_ok=True)

    html_content = '''<!DOCTYPE html>
<html>
<head>
    <title>Camera Streams</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: Arial, sans-serif;
            background: #1a1a2e;
            color: white;
            min-height: 100vh;
        }
        h1 {
            text-align: center;
            padding: 20px;
            background: #16213e;
        }
        .container {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 20px;
            padding: 20px;
        }
        .camera-box {
            background: #16213e;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .camera-header {
            padding: 10px 15px;
            background: #0f3460;
            font-weight: bold;
        }
        .camera-wrapper {
            position: relative;
            width: 640px;
            height: 480px;
        }
        .camera-wrapper img {
            width: 100%;
            height: 100%;
            object-fit: contain;
            background: #000;
        }
        .overlay {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
        }
        .controls {
            text-align: center;
            padding: 20px;
            background: #16213e;
        }
        .controls button {
            padding: 10px 20px;
            margin: 5px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        .controls button.active {
            background: #e94560;
            color: white;
        }
        .controls button:not(.active) {
            background: #0f3460;
            color: white;
        }
        .stats {
            text-align: center;
            padding: 10px;
            font-size: 14px;
            color: #888;
        }
    </style>
</head>
<body>
    <h1>Camera Streams with YOLO Detection</h1>

    <div class="controls">
        <button id="toggleYolo" class="active" onclick="toggleYolo()">YOLO Overlay: ON</button>
    </div>

    <div class="container">
        {% for cam_id, (url, port, name) in cameras.items() %}
        <div class="camera-box">
            <div class="camera-header">{{ name }}</div>
            <div class="camera-wrapper">
                <img id="img-{{ cam_id }}" src="/video/{{ cam_id }}" alt="{{ name }}">
                <canvas id="canvas-{{ cam_id }}" class="overlay" width="640" height="480"></canvas>
            </div>
        </div>
        {% endfor %}
    </div>

    <div class="stats" id="stats">Connecting...</div>

    <script>
        const socket = io();
        let showYolo = true;
        let detectionCounts = {};

        // Color map for different classes
        const classColors = {
            'person': '#e94560',
            'backpack': '#0f3460',
            'handbag': '#533483',
            'bottle': '#00b4d8',
            'chair': '#06d6a0',
            'dining table': '#ffd166',
            'tv': '#ef476f',
            'laptop': '#118ab2',
            'cell phone': '#073b4c',
        };

        function getColor(className) {
            return classColors[className] || '#ffffff';
        }

        socket.on('connect', () => {
            document.getElementById('stats').textContent = 'Connected';
        });

        socket.on('disconnect', () => {
            document.getElementById('stats').textContent = 'Disconnected';
        });

        socket.on('detections', (data) => {
            if (!showYolo) return;

            for (const [camId, detections] of Object.entries(data)) {
                drawDetections(camId, detections);
                detectionCounts[camId] = detections.length;
            }

            // Update stats
            const total = Object.values(detectionCounts).reduce((a, b) => a + b, 0);
            document.getElementById('stats').textContent =
                `Total detections: ${total} | ` +
                Object.entries(detectionCounts).map(([k, v]) => `${k}: ${v}`).join(' | ');
        });

        function drawDetections(camId, detections) {
            const canvas = document.getElementById('canvas-' + camId);
            const img = document.getElementById('img-' + camId);
            if (!canvas || !img) return;

            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // Get actual image dimensions for scaling
            const scaleX = canvas.width / 640;
            const scaleY = canvas.height / 480;

            for (const det of detections) {
                const x1 = det.x1 * scaleX;
                const y1 = det.y1 * scaleY;
                const x2 = det.x2 * scaleX;
                const y2 = det.y2 * scaleY;
                const width = x2 - x1;
                const height = y2 - y1;

                const color = getColor(det.class_name);

                // Draw box
                ctx.strokeStyle = color;
                ctx.lineWidth = 2;
                ctx.strokeRect(x1, y1, width, height);

                // Draw label background
                const label = `${det.class_name} ${(det.confidence * 100).toFixed(0)}%`;
                ctx.font = '14px Arial';
                const textWidth = ctx.measureText(label).width;

                ctx.fillStyle = color;
                ctx.fillRect(x1, y1 - 20, textWidth + 10, 20);

                // Draw label text
                ctx.fillStyle = 'white';
                ctx.fillText(label, x1 + 5, y1 - 5);
            }
        }

        function toggleYolo() {
            showYolo = !showYolo;
            const btn = document.getElementById('toggleYolo');
            btn.textContent = 'YOLO Overlay: ' + (showYolo ? 'ON' : 'OFF');
            btn.className = showYolo ? 'active' : '';

            // Clear all canvases if YOLO is off
            if (!showYolo) {
                document.querySelectorAll('.overlay').forEach(canvas => {
                    const ctx = canvas.getContext('2d');
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                });
            }
        }
    </script>
</body>
</html>'''

    with open(templates_dir / "index.html", "w") as f:
        f.write(html_content)

    print("\n" + "=" * 50)
    print("Starting camera capture threads...")
    print("=" * 50)

    # Start capture threads
    for cam_id, (url, port, display_name) in streams.items():
        locks[cam_id] = threading.Lock()
        detection_locks[cam_id] = threading.Lock()
        t = threading.Thread(target=capture_loop, args=(cam_id, url, port, display_name), daemon=True)
        t.start()
        time.sleep(3.0)

    # Start YOLO threads
    if ENABLE_YOLO and model is not None:
        print("\n" + "=" * 50)
        print("Starting YOLO inference threads...")
        print("=" * 50)

        for cam_id, (_, _, display_name) in streams.items():
            t = threading.Thread(target=yolo_loop, args=(cam_id, display_name, model), daemon=True)
            t.start()
            time.sleep(0.2)

        # Start detection broadcast thread
        t = threading.Thread(target=broadcast_detections, daemon=True)
        t.start()

    print("\n" + "=" * 50)
    print(f"Web server starting at http://{WEB_HOST}:{WEB_PORT}")
    print("=" * 50)

    try:
        socketio.run(app, host=WEB_HOST, port=WEB_PORT, debug=False, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        pass
    finally:
        running = False
        print("Shutting down...")


if __name__ == "__main__":
    main()
