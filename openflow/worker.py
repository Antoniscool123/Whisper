"""One serialized inference worker keeps Qt and PortAudio responsive."""
from __future__ import annotations

import logging
import queue
import threading
import traceback

from PySide6.QtCore import QThread, Signal

from .engine import WhisperEngine
from .models import Cancelled

LOG = logging.getLogger(__name__)


class SpeechWorker(QThread):
    event = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.commands: queue.Queue = queue.Queue()
        self.engine = WhisperEngine()
        self.download_cancel = threading.Event()
        self.job_cancel = threading.Event()
        self.stopping = threading.Event()

    def request(self, command: str, **payload) -> None:
        self.commands.put((command, payload))

    def cancel_download(self) -> None:
        self.download_cancel.set()

    def cancel_transcription(self) -> None:
        self.job_cancel.set()

    def stop(self) -> None:
        self.stopping.set()
        self.download_cancel.set()
        self.job_cancel.set()
        self.commands.put(("stop", {}))
        if not self.wait(8000):
            LOG.warning("Native inference is still finishing; it will abort through its callback.")

    def run(self) -> None:
        while not self.stopping.is_set():
            command, data = self.commands.get()
            if command == "stop":
                break
            try:
                if command == "load":
                    self.download_cancel.clear()
                    self.event.emit("state", "downloading" if data.get("download") else "loading")
                    def progress(done, total):
                        if self.download_cancel.is_set():
                            raise Cancelled("Download paused. Click Download to resume.")
                        self.event.emit("progress", (done, total))
                    self.engine.load(data["model"], self.download_cancel,
                                     download=bool(data.get("download")), progress=progress,
                                     threads=data.get("threads", 4))
                    if self.download_cancel.is_set():
                        raise Cancelled("Cancelled")
                    self.event.emit("model_ready", self.engine.model_id)
                elif command == "transcribe":
                    self.job_cancel.clear()
                    self.event.emit("state", "transcribing")
                    settings = data["settings"]
                    if self.engine.model_id != settings["model"]:
                        self.engine.load(settings["model"], self.job_cancel, threads=settings.get("threads", 4))
                    result = self.engine.transcribe(data["audio"], settings["language"],
                                                    hints=settings.get("hints", ""), cancel=self.job_cancel)
                    self.event.emit("result", (result, settings, data["job_id"]))
                elif command == "unload":
                    self.engine.unload()
                    self.event.emit("model_unloaded", None)
            except Cancelled as exc:
                self.event.emit("cancelled", (command, str(exc)))
            except Exception as exc:
                # Logs contain exception types/context, never transcript text or audio.
                LOG.error("Worker %s failed: %s\n%s", command, type(exc).__name__, traceback.format_exc(limit=4))
                message = str(exc)
                if len(message) > 700:
                    message = message[:700] + "…"
                self.event.emit("error", (command, message))
            finally:
                if command != "unload":
                    self.event.emit("state", "idle")
        self.engine.unload()
