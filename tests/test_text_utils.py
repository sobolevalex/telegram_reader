"""Tests for text_utils.filter_links."""

import pytest

from telegram_reader.text_utils import filter_links


def test_filter_links_empty_string() -> None:
    assert filter_links("") == ""


def test_filter_links_no_links() -> None:
    text = "Just some text without any links."
    assert filter_links(text) == text


def test_filter_links_markdown_link() -> None:
    assert filter_links("See [click here](https://example.com) for more.") == (
        "See click here for more."
    )


def test_filter_links_bare_http_url() -> None:
    assert filter_links("Visit https://example.com today.") == "Visit today."


def test_filter_links_bare_https_url() -> None:
    assert filter_links("Secure https://secure.site/path") == "Secure"


def test_filter_links_www_url() -> None:
    assert filter_links("Go to www.example.com now.") == "Go to now."


def test_filter_links_multiple_urls() -> None:
    result = filter_links(
        "First https://a.com then www.b.com and [text](http://c.com)."
    )
    assert result == "First then and text."


def test_filter_links_collapses_spaces() -> None:
    result = filter_links("Hello  https://x.com   world")
    assert result == "Hello world"


def test_filter_links_strips_whitespace() -> None:
    result = filter_links("  [link](https://x.com)  ")
    assert result == "link"
