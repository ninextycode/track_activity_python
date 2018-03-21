import time
import cv2
import numpy as np
import datetime

import action_watcher as aw
import screencapture as sc
import json_writer as jw
import numpy_json as nj
import window_query


offset, dim = window_query.query()
# dim_to_save = tuple([d // 2 for d in dim])
dim_to_save = (320, 192)
print(offset, dim)


last_time_screenshot = time.time()
last_time_action = time.time()
image = np.random.rand(*dim_to_save, 3) * 255
image = image.astype(np.uint8)


def run(screen_writer, actions_writer):
    def screenshot_filter(data):
        global last_time_screenshot, image
        dt = time.time() - last_time_screenshot
        print("screenshot frequency {}".format(1 / dt))
        last_time_screenshot = time.time()

        data["frame"] = cv2.resize(src=data["frame"], dsize=dim_to_save, interpolation=cv2.INTER_AREA)
        image = data["frame"]

        screen_writer.add_to_write(data)

    def action_filter(data):
        global last_time_action
        dt = time.time() - last_time_action
        print("action frequency {}".format(1 / dt))
        last_time_action = time.time()
        actions_writer.add_to_write(data)

    actions_watcher = aw.ActionWatcher(on_event=action_filter)
    screenshot_taker = sc.ScreenCapturer(*offset, *dim, on_screenshot=screenshot_filter, cap_fps=20)

    actions_watcher.start()
    screenshot_taker.start()

    try:
        while True:
            time.sleep(0.001)
            cv2.imshow("image", cv2.resize(src=image, dsize=dim, interpolation=cv2.INTER_NEAREST))
            cv2.waitKey(1)

    except KeyboardInterrupt:
        pass

    screenshot_taker.stop()
    actions_watcher.stop()

    cv2.destroyAllWindows()


def trim(s):
    return s.replace(" ", "_").replace(":", "_").replace(".", "_").replace("-", "_")


postfix = datetime.datetime.now()
screen_filename = "screen_{}".format(postfix)
actions_filename = "actions_{}".format(postfix)

screen_filename = trim(screen_filename) + ".txt"
actions_filename = trim(actions_filename) + ".txt"

with jw.JsonWriter(screen_filename, json_encoder=nj.NumpyEncoder) as screen_writer, \
        jw.JsonWriter(actions_filename) as actions_writer:
    run(screen_writer, actions_writer)
