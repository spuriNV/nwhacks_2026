"""Test script to print Arduino serial data."""

import time
from arduinoSerial import ArduinoSerialReader

def main():
    reader = ArduinoSerialReader(port='/dev/ttyACM0', baudrate=115200)
    reader.connect()

    if not reader.ser:
        print("Failed to connect to Arduino")
        return

    print("Connected! Reading Arduino data...")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            reader.read_and_parse()
            data = reader.get_data()
            print(f"Distances (cm): {data['distances']}  |  Levels: {data['levels']}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        reader.disconnect()

if __name__ == "__main__":
    main()
