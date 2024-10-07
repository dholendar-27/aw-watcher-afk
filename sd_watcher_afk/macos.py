from Quartz.CoreGraphics import (
    CGEventSourceSecondsSinceLastEventType,
    kCGEventSourceStateHIDSystemState,
    kCGAnyInputEventType
)

def seconds_since_last_input() -> float:
    """
    Return the number of seconds since the last input event.
    This is useful for determining user inactivity time.

    @return: The number of seconds since the last input event in seconds.
    """
    try:
        # Fetch the time since the last input event (keyboard, mouse, etc.)
        return CGEventSourceSecondsSinceLastEventType(kCGEventSourceStateHIDSystemState, kCGAnyInputEventType)
    except Exception as e:
        print(f"Error retrieving input event time: {e}")
        return -1

if __name__ == "__main__":
    from time import sleep
    try:
        # Sleeps for 1 second intervals, prints time since last input
        while True:
            sleep(1)
            print(f"Seconds since last input: {seconds_since_last_input()}")
    except KeyboardInterrupt:
        print("Program terminated by user.")
