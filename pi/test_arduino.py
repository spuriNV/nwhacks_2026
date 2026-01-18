"""Test script to print Arduino serial data."""

import time
import serial

def main():
    port = '/dev/ttyACM0'
    baudrate = 115200

    print(f"Connecting to {port} at {baudrate} baud...")

    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        print("Connected! Reading raw serial data...")
        print("Press Ctrl+C to stop\n")
        print("-" * 50)

        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    print(f"RAW: {line}")
            time.sleep(0.1)

    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        if 'ser' in locals():
            ser.close()
            print("Disconnected")

if __name__ == "__main__":
    main()
