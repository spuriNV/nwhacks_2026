"""
Arduino-Pi-Server Bidirectional Sync
Reads Arduino sensor data and uploads to server via MongoDB.
Polls server for new data and sends to Arduino on a separate thread.
"""

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
        Handle button press: fetch object names from server, distances from Arduino,
        and announce via ElevenLabs.
        """
        print("Button pressed - fetching detections...")
        try:
            # Get object names from server (cam1, cam2, cam3)
            server_detections = self.client.get_latest_detections()

            if server_detections is None:
                print("Could not fetch detections from server")
                return

            # Get distances from Arduino (in cm, convert to metres)
            arduino_data = self.arduino.get_data()
            distances_cm = arduino_data['distances']  # [dist0, dist1, dist2]

            # Build detections with real distances from Arduino
            # Index mapping: 0=front-left, 1=front-right, 2=back-centre
            detections = []
            for i, server_det in enumerate(server_detections):
                if server_det is not None:
                    object_name = server_det[0]  # Get object name from server
                    distance_m = distances_cm[i] / 100.0  # Convert cm to metres
                    detections.append((object_name, distance_m))
                else:
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
                    
                    # Trigger ElevenLabs voice announcement on button press
                    if num_presses > 0 and num_presses < 2:
                        self._handle_button_press()
                    
                    self.client.send_button_press("BUTTON_MAIN", num_presses)
                    self.last_gpio_button_count = current_gpio_button_count
                
                time.sleep(0.5)  # Update every 500ms
                
            except Exception as e:
                print(f"Error in upload loop: {e}")
                time.sleep(1)

    def _download_loop(self):
        """
        Thread: Poll server for latest detections and send control tuple to Arduino.
        Uses pi_client.get_latest_detections() and maps detection presence to obj flags.
        Control payload: [obj0,obj1,obj2, enable=1, pattern=0]
        """
        while self.running:
            try:
                detections = self.client.get_latest_detections()
                if detections is not None:
                    obj_flags = [1 if d else 0 for d in detections]
                    payload = (*obj_flags, 1, 0)  # enable=1, pattern=0 by default

                    if payload != self.last_control_payload:
                        self.arduino.send_control_command(obj_flags, enable=1, pattern=0)
                        self.last_control_payload = payload

                time.sleep(2)

            except Exception as e:
                print(f"Error in download loop: {e}")
                time.sleep(2)
