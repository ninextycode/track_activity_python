import subprocess
import re


def query():
    patterns = {
        "x": r"Absolute upper-left X: +(?P<x>\d+)",
        "y": r"Absolute upper-left Y: +(?P<y>\d+)",
        "width": r"Width: +(?P<width>\d+)",
        "height": r"Height: +(?P<height>\d+)"
    }
    data = {}

    text = subprocess.check_output(["xwininfo"]).decode()

    for line in text.split("\n"):
        for key in patterns.keys():
            match = re.search(patterns[key], line)
            if match is not None:
                data[key] = int(match.group(key))

    return (data["x"], data["y"]), (data["width"], data["height"])


if __name__ == "__main__":
    print(query())
