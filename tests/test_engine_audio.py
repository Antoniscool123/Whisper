import sys
import threading
import types

import numpy as np
import pytest

from openflow.audio import Recorder, SAMPLE_RATE, MAX_SECONDS
from openflow.engine import WhisperEngine
from openflow.models import Cancelled


class FakeModel:
    def transcribe(self, audio, **kwargs):
        self.kwargs = kwargs
        return [types.SimpleNamespace(text=" Hej verden. "), types.SimpleNamespace(text=" Hvordan går det? ")]
    def auto_detect_language(self, audio):
        return (("da", 0.98), {})


def test_engine_multilingual_and_hints():
    engine = WhisperEngine()
    engine.model, engine.model_id = FakeModel(), "test"
    audio = np.sin(np.arange(16000, dtype=np.float32) * 0.1) * 0.1
    result = engine.transcribe(audio, "da", hints="Aarhus, OpenFlow")
    assert result.text == "Hej verden. Hvordan går det?"
    assert result.language == "da" and result.seconds == 1
    assert engine.model.kwargs["initial_prompt"] == "Aarhus, OpenFlow"
    assert engine.model.kwargs["no_context"] is True
    auto = engine.transcribe(audio, "auto")
    assert auto.language == "da" and auto.probability == 0.98


def test_engine_rejects_silence_and_short_audio():
    engine = WhisperEngine()
    engine.model = FakeModel()
    with pytest.raises(ValueError, match="short"):
        engine.transcribe(np.zeros(100, dtype=np.float32), "da")
    with pytest.raises(ValueError, match="audible"):
        engine.transcribe(np.zeros(16000, dtype=np.float32), "da")
    with pytest.raises(ValueError, match="Unsupported"):
        engine.transcribe(np.ones(16000, dtype=np.float32), "invalid")


def test_engine_cancel():
    engine = WhisperEngine()
    engine.model = FakeModel()
    cancel = threading.Event(); cancel.set()
    with pytest.raises(Cancelled):
        engine.transcribe(np.ones(16000, dtype=np.float32) * 0.1, "auto", cancel=cancel)


def test_recorder_memory_only_and_bounded(monkeypatch):
    callbacks = []
    class Stream:
        def __init__(self, **kwargs): callbacks.append(kwargs["callback"])
        def start(self): pass
        def stop(self): pass
        def close(self): pass
    fake = types.SimpleNamespace(InputStream=Stream, query_devices=lambda: [], default=types.SimpleNamespace(device=[0, 0]))
    monkeypatch.setitem(sys.modules, "sounddevice", fake)
    recorder = Recorder()
    recorder.start()
    chunk = np.ones((1600, 1), dtype=np.float32) * 0.1
    callbacks[0](chunk, 1600, None, types.SimpleNamespace(input_overflow=False))
    assert recorder.snapshot()[1] == 0.1
    audio = recorder.stop()
    assert audio.shape == (1600,) and audio.dtype == np.float32
    assert not recorder.active
    recorder.start()
    big = np.zeros((MAX_SECONDS * SAMPLE_RATE + 100, 1), dtype=np.float32)
    callbacks[1](big, len(big), None, types.SimpleNamespace(input_overflow=True))
    assert recorder.snapshot()[1] == MAX_SECONDS
    recorder.cancel()
    assert recorder.stop().size == 0
