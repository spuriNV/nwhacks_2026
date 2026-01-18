"""
Raspberry Pi client for sending vibration/button data to the laptop server.
Copy this file to your Raspberry Pi.

Usage:
    python pi_client.py

Requirements:
    pip install requests
"""
import requests
import time

# ------------------------------
# Configuration
# ------------------------------
# Change this to your laptop's IP address
LAPTOP_IP = "192.168.6.1"  # Update this!
LAPTOP_PORT = 5050
BASE_URL = f"http://{LAPTOP_IP}:{LAPTOP_PORT}"


class LaptopClient:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url

    def check_connection(self) -> bool:
        """Check if the laptop server is reachable."""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=5)
            if response.ok:
                data = response.json()
                print(f"Server status: {data}")
                return True
            return False
        except requests.exceptions.RequestException as e:
            print(f"Connection failed: {e}")
            return False

    def send_vibration(self, vibration_id: str, vibration_level: int) -> bool:
        """
        Send vibration data to the laptop.

        Args:
            vibration_id: Identifier for the vibration sensor (e.g., "VIB_1")
            vibration_level: Vibration intensity 0-100
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/vibration",
                json={
                    "vibration_id": vibration_id,
                    "vibration_level": vibration_level
                },
                timeout=5
            )
            if response.ok:
                print(f"Vibration sent: {vibration_id}={vibration_level}")
                return True
            else:
                print(f"Failed to send vibration: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"Error sending vibration: {e}")
            return False

    def send_button_press(self, button_id: str, num_presses: int = 1) -> bool:
        """
        Send button press data to the laptop.

        Args:
            button_id: Identifier for the button (e.g., "BTN_A")
            num_presses: Number of times the button was pressed
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/button",
                json={
                    "button_id": button_id,
                    "num_presses": num_presses
                },
                timeout=5
            )
            if response.ok:
                print(f"Button press sent: {button_id} x{num_presses}")
                return True
            else:
                print(f"Failed to send button press: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"Error sending button press: {e}")
            return False

    def send_interaction(
        self,
        button_id: str = None,
        num_presses: int = None,
        vibration_id: str = None,
        vibration_level: int = None
    ) -> bool:
        """
        Send combined interaction data (button + vibration) to the laptop.
        """
        try:
            data = {}
            if button_id:
                data["button_id"] = button_id
                data["num_presses"] = num_presses or 1
            if vibration_id:
                data["vibration_id"] = vibration_id
                data["vibration_level"] = vibration_level or 0

            response = requests.post(
                f"{self.base_url}/api/interaction",
                json=data,
                timeout=5
            )
            if response.ok:
                print(f"Interaction sent: {data}")
                return True
            else:
                print(f"Failed to send interaction: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"Error sending interaction: {e}")
            return False


# ------------------------------
# Example usage with actual sensors
# ------------------------------
def example_with_gpio():
    """
    Example of reading vibration sensor and sending data.
    Uncomment and modify for your specific hardware setup.
    """
    # import RPi.GPIO as GPIO
    # import smbus  # For I2C sensors

    client = LaptopClient()

    # Check connection first
    if not client.check_connection():
        print("Cannot connect to laptop. Check IP address and make sure server is running.")
        return

    # Example: Reading from an analog vibration sensor via ADC
    # (Modify this for your specific sensor setup)

    print("Starting vibration monitoring...")
    print("Press Ctrl+C to stop")

    try:
        while True:
            # Replace with actual sensor reading
            # Example: vibration_level = read_adc_channel(0)
            vibration_level = 50  # Dummy value

            # Only send if vibration is detected
            if vibration_level > 10:
                client.send_vibration("VIB_MAIN", vibration_level)

            time.sleep(0.1)  # 10 readings per second

    except KeyboardInterrupt:
        print("\nStopped")


# ------------------------------
# Demo mode (no hardware required)
# ------------------------------
def demo_mode():
    """Demo mode - sends fake data for testing."""
    import random

    client = LaptopClient()

    print(f"Connecting to {BASE_URL}...")
    if not client.check_connection():
        print("Cannot connect to laptop!")
        print(f"Make sure the server is running and update LAPTOP_IP to your laptop's IP")
        return

    print("\nDemo mode - sending random data")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            # Random vibration
            vib_level = random.randint(0, 100)
            client.send_vibration("VIB_DEMO", vib_level)

            # Occasional button press
            if random.random() < 0.2:
                btn_id = random.choice(["BTN_A", "BTN_B", "BTN_C"])
                client.send_button_press(btn_id, random.randint(1, 3))

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nDemo stopped")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--gpio":
        example_with_gpio()
    else:
        demo_mode()
