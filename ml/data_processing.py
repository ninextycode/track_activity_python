top_corner = (3, 150)
size = (6, 6)
bottom_corner = (top_corner[0] + size[0], top_corner[1] + size[1])


def get_ingame_cross(image):
    return image[top_corner[0]:bottom_corner[0], top_corner[1]:bottom_corner[1]]


ranges = [0, 255]
histSize = [32]
[cross1, cross2, cross3] = [json.loads(data, object_hook=nj.json_numpy_obj_hook)["frame"]
                            for data in open("../data/ingame_crosses_at_3_150.txt").readlines()]


def correl(im1, im2, channel=0):  # by default use zero channel = blue in bgr
    h1 = cv2.calcHist([im1], [channel], None, histSize, ranges)
    h2 = cv2.calcHist([im2], [channel], None, histSize, ranges)

    return np.abs(cv2.compareHist(h1, h2, method=cv2.HISTCMP_CORREL))


def correl_max(im1, images, chammel=0):
    return np.max([correl(im1, imX, chammel) for imX in images])


def is_game(image):
    return correl_max(get_ingame_cross(image), [cross1, cross2, cross3]) > 0.8


def read_actions_data(postfix):
    with open("../data/actions_{}.txt".format(postfix)) as f:
        data = [json.loads(s, object_hook=nj.json_numpy_obj_hook)
                for s in f.readlines()]
    return data


def read_window_data(postfix):
    with open("../data/window_parameters_{}.txt".format(postfix)) as f:
        data = json.load(f, object_hook=nj.json_numpy_obj_hook)
    return data


def screen_data_generator(postfix):
    with open("../data/screen_{}.txt".format(postfix)) as screen_f:
        for s in screen_f:
            screen = json.loads(s, object_hook=nj.json_numpy_obj_hook)
            if is_game(screen["frame"]):
                yield screen
    return


def actions_data_generator(postfix):
    with open("../data/actions_{}.txt".format(postfix)) as actions_f:
        for s in actions_f:
            yield json.loads(s, object_hook=nj.json_numpy_obj_hook)
    return


def get_datetime(s):
    return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f")


def data_generator(postfix):
    window_data = read_window_data(postfix)

    # actions data is a relatively small file compared to screen data, so we can read it all for convinience
    actions_data = read_actions_data(postfix)
    screen_gen = screen_data_generator(postfix)
    actions_gen = actions_data_generator(postfix)

    action_next = next(actions_gen)
    action_current = action_next

    def next_action(screen_data):
        # if action_next already later than screen data time
        if get_datetime(action_next["datetime"]) >= get_datetime(screen_data["datetime"]):
            return action_current

        for action in actions_gen:
            action_current = action_next
            action_next = action
            # stop iterating if next action wont be earlier than screenshot time
            if not (get_datetime(action_next["datetime"]) < get_datetime(screen_data["datetime"])):
                return action_current

    for screen_data in screen_gen:
        if get_datetime(action_next["datetime"]) < get_datetime(screen_data["datetime"]):
            for action in actions_gen:
                action_current = action_next
                action_next = action
                # stop iterating if next action wont be earlier than screenshot time
                if not (get_datetime(action_next["datetime"]) < \
                        get_datetime(screen_data["datetime"])):
                    break

        recorded_size = screen_data["frame"].shape[1::-1]

        relative_mouse_position = get_relative_mouse_position(action_current["mouse_position"],
                                                              window_data, recorded_size)

        left_btn_pressed = "mouse left" in action_current["mouse_buttons"]
        screen_data["relative_mouse_position"] = relative_mouse_position
        screen_data["left_btn_pressed"] = left_btn_pressed

        mouse_mask = np.zeros((*screen_data["frame"].shape[:2], 2), dtype=np.uint8)

        mouse_mask[relative_mouse_position[0], relative_mouse_position[1], left_btn_pressed] = 255
        screen_data["frame"] = np.concatenate([screen_data["frame"], mouse_mask], axis=2)

        yield screen_data
    return


def data_generator_with_changes(postfix):
    data_gen = data_generator(postfix)
    try:
        data_next = next(data_gen)
    except StopIteration:
        return

    for data in data_gen:
        data_current = data_next
        data_next = data

        data_current["next_mouse_move"] = data_next["relative_mouse_position"] - \
                                          data_current["relative_mouse_position"]
        data_current["next_left_btn_pressed"] = data_next["left_btn_pressed"]

        yield data_current

        data_current = data_next
    return

