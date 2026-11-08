"""Resumable, checksum-verified downloads of free Whisper GGML models."""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import requests

from . import __version__
from .config import app_directory, atomic_json

MODEL_REPO = "ggerganov/whisper.cpp"
MODEL_API = f"https://huggingface.co/api/models/{MODEL_REPO}"


@dataclass(frozen=True)
class ModelSpec:
    id: str
    label: str
    megabytes: int
    description: str

    @property
    def filename(self) -> str:
        return f"ggml-{self.id}.bin"


MODEL_CATALOG: dict[str, ModelSpec] = {
    "tiny-q5_1": ModelSpec("tiny-q5_1", "Tiny · fastest", 31, "Quick notes; lower accuracy, especially outside English."),
    "base-q5_1": ModelSpec("base-q5_1", "Base · lightweight", 57, "Older or low-memory PCs. Danish works, but small is better."),
    "small-q5_1": ModelSpec("small-q5_1", "Small · recommended", 181, "A good Danish / multilingual balance. Compact quantized model."),
    "small": ModelSpec("small", "Small · full precision", 466, "The non-quantized small model. More disk and memory."),
    "medium-q5_0": ModelSpec("medium-q5_0", "Medium · more accurate", 514, "Better difficult audio and accents; slower on CPU."),
    "large-v3-turbo-q5_0": ModelSpec("large-v3-turbo-q5_0", "Large turbo · multilingual", 547, "Fast large-family decoder. Broad language coverage; more RAM."),
    "large-v3-q5_0": ModelSpec("large-v3-q5_0", "Large v3 · highest accuracy", 1100, "Best for difficult speech. Slower; allow several GB of RAM."),
}


class Cancelled(Exception):
    pass


Progress = Callable[[int, int], None]


def model_directory() -> Path:
    return app_directory("cache") / "models"


def model_path(model_id: str) -> Path:
    return model_directory() / MODEL_CATALOG[model_id].filename


def manifest_path(model_id: str) -> Path:
    return model_directory() / f"{MODEL_CATALOG[model_id].filename}.json"


def read_manifest(model_id: str) -> dict | None:
    try:
        data = json.loads(manifest_path(model_id).read_text(encoding="utf-8"))
        if (data.get("filename") == MODEL_CATALOG[model_id].filename
                and re.fullmatch(r"[0-9a-f]{64}", data.get("sha256", ""))
                and re.fullmatch(r"[0-9a-f]{40}", data.get("revision", ""))
                and isinstance(data.get("size"), int) and data["size"] > 0):
            return data
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return None


def is_cached(model_id: str) -> bool:
    manifest = read_manifest(model_id)
    path = model_path(model_id)
    return bool(manifest and path.is_file() and path.stat().st_size == manifest["size"])


def sha256_file(path: Path, cancel: threading.Event | None = None) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            if cancel and cancel.is_set():
                raise Cancelled("Cancelled")
            digest.update(chunk)
    return digest.hexdigest()


def verify_cached(model_id: str, cancel: threading.Event | None = None) -> Path:
    path, manifest = model_path(model_id), read_manifest(model_id)
    if not manifest or not path.is_file() or path.stat().st_size != manifest["size"]:
        raise FileNotFoundError("This model is not downloaded yet. Download it once, then use it offline.")
    if sha256_file(path, cancel) != manifest["sha256"]:
        raise ValueError("The model failed its checksum. Remove it in Settings and download it again.")
    return path


def _fetch_manifest(session: requests.Session, spec: ModelSpec) -> dict:
    response = session.get(MODEL_API, timeout=(15, 45))
    response.raise_for_status()
    revision = response.json().get("sha", "")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("The model repository returned an invalid revision.")
    response = session.get(f"{MODEL_API}/tree/{revision}", params={"path": spec.filename}, timeout=(15, 45))
    response.raise_for_status()
    entries = response.json()
    entry = next((item for item in entries if item.get("path") == spec.filename), None)
    if not entry:
        raise ValueError(f"Model file {spec.filename} was not found in the official repository.")
    size = int(entry.get("size", 0))
    checksum = entry.get("lfs", {}).get("oid", "")
    if not re.fullmatch(r"[0-9a-f]{64}", checksum) or not 1_000_000 < size < 10_000_000_000:
        raise ValueError("The model repository did not provide a valid size and SHA-256 checksum.")
    return {"filename": spec.filename, "revision": revision, "sha256": checksum, "size": size,
            "source": f"https://huggingface.co/{MODEL_REPO}"}


def ensure_model(model_id: str, progress: Progress | None = None,
                 cancel: threading.Event | None = None) -> Path:
    """Download to a .part file, verify its SHA-256, then atomically publish it.

    Existing partial downloads are resumed with HTTP Range. Checksums come from
    the official repository over HTTPS and are pinned in a local manifest.
    """
    spec = MODEL_CATALOG[model_id]
    if is_cached(model_id):
        return verify_cached(model_id, cancel)
    directory = model_directory()
    directory.mkdir(parents=True, exist_ok=True)
    final, partial = model_path(model_id), model_path(model_id).with_suffix(".bin.part")
    with requests.Session() as session:
        session.headers.update({"User-Agent": f"OpenFlow/{__version__}", "Accept-Encoding": "identity"})
        manifest = _fetch_manifest(session, spec)
        total = manifest["size"]
        if final.exists():
            if final.stat().st_size == total and sha256_file(final, cancel) == manifest["sha256"]:
                atomic_json(manifest_path(model_id), manifest)
                return final
            raise ValueError("An unverified model file already exists. Remove this model in Settings, then retry.")
        offset = partial.stat().st_size if partial.exists() else 0
        if offset > total:
            partial.unlink()
            offset = 0
        if cancel and cancel.is_set():
            raise Cancelled("Download cancelled; progress is kept for resume.")
        digest = hashlib.sha256()
        if offset:
            with partial.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    if cancel and cancel.is_set():
                        raise Cancelled("Download cancelled; progress is kept for resume.")
                    digest.update(chunk)
        headers = {"Range": f"bytes={offset}-"} if offset else {}
        url = f"https://huggingface.co/{MODEL_REPO}/resolve/{manifest['revision']}/{spec.filename}?download=true"
        if progress:
            progress(offset, total)
        with session.get(url, headers=headers, stream=True, timeout=(15, 90), allow_redirects=True) as response:
            response.raise_for_status()
            if offset and response.status_code == 200:
                offset = 0
                digest = hashlib.sha256()
            if offset and response.status_code != 206:
                raise ValueError("The download server could not resume this file. Retry the download.")
            mode = "ab" if offset else "wb"
            with partial.open(mode) as stream:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if cancel and cancel.is_set():
                        stream.flush()
                        raise Cancelled("Download paused. Click Download to resume.")
                    if not chunk:
                        continue
                    stream.write(chunk)
                    digest.update(chunk)
                    offset += len(chunk)
                    if offset > total:
                        raise ValueError("The model download exceeded its expected size.")
                    if progress:
                        progress(offset, total)
                stream.flush()
                os.fsync(stream.fileno())
        if offset != total or digest.hexdigest() != manifest["sha256"]:
            raise ValueError("The download was incomplete or failed verification. Retry to resume safely.")
        os.replace(partial, final)
        atomic_json(manifest_path(model_id), manifest)
    return final


def remove_model(model_id: str) -> None:
    for path in (model_path(model_id), manifest_path(model_id), model_path(model_id).with_suffix(".bin.part")):
        path.unlink(missing_ok=True)
