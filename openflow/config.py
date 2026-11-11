"""Validated, atomic, per-user settings. No account or cloud service."""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any


def app_directory(kind: str = "config") -> Path:
    override = os.environ.get("OPENFLOW_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA" if kind == "config" else "LOCALAPPDATA", Path.home()))
        return base / "OpenFlow"
    base = Path(os.environ.get("XDG_CONFIG_HOME" if kind == "config" else "XDG_CACHE_HOME",
                               Path.home() / (".config" if kind == "config" else ".cache")))
    return base / "openflow"


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@dataclass
class Settings:
    language: str = "da"
    model: str = "small-q5_1"
    hotkey: str = "right_ctrl"
    microphone: str = ""
    show_overlay: bool = True
    auto_paste: bool = True
    restore_clipboard: bool = True
    clean_fillers: bool = True
    voice_commands: bool = False
    vocabulary: str = ""
    hints: str = ""
    save_history: bool = True
    preload: bool = True
    minimize_to_tray: bool = True
    start_with_windows: bool = False
    start_minimized: bool = False
    threads: int = 4

    @classmethod
    def load(cls, path: Path | None = None) -> tuple["Settings", str]:
        path = path or app_directory() / "settings.json"
        settings = cls()
        warning = ""
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("Settings must be a JSON object")
            known = {field.name for field in fields(cls)}
            for key, value in raw.items():
                if key not in known:
                    continue
                expected = type(getattr(settings, key))
                if expected is bool and isinstance(value, bool):
                    setattr(settings, key, value)
                elif expected is int and isinstance(value, int) and not isinstance(value, bool):
                    setattr(settings, key, value)
                elif expected is str and isinstance(value, str):
                    setattr(settings, key, value[:20000])
            settings.validate()
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError) as exc:
            warning = f"Settings could not be read; safe defaults were used. ({exc})"
        return settings, warning

    def validate(self) -> None:
        from .languages import LANGUAGE_CODES
        from .models import MODEL_CATALOG
        from .hotkeys import HOTKEYS
        if self.language not in LANGUAGE_CODES | {"auto"}:
            self.language = "da"
        if self.model not in MODEL_CATALOG:
            self.model = "small-q5_1"
        if self.hotkey not in HOTKEYS:
            self.hotkey = "right_ctrl"
        self.threads = min(16, max(1, self.threads))
        self.microphone = self.microphone[:500]
        self.vocabulary = self.vocabulary[:12000]
        self.hints = self.hints[:1000]

    def save(self, path: Path | None = None) -> None:
        self.validate()
        atomic_json(path or app_directory() / "settings.json", asdict(self))
