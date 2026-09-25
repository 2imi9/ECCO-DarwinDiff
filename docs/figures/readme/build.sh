#!/usr/bin/env bash
# Build the README figures: pdflatex -> SVG (pdftocairo) -> render check.
# Needs a TeX Live with pgf/tikz, sansmath and standalone, plus poppler-utils and librsvg2-bin.
#   bash docs/figures/readme/build.sh                 # every figure
#   bash docs/figures/readme/build.sh readme_loop     # one figure
set -euo pipefail
cd "$(dirname "$0")"
figs=("$@")
[ ${#figs[@]} -eq 0 ] && figs=(readme_method readme_components readme_loop)
for f in "${figs[@]}"; do
  pdflatex -interaction=nonstopmode -halt-on-error "$f.tex" > "$f.buildlog" 2>&1 \
    || { tail -30 "$f.buildlog"; echo "FAIL: pdflatex $f"; exit 1; }
  if grep -q "Overfull\|Underfull" "$f.log"; then grep "Overfull\|Underfull" "$f.log"; fi
  pdftocairo -svg "$f.pdf" "$f.svg"
  pdftoppm -r 200 -png -singlefile "$f.pdf" "$f.pdfref"
  rsvg-convert -z 2.7778 -b white "$f.svg" -o "$f.svgref.png"
  python3 check_render.py "$f"
done
