"""Tests for the TitleCommand."""

import pytest
from pytest import CaptureFixture

from urload.commands.base import CommandError
from urload.commands.title import TitleCommand
from urload.url import URL


class DummyResponse:
    """A dummy response object for mocking requests.get."""

    def __init__(self, content: bytes):
        """Initialize with HTML content."""
        self.content = content
        self.text = content.decode("utf-8")

    def raise_for_status(self) -> None:
        """No-op for status check."""
        pass


def url_list() -> list[URL]:
    """Return a list of test URLs."""
    return [URL(f"https://site.com/{i}") for i in range(5)]


# Constants for test expectations
EXPECTED_RANGE_COUNT = 3
EXPECTED_END_RANGE_COUNT = 2
EXPECTED_INCLUSIVE_COUNT = 3


def test_title_command_extracts_titles(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that TitleCommand extracts and prints HTML titles."""

    def mock_get(
        url: str, timeout: int = 10, headers: dict[str, str] | None = None
    ) -> DummyResponse:
        if "site.com/0" in url:
            return DummyResponse(b"<html><head><title>Page Zero</title></head></html>")
        elif "site.com/1" in url:
            return DummyResponse(b"<html><head><title>Page One</title></head></html>")
        else:
            return DummyResponse(b"<html><head><title>Other Page</title></head></html>")

    monkeypatch.setattr("requests.get", mock_get)

    cmd = TitleCommand()
    test_urls = [URL("https://site.com/0"), URL("https://site.com/1")]
    result = cmd.run([], test_urls)

    captured = capsys.readouterr()
    output = captured.out.strip().splitlines()

    assert "0: Page Zero" in output
    assert "1: Page One" in output
    assert result == test_urls


def test_title_command_no_title_tag(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that TitleCommand handles HTML without title tag."""

    def mock_get(
        url: str, timeout: int = 10, headers: dict[str, str] | None = None
    ) -> DummyResponse:
        return DummyResponse(b"<html><body>No title here</body></html>")

    monkeypatch.setattr("requests.get", mock_get)

    cmd = TitleCommand()
    test_urls = [URL("https://site.com/notitle")]
    result = cmd.run([], test_urls)

    captured = capsys.readouterr()
    output = captured.out.strip()

    assert "0: No title found" in output
    assert result == test_urls


def test_title_command_network_error(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that TitleCommand handles network errors gracefully."""

    def mock_get(
        url: str, timeout: int = 10, headers: dict[str, str] | None = None
    ) -> DummyResponse:
        raise ConnectionError("Network error")

    monkeypatch.setattr("requests.get", mock_get)

    cmd = TitleCommand()
    test_urls = [URL("https://site.com/error")]
    result = cmd.run([], test_urls)

    captured = capsys.readouterr()
    output = captured.out.strip()

    assert "0: Error fetching title" in output
    assert "Network error" in output
    assert result == test_urls


def test_title_command_empty_list(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that TitleCommand prints nothing for an empty list."""
    cmd = TitleCommand()
    empty_list: list[URL] = []
    result = cmd.run([], empty_list)

    captured = capsys.readouterr()
    assert captured.out.strip() == ""
    assert result == empty_list


def test_title_command_single_index(
    capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that title with a single index processes only that URL."""

    def mock_get(
        url: str, timeout: int = 10, headers: dict[str, str] | None = None
    ) -> DummyResponse:
        return DummyResponse(b"<html><head><title>Single Title</title></head></html>")

    monkeypatch.setattr("requests.get", mock_get)

    cmd = TitleCommand()
    urls = url_list()
    cmd.run(["2"], urls)

    captured = capsys.readouterr()
    output = captured.out.strip()
    assert "2: Single Title" in output
    # Should only process one URL
    assert output.count("Single Title") == 1


def test_title_command_range_start_dash(
    capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that title with -N processes from 0 to N inclusive."""

    def mock_get(
        url: str, timeout: int = 10, headers: dict[str, str] | None = None
    ) -> DummyResponse:
        return DummyResponse(b"<html><head><title>Range Title</title></head></html>")

    monkeypatch.setattr("requests.get", mock_get)

    cmd = TitleCommand()
    urls = url_list()
    cmd.run(["-2"], urls)

    captured = capsys.readouterr()
    output = captured.out.strip()
    # Should process URLs 0, 1, 2
    assert "0: Range Title" in output
    assert "1: Range Title" in output
    assert "2: Range Title" in output
    assert output.count("Range Title") == EXPECTED_RANGE_COUNT


def test_title_command_range_end_dash(
    capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that title with N- processes from N to the end."""

    def mock_get(
        url: str, timeout: int = 10, headers: dict[str, str] | None = None
    ) -> DummyResponse:
        return DummyResponse(
            b"<html><head><title>End Range Title</title></head></html>"
        )

    monkeypatch.setattr("requests.get", mock_get)

    cmd = TitleCommand()
    urls = url_list()
    cmd.run(["3-"], urls)

    captured = capsys.readouterr()
    output = captured.out.strip()
    # Should process URLs 3, 4
    assert "3: End Range Title" in output
    assert "4: End Range Title" in output
    assert output.count("End Range Title") == EXPECTED_END_RANGE_COUNT


def test_title_command_range_inclusive(
    capsys: CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that title with N-M processes from N to M inclusive."""

    def mock_get(
        url: str, timeout: int = 10, headers: dict[str, str] | None = None
    ) -> DummyResponse:
        return DummyResponse(
            b"<html><head><title>Inclusive Title</title></head></html>"
        )

    monkeypatch.setattr("requests.get", mock_get)

    cmd = TitleCommand()
    urls = url_list()
    cmd.run(["1-3"], urls)

    captured = capsys.readouterr()
    output = captured.out.strip()
    # Should process URLs 1, 2, 3
    assert "1: Inclusive Title" in output
    assert "2: Inclusive Title" in output
    assert "3: Inclusive Title" in output
    assert output.count("Inclusive Title") == EXPECTED_INCLUSIVE_COUNT


def test_title_command_invalid_range_raises() -> None:
    """Test that invalid range arguments raise CommandError."""
    cmd = TitleCommand()
    urls = url_list()

    # Test various invalid range formats
    with pytest.raises(CommandError):
        cmd.run(["100"], urls)  # Out of range
    with pytest.raises(CommandError):
        cmd.run(["foo"], urls)  # Non-numeric
    with pytest.raises(CommandError):
        cmd.run(["-"], urls)  # Just dash
    with pytest.raises(CommandError):
        cmd.run(["3-bar"], urls)  # Invalid end
    with pytest.raises(CommandError):
        cmd.run(["foo-5"], urls)  # Invalid start
    with pytest.raises(CommandError):
        cmd.run(["4-1"], urls)  # Reversed range


def test_title_command_whitespace_handling(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that TitleCommand handles whitespace in titles correctly."""

    def mock_get(
        url: str, timeout: int = 10, headers: dict[str, str] | None = None
    ) -> DummyResponse:
        return DummyResponse(
            b"<html><head><title>  \n  Trimmed Title  \n  </title></head></html>"
        )

    monkeypatch.setattr("requests.get", mock_get)

    cmd = TitleCommand()
    test_urls = [URL("https://site.com/whitespace")]
    result = cmd.run([], test_urls)

    captured = capsys.readouterr()
    output = captured.out.strip()

    assert "0: Trimmed Title" in output
    assert result == test_urls
