"""CI-only: record small build-delivery metadata on the working branch.

Binaries remain outside Git history as loose GitHub blobs/release assets. This
JSON lets a restricted workspace fetch the exact verified blob through the API.
"""
import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def api(path: str, method: str = "GET", payload: dict | None = None):
    token = os.environ.get("GH_TOKEN") or os.environ["GITHUB_TOKEN"]
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request("https://api.github.com" + path, data=data, method=method,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json", "X-GitHub-Api-Version": "2022-11-28"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404 and method == "GET":
            return None
        raise RuntimeError(f"GitHub API {exc.code}: {exc.read().decode()[:500]}") from exc


def optional(path: str):
    file = Path(path)
    return json.loads(file.read_text()) if file.exists() else None


def main() -> None:
    repo = os.environ["GITHUB_REPOSITORY"]
    branch = os.environ["GITHUB_REF_NAME"]
    run = os.environ["GITHUB_RUN_ID"]
    delivery = {"run_id": run, "run_url": f"https://github.com/{repo}/actions/runs/{run}",
                "commit": os.environ["GITHUB_SHA"], "executable": optional("dist/delivery.json"),
                "preview": optional("preview-delivery.json") or optional("dist/preview-delivery.json"),
                "diagnostic": optional("integration-error-delivery.json"),
                "progress": optional("integration-progress-delivery.json")}
    path = "/build-delivery.json"
    existing = api(f"/repos/{repo}/contents{path}?ref={urllib.parse.quote(branch, safe='')}")
    content = base64.b64encode((json.dumps(delivery, indent=2) + "\n").encode()).decode()
    payload = {"message": f"Record Windows build delivery for run {run} [skip ci]",
               "content": content, "branch": branch}
    if existing:
        payload["sha"] = existing["sha"]
    result = api(f"/repos/{repo}/contents{path}", "PUT", payload)
    print("Recorded build-delivery.json at", result["commit"]["sha"])


if __name__ == "__main__":
    main()
