import serial
import time
import re

class ArduinoSerialReader:
    def __init__(self, port='/dev/ttyACM0', baudrate=115200, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.distances = [0] * 3
        self.levels = [0] * 3
        self.camera = [0] * 3
        self.button_presses = 0

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            print(f"Connected to {self.port} at {self.baudrate} baud")
        except serial.SerialException as e:
            print(f"Failed to connect to {self.port}: {e}")
            self.ser = None

    def disconnect(self):
        if self.ser:
            self.ser.close()
            print("Disconnected from serial port")

    def read_and_parse(self):
        if not self.ser:
            print("Serial port not connected")
            return

        lines = []
        while self.ser.in_waiting > 0:
            line = self.ser.readline().decode('utf-8').strip()
            if line:
                lines.append(line)

        for line in lines:
            self._parse_line(line)

    def _parse_line(self, line):
        # Parse sensor data: "Sensor 0: Distance=50 cm | Level=2"
        sensor_match = re.match(r'Sensor (\d+): Distance=(\d+) cm \| Level=(\d+)', line)
        if sensor_match:
            sensor_id = int(sensor_match.group(1))
            distance = int(sensor_match.group(2))
            level = int(sensor_match.group(3))
            if 0 <= sensor_id < 3:
                self.distances[sensor_id] = distance
                self.levels[sensor_id] = level
            return

        # Parse camera data: "Camera 0: 1"
        camera_match = re.match(r'Camera (\d+): (\d+)', line)
        if camera_match:
            cam_id = int(camera_match.group(1))
            value = int(camera_match.group(2))
            if 0 <= cam_id < 3:
                self.camera[cam_id] = value
            return

        # Parse button presses: "Button presses: 5"
        button_match = re.match(r'Button presses: (\d+)', line)
        if button_match:
            self.button_presses = int(button_match.group(1))
            return

        # Ignore other lines like "--------------------" or "Received: ..."

    def get_data(self):
        return {
            'distances': self.distances.copy(),
            'levels': self.levels.copy(),
            'camera': self.camera.copy(),
            'button_presses': self.button_presses
        }

    def run(self):
        self.connect()
        if not self.ser:
            return
        try:
            while True:
                self.read_and_parse()
                data = self.get_data()
                print(data)
                time.sleep(0.1)  # Small delay to prevent busy waiting
        except KeyboardInterrupt:
            print("Stopping...")
        finally:
            self.disconnect()

if __name__ == "__main__":
    reader = ArduinoSerialReader()
    reader.run()
