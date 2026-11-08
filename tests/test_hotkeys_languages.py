from openflow.hotkeys import ChordState, HOTKEYS
from openflow.languages import LANGUAGES, language_name


def test_all_languages_and_danish():
    assert len(LANGUAGES) == 100
    assert LANGUAGES["da"] == "Danish · Dansk"
    assert language_name("auto") == "Auto-detect"
    assert "日本語" in LANGUAGES["ja"]


def test_hold_right_ctrl_ignores_repeat():
    state = ChordState(HOTKEYS["right_ctrl"].keys)
    assert state.down("ctrl_l") is False
    assert state.down("ctrl_r") is True
    assert state.down("ctrl_r") is False
    assert state.up("ctrl_l") is False
    assert state.up("ctrl_r") is True
    assert state.up("ctrl_r") is False
    assert state.down("ctrl_r") is True


def test_chord_requires_both_keys():
    state = ChordState(HOTKEYS["ctrl_win"].keys)
    assert state.down("ctrl") is False
    assert state.down("win") is True
    assert state.up("ctrl") is True
    state.reset()
    assert not state.triggered and not state.pressed
