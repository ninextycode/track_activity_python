# Record screen+actions in python

Record screen as well as record input (mouse position+keys pressed).

Screen captured implemented with https://github.com/ninextycode/fast_screenshots_python 

Input captured implemented with https://github.com/JeffHoogland/pyxhook

Screen and input are captured in two separate threads, using ScreenCapturer and ActionWatcher classes respectively.
Data is written in separate threads as well, using JsonWriter class.
