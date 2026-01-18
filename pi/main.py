"""
Main integration script for Pi-based sensor system.
Handles Arduino communication, data transmission to laptop database,
camera data retrieval from MongoDB, and feedback to Arduino.
"""

import time
import threading
from datetime import datetime
from typing import List, Dict, Optional
from getSerialData import ArduinoSerial
from sendData import ArduinoDataSender
from serverUDP import (
    get_recent_objects,
    get_latest_detections,
    get_high_accuracy_objects
)
from pymongo import MongoClient


class SensorIntegrationSystem:
    """
    Main system that integrates Arduino sensors, database communication,
    and camera detection feedback.
    """

    def __init__(
        self,
        arduino_port: str = '/dev/ttyACM0',
        server_url: str = 'http://192.168.1.100:3000',  # Laptop IP
        mongo_host: str = '192.168.1.100',  # Laptop IP
        mongo_port: int = 27017,
        database_name: str = 'your_database_name'
    ):
        """
        Initialize the integration system.

        Args:
            arduino_port: Serial port for Arduino
            server_url: URL of the laptop server
            mongo_host: MongoDB host (laptop IP)
            mongo_port: MongoDB port
            database_name: Name of the MongoDB database
        """
        # Arduino communication
        self.arduino = ArduinoSerial(port=arduino_port)

        # Data sender to laptop
        self.data_sender = ArduinoDataSender(server_url)

        # MongoDB connection for camera data
        self.mongo_client = MongoClient(f'mongodb://{mongo_host}:{mongo_port}/')
        self.db = self.mongo_client[database_name]
        self.collection = self.db['yolo_objects']

        # System state
        self.running = False
        self.last_camera_check = datetime.now()

    def map_sensor_to_interaction(self, sensor_data: List[Dict]) -> List[Dict]:
        """
        Map Arduino sensor data to interaction format for database.

        Args:
            sensor_data: List of sensor readings from Arduino

        Returns:
            List of interaction data dictionaries
        """
        interactions = []

        for sensor in sensor_data:
            # Map sensor data to interaction format
            # Sensor ID becomes button ID, distance/level become presses/level
            interaction = self.data_sender.create_interaction_data(
                button_id=f"sensor_{sensor['sensor']}",
                num_button_presses=sensor['distance'],  # Use distance as press count
                vibration_id=f"vibration_{sensor['sensor']}",
                vibration_level=sensor['level'],  # Use level as vibration level
                timestamp=datetime.now()
            )
            interactions.append(interaction)

        return interactions

    def get_camera_detections(self) -> List[Dict]:
        """
        Get recent camera detections from MongoDB.

        Returns:
            List of recent camera detection objects
        """
        try:
            # Get detections from last 30 seconds
            recent_detections = get_recent_objects(minutes=0.5)  # 30 seconds
            return recent_detections
        except Exception as e:
            print(f"Error getting camera detections: {e}")
            return []

    def process_camera_feedback(self, detections: List[Dict]) -> List[int]:
        """
        Process camera detections and generate feedback for Arduino.

        Args:
            detections: List of camera detection objects

        Returns:
            List of 3 booleans (0/1) indicating detection status per sensor
        """
        # Initialize detection status for 3 sensors
        detection_status = [0, 0, 0]

        if detections:
            # If any objects detected, set all sensors to 1 (detected)
            # You can customize this logic based on your requirements
            detection_status = [1, 1, 1]
            print(f"Camera detected {len(detections)} objects")

        return detection_status

    def send_feedback_to_arduino(self, detection_status: List[int]) -> bool:
        """
        Send detection feedback to Arduino.

        Args:
            detection_status: List of detection booleans

        Returns:
            True if sent successfully
        """
        return self.arduino.send_camera_data(detection_status)

    def main_loop(self):
        """Main processing loop."""
        print("Starting sensor integration system...")

        # Connect to Arduino
        if not self.arduino.connect():
            print("Failed to connect to Arduino. Exiting.")
            return

        print("System running. Press Ctrl+C to stop.")

        try:
            while self.running:
                # 1. Read sensor data from Arduino
                sensor_data = self.arduino.read_sensor_data()

                if sensor_data:
                    print(f"Received sensor data: {sensor_data}")

                    # 2. Map and send to database
                    interactions = self.map_sensor_to_interaction(sensor_data)
                    for interaction in interactions:
                        success = self.data_sender.send_interaction(interaction)
                        if not success:
                            print("Failed to send interaction data")

                # 3. Get camera data from MongoDB (every 2 seconds)
                current_time = datetime.now()
                if (current_time - self.last_camera_check).seconds >= 2:
                    detections = self.get_camera_detections()
                    self.last_camera_check = current_time

                    # 4. Process and send feedback to Arduino
                    detection_status = self.process_camera_feedback(detections)
                    self.send_feedback_to_arduino(detection_status)

                # Small delay to prevent overwhelming the system
                time.sleep(0.5)

        except KeyboardInterrupt:
            print("\nStopping system...")
        finally:
            self.arduino.disconnect()
            self.mongo_client.close()
            print("System shutdown complete.")

    def start(self):
        """Start the integration system."""
        self.running = True
        self.main_loop()

    def stop(self):
        """Stop the integration system."""
        self.running = False


def main():
    """Main entry point."""
    # Configuration - adjust these values as needed
    config = {
        'arduino_port': '/dev/ttyACM0',  # Linux/Raspberry Pi
        # 'arduino_port': 'COM3',  # Uncomment for Windows
        'server_url': 'http://192.168.1.100:3000',  # Laptop server URL
        'mongo_host': '192.168.1.100',  # Laptop IP
        'mongo_port': 27017,
        'database_name': 'your_database_name'  # Replace with actual DB name
    }

    system = SensorIntegrationSystem(**config)
    system.start()


if __name__ == '__main__':
    main()