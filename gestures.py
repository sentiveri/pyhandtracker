# gestures.py - nhận diện cử chỉ và chạy các binding đăng ký trong actions.py
import logging
import math
from dataclasses import dataclass

import numpy as np

import registry
from config import *

log = logging.getLogger("gesture")

class OneEuro:
    """Bộ lọc One Euro: mượt khi tay đứng yên, bám sát khi tay di chuyển nhanh."""

    def __init__(self, min_cutoff=FILTER_MIN_CUTOFF, beta=FILTER_BETA, d_cutoff=1.0):
        self.min_cutoff, self.beta, self.d_cutoff = min_cutoff, beta, d_cutoff
        self.x = None
        self.dx = 0.0
        self.t = None

    @staticmethod
    def _alpha(dt, cutoff):
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, x, t):
        if self.x is None:
            self.x, self.t = x, t
            return x
        dt = max(t - self.t, 1e-3)
        dx = (x - self.x) / dt
        ad = self._alpha(dt, self.d_cutoff)
        self.dx = ad * dx + (1 - ad) * self.dx
        a = self._alpha(dt, self.min_cutoff + self.beta * abs(self.dx))
        self.x = a * x + (1 - a) * self.x
        self.t = t
        return self.x


def dist(a, b, w, h):
    return math.hypot((a.x - b.x) * w, (a.y - b.y) * h)


def palm_metrics(lm, w, h):
    """Tâm lòng bàn tay (px) và kích thước (cổ tay -> gốc ngón giữa)."""
    cx = sum(lm[i].x for i in PALM_IDS) / len(PALM_IDS) * w
    cy = sum(lm[i].y for i in PALM_IDS) / len(PALM_IDS) * h
    size = math.hypot((lm[0].x - lm[9].x) * w, (lm[0].y - lm[9].y) * h)
    return cx, cy, size


def _pt(p, w, h):
    return np.array([p.x * w, p.y * h, p.z * w])


def finger_angles(lm, w, h):
    """Góc gập tại khớp PIP của 4 ngón (độ). ~180 = duỗi thẳng, nhỏ = co lại."""
    out = []
    for mcp, pip, dip in FINGER_JOINTS:
        v1 = _pt(lm[mcp], w, h) - _pt(lm[pip], w, h)
        v2 = _pt(lm[dip], w, h) - _pt(lm[pip], w, h)
        c = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-9)
        out.append(math.degrees(math.acos(max(-1.0, min(1.0, c)))))
    return out


def pose_features(lm, w, h, size):
    """Vector đặc trưng: 4 góc ngón, 4 tỉ lệ đầu ngón/cổ tay, pinch, thumb_out, thumb_lift."""
    size = max(size, 1)
    angles = finger_angles(lm, w, h)
    ratios = [dist(lm[t], lm[0], w, h) / size for t in (8, 12, 16, 20)]
    pinch = dist(lm[4], lm[8], w, h) / size
    thumb_out = dist(lm[4], lm[5], w, h) / size
    thumb_lift = (lm[2].y - lm[4].y) * h / size
    return angles + ratios + [pinch, thumb_out, thumb_lift]


def classify(lm, w, h, size, feat, was_pinching):
    """Trả về (tên cử chỉ, đang pinch). Tên nằm trong registry.POSES."""
    angles, ratios = feat[0:4], feat[4:8]
    pinch, thumb_out, thumb_lift = feat[8], feat[9], feat[10]

    ext = [a > EXT_ANGLE for a in angles]
    curled = [a < CURL_ANGLE and r < CURL_RATIO for a, r in zip(angles, ratios)]
    others = sum(ext[1:])

    # Hysteresis: vào pinch cần PINCH_ON, thoát khi vượt PINCH_OFF -> không bị nhấp nháy
    pinching = (pinch < PINCH_OFF) if was_pinching else (pinch < PINCH_ON and others >= 2)
    all_curled = all(curled)
    thumbs_up = all_curled and thumb_out > THUMB_OUT and thumb_lift > THUMB_UP_LIFT and not pinching
    fist = all_curled and not thumbs_up and not pinching
    peace = (ext[0] and ext[1] and angles[2] < PEACE_CURL_ANGLE
             and angles[3] < PEACE_CURL_ANGLE and not pinching)

    # Chỉ ngón trỏ nằm ngang -> trái/phải (ảnh đã lật gương nên dx>0 = sang phải)
    only_index = ext[0] and not any(ext[1:])
    dx = (lm[8].x - lm[5].x) * w
    dy = (lm[8].y - lm[5].y) * h
    horizontal = abs(dx) > 1.2 * abs(dy) and math.hypot(dx, dy) > 0.35 * max(size, 1)

    if pinching: name = "pinch"
    elif thumbs_up: name = "thumbs_up"
    elif fist: name = "fist"
    elif peace: name = "peace"
    elif only_index and horizontal and dx > 0: name = "point_right"
    elif only_index and horizontal and dx < 0: name = "point_left"
    elif sum(ext) >= 4: name = "open"
    else: name = "other"
    return name, pinching


@dataclass
class Hand:
    """Thông tin bàn tay truyền vào action (hold/while_pose)."""
    index: int        # 0 = tay bên trái màn hình
    x: float          # vị trí tâm lòng bàn tay, 0..1 (đã lọc mượt)
    y: float
    size: float       # cỡ bàn tay / chiều cao khung hình
    pose: str
    landmarks: list   # 21 điểm MediaPipe (toạ độ chuẩn hoá) để tự tính cử chỉ riêng


def _call(b, *args):
    # Lỗi trong action không làm sập chương trình
    try:
        b.fn(*args)
    except Exception:
        log.exception("Lỗi trong action '%s'", b.label)


class HandState:
    def __init__(self):
        self.raw = (0.0, 0.0, 1.0)
        self.last_seen = 0.0
        self.born = 0.0
        self.fx, self.fy, self.fs = OneEuro(), OneEuro(), OneEuro(1.0, 0.01)
        self.feat = None
        self.pinching = False
        self.hold = {}     # binding -> [lúc bắt đầu giữ, còn được bắn?]
        self.anchor = {}   # binding -> vị trí gốc của drag

    def _reset_pose(self):
        self.pinching = False
        self.hold.clear()
        self.anchor.clear()

    def _hold(self, b, now, shared, hud, tag):
        st = self.hold.setdefault(b, [now, True])
        held = now - st[0]
        # lockout_until dùng chung giữa các tay để 2 tay không bắn lệnh cùng lúc
        if st[1] and held >= b.seconds and now >= shared["lockout_until"]:
            st[1] = False
            shared["lockout_until"] = now + b.cooldown
            log.info(b.label)
            _call(b)
        if st[1]:
            pct = min(held / b.seconds, 1) * 100 if b.seconds else 100
            hud.append((f"{tag}{b.label} {pct:.0f}%", GREEN))
        else:
            hud.append((f"{tag}{b.label} - release", MAGENTA))

    def _drag(self, b, sx, sy, ss, hud, tag):
        vertical = b.axis == "y"
        pos = sy if vertical else sx
        anchor = self.anchor.setdefault(b, pos)
        unit = max(b.step * ss, 1e-3)
        steps = int(((anchor - pos) if vertical else (pos - anchor)) / unit)
        if steps:
            steps = max(-b.max_steps, min(b.max_steps, steps))
            self.anchor[b] += -steps * unit if vertical else steps * unit
            _call(b, steps)
        hud.append((f"{tag}{b.label}: move hand {'up/down' if vertical else 'left/right'}", GOLD))

    def _run(self, name, hand, now, sx, sy, ss, shared, hud, tag):
        # Cử chỉ đã thả -> reset trạng thái giữ / kéo của binding đó
        for b in [b for b in self.hold if b.pose != name]:
            del self.hold[b]
        for b in [b for b in self.anchor if b.pose != name]:
            del self.anchor[b]

        active = False
        for b in registry.drags:
            if b.pose == name:
                active = True
                self._drag(b, sx, sy, ss, hud, tag)
        for b in registry.holds:
            if b.pose == name:
                active = True
                self._hold(b, now, shared, hud, tag)
        for b in registry.whiles:
            if b.pose in (name, "any"):
                _call(b, hand)
        if not active:
            hud.append((tag + ("READY" if name == "other" else name.upper()), GREEN))

    def process(self, now, det, w, h, shared, hud, tag, index=0):
        lm, cx, cy, size = det
        self.last_seen = now
        self.raw = (cx, cy, size)

        sx, sy, ss = self.fx(cx, now), self.fy(cy, now), self.fs(size, now)

        # Làm mượt đặc trưng tư thế (EMA)
        feat = pose_features(lm, w, h, size)
        if self.feat is None:
            self.feat = feat
        else:
            a = POSE_SMOOTH
            self.feat = [a * n + (1 - a) * o for n, o in zip(feat, self.feat)]

        if now - self.born < ENTRY_GRACE_SEC:
            self._reset_pose()
            hud.append((tag + "HAND ENTERING...", YELLOW))
            return

        too_close = ss / h > MAX_PALM_FRAC
        near_edge = (sx < EDGE_MARGIN * w or sx > (1 - EDGE_MARGIN) * w or
                     sy < EDGE_MARGIN * h or sy > (1 - EDGE_MARGIN) * h)
        if too_close or near_edge:
            self._reset_pose()
            hud.append((tag + ("TOO CLOSE - MOVE BACK" if too_close else "NEAR EDGE"), ORANGE))
            return

        name, self.pinching = classify(lm, w, h, size, self.feat, self.pinching)
        if SHOW_DEBUG:
            hud.append((tag + "ang " + " ".join(f"{a:.0f}" for a in self.feat[:4]) +
                        f"  [{name}]", WHITE))

        hand = Hand(index, sx / w, sy / h, ss / h, name, lm)
        self._run(name, hand, now, sx, sy, ss, shared, hud, tag)


def assign(states, dets, now):
    """Ghép các bàn tay phát hiện được với HandState cũ (gần nhất trước)."""
    states[:] = [s for s in states if now - s.last_seen <= LOST_RESET_SEC]
    cand = []
    for di, (_, cx, cy, size) in enumerate(dets):
        for s in states:
            d = math.hypot(cx - s.raw[0], cy - s.raw[1])
            if d <= MATCH_FACTOR * max(size, s.raw[2]):
                cand.append((d, di, id(s), s))
    cand.sort(key=lambda c: c[0])

    used_d, used_s, pairs = set(), set(), []
    for d, di, sid, s in cand:
        if di in used_d or sid in used_s: continue
        used_d.add(di)
        used_s.add(sid)
        pairs.append((s, dets[di]))

    # Tay mới: tạo state; nếu đã đủ MAX_HANDS thì bỏ state cũ nhất chưa được ghép
    for di, det in enumerate(dets):
        if di in used_d: continue
        if len(states) >= MAX_HANDS:
            free = [s for s in states if id(s) not in used_s]
            if not free: continue
            states.remove(min(free, key=lambda s: s.last_seen))
        s = HandState()
        s.raw = (det[1], det[2], det[3])
        s.last_seen = now
        s.born = now
        states.append(s)
        used_s.add(id(s))
        pairs.append((s, det))

    pairs.sort(key=lambda p: p[1][1])  # sắp theo vị trí x: H1 = tay bên trái
    return pairs