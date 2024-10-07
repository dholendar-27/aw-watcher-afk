import logging
import threading
from abc import ABCMeta, abstractmethod
from collections import defaultdict
from typing import Dict, Any

from pynput import keyboard, mouse

# Setup logging
logger = logging.getLogger(__name__)
# Uncomment the following two lines for debugging
# logger.setLevel(logging.DEBUG)
# logging.basicConfig(level=logging.DEBUG)


class EventFactory(metaclass=ABCMeta):
    def __init__(self) -> None:
        """
        Initialize the event factory and set up event tracking.
        """
        self.new_event = threading.Event()
        self._reset_data()

    @abstractmethod
    def _reset_data(self) -> None:
        """
        Reset the event data to default values. Subclasses should override this method.
        """
        self.event_data: Dict[str, Any] = {}

    def next_event(self) -> dict:
        """
        Return the next event data and reset the event state.

        @return: A dictionary containing the event data.
        """
        self.new_event.clear()
        data = self.event_data.copy()
        self._reset_data()
        return data

    def has_new_event(self) -> bool:
        """
        Check if there is a new event available.

        @return: True if there is a new event, False otherwise.
        """
        return self.new_event.is_set()


class KeyboardListener(EventFactory):
    def __init__(self):
        """
        Initialize the KeyboardListener.
        """
        super().__init__()
        self.logger = logger.getChild("keyboard")

    def _reset_data(self):
        """
        Reset event data to track key presses.
        """
        self.event_data = {"presses": 0}

    def on_press(self, key):
        """
        Callback for key press events. Increment the count of key presses.

        @param key: The key that was pressed.
        """
        try:
            logger.debug(f"Key pressed: {key}")
            self.event_data["presses"] += 1
            self.new_event.set()
        except Exception as e:
            logger.error(f"Error in on_press: {e}")

    def on_release(self, key):
        """
        Callback for key release events. Currently not tracking releases.

        @param key: The key that was released.
        """
        pass  # Only track key presses, not releases

    def start(self):
        """
        Start listening for keyboard events.
        """
        listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        listener.start()
        logger.info("Keyboard listener started")


class MouseListener(EventFactory):
    def __init__(self):
        """
        Initialize the MouseListener.
        """
        super().__init__()
        self.logger = logger.getChild("mouse")
        self.pos = None  # To track mouse position

    def _reset_data(self):
        """
        Reset event data to track clicks, movement, and scrolling.
        """
        self.event_data = defaultdict(int)
        self.event_data.update(
            {"clicks": 0, "deltaX": 0, "deltaY": 0, "scrollX": 0, "scrollY": 0}
        )

    def on_move(self, x, y):
        """
        Callback for mouse movement. Track the delta in x and y coordinates.

        @param x: The x coordinate of the mouse.
        @param y: The y coordinate of the mouse.
        """
        try:
            new_pos = (x, y)
            if self.pos is None:
                self.pos = new_pos  # Initialize position on first move
                return

            deltaX = new_pos[0] - self.pos[0]
            deltaY = new_pos[1] - self.pos[1]

            if deltaX != 0 or deltaY != 0:  # Track only actual movements
                self.event_data["deltaX"] += abs(deltaX)
                self.event_data["deltaY"] += abs(deltaY)
                self.new_event.set()

            self.pos = new_pos  # Update position
            logger.debug(f"Mouse moved to: {x}, {y}")
        except Exception as e:
            logger.error(f"Error in on_move: {e}")

    def on_click(self, x, y, button, pressed):
        """
        Callback for mouse click events. Track mouse button presses.

        @param x: The x coordinate of the click.
        @param y: The y coordinate of the click.
        @param button: The mouse button pressed.
        @param pressed: True if the button was pressed, False if released.
        """
        try:
            if pressed:  # Only track button presses
                self.event_data["clicks"] += 1
                self.new_event.set()
                logger.debug(f"Mouse clicked at: {x}, {y}, button: {button}")
        except Exception as e:
            logger.error(f"Error in on_click: {e}")

    def on_scroll(self, x, y, scroll_x, scroll_y):
        """
        Callback for mouse scroll events. Track scrolling.

        @param x: The x coordinate of the scroll.
        @param y: The y coordinate of the scroll.
        @param scroll_x: Scroll amount in the x direction.
        @param scroll_y: Scroll amount in the y direction.
        """
        try:
            self.event_data["scrollX"] += abs(scroll_x)
            self.event_data["scrollY"] += abs(scroll_y)
            self.new_event.set()
            logger.debug(f"Mouse scrolled at: {x}, {y}, scroll: ({scroll_x}, {scroll_y})")
        except Exception as e:
            logger.error(f"Error in on_scroll: {e}")

    def start(self):
        """
        Start listening for mouse events.
        """
        listener = mouse.Listener(
            on_move=self.on_move, on_click=self.on_click, on_scroll=self.on_scroll
        )
        listener.start()
        logger.info("Mouse listener started")


# Example usage to start both listeners:
if __name__ == "__main__":
    keyboard_listener = KeyboardListener()
    mouse_listener = MouseListener()

    # Start both listeners in their respective threads
    keyboard_listener.start()
    mouse_listener.start()

    # Example event loop to demonstrate handling the events
    try:
        while True:
            if keyboard_listener.has_new_event():
                print(f"Keyboard event: {keyboard_listener.next_event()}")

            if mouse_listener.has_new_event():
                print(f"Mouse event: {mouse_listener.next_event()}")

    except KeyboardInterrupt:
        print("Program interrupted and terminated by user.")
