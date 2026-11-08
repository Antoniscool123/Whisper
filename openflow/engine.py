"""Whisper.cpp inference from memory. No audio files, ffmpeg, GPU drivers or API keys."""
from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .languages import LANGUAGE_CODES
from .models import Cancelled, ensure_model, verify_cached

SAMPLE_RATE = 16000
MAX_SECONDS = 600


@dataclass
class Transcript:
    text: str
    language: str
    probability: float
    seconds: float
    inference_seconds: float


class WhisperEngine:
    def __init__(self) -> None:
        self.model = None
        self.model_id: str | None = None
        self.lock = threading.RLock()

    def load(self, model_id: str, cancel: threading.Event, *, download: bool = False,
             progress=None, threads: int = 4):
        with self.lock:
            if self.model is not None and self.model_id == model_id:
                return self.model
            self.unload()
            path = ensure_model(model_id, progress, cancel) if download else verify_cached(model_id, cancel)
            if cancel.is_set():
                raise Cancelled("Cancelled")
            with path.open("rb") as stream:
                if stream.read(4) != b"lmgg":
                    raise ValueError("This is not a supported Whisper GGML model. Remove it in Settings and download again.")
            # Import only after the file is verified. All native inference runs in
            # our worker thread, never on the UI or microphone callback thread.
            from pywhispercpp.model import Model
            model = Model(str(path), redirect_whispercpp_logs_to=None,
                          context_params={"use_gpu": False, "flash_attn": False},
                          n_threads=max(1, min(16, threads, os.cpu_count() or 4)),
                          print_progress=False, print_realtime=False, print_timestamps=False,
                          no_context=True, suppress_nst=True, translate=False)
            if not getattr(model, "_ctx", None):
                raise RuntimeError("Whisper could not load this model. Try a smaller model and make sure enough RAM is free.")
            self.model, self.model_id = model, model_id
            return model

    def transcribe(self, audio: np.ndarray, language: str, *, hints: str = "",
                   cancel: threading.Event | None = None) -> Transcript:
        with self.lock:
            if self.model is None:
                raise RuntimeError("The speech model is not ready.")
            if language not in LANGUAGE_CODES | {"auto"}:
                raise ValueError("Unsupported language")
            audio = np.ascontiguousarray(audio, dtype=np.float32).reshape(-1)
            if not np.isfinite(audio).all():
                raise ValueError("The microphone produced invalid audio. Please try again.")
            if len(audio) < SAMPLE_RATE // 4:
                raise ValueError("That recording was too short. Hold the shortcut while you speak.")
            if len(audio) > MAX_SECONDS * SAMPLE_RATE:
                raise ValueError("Recordings are limited to ten minutes.")
            seconds = len(audio) / SAMPLE_RATE
            if float(np.max(np.abs(audio))) < 0.001:
                raise ValueError("No audible speech was detected. Check your microphone and its Windows permission.")
            started = time.monotonic()
            detected, probability = language, 1.0
            if language == "auto":
                # Encode at most the first 30 seconds for language identification.
                clip = audio[:SAMPLE_RATE * 30]
                if len(clip) < SAMPLE_RATE * 30:
                    clip = np.pad(clip, (0, SAMPLE_RATE * 30 - len(clip)))
                result, _ = self.model.auto_detect_language(clip)
                detected, probability = result[0], float(result[1])
            if cancel and cancel.is_set():
                raise Cancelled("Transcription cancelled")
            # Greedy sampling with whisper.cpp's fallback safeguards is fast and
            # avoids retaining text from a previous, unrelated dictation.
            options = dict(language=detected, translate=False, no_context=True,
                           single_segment=False, no_timestamps=True, print_progress=False,
                           print_realtime=False, print_timestamps=False, suppress_nst=True,
                           carry_initial_prompt=False,
                           abort_callback=lambda: bool(cancel and cancel.is_set()))
            if hints.strip():
                options["initial_prompt"] = hints.strip()[:1000]
            segments = self.model.transcribe(audio, **options)
            if cancel and cancel.is_set():
                raise Cancelled("Transcription cancelled")
            text = " ".join(segment.text.strip() for segment in segments).strip()
            # Suppress well-known silence hallucinations rather than type them.
            normalized = text.casefold().strip(" .,!?'\"")
            if normalized in {"thanks for watching", "tak fordi du så med",
                              "undertekster af", "amara.org", "subtitles by the amara.org community"} and float(np.sqrt(np.mean(audio ** 2))) < 0.015:
                text = ""
            return Transcript(text, detected, probability, seconds, time.monotonic() - started)

    def unload(self) -> None:
        with self.lock:
            if self.model is not None:
                # pywhispercpp owns the native context and frees it on deletion.
                self.model = None
            self.model_id = None
