"""Bounded local transcript history; audio is never persisted."""
from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import app_directory, atomic_json
from .text import word_count
import json


@dataclass
class Entry:
    text: str
    language: str
    seconds: float
    created: float
    id: str


class History:
    def __init__(self, path: Path | None = None, limit: int = 100):
        self.path = path or app_directory() / "history.json"
        self.limit = limit
        self.entries: list[Entry] = []
        self.warning = ""
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                for item in raw[:limit]:
                    if isinstance(item, dict) and isinstance(item.get("text"), str):
                        self.entries.append(Entry(item["text"][:100000], str(item.get("language", ""))[:12],
                                                  float(item.get("seconds", 0)), float(item.get("created", 0)),
                                                  str(item.get("id", uuid.uuid4()))[:64]))
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError) as exc:
            self.warning = f"Local history could not be loaded: {exc}"

    def add(self, text: str, language: str, seconds: float, enabled: bool = True) -> Entry:
        entry = Entry(text, language, seconds, time.time(), uuid.uuid4().hex)
        if enabled:
            self.entries.insert(0, entry)
            del self.entries[self.limit:]
            self.save()
        return entry

    def save(self) -> None:
        atomic_json(self.path, [asdict(entry) for entry in self.entries])

    def clear(self) -> None:
        self.entries.clear()
        self.save()

    def delete(self, entry_id: str) -> None:
        self.entries = [entry for entry in self.entries if entry.id != entry_id]
        self.save()

    def today_words(self) -> int:
        # Compute local midnight without DST assumptions.
        now = time.localtime()
        midnight = time.mktime((now.tm_year, now.tm_mon, now.tm_mday, 0, 0, 0,
                                now.tm_wday, now.tm_yday, -1))
        return sum(word_count(entry.text) for entry in self.entries if entry.created >= midnight)
