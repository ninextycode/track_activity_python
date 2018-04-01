import time
import cv2
import numpy as np
import datetime
import json

import action_watcher as aw
import screencapture as sc
import json_writer as jw
import numpy_json as nj
import window_query


genymotion_panel_size = 52
offset, size = window_query.query()
size = (size[0]-genymotion_panel_size, size[1])

# dim_to_save = tuple([d // 2 for d in dim])
dim_to_save = (160, 96)
print(offset, size)



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

        data["frame"] = cv2.resize(src=data["frame"],
                                   dsize=dim_to_save, interpolation=cv2.INTER_AREA)
        image = data["frame"]

        screen_writer.add_to_write(data)

    def action_filter(data):
        global last_time_action
        dt = time.time() - last_time_action
        print("action frequency {}".format(1 / dt))
        last_time_action = time.time()
        actions_writer.add_to_write(data)

    actions_watcher = aw.ActionWatcher(on_event=action_filter)
    screenshot_taker = sc.ScreenCapturer(*offset, *size,
                                         on_screenshot=screenshot_filter,
                                         cap_fps=40)

    actions_watcher.start()
    screenshot_taker.start()

    try:
        while True:
            time.sleep(0.0001)
            cv2.imshow("image", cv2.resize(src=image, dsize=size, interpolation=cv2.INTER_NEAREST))
            cv2.waitKey(1)

    except KeyboardInterrupt:
        pass

    screenshot_taker.stop()
    actions_watcher.stop()

    cv2.destroyAllWindows()


def trim(s):
    return s.replace(" ", "_").replace(":", "_").replace(".", "_").replace("-", "_")


postfix = datetime.datetime.now()
screen_filename = "data/screen_{}".format(postfix)
actions_filename = "data/actions_{}".format(postfix)
window_parameters_filename = "data/window_parameters_{}"\
    .format(postfix)

screen_filename = trim(screen_filename) + ".txt"
actions_filename = trim(actions_filename) + ".txt"
window_parameters_filename = \
    trim(window_parameters_filename) + ".txt"

window_parameters = {
    "offset": list(offset),
    "size": list(size)
}
json.dump(window_parameters,
          open(window_parameters_filename, "w"))

with jw.JsonWriter(screen_filename, json_encoder=nj.NumpyEncoder) as screen_writer, \
        jw.JsonWriter(actions_filename) as actions_writer:
    run(screen_writer, actions_writer)
