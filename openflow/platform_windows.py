"""Focus-aware Windows text insertion, with best-effort text clipboard restoration."""
from __future__ import annotations

import ctypes as C
import os
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    hwnd: int
    pid: int


class WindowsIntegration:
    def __init__(self) -> None:
        self.available = os.name == "nt"
        self.last_external: Target | None = None
        self.clipboard_owner = None
        if not self.available:
            return
        self.user32 = C.windll.user32
        self.kernel32 = C.windll.kernel32
        self.pid = self.kernel32.GetCurrentProcessId()
        self.user32.GetForegroundWindow.restype = C.c_void_p
        self.user32.GetWindowThreadProcessId.argtypes = [C.c_void_p, C.POINTER(C.c_uint32)]
        self.user32.IsWindow.argtypes = [C.c_void_p]
        self.user32.SetForegroundWindow.argtypes = [C.c_void_p]
        self.user32.OpenClipboard.argtypes = [C.c_void_p]
        self.user32.EmptyClipboard.restype = C.c_int
        self.user32.GetClipboardSequenceNumber.restype = C.c_uint32
        self.user32.OpenClipboard.argtypes = [C.c_void_p]
        self.user32.GetClipboardData.argtypes = [C.c_uint]
        self.user32.GetClipboardData.restype = C.c_void_p
        self.user32.SetClipboardData.argtypes = [C.c_uint, C.c_void_p]
        self.user32.SetClipboardData.restype = C.c_void_p
        self.kernel32.GlobalAlloc.argtypes = [C.c_uint, C.c_size_t]
        self.kernel32.GlobalAlloc.restype = C.c_void_p
        self.kernel32.GlobalLock.argtypes = [C.c_void_p]
        self.kernel32.GlobalLock.restype = C.c_void_p
        self.kernel32.GlobalUnlock.argtypes = [C.c_void_p]
        self.kernel32.GlobalFree.argtypes = [C.c_void_p]
        self.kernel32.GlobalFree.restype = C.c_void_p
        self.kernel32.GlobalSize.argtypes = [C.c_void_p]
        self.kernel32.GlobalSize.restype = C.c_size_t

    def foreground(self) -> Target | None:
        if not self.available:
            return None
        hwnd = self.user32.GetForegroundWindow()
        if not hwnd:
            return None
        pid = C.c_uint32()
        self.user32.GetWindowThreadProcessId(hwnd, C.byref(pid))
        return Target(int(hwnd), pid.value)

    def poll(self) -> None:
        target = self.foreground()
        if target and target.pid != self.pid:
            self.last_external = target

    def valid(self, target: Target | None) -> bool:
        if not (self.available and target and self.user32.IsWindow(target.hwnd)):
            return False
        pid = C.c_uint32()
        self.user32.GetWindowThreadProcessId(target.hwnd, C.byref(pid))
        return pid.value == target.pid

    def same_target(self, target: Target | None) -> bool:
        return bool(self.valid(target) and self.foreground() == target)

    def _open_clipboard(self, owner=None) -> bool:
        for _ in range(15):
            if self.user32.OpenClipboard(owner):
                return True
            time.sleep(0.025)
        return False

    def get_text(self) -> str | None:
        if not self.available or not self._open_clipboard():
            return None
        try:
            handle = self.user32.GetClipboardData(13)
            if not handle:
                return None
            pointer = self.kernel32.GlobalLock(handle)
            if not pointer:
                return None
            try:
                size = self.kernel32.GlobalSize(handle)
                raw = C.string_at(pointer, min(size, 8_000_000))
                return raw.decode("utf-16-le", errors="replace").split("\x00", 1)[0]
            finally:
                self.kernel32.GlobalUnlock(handle)
        finally:
            self.user32.CloseClipboard()

    def set_text(self, text: str) -> bool:
        if not self.available or not self.clipboard_owner or not self._open_clipboard(self.clipboard_owner):
            return False
        handle = None
        transferred = False
        try:
            data = text.encode("utf-16-le") + b"\x00\x00"
            handle = self.kernel32.GlobalAlloc(0x0042, len(data))  # zero-initialized, movable
            if not handle:
                return False
            pointer = self.kernel32.GlobalLock(handle)
            if not pointer:
                return False
            try:
                C.memmove(pointer, data, len(data))
            finally:
                self.kernel32.GlobalUnlock(handle)
            if not self.user32.EmptyClipboard():
                return False
            transferred = bool(self.user32.SetClipboardData(13, handle))
            return transferred
        finally:
            if handle and not transferred:
                self.kernel32.GlobalFree(handle)
            self.user32.CloseClipboard()

    def _send_paste(self) -> None:
        # INPUT must include padding/union alignment exactly as the Windows ABI.
        class MOUSEINPUT(C.Structure):
            _fields_ = [("dx", C.c_long), ("dy", C.c_long), ("mouseData", C.c_uint32),
                        ("dwFlags", C.c_uint32), ("time", C.c_uint32), ("dwExtraInfo", C.c_size_t)]

        class KEYBDINPUT(C.Structure):
            _fields_ = [("wVk", C.c_uint16), ("wScan", C.c_uint16), ("dwFlags", C.c_uint32),
                        ("time", C.c_uint32), ("dwExtraInfo", C.c_size_t)]

        class HARDWAREINPUT(C.Structure):
            _fields_ = [("uMsg", C.c_uint32), ("wParamL", C.c_uint16), ("wParamH", C.c_uint16)]

        class INPUTUNION(C.Union):
            _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

        class INPUT(C.Structure):
            _anonymous_ = ("u",)
            _fields_ = [("type", C.c_uint32), ("u", INPUTUNION)]

        self.user32.SendInput.argtypes = [C.c_uint, C.POINTER(INPUT), C.c_int]
        self.user32.SendInput.restype = C.c_uint
        self.user32.GetAsyncKeyState.argtypes = [C.c_int]
        self.user32.GetAsyncKeyState.restype = C.c_short
        events = []
        # Avoid turning Ctrl+V into an application-specific modified shortcut.
        for vk in (0x10, 0x11, 0x12, 0x5B, 0x5C):
            if self.user32.GetAsyncKeyState(vk) & 0x8000:
                item = INPUT(type=1)
                item.ki = KEYBDINPUT(wVk=vk, dwFlags=0x0002, dwExtraInfo=0x0F10)
                events.append(item)
        for vk, flags in ((0x11, 0), (0x56, 0), (0x56, 2), (0x11, 2)):
            item = INPUT(type=1)
            item.ki = KEYBDINPUT(wVk=vk, dwFlags=flags, dwExtraInfo=0x0F10)
            events.append(item)
        array = (INPUT * len(events))(*events)
        if self.user32.SendInput(len(events), array, C.sizeof(INPUT)) != len(events):
            raise RuntimeError("Windows blocked keyboard insertion. The text is copied; press Ctrl+V manually.")

    def paste(self, text: str, target: Target | None, restore: bool = True, require_same: bool = False) -> str:
        if not self.available:
            return "unavailable"
        if not self.valid(target):
            return "no_target"
        if not require_same:
            self.user32.SetForegroundWindow(target.hwnd)
            time.sleep(0.15)
        if not self.same_target(target):
            return "focus_changed"
        previous = self.get_text() if restore else None
        if not self.set_text(text):
            return "clipboard_busy"
        sequence = self.user32.GetClipboardSequenceNumber()
        if not self.same_target(target):
            return "focus_changed"
        try:
            self._send_paste()
        except RuntimeError:
            return "copied_blocked"
        if restore:
            time.sleep(0.7)
            # Never overwrite something the user copied while we were pasting.
            if self.user32.GetClipboardSequenceNumber() == sequence and previous is not None:
                self.set_text(previous)
        return "inserted"
