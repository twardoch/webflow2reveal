# this_file: py/tests/test_compiler.py
"""Unit and functional tests for the webflow2reveal compiler.

Network is never touched: URL conversion is exercised by monkeypatching
``requests.get`` so the suite runs offline and deterministically.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from webflow2reveal import compiler
from webflow2reveal.compiler import (
    convert,
    extract_webflow2reveal_options,
    find_balanced_braces,
    get_section_bg_color,
    is_slide_section,
    parse_css_background_colors,
    parse_options_from_js,
)

FIXTURE = """<!DOCTYPE html>
<html>
<head>
<style>
  .dark-slide { background-color: #101010; }
  .light-slide { background-color: #f5f5f5; }
  body { background-color: rgb(20, 20, 20); }
</style>
</head>
<body class="body">
  <section class="nav menu">navbar chrome</section>
  <section class="dark-slide">
    <div class="container"><h1>Hello</h1><p>First slide</p></div>
  </section>
  <section class="light-slide">
    <div class="container"><h2>Bright</h2></div>
  </section>
  <section class="footer">footer chrome</section>
</body>
</html>
"""


def test_parse_css_background_colors_reads_class_colors() -> None:
    colors = parse_css_background_colors(
        ".a { background-color: #fff; } .b { background: #000; }"
    )
    assert colors["a"] == "#fff"
    assert colors["b"] == "#000"


def test_parse_css_background_colors_ignores_comments() -> None:
    colors = parse_css_background_colors("/* .x { background-color: red } */ .y { background-color: blue }")
    assert "x" not in colors
    assert colors["y"] == "blue"


def test_is_slide_section_filters_chrome() -> None:
    soup = BeautifulSoup(FIXTURE, "html.parser")
    sections = soup.find_all("section")
    keep = [s for s in sections if is_slide_section(s)]
    assert len(keep) == 2  # the two content slides, nav and footer dropped


def test_get_section_bg_color_prefers_most_specific() -> None:
    colors = {"outer": "#111", "inner": "#eee"}
    assert get_section_bg_color(["outer", "inner"], colors) == "#eee"
    assert get_section_bg_color(["unknown"], colors) is None


def test_find_balanced_braces_handles_nesting_and_strings() -> None:
    text = "opts = { a: 1, b: { c: '}' } } trailing"
    assert find_balanced_braces(text, 0) == "{ a: 1, b: { c: '}' } }"
    assert find_balanced_braces("no braces here", 0) is None


def test_parse_options_from_js_extracts_exclude_and_layout() -> None:
    js = 'window.webflow2revealOptions = { excludeSelectors: [".ad", "#promo"], disableLayout: false };'
    opts = parse_options_from_js(js)
    assert opts["excludeSelectors"] == [".ad", "#promo"]
    assert opts["disableLayout"] is False


def test_extract_options_from_inline_script() -> None:
    html = (
        "<html><body><script>window.webflow2revealOptions = "
        '{ excludeSelectors: [".skip"] };</script></body></html>'
    )
    opts = extract_webflow2reveal_options(html)
    assert opts["excludeSelectors"] == [".skip"]


def test_convert_local_file_builds_reveal_scaffold(tmp_path: Path) -> None:
    src = tmp_path / "page.html"
    src.write_text(FIXTURE, encoding="utf-8")
    out = tmp_path / "deck.html"

    convert(str(src), output=str(out))

    assert out.exists()
    result = BeautifulSoup(out.read_text(encoding="utf-8"), "html.parser")

    # Reveal scaffold is present.
    assert result.select_one("div.reveal > div.slides") is not None

    slides = result.select("div.slides > section.slide-section")
    assert len(slides) == 2

    # Background colours were assigned from the page CSS.
    assert slides[0]["data-background-color"] == "#101010"
    assert slides[1]["data-background-color"] == "#f5f5f5"

    # Luminance classification: dark vs light.
    assert "slide-dark-bg" in slides[0]["class"]
    assert "slide-light-bg" in slides[1]["class"]

    # Reveal.js library and init are injected.
    assert result.find("script", src=lambda v: bool(v) and "reveal.js" in v) is not None


def test_convert_url_source_mocks_network(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        status_code = 200
        text = FIXTURE

        def raise_for_status(self) -> None:
            return None

    def fake_get(url: str, timeout: int = 10) -> FakeResponse:
        return FakeResponse()

    monkeypatch.setattr(compiler.requests, "get", fake_get)

    out = tmp_path / "deck.html"
    convert("https://example.webflow.io/deck", output=str(out))

    assert out.exists()
    result = BeautifulSoup(out.read_text(encoding="utf-8"), "html.parser")
    assert len(result.select("div.slides > section.slide-section")) == 2


def test_convert_exclude_removes_elements(tmp_path: Path) -> None:
    src = tmp_path / "page.html"
    src.write_text(FIXTURE, encoding="utf-8")
    out = tmp_path / "deck.html"

    convert(str(src), output=str(out), exclude=".light-slide")

    result = BeautifulSoup(out.read_text(encoding="utf-8"), "html.parser")
    slides = result.select("div.slides > section.slide-section")
    assert len(slides) == 1
    assert slides[0]["data-background-color"] == "#101010"
