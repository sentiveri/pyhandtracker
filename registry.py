# registry.py - nơi đăng ký "cử chỉ -> hành động". Dùng trong actions.py
from dataclasses import dataclass
from typing import Callable

# Các tư thế tay engine nhận diện được
POSES = ("pinch", "thumbs_up", "fist", "peace", "point_right", "point_left", "open", "other")

holds, drags, whiles = [], [], []


@dataclass(eq=False)
class Binding:
    pose: str
    fn: Callable
    label: str
    seconds: float = 0.0     # hold: thời gian giữ
    cooldown: float = 1.0    # hold: nghỉ sau khi bắn (dùng chung giữa các tay)
    axis: str = "y"          # drag: "x" hoặc "y"
    step: float = 0.35       # drag: 1 bước = step * kích thước bàn tay
    max_steps: int = 5       # drag: tối đa số bước mỗi lần gọi


def _check(pose, allow_any=False):
    if pose == "any" and allow_any:
        return
    if pose not in POSES:
        raise ValueError(f"Cử chỉ '{pose}' không có. Chọn một trong: {', '.join(POSES)}")


def _label(fn, label):
    return label or fn.__name__.replace("_", " ").upper()


def hold(pose, seconds=0.6, cooldown=1.0, label=None):
    """Giữ cử chỉ `seconds` giây -> gọi fn() một lần, thả tay mới bắn lại được."""
    _check(pose)

    def deco(fn):
        holds.append(Binding(pose, fn, _label(fn, label), seconds=seconds, cooldown=cooldown))
        return fn
    return deco


def drag(pose, axis="y", step=0.35, max_steps=5, label=None):
    """Giữ cử chỉ và di chuyển tay -> gọi fn(steps). steps > 0: tay đi lên (y) / sang phải (x)."""
    _check(pose)
    if axis not in ("x", "y"):
        raise ValueError("axis phải là 'x' hoặc 'y'")

    def deco(fn):
        drags.append(Binding(pose, fn, _label(fn, label), axis=axis, step=step, max_steps=max_steps))
        return fn
    return deco


def while_pose(pose="any", label=None):
    """Gọi fn(hand) MỖI FRAME khi tay đang ở cử chỉ này ("any" = mọi cử chỉ)."""
    _check(pose, allow_any=True)

    def deco(fn):
        whiles.append(Binding(pose, fn, _label(fn, label)))
        return fn
    return deco
