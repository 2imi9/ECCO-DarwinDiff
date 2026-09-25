"""Check that a figure's SVG renders like its PDF.

Guards the failure that blanked fig4_architecture_bw.svg: an SVG that converts without error but
renders empty. Compares the poppler raster of the PDF with the librsvg raster of the SVG.
Usage: python3 check_render.py FIGURE_STEM  (run by build.sh)
"""
import sys

from PIL import Image, ImageChops, ImageStat

stem = sys.argv[1]
ref = Image.open(f"{stem}.pdfref.png").convert("L")
svg = Image.open(f"{stem}.svgref.png").convert("L")
ok = True
if abs(ref.size[0] - svg.size[0]) > 2 or abs(ref.size[1] - svg.size[1]) > 2:
    print(f"FAIL {stem}: size pdf {ref.size} vs svg {svg.size}")
    ok = False
else:
    svg = svg.resize(ref.size)
    ink = sum(ImageStat.Stat(svg.point(lambda v: 255 if v < 200 else 0)).sum) / 255 / (svg.size[0] * svg.size[1])
    mad = ImageStat.Stat(ImageChops.difference(ref, svg)).mean[0]
    print(f"{stem}: {svg.size[0]}x{svg.size[1]} px, ink {ink:.1%}, mean |pdf-svg| {mad:.2f}/255")
    if ink < 0.01:
        print(f"FAIL {stem}: SVG is near-blank")
        ok = False
    if mad > 4:
        print(f"FAIL {stem}: SVG diverges from PDF")
        ok = False
sys.exit(0 if ok else 1)
