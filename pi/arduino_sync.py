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
from elevenlabs import announce_detections


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
        
        self.last_sensor_time = datetime.now(timezone.utc)
        self.last_db_poll_time = datetime.now(timezone.utc)
        self.last_button_count = 0
        
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
        self.arduino.disconnect()
        print("Arduino Sync stopped")

    def _handle_button_press(self):
        """
        Handle button press: fetch latest detections and announce via ElevenLabs.
        """
        print("Button pressed - fetching detections...")
        try:
            # Get latest detections from server
            detections = self.client.get_latest_detections()

            if detections is None:
                print("Could not fetch detections from server")
                return

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
                
                # Upload button presses if count changed
                current_button_count = data['button_presses']
                if current_button_count != self.last_button_count:
                    num_presses = current_button_count - self.last_button_count

                    # Trigger ElevenLabs voice announcement on button press
                    if num_presses > 0:
                        self._handle_button_press()

                    self.client.send_button_press("BUTTON_MAIN", num_presses)
                    self.last_button_count = current_button_count
                
                time.sleep(0.5)  # Update every 500ms
                
            except Exception as e:
                print(f"Error in upload loop: {e}")
                time.sleep(1)

    def _download_loop(self):
        """
        Thread: Periodically poll server for new data and send to Arduino.
        """
        while self.running:
            try:
                current_time = datetime.now(timezone.utc)
                
                # TODO: Replace with actual server API call to fetch latest data
                # Example: server_data = self.client.get_latest_data(since=self.last_db_poll_time)
                # For now, this is a placeholder structure:
                
                # Check if new data exists from server
                # if server_data and server_data.get('timestamp'):
                #     data_timestamp = datetime.fromisoformat(server_data['timestamp'])
                #     
                #     if data_timestamp > self.last_db_poll_time:
                #         # Format and send to Arduino
                #         # Example: camera data as "1,0,1"
                #         camera_data = server_data.get('camera', [0, 0, 0])
                #         message = f"{camera_data[0]},{camera_data[1]},{camera_data[2]}"
                #         self.arduino.write_line(message)
                #         
                #         self.last_db_poll_time = data_timestamp
                
                time.sleep(2)  # Poll every 2 seconds
                
            except Exception as e:
                print(f"Error in download loop: {e}")
                time.sleep(2)
