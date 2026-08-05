#!/usr/bin/env python3
"""Render the three-collapse comparison figure from the pooler audit.

The numbers are transcribed from the committed finding, which is the canonical record:
    docs/findings/2026-08-04_pooler_audit_the_flagship_trio_halves.md
graded by scripts/analysis/pooler_audit.py on `collapse/collapse_n50`. They are NOT re-derived
here -- this script only draws. If the finding is revised, edit PANEL_A / PANEL_B to match and
re-run; do not let the figure and the finding drift.

    python scripts/analysis/plot_pooler_collapses.py

Writes docs/figures/fig_pooler_three_collapses.svg.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "figures" / "fig_pooler_three_collapses.svg"

# Palette: a single-hue LUMINANCE LADDER anchored on ddBlue from docs/figures/tikz/
# darwindiff-tikz-v2.sty. The first draft used a generic categorical palette whose worst
# greyscale contrast between series measured 1.14 -- the three collapses merge in a monochrome
# print, which is precisely the failure that style file exists to prevent (it rejects Okabe-Ito
# for the same reason). This ladder measures 2.23 worst-pair against the house floor of 2.11,
# and lightness is monotonic (Y 5.9 / 19.3 / 51.8 %), which is the right check for a ramp --
# the categorical CVD validator does not apply to a one-hue scale.
#
# The house triple is NOT used directly: its colours are semantic (ddBlue = a real absolute
# observation constrains this; ddGold = constrained only by pattern; ddRed = stroke only, never
# a fill), so painting three pooling operators with them would assert evidence-class claims that
# mean nothing here. Emphasis is carried by the bold value and the dashed ring, not by hue.
SERIES = [("arithmetic", "#004488"), ("geometric", "#3C7FB1"), ("median", "#9BC4DF")]
# The lightest step is only 1.80:1 against the surface, so every bar carries a hairline edge.
BAR_EDGE, BAR_EDGE_W = "#1A1A1A", 0.5
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#6b6a66"
GRID, AXIS, SURFACE = "#e5e4e0", "#b8b7b2", "#fcfcfb"
MONO = "ui-monospace, Consolas, monospace"

# (label, [arithmetic, geometric, median], mono?, emphasise-index or None)
PANEL_A = [
    ("alpfe", [49, 49, 49], True, None),
    ("R_PICPOC", [50, 50, 50], True, None),
    ("scav_rat", [26, 13, 24], True, None),
    ("trio", [25, 12, 23], False, 1),
]
PANEL_B = [
    ("eqpac", [8, 8, 10], True, None),
    ("natlsubpolar", [19, 5, 16], True, 1),
    ("southernoceanpac", [49, 49, 49], True, None),
]

YMAX, TOP, BASE = 50, 140, 430          # value 50 sits at y=TOP; 0 at y=BASE
H = BASE - TOP
PANELS = [(70, 480), (590, 1000)]        # x extents
BARW, GAP = 26, 2                        # 2px surface gap between adjacent fills
W, HEIGHT = 1040, 580


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def y_of(v: float) -> float:
    return BASE - (v / YMAX) * H


def bar(x: float, v: float, fill: str) -> str:
    """Top corners rounded 4px, square where it meets the baseline."""
    y, r = y_of(v), 4
    return (f'<path d="M{x},{BASE} L{x},{y + r} Q{x},{y} {x + r},{y} '
            f'L{x + BARW - r},{y} Q{x + BARW},{y} {x + BARW},{y + r} '
            f'L{x + BARW},{BASE} Z" fill="{fill}" stroke="{BAR_EDGE}" '
            f'stroke-width="{BAR_EDGE_W}"/>')


def panel(groups, x0: float, x1: float) -> list[str]:
    out, gw = [], (x1 - x0) / len(groups)
    span = len(SERIES) * BARW + (len(SERIES) - 1) * GAP
    for gi, (name, vals, mono, emph) in enumerate(groups):
        gx = x0 + gi * gw + (gw - span) / 2
        for si, v in enumerate(vals):
            bx = gx + si * (BARW + GAP)
            out.append(bar(bx, v, SERIES[si][1]))
            bold = ' font-weight="700"' if emph == si else ""
            col = INK if emph == si else INK2
            out.append(f'<text x="{bx + BARW / 2:.1f}" y="{y_of(v) - 6:.1f}" font-size="10.5" '
                       f'fill="{col}"{bold} text-anchor="middle">{v}</text>')
        fam = f' font-family="{MONO}"' if mono else ' font-weight="600"'
        out.append(f'<text x="{gx + span / 2:.1f}" y="{BASE + 20}" font-size="11.5" '
                   f'fill="{INK}"{fam} text-anchor="middle">{esc(name)}</text>')
    return out


def main() -> None:
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {HEIGHT}" width="{W}" '
         f'height="{HEIGHT}" font-family="Inter, Segoe UI, Helvetica, Arial, sans-serif">',
         f'<rect width="{W}" height="{HEIGHT}" fill="{SURFACE}"/>',
         f'<text x="40" y="38" font-size="19" font-weight="600" fill="{INK}">'
         'The pooled average decides the headline, and it moves one basin</text>',
         f'<text x="40" y="60" font-size="12.5" fill="{INK2}">Flagship twin '
         f'<tspan font-family="{MONO}">collapse/collapse_n50</tspan>, n = 50 seeds, per-AOI '
         f'&#8805;2-of-3 at the &#177;40% band. Bitwise identical to '
         f'<tspan font-family="{MONO}">ctrl_n50</tspan> on all 50 seeds.</text>']

    lx = 40
    for name, col in SERIES:
        s.append(f'<rect x="{lx}" y="76" width="11" height="11" rx="2" fill="{col}" '
                 f'stroke="{BAR_EDGE}" stroke-width="{BAR_EDGE_W}"/>')
        s.append(f'<text x="{lx + 17}" y="86" font-size="12" fill="{INK2}">{name}</text>')
        lx += 24 + len(name) * 6.6

    s.append(f'<text x="70" y="112" font-size="13" font-weight="600" fill="{INK}">'
             'A &#183; Per parameter, and the joint trio</text>')
    s.append(f'<text x="590" y="112" font-size="13" font-weight="600" fill="{INK}">B &#183; '
             f'<tspan font-family="{MONO}">scav_rat</tspan> broken out by basin</text>')

    for x0, x1 in PANELS:
        for v in range(0, YMAX + 1, 10):
            y = y_of(v)
            stroke = AXIS if v == 0 else GRID
            s.append(f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{stroke}" stroke-width="1"/>')
            s.append(f'<text x="{x0 - 8}" y="{y + 4}" font-size="10.5" fill="{MUTED}" '
                     f'text-anchor="end">{v}</text>')
    s.append(f'<text x="34" y="{(TOP + BASE) / 2}" font-size="10.5" fill="{MUTED}" '
             f'text-anchor="middle" transform="rotate(-90 34 {(TOP + BASE) / 2})">'
             'seeds passing (of 50)</text>')

    s += panel(PANEL_A, *PANELS[0])
    s += panel(PANEL_B, *PANELS[1])

    # ring the one leg that moves
    gw = (PANELS[1][1] - PANELS[1][0]) / 3
    hx = PANELS[1][0] + gw
    s.append(f'<rect x="{hx + 8:.1f}" y="{TOP - 22}" width="{gw - 16:.1f}" height="{H + 22}" '
             f'fill="none" stroke="{INK}" stroke-width="1" stroke-dasharray="3 3" opacity="0.42"/>')

    notes = [
        (40, 478, f'<tspan font-family="{MONO}">alpfe</tspan> and '
                  f'<tspan font-family="{MONO}">R_PICPOC</tspan> are exactly invariant. The trio '
                  'count equals'),
        (40, 495, f'<tspan font-family="{MONO}">scav_rat</tspan>’s, so '
                  f'<tspan font-family="{MONO}">scav_rat</tspan> is the sole binding leg.'),
        (590, 478, 'Only the North Atlantic moves. Its per-cell '
                   f'<tspan font-family="{MONO}">log_sd</tspan> is 0.940'),
        (590, 495, '(inflation &#215;1.56) against 0.245 at eqpac and 0.379 in the SO.'),
    ]
    for x, y, t in notes:
        s.append(f'<text x="{x}" y="{y}" font-size="11.5" fill="{INK2}">{t}</text>')

    s.append(f'<line x1="40" y1="518" x2="1000" y2="518" stroke="{GRID}" stroke-width="1"/>')
    foot = [
        f'Paired McNemar on <tspan font-family="{MONO}">scav_rat</tspan>, same seeds and same '
        'fits: 13 seeds pass under arithmetic only, 0 under geometric only, P = 2.4e-04. The '
        'collapse never flips a seed the other way.',
        'Source: docs/findings/2026-08-04_pooler_audit_the_flagship_trio_halves.md &#183; graded '
        'with scripts/analysis/pooler_audit.py &#183; counts are the per-AOI &#8805;2-of-3 '
        'metric, not cell-weighted.',
        f'A separate single-AOI Southern Ocean run (<tspan font-family="{MONO}">so_only</tspan>) '
        f'is not shown: there <tspan font-family="{MONO}">scav_rat</tspan> reads 30/50 arithmetic '
        'and 49/50 geometric. Do not conflate it with the SO leg above.',
    ]
    for i, t in enumerate(foot):
        s.append(f'<text x="40" y="{536 + i * 17}" font-size="10.5" fill="{MUTED}">{t}</text>')

    s.append("</svg>")
    OUT.write_text("\n".join(s) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO).as_posix()}  {OUT.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
