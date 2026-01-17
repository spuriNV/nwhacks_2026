import cv2

# Use FFMPEG backend with RTP
cap = cv2.VideoCapture("rtp://192.168.137.1:5000", cv2.CAP_FFMPEG)

if not cap.isOpened():
    print("Error: Could not open stream")
    exit()

print("Stream opened successfully!")

while True:
    ret, frame = cap.read()
    
    if not ret:
        print("Error: Failed to read frame")
        break
    
    cv2.imshow('RPi Camera Stream', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()