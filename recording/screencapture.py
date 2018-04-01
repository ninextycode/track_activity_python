import cv2
import capturer as cp
import threading
import time
import numpy as np


class ScreenCapturer:
    def __init__(self, x, y, width, height, on_screenshot, cap_fps=np.inf):
        self._on_screenshot = on_screenshot
        self._screenshot_taker = cp.Capturer(x, y, width, height)

        self.cap_fps = cap_fps
        self.last_time_screenshot = time.time()
        self._stop = False

        self._screenshot_thread = threading.Thread(target=self._take_screenshots)

    def start(self):
        self._screenshot_thread.start()

    def wait_before_next_shot(self):
        period = 1 / self.cap_fps
        dt = time.time() - self.last_time_screenshot
        while dt < period:
            dt = time.time() - self.last_time_screenshot
        self.last_time_screenshot = time.time()

    def _take_screenshots(self):
        while True:
            self.wait_before_next_shot()

            frame = self._screenshot_taker.get_fast_screenshot()
            [b, g, r, a] = cv2.split(frame)
            frame = cv2.merge([b, g, r])
            self._on_screenshot({"frame": frame})
            if self._stop:
                break

    def stop(self):
        self._stop = True
        if self._screenshot_thread.is_alive():
            self._screenshot_thread.join()

    def __del__(self):
        self.stop()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

