# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
import http.client
import io
import urllib.error

import pytest
from twinfinder import fetch as fetch_module

URL = "https://example.invalid/data/tile.tif"


class FakeResponse(io.BytesIO):
    """A response body with headers, as urlopen returns."""

    def __init__(self, payload=b"", content_length=None):
        super().__init__(payload)
        self.headers = {} if content_length is None else {"Content-Length": str(content_length)}


class FakeServer:
    """Stands in for urlopen: gives the queued replies in order (raising the errors), then the payload."""

    def __init__(self, replies, payload=b"tile-bytes"):
        self.replies = list(replies)
        self.payload = payload
        self.calls = 0
        self.methods = []

    def __call__(self, request, timeout=None):
        self.calls += 1
        self.methods.append(request.get_method())
        if self.replies:
            reply = self.replies.pop(0)
            if isinstance(reply, Exception):
                raise reply
            return reply
        return FakeResponse(self.payload)


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr(fetch_module.time, "sleep", lambda seconds: None)


def serve(monkeypatch, replies, payload=b"tile-bytes"):
    server = FakeServer(replies, payload)
    monkeypatch.setattr(fetch_module.urllib.request, "urlopen", server)
    return server


def http_error(code, reason):
    return urllib.error.HTTPError(URL, code, reason, None, None)


def not_found():
    return http_error(404, "Not Found")


def forbidden():
    return http_error(403, "Forbidden")


def test_connection_resets_are_retried(tmp_path, monkeypatch, no_sleep):
    server = serve(monkeypatch, [urllib.error.URLError("reset"), ConnectionResetError("reset")])
    path = fetch_module.fetch(URL, tmp_path)
    assert path.read_bytes() == b"tile-bytes"
    assert server.calls == 3


def test_gives_up_after_the_last_retry(tmp_path, monkeypatch, no_sleep):
    server = serve(monkeypatch, [urllib.error.URLError("reset")] * fetch_module.ATTEMPTS)
    with pytest.raises(urllib.error.URLError):
        fetch_module.fetch(URL, tmp_path)
    assert server.calls == fetch_module.ATTEMPTS
    assert not (tmp_path / "tile.tif").exists()


def test_a_missing_file_is_not_retried_and_is_remembered(tmp_path, monkeypatch, no_sleep):
    server = serve(monkeypatch, [not_found()])
    assert fetch_module.fetch_optional(URL, tmp_path) is None
    assert fetch_module.fetch_optional(URL, tmp_path) is None  # answered from the marker
    assert server.calls == 1


def test_a_refused_file_is_an_error_and_is_not_remembered_as_missing(tmp_path, monkeypatch, no_sleep):
    # 403 means the server refused (rate limit, permissions), not that the tile is open ocean.
    server = serve(monkeypatch, [forbidden()])
    with pytest.raises(urllib.error.HTTPError) as raised:
        fetch_module.fetch_optional(URL, tmp_path)
    assert raised.value.code == 403
    assert list(tmp_path.iterdir()) == []                                  # no marker, no partial file
    assert fetch_module.fetch_optional(URL, tmp_path).read_bytes() == b"tile-bytes"  # asked again
    assert server.calls == 2


def test_a_cached_file_is_not_downloaded_again(tmp_path, monkeypatch, no_sleep):
    server = serve(monkeypatch, [])
    fetch_module.fetch(URL, tmp_path)
    fetch_module.fetch(URL, tmp_path)
    assert server.calls == 1


def test_a_body_of_the_announced_length_is_kept(tmp_path, monkeypatch, no_sleep):
    server = serve(monkeypatch, [FakeResponse(b"tile-bytes", content_length=10)])
    assert fetch_module.fetch(URL, tmp_path).read_bytes() == b"tile-bytes"
    assert server.calls == 1


def test_a_short_body_is_retried(tmp_path, monkeypatch, no_sleep):
    server = serve(monkeypatch, [FakeResponse(b"tile", content_length=10),
                                 FakeResponse(b"tile-bytes", content_length=10)])
    assert fetch_module.fetch(URL, tmp_path).read_bytes() == b"tile-bytes"
    assert server.calls == 2


def test_a_body_that_stays_short_is_an_error_and_leaves_no_file(tmp_path, monkeypatch, no_sleep):
    server = serve(monkeypatch, [FakeResponse(b"tile", content_length=10)
                                 for _ in range(fetch_module.ATTEMPTS)])
    with pytest.raises(ConnectionError, match="4 of 10 bytes"):
        fetch_module.fetch(URL, tmp_path)
    assert server.calls == fetch_module.ATTEMPTS
    assert list(tmp_path.iterdir()) == []


def test_a_body_cut_off_mid_read_is_retried(tmp_path, monkeypatch, no_sleep):
    server = serve(monkeypatch, [http.client.IncompleteRead(b"tile", 6)])
    assert fetch_module.fetch(URL, tmp_path).read_bytes() == b"tile-bytes"
    assert server.calls == 2


class CutOffResponse(FakeResponse):
    """A body that gives its first four bytes and then breaks off, as a dropped connection does."""

    def read(self, *args):
        if self.tell():
            raise http.client.IncompleteRead(b"", 6)
        return super().read(4)


def test_a_body_that_breaks_off_after_some_bytes_is_retried(tmp_path, monkeypatch, no_sleep):
    server = serve(monkeypatch, [CutOffResponse(b"tile-bytes")])
    assert fetch_module.fetch(URL, tmp_path).read_bytes() == b"tile-bytes"
    assert server.calls == 2
    assert [p.name for p in tmp_path.iterdir()] == ["tile.tif"]  # the four bytes were not kept


def test_a_body_that_keeps_breaking_off_is_an_error_and_leaves_no_file(tmp_path, monkeypatch, no_sleep):
    server = serve(monkeypatch, [CutOffResponse(b"tile-bytes") for _ in range(fetch_module.ATTEMPTS)])
    with pytest.raises(http.client.IncompleteRead):
        fetch_module.fetch(URL, tmp_path)
    assert server.calls == fetch_module.ATTEMPTS
    assert list(tmp_path.iterdir()) == []


# Every answer except 404 says nothing about whether the file exists.
OTHER_ANSWERS = [401, 403, 429, 500, 503]


@pytest.mark.parametrize("code", OTHER_ANSWERS)
def test_no_answer_but_404_is_remembered_as_missing(code, tmp_path, monkeypatch, no_sleep):
    server = serve(monkeypatch, [http_error(code, "refused")])
    with pytest.raises(urllib.error.HTTPError) as raised:
        fetch_module.fetch_optional(URL, tmp_path)
    assert raised.value.code == code
    assert list(tmp_path.iterdir()) == []  # no marker, no partial file
    assert server.calls == 1               # the server answered, so it is not asked again at once


def test_exists_on_server_asks_without_downloading(monkeypatch):
    server = serve(monkeypatch, [])
    assert fetch_module.exists_on_server(URL) is True
    assert server.methods == ["HEAD"]


def test_only_404_means_not_on_the_server(monkeypatch):
    serve(monkeypatch, [not_found()])
    assert fetch_module.exists_on_server(URL) is False
    serve(monkeypatch, [forbidden()])
    with pytest.raises(urllib.error.HTTPError):
        fetch_module.exists_on_server(URL)


@pytest.mark.parametrize("code", OTHER_ANSWERS)
def test_exists_on_server_raises_on_any_answer_but_404(code, monkeypatch):
    serve(monkeypatch, [http_error(code, "refused")])
    with pytest.raises(urllib.error.HTTPError) as raised:
        fetch_module.exists_on_server(URL)
    assert raised.value.code == code
