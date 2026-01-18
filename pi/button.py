import threading
import time
import RPi.GPIO as GPIO


class Button:
    def __init__(self, pin, debounce_ms=20):
        """
        Initialize the Button class with GPIO pin monitoring.
        
        Args:
            pin: GPIO pin number (BCM numbering)
            debounce_ms: Debounce delay in milliseconds (default: 20ms)
        """
        self.pin = pin
        self.debounce_ms = debounce_ms / 1000.0  # Convert to seconds
        self.press_count = 0
        self.running = False
        self.monitor_thread = None
        
        # State tracking for debounce
        self.last_state = GPIO.HIGH
        self.last_state_change = time.time()
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def start(self):
        """Start the background button monitoring thread."""
        if self.running:
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print(f"Button monitor started on pin {self.pin}")

    def stop(self):
        """Stop the background button monitoring thread."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        GPIO.cleanup(self.pin)
        print(f"Button monitor stopped on pin {self.pin}")

    def _monitor_loop(self):
        """Background thread loop that continuously samples GPIO pin."""
        while self.running:
            try:
                current_state = GPIO.input(self.pin)
                current_time = time.time()
                
                # Check if state changed and debounce time has passed
                if current_state != self.last_state:
                    if (current_time - self.last_state_change) > self.debounce_ms:
                        # Valid state change detected
                        self.last_state = current_state
                        self.last_state_change = current_time
                        
                        # Count button press on falling edge (GPIO.HIGH -> GPIO.LOW)
                        if current_state == GPIO.LOW:
                            with self.lock:
                                self.press_count += 1
                
                time.sleep(0.01)  # Sample every 10ms
                
            except Exception as e:
                print(f"Error in button monitor: {e}")
                time.sleep(0.1)

    def get_press_count(self):
        """Get the current accumulated button press count (thread-safe)."""
        with self.lock:
            return self.press_count

    def reset_press_count(self):
        """Reset the button press counter to zero (thread-safe)."""
        with self.lock:
            count = self.press_count
            self.press_count = 0
            return count

    def get_and_reset(self):
        """Get current press count and reset in one operation (thread-safe)."""
        with self.lock:
            count = self.press_count
            self.press_count = 0
            return count


if __name__ == "__main__":
    # Example usage
    button = Button(pin=17, debounce_ms=20)
    button.start()
    
    try:
        while True:
            print(f"Total presses: {button.get_press_count()}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping...")
        button.stop()
