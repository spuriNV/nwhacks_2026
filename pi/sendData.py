'''
@file sendData.py
Sends data to the remote MongoDB 
'''

import requests
import json
from datetime import datetime
from typing import Dict, List, Optional
import time


class ArduinoDataSender:
    """
    Handles sending Arduino sensor data to a server API endpoint.
    Compatible with MongoDB interaction schema.
    """
    
    def __init__(self, server_url: str, api_endpoint: str = "/api/interactions"):
        """
        Initialize the data sender.
        
        Args:
            server_url: Base URL of your server (e.g., 'http://192.168.1.100:3000')
            api_endpoint: API endpoint path (default: '/api/interactions')
        """
        self.server_url = server_url.rstrip('/')
        self.api_endpoint = api_endpoint
        self.full_url = f"{self.server_url}{self.api_endpoint}"
    
    def create_interaction_data(
        self,
        button_id: str,
        num_button_presses: int,
        vibration_id: str,
        vibration_level: int,
        timestamp: Optional[datetime] = None
    ) -> Dict:
        """
        Create interaction data matching MongoDB schema.
        
        Args:
            button_id: Identifier for the button
            num_button_presses: Number of button presses
            vibration_id: Identifier for the vibration motor
            vibration_level: Vibration intensity level (0-3)
            timestamp: Optional timestamp (defaults to now)
        
        Returns:
            Dictionary matching the interaction schema
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        return {
            "button": {
                "buttonId": button_id,
                "numButtonPresses": num_button_presses
            },
            "vibration": {
                "vibrationId": vibration_id,
                "vibrationLevel": vibration_level
            },
            "timestamp": timestamp.isoformat()
        }
    
    def send_interaction(self, interaction_data: Dict) -> bool:
        """
        Send interaction data to server.
        
        Args:
            interaction_data: Dictionary with interaction data
        
        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.post(
                self.full_url,
                json=interaction_data,
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            
            if response.status_code in [200, 201]:
                print(f"✓ Data sent successfully: {response.status_code}")
                return True
            else:
                print(f"✗ Server error: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.ConnectionError:
            print("✗ Connection error: Could not reach server")
            return False
        except requests.exceptions.Timeout:
            print("✗ Request timeout")
            return False
        except Exception as e:
            print(f"✗ Error sending data: {e}")
            return False
    
    def send_sensor_data(
        self,
        sensor_id: int,
        distance: int,
        level: int,
        button_presses: int = 0
    ) -> bool:
        """
        Convert sensor data to interaction format and send to server.
        
        Args:
            sensor_id: Sensor identifier (0, 1, 2)
            distance: Distance in cm
            level: Vibration level (0-3)
            button_presses: Number of button presses
        
        Returns:
            True if successful, False otherwise
        """
        interaction_data = self.create_interaction_data(
            button_id=f"sensor_{sensor_id}",
            num_button_presses=button_presses,
            vibration_id=f"motor_{sensor_id}",
            vibration_level=level
        )
        
        return self.send_interaction(interaction_data)
    
    def send_batch(self, interactions: List[Dict]) -> Dict[str, int]:
        """
        Send multiple interactions to server.
        
        Args:
            interactions: List of interaction dictionaries
        
        Returns:
            Dictionary with success/failure counts
        """
        results = {"success": 0, "failed": 0}
        
        for interaction in interactions:
            if self.send_interaction(interaction):
                results["success"] += 1
            else:
                results["failed"] += 1
            time.sleep(0.1)  # Small delay between requests
        
        return results
    
    def test_connection(self) -> bool:
        """
        Test if server is reachable.
        
        Returns:
            True if server responds, False otherwise
        """
        try:
            # Try a simple GET request to the base URL
            response = requests.get(self.server_url, timeout=3)
            print(f"✓ Server is reachable (Status: {response.status_code})")
            return True
        except:
            print("✗ Cannot reach server")
            return False


class ArduinoToServerBridge:
    """
    Bridge between Arduino serial data and server API.
    Automatically sends sensor readings to server.
    """
    
    def __init__(self, server_url: str, api_endpoint: str = "/api/interactions"):
        """
        Initialize the bridge.
        
        Args:
            server_url: Base URL of your server
            api_endpoint: API endpoint path
        """
        self.sender = ArduinoDataSender(server_url, api_endpoint)
        self.button_press_counter = {}  # Track button presses per sensor
    
    def process_and_send_sensor_data(self, sensor_data: List[Dict]) -> Dict[str, int]:
        """
        Process Arduino sensor data and send to server.
        
        Args:
            sensor_data: List of sensor dictionaries from arduino_serial module
                        [{'sensor': 0, 'distance': 45, 'level': 2}, ...]
        
        Returns:
            Dictionary with success/failure counts
        """
        results = {"success": 0, "failed": 0}
        
        for sensor in sensor_data:
            sensor_id = sensor['sensor']
            distance = sensor['distance']
            level = sensor['level']
            
            # Get button press count for this sensor
            button_presses = self.button_press_counter.get(sensor_id, 0)
            
            # Send data
            if self.sender.send_sensor_data(sensor_id, distance, level, button_presses):
                results["success"] += 1
            else:
                results["failed"] += 1
            
            time.sleep(0.05)  # Small delay between sensors
        
        return results
    
    def increment_button_press(self, sensor_id: int):
        """
        Increment button press counter for a sensor.
        
        Args:
            sensor_id: Sensor identifier (0, 1, 2)
        """
        if sensor_id not in self.button_press_counter:
            self.button_press_counter[sensor_id] = 0
        self.button_press_counter[sensor_id] += 1
    
    def reset_button_presses(self, sensor_id: Optional[int] = None):
        """
        Reset button press counter.
        
        Args:
            sensor_id: Specific sensor to reset, or None to reset all
        """
        if sensor_id is None:
            self.button_press_counter.clear()
        else:
            self.button_press_counter[sensor_id] = 0
    
    def create_custom_interaction(
        self,
        button_id: str,
        button_presses: int,
        vibration_id: str,
        vibration_level: int
    ) -> bool:
        """
        Create and send a custom interaction.
        
        Args:
            button_id: Button identifier
            button_presses: Number of presses
            vibration_id: Vibration motor identifier
            vibration_level: Level (0-3)
        
        Returns:
            True if successful
        """
        interaction = self.sender.create_interaction_data(
            button_id=button_id,
            num_button_presses=button_presses,
            vibration_id=vibration_id,
            vibration_level=vibration_level
        )
        return self.sender.send_interaction(interaction)


# Utility functions for easy integration

def send_to_server(
    server_url: str,
    sensor_data: List[Dict],
    endpoint: str = "/api/interactions"
) -> bool:
    """
    Simple function to send sensor data to server.
    
    Args:
        server_url: Server URL (e.g., 'http://192.168.1.100:3000')
        sensor_data: Sensor data from arduino_serial module
        endpoint: API endpoint
    
    Returns:
        True if all data sent successfully
    """
    bridge = ArduinoToServerBridge(server_url, endpoint)
    results = bridge.process_and_send_sensor_data(sensor_data)
    return results["failed"] == 0


def create_interaction_payload(
    button_id: str,
    button_presses: int,
    vibration_id: str,
    vibration_level: int
) -> str:
    """
    Create JSON payload for manual posting.
    
    Returns:
        JSON string ready to send
    """
    sender = ArduinoDataSender("http://dummy.com")
    data = sender.create_interaction_data(
        button_id, button_presses, vibration_id, vibration_level
    )
    return json.dumps(data, indent=2)


# Example usage
if __name__ == "__main__":
    # Example 1: Simple send
    print("Example 1: Simple data send")
    print("="*50)
    
    sender = ArduinoDataSender(server_url="http://192.168.1.100:3000")
    
    # Test connection
    sender.test_connection()
    
    # Create and send interaction
    interaction = sender.create_interaction_data(
        button_id="sensor_0",
        num_button_presses=5,
        vibration_id="motor_0",
        vibration_level=2
    )
    
    print("\nSending interaction:")
    print(json.dumps(interaction, indent=2))
    sender.send_interaction(interaction)
    
    print("\n" + "="*50)
    print("Example 2: Using bridge with sensor data")
    print("="*50)
    
    # Simulated sensor data (normally from arduino_serial module)
    sensor_data = [
        {'sensor': 0, 'distance': 45, 'level': 2},
        {'sensor': 1, 'distance': 80, 'level': 1},
        {'sensor': 2, 'distance': 15, 'level': 3}
    ]
    
    bridge = ArduinoToServerBridge(server_url="http://192.168.1.100:3000")
    results = bridge.process_and_send_sensor_data(sensor_data)
    
    print(f"\nResults: {results['success']} successful, {results['failed']} failed")
    
    print("\n" + "="*50)
    print("Example 3: Create JSON payload")
    print("="*50)
    
    payload = create_interaction_payload(
        button_id="button_1",
        button_presses=3,
        vibration_id="vibration_motor_1",
        vibration_level=2
    )
    
    print("\nJSON Payload:")
    print(payload)