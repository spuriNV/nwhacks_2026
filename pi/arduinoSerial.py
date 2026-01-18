import serial
import time

class ArduinoSerialReader:
    def __init__(self, port='/dev/ttyACM0', baudrate=115200, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.distances = [0] * 3
        self.levels = [0] * 3
        self.camera = [0] * 3

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

    def write_line(self, message: str):
        """Send a single line to Arduino with newline termination."""
        if not self.ser:
            print("Serial port not connected")
            return
        try:
            if not message.endswith('\n'):
                message += '\n'
            self.ser.write(message.encode('utf-8'))
        except serial.SerialException as e:
            print(f"Failed to write to Arduino: {e}")

    def send_control_command(self, objs, enable: int, pattern: int):
        """Send control tuple: 3 object flags, enable flag, pattern (0-3)."""
        if not self.ser:
            print("Serial port not connected")
            return
        if len(objs) != 3:
            print("objs must be length 3")
            return
        safe_objs = [1 if bool(o) else 0 for o in objs]
        safe_enable = 1 if bool(enable) else 0
        safe_pattern = max(0, min(3, int(pattern)))
        payload = f"{safe_objs[0]},{safe_objs[1]},{safe_objs[2]},{safe_enable},{safe_pattern}"
        self.write_line(payload)

    def _parse_line(self, line):
        # Parse aggregated CSV line: dist0,dist1,dist2,level0,level1,level2
        if ',' in line:
            parts = [p for p in line.split(',') if p.strip() != '']
            if len(parts) == 6:
                try:
                    d0, d1, d2, l0, l1, l2 = [int(p) for p in parts]
                    self.distances = [d0, d1, d2]
                    self.levels = [l0, l1, l2]
                    return
                except ValueError:
                    pass

        # Ignore other lines like separators

    def get_data(self):
        return {
            'distances': self.distances.copy(),
            'levels': self.levels.copy(),
            'camera': self.camera.copy()
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
