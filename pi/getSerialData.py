"""
Arduino Serial Communication Module
Handles communication with Arduino ultrasonic sensors and camera data
"""

import serial
import time
from typing import List, Optional, Tuple


class ArduinoSerial:
    """
    Module for communicating with Arduino sensor system.
    Reads sensor data and sends camera detection data.
    """
    
    def __init__(self, port: str = '/dev/ttyACM0', baudrate: int = 115200, timeout: float = 1.0):
        """
        Initialize serial connection to Arduino.
        
        Args:
            port: Serial port name (e.g., 'COM3' on Windows, '/dev/ttyACM0' on Linux)
            baudrate: Communication speed (must match Arduino)
            timeout: Read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.num_sensors = 3
        
    def connect(self) -> bool:
        """
        Establish connection to Arduino.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            time.sleep(2)  # Wait for Arduino to reset
            print(f"Connected to Arduino on {self.port}")
            return True
        except serial.SerialException as e:
            print(f"Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Close the serial connection."""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Disconnected from Arduino")
    
    def read_line(self) -> Optional[str]:
        """
        Read a single line from Arduino.
        
        Returns:
            String data from Arduino or None if no data available
        """
        if not self.ser or not self.ser.is_open:
            print("Serial connection not open")
            return None
        
        try:
            if self.ser.in_waiting > 0:
                line = self.ser.readline().decode('utf-8').strip()
                return line
        except Exception as e:
            print(f"Error reading line: {e}")
            return None
    
    def read_sensor_data(self) -> Optional[List[dict]]:
        """
        Read and parse sensor data from Arduino.
        
        Returns:
            List of dictionaries containing sensor data:
            [{'sensor': 0, 'distance': 45, 'level': 2}, ...]
            or None if parsing fails
        """
        sensor_data = []
        
        try:
            # Read data for all sensors
            for _ in range(self.num_sensors):
                line = self.read_line()
                if line and line.startswith("Sensor"):
                    # Parse line like: "Sensor 0: Distance=45 cm | Level=2"
                    parts = line.split(":")
                    sensor_id = int(parts[0].replace("Sensor", "").strip())
                    
                    distance_part = parts[1].split("|")[0]
                    distance = int(distance_part.replace("Distance=", "").replace("cm", "").strip())
                    
                    level_part = parts[1].split("|")[1]
                    level = int(level_part.replace("Level=", "").strip())
                    
                    sensor_data.append({
                        'sensor': sensor_id,
                        'distance': distance,
                        'level': level
                    })
            
            # Read separator line
            self.read_line()
            
            return sensor_data if sensor_data else None
            
        except Exception as e:
            print(f"Error parsing sensor data: {e}")
            return None
    
    def send_camera_data(self, detections: List[int]) -> bool:
        """
        Send camera detection data to Arduino.
        
        Args:
            detections: List of 3 integers (0 or 1) representing object detection
                       Example: [1, 0, 1] means objects detected in cameras 0 and 2
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.ser or not self.ser.is_open:
            print("Serial connection not open")
            return False
        
        if len(detections) != self.num_sensors:
            print(f"Error: Expected {self.num_sensors} detection values")
            return False
        
        try:
            # Format: "1,0,1\n"
            data_string = ','.join(map(str, detections)) + '\n'
            self.ser.write(data_string.encode('utf-8'))
            return True
        except Exception as e:
            print(f"Error sending camera data: {e}")
            return False
    
    def read_all_available(self) -> List[str]:
        """
        Read all available lines from Arduino buffer.
        
        Returns:
            List of strings
        """
        lines = []
        while self.ser and self.ser.in_waiting > 0:
            line = self.read_line()
            if line:
                lines.append(line)
        return lines
    
    def get_sensor_reading(self, sensor_id: int) -> Optional[Tuple[int, int]]:
        """
        Get specific sensor reading.
        
        Args:
            sensor_id: Sensor index (0, 1, or 2)
        
        Returns:
            Tuple of (distance, level) or None
        """
        data = self.read_sensor_data()
        if data:
            for sensor in data:
                if sensor['sensor'] == sensor_id:
                    return (sensor['distance'], sensor['level'])
        return None
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


# Example usage
if __name__ == "__main__":
    # Example 1: Basic usage
    arduino = ArduinoSerial(port='/dev/ttyACM0')  # Change port as needed
    
    if arduino.connect():
        try:
            # Read sensor data
            print("Reading sensor data...")
            for i in range(5):
                sensor_data = arduino.read_sensor_data()
                if sensor_data:
                    print(f"\nReading {i+1}:")
                    for sensor in sensor_data:
                        print(f"  Sensor {sensor['sensor']}: {sensor['distance']} cm, Level {sensor['level']}")
                
                # Send camera data (example: object detected in camera 0)
                arduino.send_camera_data([1, 0, 0])
                time.sleep(1)
        
        finally:
            arduino.disconnect()
    
    print("\n" + "="*50)
    print("Example 2: Using context manager")
    print("="*50)

import serial
import time
from typing import List, Optional, Tuple


class ArduinoSerial:
    """
    Module for communicating with Arduino sensor system.
    Reads sensor data and sends camera detection data.
    """
    
    def __init__(self, port: str = '/dev/ttyACM0', baudrate: int = 115200, timeout: float = 1.0):
        """
        Initialize serial connection to Arduino.
        
        Args:
            port: Serial port name (e.g., 'COM3' on Windows, '/dev/ttyACM0' on Linux)
            baudrate: Communication speed (must match Arduino)
            timeout: Read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.num_sensors = 3
        
    def connect(self) -> bool:
        """
        Establish connection to Arduino.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            time.sleep(2)  # Wait for Arduino to reset
            print(f"Connected to Arduino on {self.port}")
            return True
        except serial.SerialException as e:
            print(f"Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Close the serial connection."""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Disconnected from Arduino")
    
    def read_line(self) -> Optional[str]:
        """
        Read a single line from Arduino.
        
        Returns:
            String data from Arduino or None if no data available
        """
        if not self.ser or not self.ser.is_open:
            print("Serial connection not open")
            return None
        
        try:
            if self.ser.in_waiting > 0:
                line = self.ser.readline().decode('utf-8').strip()
                return line
        except Exception as e:
            print(f"Error reading line: {e}")
            return None
    
    def read_sensor_data(self) -> Optional[List[dict]]:
        """
        Read and parse sensor data from Arduino.
        
        Returns:
            List of dictionaries containing sensor data:
            [{'sensor': 0, 'distance': 45, 'level': 2}, ...]
            or None if parsing fails
        """
        sensor_data = []
        
        try:
            # Read data for all sensors
            for _ in range(self.num_sensors):
                line = self.read_line()
                if line and line.startswith("Sensor"):
                    # Parse line like: "Sensor 0: Distance=45 cm | Level=2"
                    parts = line.split(":")
                    sensor_id = int(parts[0].replace("Sensor", "").strip())
                    
                    distance_part = parts[1].split("|")[0]
                    distance = int(distance_part.replace("Distance=", "").replace("cm", "").strip())
                    
                    level_part = parts[1].split("|")[1]
                    level = int(level_part.replace("Level=", "").strip())
                    
                    sensor_data.append({
                        'sensor': sensor_id,
                        'distance': distance,
                        'level': level
                    })
            
            # Read separator line
            self.read_line()
            
            return sensor_data if sensor_data else None
            
        except Exception as e:
            print(f"Error parsing sensor data: {e}")
            return None
    
    def send_camera_data(self, detections: List[int]) -> bool:
        """
        Send camera detection data to Arduino.
        
        Args:
            detections: List of 3 integers (0 or 1) representing object detection
                       Example: [1, 0, 1] means objects detected in cameras 0 and 2
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.ser or not self.ser.is_open:
            print("Serial connection not open")
            return False
        
        if len(detections) != self.num_sensors:
            print(f"Error: Expected {self.num_sensors} detection values")
            return False
        
        try:
            # Format: "1,0,1\n"
            data_string = ','.join(map(str, detections)) + '\n'
            self.ser.write(data_string.encode('utf-8'))
            return True
        except Exception as e:
            print(f"Error sending camera data: {e}")
            return False
    
    def read_all_available(self) -> List[str]:
        """
        Read all available lines from Arduino buffer.
        
        Returns:
            List of strings
        """
        lines = []
        while self.ser and self.ser.in_waiting > 0:
            line = self.read_line()
            if line:
                lines.append(line)
        return lines
    
    def get_sensor_reading(self, sensor_id: int) -> Optional[Tuple[int, int]]:
        """
        Get specific sensor reading.
        
        Args:
            sensor_id: Sensor index (0, 1, or 2)
        
        Returns:
            Tuple of (distance, level) or None
        """
        data = self.read_sensor_data()
        if data:
            for sensor in data:
                if sensor['sensor'] == sensor_id:
                    return (sensor['distance'], sensor['level'])
        return None
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


# Example usage
if __name__ == "__main__":
    # Example 1: Basic usage
    arduino = ArduinoSerial(port='/dev/ttyACM0')  # Change port as needed
    
    if arduino.connect():
        try:
            # Read sensor data
            print("Reading sensor data...")
            for i in range(5):
                sensor_data = arduino.read_sensor_data()
                if sensor_data:
                    print(f"\nReading {i+1}:")
                    for sensor in sensor_data:
                        print(f"  Sensor {sensor['sensor']}: {sensor['distance']} cm, Level {sensor['level']}")
                
                # Send camera data (example: object detected in camera 0)
                arduino.send_camera_data([1, 0, 0])
                time.sleep(1)
        
        finally:
            arduino.disconnect()
    
    print("\n" + "="*50)
    print("Example 2: Using context manager")
    print("="*50)
    
    # Example 2: Using context manager
    with ArduinoSerial(port='/dev/ttyACM0') as arduino:
        # Read all available data
        all_lines = arduino.read_all_available()
        for line in all_lines:
            print(line)
    print("="*50)
    
    # Example 2: Using context manager
    with ArduinoSerial(port='/dev/ttyACM0') as arduino:
        # Read all available data
        all_lines = arduino.read_all_available()
        for line in all_lines:
            print(line)