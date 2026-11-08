"""CI-only: store a build artifact as a GitHub Git blob without adding binaries to history.

The returned blob SHA lets the Arena workspace retrieve the real Windows binary
through api.github.com, the permitted GitHub host. The normal user download is
the GitHub Release asset, not this internal transport mechanism.
"""
import base64
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path


def main() -> None:
    path = Path(sys.argv[1])
    data = path.read_bytes()
    repository = os.environ["GITHUB_REPOSITORY"]
    token = os.environ.get("GH_TOKEN") or os.environ["GITHUB_TOKEN"]
    payload = json.dumps({"content": base64.b64encode(data).decode("ascii"), "encoding": "base64"}).encode()
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/git/blobs", data=payload, method="POST",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json", "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(request, timeout=300) as response:
        result = json.load(response)
    print(json.dumps({"repository": repository, "blob": result["sha"], "filename": path.name,
                      "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}))


if __name__ == "__main__":
    main()
