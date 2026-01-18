"""
Test script for Button class GPIO monitoring.
Run this to verify button functionality before integrating into main system.

Usage:
    python button_test.py
"""

import time
from gpiozero import Button as GpioButton
from threading import Event

class Button:
    def __init__(self, pin: int, debounce_ms: int = 20):
        self.pin = pin
        self.debounce = debounce_ms / 1000.0
        self._count = 0
        self._stop_event = Event()

        self.button = GpioButton(
            pin,
            pull_up=True,
            bounce_time=self.debounce
        )

        self.button.when_pressed = self._on_press

    def _on_press(self):
        self._count += 1

    def start(self):
        # gpiozero runs callbacks automatically
        pass

    def stop(self):
        self.button.close()

    def get_press_count(self):
        return self._count

    def get_and_reset(self):
        count = self._count
        self._count = 0
        return count

# def main():
#     print("=== Button Test ===")
#     print("Testing GPIO button on pin 4 with 20ms debounce")
#     print("Press Ctrl+C to stop\n")
    
#     # Initialize button on GPIO pin 4
#     button = Button(pin=4, debounce_ms=20)
    
#     # Start monitoring
#     button.start()
    
#     try:
#         print("Button monitor started. Press the button to test...")
#         last_count = 0
        
#         while True:
#             current_count = button.get_press_count()
            
#             # Display when count changes
#             if current_count != last_count:
#                 print(f"Button pressed! Total count: {current_count}")
#                 last_count = current_count
            
#             time.sleep(0.1)  # Check every 100ms
            
#     except KeyboardInterrupt:
#         print("\n\n=== Test Results ===")
#         final_count = button.get_press_count()
#         print(f"Total button presses detected: {final_count}")
        
#         # Test get_and_reset
#         print("\nTesting get_and_reset()...")
#         count_before_reset = button.get_and_reset()
#         count_after_reset = button.get_press_count()
#         print(f"Count before reset: {count_before_reset}")
#         print(f"Count after reset: {count_after_reset}")
        
#         if count_after_reset == 0:
#             print("✓ Reset successful!")
#         else:
#             print("✗ Reset failed!")
        
#     finally:
#         button.stop()
#         print("\nButton monitor stopped.")


# if __name__ == "__main__":
#     main()
