import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs" / "findings" / "2026-08-09_loss_twin_dimensional_matrix.json"
DECK = (
    ROOT
    / "docs"
    / "findings"
    / "2026-08-09_presentation_planning_weekly_log_aug4_11_as_of_aug9.html"
)


def _matrix():
    return json.loads(MATRIX.read_text(encoding="utf-8"))


def _cell(payload, arm, parameter, pooler, band):
    return next(
        row
        for row in payload["records"]
        if row["arm"] == arm
        and row["parameter"] == parameter
        and row["pooler"] == pooler
        and row["band"] == band
    )


def test_loss_twin_matrix_preserves_every_design_cell():
    payload = _matrix()

    assert len(payload["arms"]) == 15
    assert len(payload["records"]) == 15 * 6 * 3 * 4
    assert all(arm["n"] == 50 for arm in payload["arms"])
    assert {row["reporting_status"] for row in payload["records"]} == {
        "reported",
        "excluded",
        "gated",
    }


def test_loss_twin_matrix_never_leaks_gated_or_excluded_counts():
    payload = _matrix()

    suppressed = [
        row for row in payload["records"] if row["reporting_status"] != "reported"
    ]
    assert suppressed
    assert all(row["count"] is None for row in suppressed)
    assert all(row["median_x_truth"] is None for row in suppressed)
    assert all(
        row["reporting_status"] == "gated"
        for row in payload["records"]
        if row["aoi"] == "southernoceanpac"
    )


def test_loss_twin_matrix_pins_the_bounded_scav_rat_result():
    payload = _matrix()

    assert _cell(payload, "eq_ee", "scav_rat", "geometric", 0.20)["count"] == 50
    assert _cell(payload, "na_ee", "scav_rat", "median", 0.10)["count"] == 24
    assert _cell(payload, "eq_le", "scav_rat", "geometric", 0.40)["count"] == 0
    assert _cell(payload, "na_lm", "scav_rat", "geometric", 0.40)["count"] == 0


def test_loss_twin_matrix_keeps_parameter_interpretation_explicit():
    roles = _matrix()["parameter_roles"]

    assert roles["scav_rat"]["role"] == "primary-inferential-target"
    assert roles["alpfe"]["role"] == "boundary-diagnostic-only"
    assert roles["R_PICPOC"]["role"] == "twin-anchor-machinery-check"
    assert roles["Smallgrow"]["numeric"] is False
    assert roles["Biggrow"]["numeric"] is False
    assert roles["diatomgraz"]["numeric"] is False


def test_html_deck_exposes_the_complete_matrix_without_forbidden_images():
    html = DECK.read_text(encoding="utf-8")

    slides = re.findall(
        r'<section class="slide(?: [^"]*)?" id="slide-(\d+)" data-title="[^"]+">',
        html,
    )
    assert [int(number) for number in slides] == list(range(1, 18))
    assert re.findall(r'<span class="folio">(\d{2}) / 17</span>', html) == [
        f"{number:02d}" for number in range(1, 18)
    ]
    assert "1,080-cell relation" in html
    assert "All bands / all poolers" in html
    assert "all 15 arms" in html
    assert "all six parameters" in html
    assert "stage0-failed-stop" in html
    assert "all eight waiver subsets" in html
    assert "prey-field-energy-deficit" in html
    assert "The core log is frozen as of Aug 9" in html
    assert "Aug 10 verified appendix, not backfilled outcomes" in html
    assert "every task on this slide is planned closeout" in html
    assert not re.search(r"<img\b", html, flags=re.IGNORECASE)
    assert not re.search(r"<img[^>]+emulator_globe_chl1\.png", html, flags=re.IGNORECASE)
    assert "beats persistence at every scale tested" not in html.lower()
