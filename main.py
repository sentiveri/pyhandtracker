# main.py
# adb devices
# adb forward tcp:4747 tcp:4747
import os
import sys
import warnings

# Tắt log rác của MediaPipe / TFLite / OpenCV (phải đặt TRƯỚC khi import chúng)
os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("OPENCV_LOG_LEVEL", "SILENT")
warnings.filterwarnings("ignore")

import logging
import time
import tkinter as tk
from tkinter import simpledialog

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from camera import LatestFrameReader
from config import *
from display import draw_hud, draw_skeleton, make_base, paste_hand, put_text
import registry
from gestures import HandState, assign, palm_metrics

import actions  # noqa: F401  (import để các @hold/@drag trong actions.py được đăng ký)

try:
    from absl import logging as absl_logging
    absl_logging.set_verbosity(absl_logging.ERROR)
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("main")

WIN = "Gesture Controller"
MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
             "hand_landmarker/float16/latest/hand_landmarker.task")


def build_detector():
    return vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=MODEL_PATH),
        num_hands=MAX_HANDS,
        running_mode=vision.RunningMode.VIDEO,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    ))


def ask_custom_url(current_url):
    """Hộp thoại nhỏ để dán URL camera mới. Trả về None nếu huỷ."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    new_url = simpledialog.askstring("Webcam URL", "Nhập đường dẫn URL của Camera:",
                                     initialvalue=current_url)
    root.destroy()
    return new_url.strip() if new_url and new_url.strip() else None


def waiting_screen(label, src):
    blank = np.zeros((PROCESS_HEIGHT or 480, PROCESS_WIDTH or 640, 3), dtype=np.uint8)
    put_text(blank, f"Dang ket noi: {label}...", (20, 40), YELLOW, 0.6)
    put_text(blank, f"Nguon: {src}", (20, 75), WHITE, 0.5, 1)
    put_text(blank, "[1] Laptop | [2] USB | [3] URL | [U] Doi URL | [Q] Thoat",
             (20, blank.shape[0] - 20), CYAN, 0.48, 1)
    return blank


def main():
    if not os.path.exists(MODEL_PATH):
        sys.exit(f"Không tìm thấy '{MODEL_PATH}'. Tải về tại:\n{MODEL_URL}")

    detector = build_detector()

    sources = {
        ord("1"): ("Laptop Cam", LAPTOP_CAM),
        ord("2"): ("USB Cam", USB_CAM),
        ord("3"): ("URL Cam", URL),
    }
    label, src = sources[ord("1")]
    reader = LatestFrameReader(src)

    states, shared = [], {"lockout_until": 0.0}
    mode, last_ts, prev_t, fps = DISPLAY_MODE, 0, None, 0.0
    last_frame_t = time.monotonic()

    def switch(new_label, new_src):
        nonlocal reader, label, src
        if new_src == src:
            return
        log.info("Đổi nguồn: %s", new_label)
        reader.stop()
        label, src = new_label, new_src
        reader = LatestFrameReader(src)
        states.clear()

    n = len(registry.holds) + len(registry.drags) + len(registry.whiles)
    if n:
        log.info("Đã đăng ký %d action từ actions.py", n)
    else:
        log.warning("Chưa có action nào - thêm trong actions.py")
    log.info("Sẵn sàng - 1/2/3: camera | u: nhập URL | m: đổi nền | q: thoát")
    cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN, 640, 480)

    while True:
        item = reader.read()

        if item is None:
            # Chưa có frame mới. Chỉ hiện màn hình chờ khi mất frame > 1s,
            # tránh nhấp nháy khi vòng lặp chạy nhanh hơn camera.
            if time.monotonic() - last_frame_t > 1.0:
                cv2.imshow(WIN, waiting_screen(label, src))
                key = cv2.waitKey(30) & 0xFF
            else:
                key = cv2.waitKey(2) & 0xFF
        else:
            frame, now = item
            last_frame_t = time.monotonic()
            if PROCESS_WIDTH and PROCESS_HEIGHT:
                frame = cv2.resize(frame, (PROCESS_WIDTH, PROCESS_HEIGHT),
                                   interpolation=cv2.INTER_AREA)
            frame = cv2.flip(frame, 1)  # lật gương cho tự nhiên
            h, w = frame.shape[:2]

            if prev_t is not None and now > prev_t:
                inst = 1.0 / (now - prev_t)
                fps = 0.9 * fps + 0.1 * inst if fps else inst
            prev_t = now

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            last_ts = max(int(now * 1000), last_ts + 1)  # timestamp phải tăng dần
            result = detector.detect_for_video(mp_image, last_ts)

            dets = [(lm, *palm_metrics(lm, w, h)) for lm in result.hand_landmarks]
            pairs = assign(states, dets, now)

            display = make_base(frame, mode)
            if mode == 0:
                for _, det in pairs:
                    display = paste_hand(display, frame, det[0], w, h, det[3])
            for i, (_, det) in enumerate(pairs):
                draw_skeleton(display, det[0], w, h, HAND_COLORS[i % len(HAND_COLORS)])

            hud = []
            if not pairs:
                hud.append(("NO HAND SAW", RED))
            for i, (st, det) in enumerate(pairs):
                tag = f"H{i + 1} " if len(pairs) > 1 else ""
                st.process(now, det, w, h, shared, hud, tag, i)

            lag_ms = (time.monotonic() - now) * 1000
            draw_hud(display, hud)
            put_text(display, f"Cam: {label} ([1]Laptop [2]USB [3]URL [U]Edit)",
                     (20, h - 38), CYAN, 0.45, 1)
            put_text(display, f"{DISPLAY_MODES[mode]} (m)   {fps:.0f} fps   lag {lag_ms:.0f} ms",
                     (20, h - 15), (200, 200, 200), 0.5, 1)
            cv2.imshow(WIN, display)
            key = cv2.waitKey(1) & 0xFF

        # Bấm nút X của cửa sổ cũng thoát được
        if cv2.getWindowProperty(WIN, cv2.WND_PROP_VISIBLE) < 1:
            break

        if key == ord("q"):
            break
        elif key == ord("m"):
            mode = (mode + 1) % len(DISPLAY_MODES)
        elif key in sources:
            switch(*sources[key])
        elif key == ord("u"):
            url = ask_custom_url(sources[ord("3")][1])
            if url:
                sources[ord("3")] = ("URL Cam", url)
                switch(*sources[ord("3")])

    reader.stop()
    cv2.destroyAllWindows()
    log.info("Đã thoát")


if __name__ == "__main__":
    main()