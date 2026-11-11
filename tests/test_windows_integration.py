import ctypes as C
from types import SimpleNamespace

from openflow.platform_windows import Target, WindowsIntegration


def integration():
    instance = WindowsIntegration.__new__(WindowsIntegration)
    instance.available = True
    instance.clipboard_owner = 123
    return instance


def test_set_text_empties_clipboard_before_setting():
    instance = integration()
    events = []
    buffer = C.create_string_buffer(100)
    instance.user32 = SimpleNamespace(
        OpenClipboard=lambda owner: events.append(("open", owner)) or 1,
        EmptyClipboard=lambda: events.append(("empty",)) or 1,
        SetClipboardData=lambda kind, handle: events.append(("set", kind)) or handle,
        CloseClipboard=lambda: events.append(("close",)))
    instance.kernel32 = SimpleNamespace(GlobalAlloc=lambda flags, size: 42,
        GlobalLock=lambda handle: C.addressof(buffer), GlobalUnlock=lambda handle: None,
        GlobalFree=lambda handle: events.append(("free",)))
    assert instance.set_text("Hej æøå")
    assert events == [("open", 123), ("empty",), ("set", 13), ("close",)]
    assert buffer.raw[:16] == "Hej æøå".encode("utf-16-le") + b"\0\0"


def test_automatic_paste_never_changes_focus(monkeypatch):
    instance = integration()
    target = Target(1, 2)
    events = []
    instance.user32 = SimpleNamespace(SetForegroundWindow=lambda hwnd: events.append("focus"),
                                     GetClipboardSequenceNumber=lambda: 1)
    instance.valid = lambda candidate: True
    instance.same_target = lambda candidate: True
    instance.get_text = lambda: "previous"
    instance.set_text = lambda text: events.append(text) or True
    instance._send_paste = lambda: events.append("paste")
    monkeypatch.setattr("openflow.platform_windows.time.sleep", lambda _: None)
    assert instance.paste("Hej", target, require_same=True) == "inserted"
    assert events == ["Hej", "paste", "previous"]


def test_focus_change_before_injection_blocks_paste():
    instance = integration()
    instance.valid = lambda target: True
    states = iter([True, False])
    instance.same_target = lambda target: next(states)
    instance.get_text = lambda: None
    instance.set_text = lambda text: True
    instance.user32 = SimpleNamespace(GetClipboardSequenceNumber=lambda: 1)
    instance._send_paste = lambda: (_ for _ in ()).throw(AssertionError("must not paste"))
    assert instance.paste("Hej", Target(1, 2), require_same=True) == "focus_changed"
