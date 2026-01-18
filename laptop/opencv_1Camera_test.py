import cv2
import threading
import time

# ------------------------------
# Camera streams (RTP)
# ------------------------------
streams = {
    "CSI Cam 1": "rtp://192.168.6.2:5000?reuse=1",
    "CSI Cam 2": "rtp://192.168.6.2:5001?reuse=1",
    "USB Cam 3": "rtp://192.168.6.2:5002?reuse=1",
}

frames = {}  # latest frame per camera
locks = {}   # per-camera locks
running = True


# ------------------------------
# Capture thread for each camera
# ------------------------------
def capture_loop(name, url):
    print(f"🔌 Opening {name}...")
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # low-latency

    if not cap.isOpened():
        print(f"❌ Error: Could not open {name}")
        return

    print(f"✅ {name} opened successfully")

    while running:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.01)  # avoid busy-loop
            continue

        with locks[name]:
            frames[name] = frame

    cap.release()
    print(f"🔴 {name} closed")


# ------------------------------
# Start all capture threads
# ------------------------------
threads = []
for name, url in streams.items():
    locks[name] = threading.Lock()
    t = threading.Thread(target=capture_loop, args=(name, url), daemon=True)
    t.start()
    threads.append(t)
    time.sleep(2.0)  # small delay to reduce RTP bind/startup issues

# ------------------------------
# Main display loop
# ------------------------------
while True:
    for name in list(frames.keys()):
        with locks[name]:
            frame = frames.get(name)
        if frame is not None:
            cv2.imshow(name, frame)

    # Quit on 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# ------------------------------
# Cleanup
# ------------------------------
running = False
time.sleep(0.3)
cv2.destroyAllWindows()
print("🛑 Viewer closed")
