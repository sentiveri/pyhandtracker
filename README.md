# GESTURE TRACKER

**English** | [Tiếng Việt](README.vi.md)

A bare-bones hand gesture framework for your webcam (MediaPipe + OpenCV). It ships with
**no built-in features** (no play/pause, no volume control...). You bind gestures to your own
actions in `actions.py`.

## Setup

1. Install [Python](https://www.python.org/downloads/) 3.10 - 3.12.
2. `pip install -r requirements.txt`
3. Put `hand_landmarker.task` next to `main.py`
   ([download](https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task)).
4. `python main.py`

By default `actions.py` only contains two demos that print to the console (fist, pinch-drag),
so you can see gestures being detected.

## Adding actions

Edit **`actions.py`** only:

```python
import pyautogui
from registry import hold, drag, while_pose

@hold("fist", seconds=0.6)          # hold a fist for 0.6s -> called once
def play_pause():
    pyautogui.press("playpause")

@drag("pinch", axis="y")            # pinch + move hand -> steps (+ = up)
def volume(steps):
    pyautogui.press("volumeup" if steps > 0 else "volumedown", presses=abs(steps))

@while_pose("open")                 # called every frame while the hand is open
def track(hand):
    print(hand.x, hand.y)           # 0..1, smoothed
```

| Decorator | Called when | Function argument |
|---|---|---|
| `@hold(pose, seconds=0.6, cooldown=1.0)` | the pose is held long enough; release to fire again | none |
| `@drag(pose, axis="y", step=0.35, max_steps=5)` | the pose is held while the hand moves | `steps` (signed int; `y`: + is up, `x`: + is right) |
| `@while_pose(pose="any")` | every frame while in that pose (`"any"` = any pose) | `hand` |

Available poses: `pinch`, `thumbs_up`, `fist`, `peace`, `point_right`, `point_left`, `open`, `other`.

`hand` provides `x`, `y`, `size`, `pose`, `index` (0 = leftmost hand on screen) and `landmarks`
(the 21 MediaPipe points, for writing your own gestures). Errors inside an action are logged and
never crash the program.

## Keys

`1` / `2` / `3`: switch camera (laptop / USB / URL) · `u`: enter URL · `m`: change display mode · `q`: quit

## Camera

- Camera indexes are set in `config.py` (`LAPTOP_CAM`, `USB_CAM`). On Windows, virtual cameras such as
  OBS Virtual Camera or DroidCam take up an index too, so if you get the wrong camera, change the
  index or turn them off.
- Using a phone as a camera via DroidCam over USB: enable USB debugging, run
  `adb forward tcp:4747 tcp:4747`, then press `3`. Re-run the command each time you replug the cable.

## Project layout

| File | Role |
|---|---|
| `actions.py` | **bind gestures to actions (the file you edit)** |
| `registry.py` | the `hold` / `drag` / `while_pose` decorators |
| `gestures.py` | gesture detection, filtering, running the bindings |
| `camera.py`, `display.py`, `main.py` | camera reader, HUD drawing, main loop |
| `config.py` | detection thresholds, cameras |

## Credits & license

The `hand_landmarker.task` model is from Google MediaPipe (Apache 2.0). Code is released under the [MIT License](LICENSE).
