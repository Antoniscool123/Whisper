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


def test_model_load_supports_windowed_executable_without_stderr(tmp_path, monkeypatch):
    import openflow.engine as engine_module
    path = tmp_path / "model.bin"
    path.write_bytes(b"lmgg")
    monkeypatch.setattr(engine_module, "verify_cached", lambda *args: path)
    seen = {}
    class LoadingModel:
        def __init__(self, filename, **kwargs):
            seen.update(kwargs)
            self._ctx = object()
    monkeypatch.setitem(sys.modules, "pywhispercpp", types.ModuleType("pywhispercpp"))
    monkeypatch.setitem(sys.modules, "pywhispercpp.model", types.SimpleNamespace(Model=LoadingModel))
    monkeypatch.setattr(sys, "stderr", None)
    engine = WhisperEngine()
    engine.load("tiny-q5_1", threading.Event())
    assert seen["redirect_whispercpp_logs_to"] is False
    assert engine.model_id == "tiny-q5_1"


def test_short_audio_context_never_truncates_and_long_resets():
    from openflow.engine import short_audio_context
    for seconds in (0.25, 1, 10, 25, 26):
        ctx = short_audio_context(int(seconds * SAMPLE_RATE))
        assert 512 <= ctx <= 1500
        assert ctx >= seconds * 50
    assert short_audio_context(27 * SAMPLE_RATE) == 0
    assert short_audio_context(600 * SAMPLE_RATE) == 0


def test_engine_resets_context_and_prompt_between_transcriptions():
    engine = WhisperEngine()
    engine.model = FakeModel()
    sample = np.ones(SAMPLE_RATE, dtype=np.float32) * 0.1
    engine.transcribe(sample, "da", hints="Aarhus", fast_short_audio=True)
    assert engine.model.kwargs["audio_ctx"] == 512
    engine.transcribe(sample, "da", hints="", fast_short_audio=False)
    assert engine.model.kwargs["audio_ctx"] == 0
    assert engine.model.kwargs["initial_prompt"] == ""


def test_prepare_audio_amplifies_quiet_speech_without_clipping():
    from openflow.engine import prepare_audio
    quiet = np.full(SAMPLE_RATE, 0.05, dtype=np.float32)
    assert np.allclose(prepare_audio(quiet), 0.2)
    silence = np.full(SAMPLE_RATE, 0.0001, dtype=np.float32)
    assert np.array_equal(prepare_audio(silence), silence)
    loud = np.full(SAMPLE_RATE, 0.5, dtype=np.float32)
    assert np.array_equal(prepare_audio(loud), loud)


def test_silence_hallucination_filter_uses_original_volume():
    engine = WhisperEngine()
    class HallucinationModel:
        def transcribe(self, audio, **kwargs):
            assert np.sqrt(np.mean(audio ** 2)) > 0.015
            return [types.SimpleNamespace(text="thanks for watching")]
    engine.model = HallucinationModel()
    quiet_speech = (np.sin(np.arange(SAMPLE_RATE, dtype=np.float32) * 0.1) * 0.012)
    assert engine.transcribe(quiet_speech, "da").text == ""
