# actions.py - FILE DUY NHẤT CẦN SỬA: gắn cử chỉ với hành động bạn muốn.
#
# Cử chỉ: pinch, thumbs_up, fist, peace, point_right, point_left, open, other
#
#   @hold("fist", seconds=0.6)       giữ cử chỉ -> gọi fn() một lần
#   @drag("pinch", axis="y")         giữ cử chỉ + di chuyển tay -> gọi fn(steps)
#   @while_pose("open")              gọi fn(hand) mỗi frame (hand.x, hand.y, hand.size, ...)
import logging

from registry import drag, hold, while_pose  # noqa: F401

log = logging.getLogger("actions")

# ---- Demo: chỉ in ra console để thấy cử chỉ hoạt động. Xoá/thay bằng của bạn. ----

@hold("fist")
def fist():
    log.info("Nắm tay!")


@drag("pinch", axis="y")
def pinch_drag(steps):
    log.info("Pinch kéo %+d", steps)


# ---- Ví dụ điều khiển media (bỏ comment + `pip install pyautogui`) ----
#
# import pyautogui
# pyautogui.PAUSE = 0
# pyautogui.FAILSAFE = False
#
# @hold("fist")
# def play_pause():
#     pyautogui.press("playpause")
#
# @hold("point_right", seconds=0.35)
# def next_track():
#     pyautogui.press("nexttrack")
#
# @drag("pinch", axis="y")
# def volume(steps):
#     pyautogui.press("volumeup" if steps > 0 else "volumedown", presses=abs(steps))
