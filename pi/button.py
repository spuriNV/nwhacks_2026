import threading
from gpiozero import Button as GpioZeroButton


class Button:
    def __init__(self, pin, debounce_ms=20):
        """
        GPIOZero-based button helper with debounced press counting.

        Args:
            pin: BCM pin number.
            debounce_ms: Debounce time in milliseconds.
        """
        self.pin = pin
        self.debounce_s = debounce_ms / 1000.0
        self.press_count = 0
        self.lock = threading.Lock()
        self.running = False
        self.device = None

    def start(self):
        if self.running:
            return

        # Set up gpiozero Button with pull-up and debounce
        self.device = GpioZeroButton(self.pin, pull_up=True, bounce_time=self.debounce_s)
        self.device.when_pressed = self._on_press
        self.running = True
        print(f"Button monitor started on pin {self.pin}")

    def stop(self):
        self.running = False
        if self.device:
            self.device.close()
            self.device = None
        print(f"Button monitor stopped on pin {self.pin}")

    def _on_press(self):
        # Count press on falling edge handled by gpiozero
        with self.lock:
            self.press_count += 1

    def get_press_count(self):
        with self.lock:
            return self.press_count

    def reset_press_count(self):
        with self.lock:
            count = self.press_count
            self.press_count = 0
            return count

    def get_and_reset(self):
        with self.lock:
            count = self.press_count
            self.press_count = 0
            return count


if __name__ == "__main__":
    import time

    button = Button(pin=25, debounce_ms=20)
    button.start()

    try:
        while True:
            print(f"Total presses: {button.get_press_count()}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping...")
        button.stop()
