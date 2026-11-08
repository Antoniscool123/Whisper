import hashlib
import threading

import pytest

import openflow.models as models


class Response:
    def __init__(self, data=None, status=200):
        self.data = data
        self.status_code = status
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def raise_for_status(self):
        if self.status_code >= 400: raise RuntimeError(self.status_code)
    def json(self): return self.data
    def iter_content(self, chunk_size):
        for offset in range(0, len(self.data), chunk_size):
            yield self.data[offset:offset + chunk_size]


class Session:
    def __init__(self, payload):
        self.payload = payload
        self.digest = hashlib.sha256(payload).hexdigest()
        self.ranges = []
        self.headers = {}
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def mount(self, *args, **kwargs): pass
    def get(self, url, **kwargs):
        if url == models.MODEL_API:
            return Response({"sha": "a" * 40})
        if "/tree/" in url:
            return Response([{"path": "ggml-tiny-q5_1.bin", "size": len(self.payload), "lfs": {"oid": self.digest}}])
        headers = kwargs.get("headers", {})
        self.ranges.append(headers.get("Range"))
        if "Range" in headers:
            offset = int(headers["Range"].split("=")[1].rstrip("-"))
            return Response(self.payload[offset:], 206)
        return Response(self.payload)


@pytest.fixture
def catalog(tmp_path, monkeypatch):
    monkeypatch.setattr(models, "model_directory", lambda: tmp_path)
    payload = b"lmgg" + b"test model" * 200000
    session = Session(payload)
    monkeypatch.setattr(models.requests, "Session", lambda: session)
    return session


def test_download_checksum_and_offline_cache(catalog):
    progress = []
    path = models.ensure_model("tiny-q5_1", lambda done, total: progress.append((done, total)))
    assert path.read_bytes() == catalog.payload
    assert models.is_cached("tiny-q5_1")
    assert progress[-1][0] == progress[-1][1] == len(catalog.payload)
    assert models.verify_cached("tiny-q5_1") == path
    assert catalog.ranges == [None]


def test_resume_partial_download(catalog, monkeypatch):
    partial = models.model_path("tiny-q5_1").with_suffix(".bin.part")
    partial.write_bytes(catalog.payload[:12345])
    # A second ensure call needs a fresh fake session with the same payload.
    replacement = Session(catalog.payload)
    monkeypatch.setattr(models.requests, "Session", lambda: replacement)
    path = models.ensure_model("tiny-q5_1")
    assert path.read_bytes() == catalog.payload
    assert replacement.ranges == ["bytes=12345-"]
    assert not partial.exists()


def test_cancel_keeps_partial(catalog):
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(models.Cancelled):
        models.ensure_model("tiny-q5_1", cancel=cancel)
    assert not models.is_cached("tiny-q5_1")


def test_tampered_cache_rejected(catalog):
    path = models.ensure_model("tiny-q5_1")
    path.write_bytes(b"bad!" + path.read_bytes()[4:])
    with pytest.raises(ValueError, match="checksum"):
        models.verify_cached("tiny-q5_1")
