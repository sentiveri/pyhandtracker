# GESTURE TRACKER

[English](README.md) | **Tiếng Việt**

Bộ khung nhận diện cử chỉ tay qua webcam (MediaPipe + OpenCV). **Không có sẵn tính năng nào**
(không play/pause, không chỉnh âm lượng...). Bạn tự gắn cử chỉ với hành động trong `actions.py`.

## Cài đặt

1. Cài [Python](https://www.python.org/downloads/) 3.10 - 3.12.
2. `pip install -r requirements.txt`
3. Cần file `hand_landmarker.task` cùng thư mục với `main.py`
   ([tải ở đây](https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task)).
4. `python main.py`

Mặc định `actions.py` chỉ có 2 demo in ra console (nắm tay, pinch kéo) để bạn thấy nó hoạt động.

## Thêm hành động

Chỉ sửa **`actions.py`**:

```python
import pyautogui
from registry import hold, drag, while_pose

@hold("fist", seconds=0.6)          # giữ nắm tay 0.6s -> gọi 1 lần
def play_pause():
    pyautogui.press("playpause")

@drag("pinch", axis="y")            # chụm tay + kéo lên/xuống -> steps (+ = lên)
def volume(steps):
    pyautogui.press("volumeup" if steps > 0 else "volumedown", presses=abs(steps))

@while_pose("open")                 # gọi mỗi frame khi đang xoè tay
def track(hand):
    print(hand.x, hand.y)           # 0..1, đã lọc mượt
```

| Decorator | Khi nào gọi | Tham số của hàm |
|---|---|---|
| `@hold(pose, seconds=0.6, cooldown=1.0)` | giữ cử chỉ đủ lâu, thả tay mới bắn lại | không có |
| `@drag(pose, axis="y", step=0.35, max_steps=5)` | giữ cử chỉ và di chuyển tay | `steps` (số nguyên có dấu; `y`: + là lên, `x`: + là sang phải) |
| `@while_pose(pose="any")` | mỗi frame khi đang ở cử chỉ đó (`"any"` = mọi cử chỉ) | `hand` |

Các `pose`: `pinch`, `thumbs_up`, `fist`, `peace`, `point_right`, `point_left`, `open`, `other`.

`hand` có: `x`, `y`, `size`, `pose`, `index` (0 = tay trái màn hình) và `landmarks` (21 điểm MediaPipe,
dùng để tự tính cử chỉ riêng). Lỗi trong action sẽ được log ra, không làm sập chương trình.

## Phím tắt

`1` / `2` / `3`: đổi camera (laptop / USB / URL) · `u`: nhập URL · `m`: đổi kiểu hiển thị · `q`: thoát

## Camera

- Số camera chỉnh ở `config.py` (`LAPTOP_CAM`, `USB_CAM`). Trên Windows, OBS Virtual Camera và DroidCam
  cũng chiếm một số thứ tự, nên nếu ra nhầm camera thì đổi số hoặc tắt chúng.
- Điện thoại làm camera qua DroidCam + cáp USB: bật USB debugging, rồi chạy
  `adb forward tcp:4747 tcp:4747` và bấm `3`. Chạy lại lệnh này mỗi lần rút/cắm cáp.

## Cấu trúc

| File | Vai trò |
|---|---|
| `actions.py` | **gắn cử chỉ -> hành động (file bạn sửa)** |
| `registry.py` | các decorator `hold` / `drag` / `while_pose` |
| `gestures.py` | nhận diện cử chỉ, lọc nhiễu, chạy các binding |
| `camera.py`, `display.py`, `main.py` | đọc camera, vẽ HUD, vòng lặp chính |
| `config.py` | ngưỡng nhận diện, camera |

## Ghi công

Model `hand_landmarker.task` là của Google MediaPipe (Apache 2.0).
