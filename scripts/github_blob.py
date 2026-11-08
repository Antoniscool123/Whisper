"""CI-only: store build artifacts as GitHub Git blobs without adding binaries to history.

Large files are split into modest blobs so the REST request body stays small.
The returned SHA list lets the Arena workspace retrieve the exact Windows binary
through api.github.com. Normal users download the GitHub Release asset instead.
"""
import base64
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

CHUNK = 8 * 1024 * 1024


def create_blob(repository: str, token: str, data: bytes) -> str:
    payload = json.dumps({"content": base64.b64encode(data).decode("ascii"), "encoding": "base64"}).encode()
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/git/blobs", data=payload, method="POST",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json", "X-GitHub-Api-Version": "2022-11-28"})
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.load(response)["sha"]
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GitHub blob API {exc.code}: {exc.read().decode(errors='replace')[:1000]}") from exc


def main() -> None:
    path = Path(sys.argv[1])
    data = path.read_bytes()
    repository = os.environ["GITHUB_REPOSITORY"]
    token = os.environ.get("GH_TOKEN") or os.environ["GITHUB_TOKEN"]
    result = {"repository": repository, "filename": path.name, "bytes": len(data),
              "sha256": hashlib.sha256(data).hexdigest()}
    if len(data) <= CHUNK:
        result["blob"] = create_blob(repository, token, data)
    else:
        result["chunks"] = []
        for offset in range(0, len(data), CHUNK):
            chunk = data[offset:offset + CHUNK]
            result["chunks"].append({"blob": create_blob(repository, token, chunk), "bytes": len(chunk),
                                     "sha256": hashlib.sha256(chunk).hexdigest()})
    print(json.dumps(result))


if __name__ == "__main__":
    main()
