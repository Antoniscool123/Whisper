"""Real native-engine smoke test on CI. Uses a public English sample, not user audio."""
import base64
import json
from difflib import SequenceMatcher
import os
import tempfile
import urllib.request
import wave
from pathlib import Path

import numpy as np

from openflow.engine import WhisperEngine
from openflow.models import ensure_model
from openflow.text import tidy_text


PROGRESS = Path("integration-progress.txt")


def checkpoint(message: str) -> None:
    print(message, flush=True)
    with PROGRESS.open("a", encoding="utf-8") as stream:
        stream.write(message + "\n")
        stream.flush()


def main() -> None:
    checkpoint("integration start")
    with tempfile.TemporaryDirectory(prefix="openflow-integration-") as directory:
        os.environ["OPENFLOW_DATA_DIR"] = directory
        checkpoint("downloading tiny model")
        model = ensure_model("tiny-q5_1", lambda done, total: None)
        checkpoint(f"model verified: {model.stat().st_size} bytes")
        request = urllib.request.Request(
            "https://api.github.com/repos/ggml-org/whisper.cpp/contents/samples/jfk.wav",
            headers={"Accept": "application/vnd.github+json", "User-Agent": "OpenFlow-CI"})
        with urllib.request.urlopen(request, timeout=30) as response:
            sample = base64.b64decode(json.load(response)["content"])
        path = Path(directory) / "jfk.wav"
        path.write_bytes(sample)
        with wave.open(str(path), "rb") as audio:
            assert audio.getframerate() == 16000 and audio.getnchannels() == 1
            pcm = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2")
        checkpoint("loading native engine")
        engine = WhisperEngine()
        engine.load("tiny-q5_1", __import__("threading").Event(), threads=4)
        checkpoint("native engine loaded")
        result = engine.transcribe(pcm.astype(np.float32) / 32768.0, "en")
        checkpoint("native transcription returned")
        text = tidy_text(result.text, fillers=False)
        print("Public JFK sample:", text)
        assert "ask not" in text.lower(), text
        assert "country" in text.lower(), text
        engine.unload()
        checkpoint("loading small model for Danish comparison")
        ensure_model("small-q5_1", lambda done, total: None)
        engine.load("small-q5_1", __import__("threading").Event(), threads=4)
        with wave.open("tests/fixtures/danish-example.wav", "rb") as audio:
            assert audio.getframerate() == 16000 and audio.getnchannels() == 1
            danish = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
        baseline = engine.transcribe(danish, "da", fast_short_audio=False)
        fast = engine.transcribe(danish, "da", fast_short_audio=True)
        assert baseline.text.strip() and fast.text.strip(), "Empty Danish output"
        similarity = SequenceMatcher(None, baseline.text.casefold().split(), fast.text.casefold().split()).ratio()
        assert similarity >= 0.75, f"Short-context output differs substantially from full context: {similarity:.2f}"
        checkpoint(f"Danish full context ({baseline.inference_seconds:.2f}s): {baseline.text}")
        checkpoint(f"Danish short context ({fast.inference_seconds:.2f}s, similarity {similarity:.2f}): {fast.text}")
        engine.unload()
        print("PASS: checksum-verified model download, native Whisper inference, English transcription, cleanup and unload")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        detail = traceback.format_exc()
        Path("integration-error.txt").write_text(detail, encoding="utf-8")
        print(detail)
        raise
