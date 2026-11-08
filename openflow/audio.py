"""16 kHz mono microphone capture, kept in memory and bounded to ten minutes."""
from __future__ import annotations

import threading
from dataclasses import dataclass

import numpy as np

SAMPLE_RATE = 16000
MAX_SECONDS = 600


@dataclass(frozen=True)
class Microphone:
    name: str
    default: bool = False


def microphones() -> list[Microphone]:
    try:
        import sounddevice as sd
        default = sd.default.device[0]
        devices = [Microphone(str(device["name"]), index == default)
                   for index, device in enumerate(sd.query_devices()) if device["max_input_channels"] > 0]
        return devices
    except Exception:
        return []


class Recorder:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._chunks: list[np.ndarray] = []
        self._frames = 0
        self._level = 0.0
        self._overflows = 0
        self._stream = None
        self.active = False

    def start(self, device_name: str = "") -> None:
        if self.active:
            raise RuntimeError("Already recording")
        try:
            import sounddevice as sd
        except Exception as exc:
            raise RuntimeError(f"Audio input is unavailable: {exc}") from exc
        device = None
        if device_name:
            matches = [index for index, info in enumerate(sd.query_devices())
                       if info["max_input_channels"] > 0 and info["name"] == device_name]
            if not matches:
                raise RuntimeError("The selected microphone is unavailable. Choose another one in Settings.")
            device = matches[0]
        with self._lock:
            self._chunks = []
            self._frames = 0
            self._level = 0.0
            self._overflows = 0

        def callback(indata, frames, time_info, status):
            with self._lock:
                if not self.active:
                    return
                if status.input_overflow:
                    self._overflows += 1
                remaining = MAX_SECONDS * SAMPLE_RATE - self._frames
                if remaining <= 0:
                    return
                chunk = indata[:min(frames, remaining), 0].copy()
                self._chunks.append(chunk)
                self._frames += len(chunk)
                rms = float(np.sqrt(np.mean(np.square(chunk, dtype=np.float32)))) if len(chunk) else 0.0
                self._level = min(1.0, rms * 9.0)

        try:
            stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                                    blocksize=1600, device=device, callback=callback)
            self.active = True
            self._stream = stream
            stream.start()
        except Exception as exc:
            self.active = False
            if self._stream is not None:
                self._stream.close()
            self._stream = None
            raise RuntimeError(f"Could not open the microphone: {exc}. Check Windows Settings → Privacy & security → Microphone.") from exc

    def snapshot(self) -> tuple[float, float, int]:
        with self._lock:
            return self._level, self._frames / SAMPLE_RATE, self._overflows

    def _close(self) -> None:
        self.active = False
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
            finally:
                stream.close()

    def stop(self) -> np.ndarray:
        self._close()
        with self._lock:
            chunks, self._chunks = self._chunks, []
            self._level = 0.0
        return np.concatenate(chunks) if chunks else np.empty(0, dtype=np.float32)

    def cancel(self) -> None:
        self._close()
        with self._lock:
            self._chunks = []
            self._frames = 0
            self._level = 0.0
