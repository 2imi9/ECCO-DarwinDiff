from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECK = (
    ROOT
    / "docs/findings/2026-08-11_eccodarwindiff_summer_research_closeout.html"
)


def _html() -> str:
    return DECK.read_text(encoding="utf-8")


def test_deck_has_a_complete_sixteen_slide_sequence() -> None:
    html = _html()
    slides = re.findall(
        r'<section class="slide(?: [^"]*)?" id="slide-(\d+)" data-title="([^"]+)">',
        html,
    )
    assert [int(number) for number, _ in slides] == list(range(1, 17))
    assert all(title.strip() for _, title in slides)
    assert re.findall(r'<span class="folio">(\d{2}) / 16</span>', html) == [
        f"{number:02d}" for number in range(1, 17)
    ]
    assert '<span class="counter" id="counter" aria-live="off">1 / 16</span>' in html


def test_deck_is_self_contained_and_diagram_led() -> None:
    html = _html()
    lowered = html.lower()
    assert html.isascii()
    assert html.count("<svg") >= 8
    assert "<img" not in lowered
    assert "<script src=" not in lowered
    assert '<link rel="stylesheet"' not in lowered
    assert "http://" not in lowered
    assert "https://" not in lowered


def test_deck_preserves_the_scientific_guardrails() -> None:
    html = _html()
    lowered = html.lower()
    assert "emulator_globe_chl1.png" not in lowered
    assert "beats persistence at every scale tested" not in lowered
    assert re.search(r"alpfe.{0,40}accur|accur.{0,40}alpfe", lowered) is None

    assert "Southern Ocean, geometric pooler" in html
    assert "one unreplicated result" in html
    assert "Expected zero Daniels/POSi coverage" in html
    assert "does not choose endpoint versus time mean for Darwin" in html
    assert "no optimizer, no recovery array, no B200" in html


def test_deck_reports_the_current_parameter_and_emulator_results() -> None:
    html = _html()
    assert "two globally recovered" in html.lower()
    assert "two regionally identifiable" in html.lower()
    assert "two excluded" in html.lower()
    assert "18/50 arithmetic, geometric, and median" in html
    assert "0 / 10 = 0 / 10" in html
    assert "+0.055" in html
    assert "-0.161" in html
    assert "7.45 ms" in html


def test_deck_points_to_the_honest_product_boundary() -> None:
    html = _html()
    assert "darwindiff_evidence_navigator.html" in html
    assert "Decision support for evidence and experiment design, not ocean prediction" in html
    assert "Do not ship the emulator as a forecast tool" in html
