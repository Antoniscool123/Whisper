"""Real native-engine smoke test on CI. Uses a public English sample, not user audio."""
import base64
import json
import os
import tempfile
import urllib.request
import wave
from pathlib import Path

import numpy as np

from openflow.engine import WhisperEngine
from openflow.models import ensure_model
from openflow.text import tidy_text


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="openflow-integration-") as directory:
        os.environ["OPENFLOW_DATA_DIR"] = directory
        model = ensure_model("tiny-q5_1", lambda done, total: None)
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
        engine = WhisperEngine()
        engine.load("tiny-q5_1", __import__("threading").Event(), threads=4)
        result = engine.transcribe(pcm.astype(np.float32) / 32768.0, "en")
        text = tidy_text(result.text, fillers=False)
        print("Public JFK sample:", text)
        assert "ask not" in text.lower(), text
        assert "country" in text.lower(), text
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
