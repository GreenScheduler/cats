"""
Cache HTTP requests for use by cats.providers

URLs are cached by SHA256 of URL and mtimes checked to remove stale URL caches
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import tempfile
import time
from datetime import timedelta
from pathlib import Path
from typing import Any

import requests
from requests.structures import CaseInsensitiveDict

CACHE_NAME = "cats"
CACHE_SUFFIX = ".json"


def serialise(response: requests.Response) -> str:
    "Serialise a response to a JSON string for storage in the cache"
    return json.dumps(
        {
            "url": response.url,
            "status_code": response.status_code,
            "reason": response.reason,
            "headers": dict(response.headers),
            "encoding": response.encoding,
            "content": base64.b64encode(response.content).decode("ascii"),
        }
    )


def deserialise(data: str) -> requests.Response:
    "Reconstruct a response from a string written by serialise()"
    obj = json.loads(data)
    response = requests.Response()
    response.url = obj["url"]
    response.status_code = obj["status_code"]
    response.reason = obj["reason"]
    response.headers = CaseInsensitiveDict(obj["headers"])
    response.encoding = obj["encoding"]
    response._content = base64.b64decode(obj["content"])
    return response


class Cache:
    def __init__(self, base_path: Path, expires_after: timedelta):
        if not base_path.exists():
            raise FileNotFoundError(f"{base_path} does not exist")
        self.path = base_path / CACHE_NAME
        self.path.mkdir(exist_ok=True)
        self.expires_after = expires_after
        self.clear_expired()

    def _key(self, url: str) -> Path:
        "Path of the cache file for a URL"
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.path / (digest + CACHE_SUFFIX)

    def _is_expired(self, path: Path) -> bool:
        return time.time() - path.stat().st_mtime > self.expires_after.total_seconds()

    def _write(self, path: Path, data: str) -> None:
        "Atomically write data to path so concurrent readers never see partial files"
        fd, tmp = tempfile.mkstemp(dir=self.path, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(data)
            os.replace(tmp, path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def clear_expired(self) -> list[Path]:
        "Clear expired URLs from cache"
        removed = []
        for path in self.path.glob("*" + CACHE_SUFFIX):
            try:
                if self._is_expired(path):
                    path.unlink()
                    removed.append(path)
            except FileNotFoundError:  # removed by another process
                continue
        return removed

    def clear(self, url: str) -> bool:
        "Clear a specific URL from the cache"
        try:
            self._key(url).unlink()
            return True
        except FileNotFoundError:
            return False

    def get(self, url: str, headers: dict[str, Any] | None = None) -> requests.Response:
        """Return the response for a URL, from the cache if present and not expired

        Only successful responses are cached. Headers are passed on to the
        request but are not part of the cache key.
        """
        path = self._key(url)
        try:
            if not self._is_expired(path):
                return deserialise(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError, KeyError):
            # missing, or corrupt cache entry: fall through and refetch
            pass
        response = requests.get(url, headers=headers or {})
        if response.ok:
            self._write(path, serialise(response))
        return response
