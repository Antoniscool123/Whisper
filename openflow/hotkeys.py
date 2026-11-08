"""Windows global hold-to-talk and hands-free shortcuts, without a keyboard hook dependency."""
from __future__ import annotations

import ctypes as C
import os
import queue
import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class Hotkey:
    label: str
    keys: frozenset[str]


HOTKEYS = {
    "right_ctrl": Hotkey("Hold Right Ctrl", frozenset({"ctrl_r"})),
    "ctrl_win": Hotkey("Hold Ctrl + Win", frozenset({"ctrl", "win"})),
    "ctrl_shift": Hotkey("Hold Ctrl + Shift", frozenset({"ctrl", "shift"})),
    "f8": Hotkey("Hold F8", frozenset({"f8"})),
}


class ChordState:
    def __init__(self, keys: frozenset[str]):
        self.keys = keys
        self.pressed: set[str] = set()
        self.triggered = False

    def down(self, key: str) -> bool:
        repeated = key in self.pressed
        self.pressed.add(key)
        if not repeated and not self.triggered and self.keys.issubset(self.pressed):
            self.triggered = True
            return True
        return False

    def up(self, key: str) -> bool:
        self.pressed.discard(key)
        if self.triggered and key in self.keys:
            self.triggered = False
            return True
        return False

    def reset(self) -> None:
        self.pressed.clear()
        self.triggered = False


class WindowsHotkeys:
    """All Win32 calls and the hook callback live on one pumped native thread.

    Events are delivered to a queue; the Qt thread never touches native hooks.
    Ctrl+Alt+Space toggles hands-free; Ctrl+Alt+Escape cancels a recording.
    """
    def __init__(self, shortcut: str, events: queue.Queue):
        self.shortcut = shortcut
        self.events = events
        self.thread: threading.Thread | None = None
        self.thread_id = 0
        self.ready = threading.Event()
        self.stopping = threading.Event()

    def start(self) -> None:
        if os.name != "nt":
            self.events.put(("info", "Global shortcuts are available on Windows. Use the on-screen record button here."))
            return
        self.thread = threading.Thread(target=self._run, name="openflow-hotkeys", daemon=True)
        self.thread.start()
        self.ready.wait(4)

    def stop(self) -> None:
        self.stopping.set()
        if self.thread and self.thread_id and os.name == "nt":
            C.windll.user32.PostThreadMessageW(self.thread_id, 0x0012, 0, 0)
            self.thread.join(timeout=3)

    def _run(self) -> None:
        # Preserve pointer widths on 64-bit Windows. A truncated LRESULT can
        # break hooks or crash when called from native code.
        user32 = C.windll.user32
        kernel32 = C.windll.kernel32
        WPARAM, LPARAM, LRESULT = C.c_size_t, C.c_ssize_t, C.c_ssize_t
        HOOKPROC = C.CFUNCTYPE(LRESULT, C.c_int, WPARAM, LPARAM)

        class KBDLLHOOKSTRUCT(C.Structure):
            _fields_ = [("vkCode", C.c_uint32), ("scanCode", C.c_uint32), ("flags", C.c_uint32),
                        ("time", C.c_uint32), ("dwExtraInfo", C.c_size_t)]

        class POINT(C.Structure):
            _fields_ = [("x", C.c_long), ("y", C.c_long)]

        class MSG(C.Structure):
            _fields_ = [("hwnd", C.c_void_p), ("message", C.c_uint), ("wParam", WPARAM),
                        ("lParam", LPARAM), ("time", C.c_uint32), ("pt", POINT)]

        user32.SetWindowsHookExW.argtypes = [C.c_int, C.c_void_p, C.c_void_p, C.c_uint32]
        user32.SetWindowsHookExW.restype = C.c_void_p
        user32.CallNextHookEx.argtypes = [C.c_void_p, C.c_int, WPARAM, LPARAM]
        user32.CallNextHookEx.restype = LRESULT
        user32.UnhookWindowsHookEx.argtypes = [C.c_void_p]
        user32.GetMessageW.argtypes = [C.POINTER(MSG), C.c_void_p, C.c_uint, C.c_uint]
        user32.GetMessageW.restype = C.c_int
        user32.RegisterHotKey.argtypes = [C.c_void_p, C.c_int, C.c_uint, C.c_uint]
        user32.UnregisterHotKey.argtypes = [C.c_void_p, C.c_int]
        kernel32.GetModuleHandleW.argtypes = [C.c_wchar_p]
        kernel32.GetModuleHandleW.restype = C.c_void_p
        kernel32.GetCurrentThreadId.restype = C.c_uint32
        self.thread_id = kernel32.GetCurrentThreadId()
        chord = ChordState(HOTKEYS[self.shortcut].keys)
        special = {160: "shift", 161: "shift", 162: "ctrl", 163: "ctrl",
                   164: "alt", 165: "alt", 91: "win", 92: "win", 119: "f8"}

        def normalize(vk: int) -> str:
            if self.shortcut == "right_ctrl" and vk in (162, 163):
                return "ctrl_r" if vk == 163 else "ctrl_l"
            return special.get(vk, str(vk))

        def emit(event: str) -> None:
            try:
                self.events.put_nowait(("hotkey", event))
            except queue.Full:
                pass

        @HOOKPROC
        def hook(code, wparam, lparam):
            try:
                if code >= 0 and lparam:
                    info = C.cast(lparam, C.POINTER(KBDLLHOOKSTRUCT)).contents
                    if info.dwExtraInfo == 0x0F10:
                        return user32.CallNextHookEx(None, code, wparam, lparam)
                    key = normalize(info.vkCode)
                    if wparam in (0x0100, 0x0104):  # WM_KEYDOWN / WM_SYSKEYDOWN
                        if chord.down(key):
                            emit("press")
                    elif wparam in (0x0101, 0x0105):
                        if chord.up(key):
                            emit("release")
            except Exception:
                # A Python exception must never escape into the OS hook chain.
                pass
            return user32.CallNextHookEx(None, code, wparam, lparam)

        handle = user32.SetWindowsHookExW(13, C.cast(hook, C.c_void_p), kernel32.GetModuleHandleW(None), 0)
        toggle = bool(user32.RegisterHotKey(None, 1, 0x0001 | 0x0002, 0x20))
        cancel = bool(user32.RegisterHotKey(None, 2, 0x0001 | 0x0002, 0x1B))
        if not handle:
            self.events.put(("info", "Hold shortcut unavailable. Use Ctrl+Alt+Space to dictate, or the record button." if toggle
                             else "Global shortcuts unavailable. Use the record button; try restarting OpenFlow as administrator."))
        elif not toggle:
            self.events.put(("info", "Hold shortcut is ready. Ctrl+Alt+Space is already used by another app."))
        self.ready.set()
        try:
            message = MSG()
            while not self.stopping.is_set():
                result = user32.GetMessageW(C.byref(message), None, 0, 0)
                if result in (0, -1):
                    break
                if message.message == 0x0315:
                    if message.wParam == 1:
                        emit("toggle")
                    elif message.wParam == 2 and cancel:
                        emit("cancel")
                user32.TranslateMessage(C.byref(message))
                user32.DispatchMessageW(C.byref(message))
        finally:
            if handle:
                user32.UnhookWindowsHookEx(handle)
            if toggle:
                user32.UnregisterHotKey(None, 1)
            if cancel:
                user32.UnregisterHotKey(None, 2)
