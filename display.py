# display.py - vẽ HUD, khung xương, nền
import cv2
import numpy as np

from config import BLUR_BLOCKS, HAND_CONNECTIONS


def put_text(img, text, org, color, scale=0.55, thick=2):
    """Chữ có viền đen để dễ đọc trên mọi nền."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, text, org, font, scale, (0, 0, 0), thick + 2, cv2.LINE_AA)
    cv2.putText(img, text, org, font, scale, color, thick, cv2.LINE_AA)


def draw_hud(img, lines):
    for i, (text, color) in enumerate(lines):
        put_text(img, text, (20, 35 + i * 26), color)


def make_base(frame, mode):
    h, w = frame.shape[:2]
    if mode == 1:                      # chỉ khung xương trên nền đen
        return np.zeros_like(frame)
    if mode == 3:                      # camera gốc
        return frame.copy()
    # nền mờ kiểu pixel hoá
    small = cv2.resize(frame, (max(w // BLUR_BLOCKS, 1), max(h // BLUR_BLOCKS, 1)),
                       interpolation=cv2.INTER_AREA)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)


def paste_hand(display, frame, lm, w, h, palm_size):
    """Dán vùng bàn tay (mask mềm) từ frame gốc lên nền mờ."""
    pts = np.array([(int(p.x * w), int(p.y * h)) for p in lm], np.int32)
    pad = int(max(palm_size * 0.4, 12))
    x0, x1 = max(int(pts[:, 0].min()) - pad, 0), min(int(pts[:, 0].max()) + pad, w)
    y0, y1 = max(int(pts[:, 1].min()) - pad, 0), min(int(pts[:, 1].max()) + pad, h)
    if x1 - x0 < 4 or y1 - y0 < 4:
        return display
    mask = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.fillConvexPoly(mask, cv2.convexHull(pts - np.array([x0, y0], np.int32)), 255)
    k = max(15, int(palm_size * 0.3)) | 1
    mask = cv2.dilate(mask, np.ones((k, k), np.uint8))
    mask = cv2.GaussianBlur(mask, (21, 21), 0)
    alpha = (mask.astype(np.float32) / 255.0)[..., None]
    display[y0:y1, x0:x1] = (frame[y0:y1, x0:x1] * alpha +
                             display[y0:y1, x0:x1] * (1 - alpha)).astype(np.uint8)
    return display


def draw_skeleton(img, lm, w, h, color):
    for a, b in HAND_CONNECTIONS:
        cv2.line(img, (int(lm[a].x * w), int(lm[a].y * h)),
                 (int(lm[b].x * w), int(lm[b].y * h)), color, 2, cv2.LINE_AA)
    for p in lm:
        cv2.circle(img, (int(p.x * w), int(p.y * h)), 3, (0, 0, 255), -1, cv2.LINE_AA)
