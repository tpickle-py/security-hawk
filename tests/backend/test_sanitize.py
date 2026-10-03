"""Tests for SVG sanitization."""

from __future__ import annotations

from plans.sanitize import sanitize_svg


def test_sanitize_clean_svg() -> None:
    clean_svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="50" height="50" fill="red"/></svg>'
    sanitized = sanitize_svg(clean_svg)
    assert b"<rect" in sanitized
    assert b'fill="red"' in sanitized


def test_strip_script_tags() -> None:
    malicious = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert("xss")</script><rect width="10" height="10"/></svg>'
    sanitized = sanitize_svg(malicious)
    assert b"<script" not in sanitized
    assert b"alert" not in sanitized
    assert b"<rect" in sanitized


def test_strip_inline_event_handlers() -> None:
    malicious = b'<svg xmlns="http://www.w3.org/2000/svg"><rect onload="alert(1)" onclick="alert(2)" width="10" height="10"/></svg>'
    sanitized = sanitize_svg(malicious)
    assert b"onload" not in sanitized
    assert b"onclick" not in sanitized
    assert b"<rect" in sanitized


def test_strip_javascript_href() -> None:
    malicious = b'<svg xmlns="http://www.w3.org/2000/svg"><a href="javascript:alert(1)"><text>Click</text></a></svg>'
    sanitized = sanitize_svg(malicious)
    assert b"javascript:" not in sanitized
