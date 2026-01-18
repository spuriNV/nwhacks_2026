import cv2
import threading
import time
import socket

# ------------------------------
# Camera streams (RTP)
# Listen on local ports - the Jetson sends TO these ports
# NOTE: RTP uses port pairs (data + RTCP control on next port)
#       So port 5000 also uses 5001, port 5002 also uses 5003, etc.
#       Use even ports spaced at least 2 apart to avoid conflicts.
# ------------------------------
streams = {
    "CSI Cam 1": ("rtp://0.0.0.0:5000", 5000),  # uses 5000 + 5001
    "CSI Cam 2": ("rtp://0.0.0.0:5002", 5002),  # uses 5002 + 5003
    "USB Cam 3": ("rtp://0.0.0.0:5004", 5004),  # uses 5004 + 5005
}

frames = {}  # latest frame per camera
locks = {}   # per-camera locks
running = True


def check_port_available(port):
    """Check if a UDP port is available for binding."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(('0.0.0.0', port))
        sock.close()
        return True, None
    except OSError as e:
        return False, str(e)


# ------------------------------
# Capture thread for each camera
# ------------------------------
def capture_loop(name, url, port):
    print(f"🔌 [{name}] Starting capture thread...")
    print(f"   [{name}] URL: {url}")
    print(f"   [{name}] Port: {port}")

    # Check if port is available before trying to open
    available, error = check_port_available(port)
    if not available:
        print(f"   [{name}] ⚠️  Port {port} check: ALREADY IN USE - {error}")
    else:
        print(f"   [{name}] ✓ Port {port} check: available")

    print(f"   [{name}] Creating VideoCapture...")
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    print(f"   [{name}] Setting buffer size...")
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # low-latency

    if not cap.isOpened():
        print(f"❌ [{name}] Error: Could not open stream")
        print(f"   [{name}] isOpened() returned False")
        return

    print(f"✅ [{name}] Opened successfully")
    print(f"   [{name}] Resolution: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
    print(f"   [{name}] FPS: {cap.get(cv2.CAP_PROP_FPS)}")

    frame_count = 0
    error_count = 0
    last_status_time = time.time()

    while running:
        ret, frame = cap.read()
        if not ret:
            error_count += 1
            if error_count % 100 == 1:  # Print every 100 errors
                print(f"   [{name}] Read failed (error #{error_count})")
            time.sleep(0.01)  # avoid busy-loop
            continue

        frame_count += 1
        with locks[name]:
            frames[name] = frame

        # Print status every 5 seconds
        if time.time() - last_status_time > 5.0:
            print(f"   [{name}] Frames received: {frame_count}, Errors: {error_count}")
            last_status_time = time.time()

    cap.release()
    print(f"🔴 [{name}] Closed - Total frames: {frame_count}, Total errors: {error_count}")


# ------------------------------
# Start all capture threads
# ------------------------------
print("=" * 50)
print("Starting camera capture threads...")
print("=" * 50)

threads = []
for name, (url, port) in streams.items():
    print(f"\n>>> Launching thread for {name}")
    locks[name] = threading.Lock()
    t = threading.Thread(target=capture_loop, args=(name, url, port), daemon=True)
    t.start()
    threads.append(t)
    print(f">>> Waiting 3 seconds before next camera...")
    time.sleep(3.0)  # increased delay to let each stream fully initialize

print("\n" + "=" * 50)
print("All capture threads launched")
print("=" * 50)

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
