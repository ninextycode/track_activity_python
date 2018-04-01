import pyxhook
import threading
import datetime
import time
import numpy as np


class ActionWatcher:
    # when to call callback for a mouse move event
    noticeable_mouse_move_length = 16

    def __init__(self, on_event=None):
        if on_event is None:
            on_event = lambda data: None

        self._on_event = on_event

        self._pressed_keys = set()
        self._mouse_position = [0, 0]
        self._old_reported_position = self._mouse_position

        self._pressed_mouse_buttons = set()

        self._hook_thread = pyxhook.HookManager()

        self._hook_thread.KeyDown = self._on_key_event
        self._hook_thread.KeyUp = self._on_key_event
        self._hook_thread.MouseAllButtonsDown = self._on_mouse_button_event
        self._hook_thread.MouseAllButtonsUp = self._on_mouse_button_event
        self._hook_thread.MouseMovement = self._on_mouse_move_event

        self._query_lock = threading.Lock()

        self.interesting_keys = ["esc", "space", "alt", "tab",
                                    "shift", "control",
                                    "caps", "left", "right", "up", "down"]

    def query(self):
        with self._query_lock:
            data = {
                "mouse_position": self._mouse_position,
                "keys": list(self._pressed_keys),
                "mouse_buttons": list(self._pressed_mouse_buttons)
            }
        return data

    def _on_key_event(self, event):
        #  Track letters ignoring case, control key names(ex "shift") and digits
        key = event.key.casefold()
        if not (key.isalpha() or key == " " or len(key) > 1):
            return

        if len(key) > 1 and len([True for ctrl in self.interesting_keys if ctrl in key]) == 0:
            return

        old_pressed_keys_len = len(self._pressed_keys)

        if event.pressed:
            self._pressed_keys.add(key)
        elif key in self._pressed_keys:
            self._pressed_keys.remove(key)
        new_pressed_keys_len = len(self._pressed_keys)

        # if there was change
        if new_pressed_keys_len != old_pressed_keys_len:
            self._on_event(self.query())

    def _on_mouse_move_event(self, event):
        self._mouse_position = event.position

        difference = np.hypot(
            self._mouse_position[0] - self._old_reported_position[0],
            self._mouse_position[1] - self._old_reported_position[1])

        if difference > ActionWatcher.noticeable_mouse_move_length:
            self._old_reported_position = self._mouse_position
            self._on_event(self.query())

    def _on_mouse_button_event(self, event):
        button = event.button.lower()

        old_pressed_btns_len = len(self._pressed_mouse_buttons)

        if event.pressed:
            self._pressed_mouse_buttons.add(button)
        elif button in self._pressed_mouse_buttons:
            self._pressed_mouse_buttons.remove(button)

        new_pressed_btns_len = len(self._pressed_mouse_buttons)

        # if there was change
        if new_pressed_btns_len != old_pressed_btns_len:
            self._on_event(self.query())

    def stop(self):
        if self._hook_thread.is_alive():
            self._hook_thread.cancel()
            self._hook_thread.join()

    def start(self):
        self._hook_thread.start()

    def __del__(self):
        self.stop()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()


def demo(writer):
    def on_input_event(data):
        print(datetime.datetime.now())
        writer.add_to_write(data)

    watcher = ActionWatcher(on_event=on_input_event)
    watcher.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    watcher.stop()

if __name__ == "__main__":
    from json_writer import JsonWriter
    with JsonWriter("actions1.txt") as writer:
        demo(writer)
