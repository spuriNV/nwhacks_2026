import os
os.environ['PATH'] += r";C:\Program Files\GStreamer\1.0\msvc_x86_64\bin"
import cv2

# Replace with your Windows GStreamer bin path if needed
pipeline = (
    'udpsrc port=5000 caps="application/x-rtp,media=video,encoding-name=JPEG,payload=26" ! '
    'rtpjpegdepay ! jpegdec ! videoconvert ! appsink'
)

cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
if not cap.isOpened():
    raise RuntimeError("Failed to open video stream")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Flip upside down if needed
    # frame = cv2.flip(frame, -1)  # -1 flips both vertically and horizontally

    # Example processing: convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Show the frame
    cv2.imshow("Camera 1", gray)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
