"""Collect upstream license texts into the packaged application at build time."""
from __future__ import annotations

import base64
import importlib.metadata as metadata
import json
import shutil
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "openflow" / "assets" / "licenses"
PACKAGES = ["PySide6-Essentials", "shiboken6", "numpy", "pywhispercpp", "platformdirs",
            "sounddevice", "requests", "tqdm", "certifi", "charset-normalizer", "idna",
            "urllib3", "cffi", "pycparser", "colorama", "PyInstaller"]
UPSTREAM = [
    ("qt-lgpl", "spdx/license-list-data", "text/LGPL-3.0-only.txt"),
    ("qt-gpl", "spdx/license-list-data", "text/GPL-3.0-only.txt"),
    ("whisper-cpp", "ggml-org/whisper.cpp", "LICENSE"),
    ("portaudio", "PortAudio/portaudio", "LICENSE.txt"),
]


def github_file(repo: str, path: str) -> bytes:
    request = urllib.request.Request(f"https://api.github.com/repos/{repo}/contents/{path}",
                                     headers={"Accept": "application/vnd.github+json", "User-Agent": "OpenFlow-build"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return base64.b64decode(json.load(response)["content"])


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    index = []
    for name in PACKAGES:
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            continue  # optional platform-specific dependency
        directory = OUT / name
        directory.mkdir()
        info = dist.metadata
        summary = f"{info.get('Name', name)} {dist.version}\nLicense: {info.get('License', '')}\nLicense-Expression: {info.get('License-Expression', '')}\nHome-page: {info.get('Home-page', '')}\n"
        (directory / "PACKAGE.txt").write_text(summary, encoding="utf-8")
        for item in dist.files or []:
            parts = item.parts
            if any(part.endswith(".dist-info") for part in parts) and parts[-1].upper().startswith(("LICENSE", "COPYING", "NOTICE")):
                source = Path(dist.locate_file(item))
                if source.is_file():
                    shutil.copy2(source, directory / parts[-1])
        index.append(name)
    for name, repo, path in UPSTREAM:
        (OUT / f"{name}.txt").write_bytes(github_file(repo, path))
        index.append(name)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.is_file():
        shutil.copy2(python_license, OUT / "python.txt")
    shutil.copy2(ROOT / "LICENSE", OUT / "OpenFlow-MIT.txt")
    shutil.copy2(ROOT / "THIRD_PARTY_NOTICES.md", OUT / "THIRD_PARTY_NOTICES.md")
    (OUT / "INDEX.txt").write_text("Bundled license notices:\n" + "\n".join(index) + "\n", encoding="utf-8")
    print(f"Collected {len(index)} license notices into {OUT}")


if __name__ == "__main__":
    main()
