# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Download a file once and reuse it."""
from __future__ import annotations

import http.client
import shutil
import time
import urllib.error
import urllib.request
from pathlib import Path

RAW_DIR = Path("data/raw")
ATTEMPTS = 4  # connection resets are common when many tiles download at once
USER_AGENT = "twinfinder/0.1"


def _download(url: str, part: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=120) as response, open(part, "wb") as out:
                shutil.copyfileobj(response, out)
                expected = response.headers.get("Content-Length")
            got = part.stat().st_size
            if expected is not None and got != int(expected):
                raise ConnectionError(f"short body: {got} of {expected} bytes from {url}")
            return
        except urllib.error.HTTPError:
            raise  # the server answered (for example 404); retrying will not help
        except (urllib.error.URLError, ConnectionError, TimeoutError, http.client.IncompleteRead):
            part.unlink(missing_ok=True)
            if attempt == ATTEMPTS:
                raise
            time.sleep(1.5 * attempt)


def fetch(url: str, dest_dir: Path = RAW_DIR) -> Path:
    """Return the local path for url, downloading it on first use."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / url.rsplit("/", 1)[-1]
    if dest.exists():
        return dest
    part = dest.with_suffix(dest.suffix + ".part")
    _download(url, part)
    part.rename(dest)
    return dest


def fetch_optional(url: str, dest_dir: Path = RAW_DIR) -> Path | None:
    """Like fetch, but a file the server does not have (404) returns None.

    The miss is remembered with an empty marker file so it is not requested again.
    Any other answer, such as 403, is an error: a refusal says nothing about the file.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    marker = dest_dir / (url.rsplit("/", 1)[-1] + ".missing")
    if marker.exists():
        return None
    try:
        return fetch(url, dest_dir)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            marker.touch()
            return None
        raise


def exists_on_server(url: str) -> bool:
    """Ask for the headers only. False means 404; any other refusal is an error."""
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=60):
            return True
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return False
        raise
