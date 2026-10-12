# camera.py
import logging
import threading
import time

import cv2

log = logging.getLogger("camera")


class LatestFrameReader:
    """Đọc camera ở luồng nền, luôn giữ frame mới nhất (không bị trễ do buffer)."""

    def __init__(self, source):
        self.source = source
        self.cap = None
        self.item = None
        self.lock = threading.Lock()
        self.running = True
        self.connected = False
        # Mở camera trong luồng nền để không treo UI
        threading.Thread(target=self._loop, daemon=True).start()

    def _set_connected(self, value):
        # Chỉ log khi trạng thái thật sự thay đổi -> console không bị spam
        if value != self.connected:
            self.connected = value
            log.info("Camera đã kết nối" if value else "Mất kết nối camera, đang thử lại...")

    def _open_cam(self):
        if isinstance(self.source, int):
            cap = cv2.VideoCapture(self.source, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(self.source)
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 2000)
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 2000)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def _release(self):
        try:
            if self.cap is not None:
                self.cap.release()
        except Exception:
            pass

    def _loop(self):
        self.cap = self._open_cam()
        fails = 0
        is_video_file = isinstance(self.source, str) and not self.source.startswith("http")

        while self.running:
            if self.cap is None or not self.cap.isOpened():
                self._set_connected(False)
                time.sleep(0.5)
                if not self.running:
                    break
                self.cap = self._open_cam()
                continue

            ok, frame = self.cap.read()
            if ok and frame is not None:
                self._set_connected(True)
                fails = 0
                with self.lock:
                    self.item = (frame, time.monotonic())
                if is_video_file:
                    time.sleep(0.033)  # giữ ~30fps khi phát từ file
            else:
                if is_video_file:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # lặp lại video
                    continue
                self._set_connected(False)
                fails += 1
                time.sleep(0.05)
                if fails > 40:  # ~2s không có frame -> mở lại
                    self._release()
                    if not self.running:
                        break
                    self.cap = self._open_cam()
                    fails = 0

        self._release()

    def read(self):
        """Trả về (frame, timestamp) mới nhất, hoặc None nếu chưa có frame mới."""
        with self.lock:
            it, self.item = self.item, None
        return it

    def stop(self):
        # Chỉ bật cờ dừng; luồng tự release cap để không làm treo cửa sổ chính
        self.running = False
