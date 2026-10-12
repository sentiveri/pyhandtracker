# config.py
import os

URL = "http://127.0.0.1:4747/video.mjpg"
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hand_landmarker.task")

# Số thứ tự camera (Windows có thể bị lệch nếu có OBS/DroidCam, xem README)
LAPTOP_CAM = 0
USB_CAM = 1

MAX_HANDS = 2
MATCH_FACTOR = 2.5          # khoảng cách tối đa để ghép tay giữa 2 frame
PROCESS_WIDTH = 640
PROCESS_HEIGHT = 480

# ---- Lọc nhiễu ----
FILTER_MIN_CUTOFF = 1.2
FILTER_BETA = 0.02
POSE_SMOOTH = 0.6

# ---- Quá gần / sát mép ----
MAX_PALM_FRAC = 0.45
EDGE_MARGIN = 0.0

# ---- Thời gian chờ ----
LOST_RESET_SEC = 0.3        # mất tay quá lâu thì reset trạng thái
ENTRY_GRACE_SEC = 0.5       # bỏ qua cử chỉ ngay khi tay vừa xuất hiện

PALM_IDS = (0, 5, 9, 13, 17)

# ---- Ngưỡng tư thế ngón tay ----
EXT_ANGLE = 150
CURL_ANGLE = 95
CURL_RATIO = 1.25
PEACE_CURL_ANGLE = 110
THUMB_OUT = 0.60
THUMB_UP_LIFT = 0.25
PINCH_ON = 0.30
PINCH_OFF = 0.50

DISPLAY_MODES = ["hand cutout", "skeleton only", "skeleton on blur", "RAW CAMERA"]
DISPLAY_MODE = 0
BLUR_BLOCKS = 24
SHOW_DEBUG = False          # bật để xem góc các ngón trên HUD

HAND_COLORS = [(255, 255, 0), (0, 165, 255)]
WHITE, GREEN, RED, YELLOW, ORANGE, MAGENTA, GOLD, CYAN = (
    (255, 255, 255), (0, 255, 0), (0, 0, 255), (0, 255, 255),
    (0, 165, 255), (255, 0, 255), (255, 200, 0), (255, 255, 0))

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20), (0, 17),
]
FINGER_JOINTS = [(5, 6, 7), (9, 10, 11), (13, 14, 15), (17, 18, 19)]
