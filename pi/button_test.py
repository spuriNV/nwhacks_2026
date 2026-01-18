"""
Test script for Button class GPIO monitoring.
Run this to verify button functionality before integrating into main system.

Usage:
    python button_test.py
"""

import time
from button import Button


def main():
    print("=== Button Test ===")
    print("Testing GPIO button on pin 7 (GPIO7) with 20ms debounce")
    print("Press Ctrl+C to stop\n")
    
    # Initialize button on GPIO pin 7 (physical pin 26)
    button = Button(pin=25, debounce_ms=20)
    
    # Start monitoring
    button.start()
    
    try:
        print("Button monitor started. Press the button to test...")
        last_count = 0
        
        while True:
            current_count = button.get_press_count()
            
            # Display when count changes
            if current_count != last_count:
                print(f"Button pressed! Total count: {current_count}")
                last_count = current_count
            
            time.sleep(0.1)  # Check every 100ms
            
    except KeyboardInterrupt:
        print("\n\n=== Test Results ===")
        final_count = button.get_press_count()
        print(f"Total button presses detected: {final_count}")
        
        # Test get_and_reset
        print("\nTesting get_and_reset()...")
        count_before_reset = button.get_and_reset()
        count_after_reset = button.get_press_count()
        print(f"Count before reset: {count_before_reset}")
        print(f"Count after reset: {count_after_reset}")
        
        if count_after_reset == 0:
            print("✓ Reset successful!")
        else:
            print("✗ Reset failed!")
        
    finally:
        button.stop()
        print("\nButton monitor stopped.")


if __name__ == "__main__":
    main()
