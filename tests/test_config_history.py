import json
import time

from openflow.config import Settings, atomic_json
from openflow.history import History


def test_settings_defaults_to_danish(tmp_path):
    settings, warning = Settings.load(tmp_path / "missing.json")
    assert settings.language == "da" and settings.model == "small-q5_1"
    assert warning == ""
    settings.save(tmp_path / "settings.json")
    loaded, _ = Settings.load(tmp_path / "settings.json")
    assert loaded == settings


def test_settings_corrupt_and_invalid(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("not json", encoding="utf-8")
    settings, warning = Settings.load(path)
    assert warning and settings.language == "da"
    path.write_text(json.dumps({"language": "xx", "model": "evil", "threads": 999, "auto_paste": "false", "unknown": 1}))
    settings, _ = Settings.load(path)
    assert settings.language == "da" and settings.model == "small-q5_1"
    assert settings.threads == 16 and settings.auto_paste is True


def test_atomic_json_unicode(tmp_path):
    path = tmp_path / "data.json"
    atomic_json(path, {"text": "ÆØÅ 日本語"})
    assert json.loads(path.read_text(encoding="utf-8"))["text"] == "ÆØÅ 日本語"
    assert not list(tmp_path.glob("*.tmp"))


def test_history_bounded_and_optional(tmp_path):
    path = tmp_path / "history.json"
    history = History(path, limit=2)
    history.add("one", "en", 1)
    history.add("two", "da", 2)
    history.add("three", "da", 3)
    assert [e.text for e in history.entries] == ["three", "two"]
    assert History(path).entries[0].text == "three"
    history.add("not saved", "da", 1, enabled=False)
    assert len(History(path).entries) == 2
    assert history.today_words() == 2
    history.clear()
    assert History(path).entries == []


def test_history_corrupt_is_nonfatal(tmp_path):
    path = tmp_path / "history.json"
    path.write_text("[]oops")
    history = History(path)
    assert history.warning and history.entries == []
