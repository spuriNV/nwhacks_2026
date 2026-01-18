"""
Arduino-Pi-Server Bidirectional Sync
Reads Arduino sensor data and uploads to server via MongoDB.
Polls server for new data and sends to Arduino on a separate thread.
"""

from csv import reader
import threading
import time
from datetime import datetime, timezone
from arduinoSerial import ArduinoSerialReader
from pi_client import LaptopClient
from button import Button
from elevenlabs_tts import announce_detections


class ArduinoSync:
    def __init__(self, port='/dev/ttyACM0', baudrate=115200, 
                 server_url="http://192.168.6.1:5050"):
        """
        Initialize the Arduino-Server sync.
        
        Args:
            port: Serial port for Arduino (default: /dev/ttyACM0 for Raspberry Pi)
            baudrate: Serial baud rate (default: 115200)
            server_url: Base URL for the laptop server
        """
        self.arduino = ArduinoSerialReader(port=port, baudrate=baudrate)
        self.client = LaptopClient(base_url=server_url)
        self.button = Button(pin=25, debounce_ms=20)
        
        self.last_gpio_button_count = 0
        self.last_control_payload = None  # track last sent control tuple
        self.vibration_enabled = True  # toggle via double press
        self.vibration_pattern = 0  # cycle 0-3 via triple press
        self.last_button_press_time = 0  # for multi-press detection
        self.double_press_timeout = 0.5  # 500ms window for multi-press
        
        self.running = False
        self.upload_thread = None
        self.download_thread = None

    def start(self):
        """Start both upload and download threads."""
        self.running = True
        self.arduino.connect()
        
        if not self.arduino.ser:
            print("Failed to connect to Arduino")
            return False
        
        # Verify server connection
        if not self.client.check_connection():
            print("Warning: Cannot reach server, but continuing...")
        
        # Start button monitor
        self.button.start()
        
        # Start threads
        self.upload_thread = threading.Thread(target=self._upload_loop, daemon=True)
        self.download_thread = threading.Thread(target=self._download_loop, daemon=True)
        
        self.upload_thread.start()
        self.download_thread.start()
        
        print("Arduino Sync started. Press Ctrl+C to stop.")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping Arduino Sync...")
            self.stop()

    def stop(self):
        """Stop all threads and disconnect."""
        self.running = False
        if self.upload_thread:
            self.upload_thread.join(timeout=2)
        if self.download_thread:
            self.download_thread.join(timeout=2)
        self.button.stop()
        self.arduino.disconnect()
        print("Arduino Sync stopped")

    def _handle_button_press(self):
        """
        Handle button press: fetch object names and camera_ids from server,
        distances from Arduino, and announce via ElevenLabs.
        """
        print("Button pressed - fetching detections...")
        try:
            # Get object names and camera_ids from server
            # Returns: [(object_name, camera_id), None, ...]
            server_detections = self.client.get_latest_detections()
            print(f"[DEBUG] Server detections: {server_detections}")

            if server_detections is None:
                print("Could not fetch detections from server")
                return

            data = self.arduino.get_data()
            if not data:
                print("No Arduino data available")
                return

            d = data['distances']
            distances_cm = d
            l = data['levels']

            print(f"Distances (cm): [{d[0]:4}, {d[1]:4}, {d[2]:4}] | Levels: {l}")

            # Map camera_id to Arduino distance index
            # Configure this based on your wiring!
            # Supports both string ("cam1") and numeric (1, 1.0) camera IDs
            # 1 = back, 2 = front-left, 3 = front-right
            CAMERA_TO_ARDUINO_INDEX = {
                "cam1": 2,
                "cam2": 0,
                "cam3": 1,
            }

            # Build detections with camera_id and distance
            # Format for elevenlabs: [(object_name, camera_id, distance_m), ...]
            detections = []
            for i, server_det in enumerate(server_detections):
                if server_det is not None:
                    object_name, camera_id = server_det
                    arduino_idx = CAMERA_TO_ARDUINO_INDEX.get(camera_id, 0)
                    print(f"[DEBUG] Mapping camera_id {camera_id} to Arduino index {arduino_idx}")
                    distance_cm = distances_cm[arduino_idx]
                    print(f"[DEBUG] Detection {i}: obj={object_name}, camera_id={camera_id} -> arduino_idx={arduino_idx}, distance={distance_cm}cm ({distance_cm:.2f}cm)")
                    detections.append((object_name, camera_id, distance_cm))
                else:
                    print(f"[DEBUG] Detection {i}: None")
                    detections.append(None)

            # Check if there are any detections
            has_detections = any(d is not None for d in detections)
            if not has_detections:
                print("No objects detected by cameras")
                return

            # Announce detections via ElevenLabs TTS
            print(f"Announcing detections: {detections}")
            announce_detections(detections)

        except Exception as e:
            print(f"Error handling button press: {e}")

    def _upload_loop(self):
        """
        Thread: Continuously read Arduino data and upload to server.
        """
        while self.running:
            try:
                # Read new data from Arduino
                self.arduino.read_and_parse()
                data = self.arduino.get_data()
                
                # Upload sensor distances and levels
                for i in range(3):
                    vibration_id = f"VIB_{i}"
                    vibration_level = data['levels'][i]
                    self.client.send_vibration(vibration_id, vibration_level * 85)
                
                # Upload GPIO button presses if count changed
                current_gpio_button_count = self.button.get_press_count()
                if current_gpio_button_count != self.last_gpio_button_count:
                    num_presses = current_gpio_button_count - self.last_gpio_button_count
                    
                    # Detect multi-press within timeout window
                    current_time = time.time()
                    if (current_time - self.last_button_press_time) < self.double_press_timeout:
                        # Triple press: cycle pattern 0->1->2->3->0
                        if num_presses == 3:
                            self.vibration_pattern = (self.vibration_pattern + 1) % 4
                            print(f"Triple press detected! Pattern cycled to: {self.vibration_pattern}")
                        # Double press: toggle vibration enable
                        elif num_presses == 2:
                            self.vibration_enabled = not self.vibration_enabled
                            print(f"Double press detected! Vibration toggled: {self.vibration_enabled}")
                    elif num_presses == 1:
                        # Single press: announce detections
                        self._handle_button_press()
                    
                    self.last_button_press_time = current_time
                    self.client.send_button_press("BUTTON_MAIN", num_presses)
                    self.last_gpio_button_count = current_gpio_button_count
                
                time.sleep(0.5)  # Update every 500ms
                
            except Exception as e:
                print(f"Error in upload loop: {e}")
                time.sleep(1)

    def _download_loop(self):
        """
        Thread: Poll server for latest detections and send control tuple to Arduino.
        Single press: announce detections
        Double press: toggles vibration_enabled boolean
        Triple press: cycles vibration_pattern 0->1->2->3->0
        Control payload: [obj0,obj1,obj2, enable, pattern]
        """
        while self.running:
            try:
                detections = self.client.get_latest_detections()
                if detections is not None:
                    obj_flags = [1 if d else 0 for d in detections]
                    enable = 1 if self.vibration_enabled else 0
                    payload = (*obj_flags, enable, self.vibration_pattern)

                    if payload != self.last_control_payload:
                        self.arduino.send_control_command(obj_flags, enable=enable, pattern=self.vibration_pattern)
                        self.last_control_payload = payload

                time.sleep(2)

            except Exception as e:
                print(f"Error in download loop: {e}")
                time.sleep(2)
