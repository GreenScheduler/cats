import os
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
import requests

from cats.cache import CACHE_NAME, Cache, deserialise, serialise
from cats.providers.base import fetch_url
from cats.version import user_agent

URL = "https://api.example.com/forecast?at=2026-01-01T00:00Z"


def make_response(
    status_code: int = 200, content: bytes = b'{"data": [1, 2, 3]}', url: str = URL
) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response.reason = "OK" if status_code < 400 else "Error"
    response.url = url
    response.encoding = "utf-8"
    response.headers["Content-Type"] = "application/json"
    response._content = content
    return response


@pytest.fixture
def cache(tmp_path: Path) -> Cache:
    return Cache(tmp_path, expires_after=timedelta(hours=1))


@pytest.fixture
def mock_get():
    with patch("cats.cache.requests.get") as mock:
        mock.return_value = make_response()
        yield mock


def age(path: Path, seconds: float) -> None:
    "Set the mtime of path to `seconds` in the past"
    mtime = path.stat().st_mtime - seconds
    os.utime(path, (mtime, mtime))


def test_serialise_roundtrip():
    original = make_response(content=b"\x00\xffbinary")
    restored = deserialise(serialise(original))
    assert restored.status_code == original.status_code
    assert restored.reason == original.reason
    assert restored.url == original.url
    assert restored.encoding == original.encoding
    assert restored.content == original.content
    # headers remain case insensitive
    assert restored.headers["content-type"] == "application/json"


def test_init_missing_base_path(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        Cache(tmp_path / "missing", expires_after=timedelta(hours=1))


def test_init_creates_and_reuses_cache_dir(tmp_path: Path):
    Cache(tmp_path, expires_after=timedelta(hours=1))
    assert (tmp_path / CACHE_NAME).is_dir()
    # a second instance reuses the existing directory
    Cache(tmp_path, expires_after=timedelta(hours=1))


def test_get_fetches_and_caches(cache: Cache, mock_get):
    headers = {"User-Agent": "cats-test"}
    response = cache.get(URL, headers=headers)
    assert response.json() == {"data": [1, 2, 3]}
    mock_get.assert_called_once_with(URL, headers=headers)
    assert cache._key(URL).exists()


def test_get_uses_cache(cache: Cache, mock_get):
    cache.get(URL)
    response = cache.get(URL)
    assert response.json() == {"data": [1, 2, 3]}
    assert response.status_code == 200
    mock_get.assert_called_once()


def test_get_keys_by_url(cache: Cache, mock_get):
    other = URL + "&extra=1"
    cache.get(URL)
    cache.get(other)
    assert mock_get.call_count == 2
    assert cache._key(URL) != cache._key(other)


def test_get_refetches_when_expired(cache: Cache, mock_get):
    cache.get(URL)
    age(cache._key(URL), timedelta(hours=2).total_seconds())
    mock_get.return_value = make_response(content=b'{"data": "new"}')
    assert cache.get(URL).json() == {"data": "new"}
    assert mock_get.call_count == 2
    # the refreshed entry is served from the cache
    assert cache.get(URL).json() == {"data": "new"}
    assert mock_get.call_count == 2


def test_get_does_not_cache_errors(cache: Cache, mock_get):
    mock_get.return_value = make_response(status_code=500, content=b"")
    response = cache.get(URL)
    assert response.status_code == 500
    with pytest.raises(requests.exceptions.HTTPError):
        response.raise_for_status()
    assert not cache._key(URL).exists()
    cache.get(URL)
    assert mock_get.call_count == 2


def test_get_refetches_corrupt_entry(cache: Cache, mock_get):
    cache._key(URL).write_text("not json")
    assert cache.get(URL).json() == {"data": [1, 2, 3]}
    mock_get.assert_called_once()
    # corrupt entry is replaced
    deserialise(cache._key(URL).read_text())


def test_get_propagates_connection_errors(cache: Cache, mock_get):
    mock_get.side_effect = requests.exceptions.ConnectionError
    with pytest.raises(requests.exceptions.ConnectionError):
        cache.get(URL)
    assert not cache._key(URL).exists()


def test_clear(cache: Cache, mock_get):
    assert not cache.clear(URL)
    cache.get(URL)
    assert cache.clear(URL)
    assert not cache._key(URL).exists()
    cache.get(URL)
    assert mock_get.call_count == 2


def test_clear_expired(cache: Cache, mock_get):
    old, new = URL + "&old", URL + "&new"
    cache.get(old)
    cache.get(new)
    age(cache._key(old), timedelta(hours=2).total_seconds())
    assert cache.clear_expired() == [cache._key(old)]
    assert not cache._key(old).exists()
    assert cache._key(new).exists()
    assert cache.clear_expired() == []


def test_no_temp_files_left(cache: Cache, mock_get):
    cache.get(URL)
    assert [p.name for p in cache.path.iterdir()] == [cache._key(URL).name]


def test_fetch_url_uses_cache(tmp_path: Path, mock_get):
    with patch("cats.providers.base.tempfile.gettempdir", return_value=str(tmp_path)):
        assert fetch_url(URL) == {"data": [1, 2, 3]}
        assert fetch_url(URL) == {"data": [1, 2, 3]}
    mock_get.assert_called_once()
    # user agent is always sent
    assert user_agent.items() <= mock_get.call_args.kwargs["headers"].items()
    assert (tmp_path / CACHE_NAME).is_dir()


def test_get_retries_transient_errors(cache: Cache, mock_get):
    mock_get.side_effect = [make_response(503), make_response(429), make_response()]
    with patch("cats.cache.time.sleep") as sleep:
        response = cache.get(URL)
    assert response.ok
    assert mock_get.call_count == 3
    assert sleep.call_count == 2


def test_get_does_not_retry_500(cache: Cache, mock_get):
    mock_get.return_value = make_response(500)
    with patch("cats.cache.time.sleep") as sleep:
        assert cache.get(URL).status_code == 500
    assert mock_get.call_count == 1
    sleep.assert_not_called()


def test_get_gives_up_after_max_retries(cache: Cache, mock_get):
    mock_get.return_value = make_response(503)
    with patch("cats.cache.time.sleep"):
        assert cache.get(URL).status_code == 503
    assert mock_get.call_count == 4
