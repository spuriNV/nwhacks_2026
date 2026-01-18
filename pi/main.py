from arduino_sync import ArduinoSync


def main():
    """Entry point to start Arduino-Pi sync."""
    sync = ArduinoSync()
    sync.start()


if __name__ == "__main__":
    main()
