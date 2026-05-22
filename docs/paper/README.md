# Internal white paper — DarwinDiff proof-of-concept

LaTeX source for the DarwinDiff internal white paper. Not a publication submission; an internal record of the v3.1 proof-of-concept result with all numerical claims anchored to the canonical project sources (`STATUS.md`, `docs/findings/v3.1_closeout.md`, `docs/ecco_darwin_parameter_inventory.md`).

No author block, no venue, no acknowledgements section. Lives in the repo as documentation; can be promoted to a public submission later if scope expands.

## What's here

| File | Purpose |
|---|---|
| [`main.tex`](main.tex) | LaTeX source. Builds with stock `pdflatex` + `bibtex`. |
| [`references.bib`](references.bib) | BibTeX bibliography. 14 entries; DOIs verified. |
| [`figures.md`](figures.md) | Per-figure specifications + copy-paste prompts for Claude Design. Five figures (4 required + 1 optional). |
| `figures/` | (To be populated) — rendered figure files (PDF / SVG preferred). |

## Build

```bash
cd docs/paper
latexmk -pdf main.tex
# or
pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

The default class is `\documentclass[11pt,letterpaper]{article}` — portable, no external class files required.

## Status

- **Draft complete.** All numerical claims anchored.
- **Figures pending.** Five Claude Design prompts in `figures.md`; rendered figures will live in `figures/`.
- **No names.** Internal doc; no author block, no acknowledgements.

## Verified claims map

Every numerical claim in `main.tex` is anchored:

| Claim | Source |
|---|---|
| 857 seeds / 86 configs / 5 sweep waves + Wave 6 composition | `STATUS.md` current-state bullet; `docs/findings/v3.1_closeout.md` Summary |
| Basin C iron-pair 38/40 at n=40 | `STATUS.md` headline-results table; v3.1_closeout headline table |
| 2/857 = 0.24% break to 5/6, 0/857 at 6/6 | v3.1_closeout headline table |
| F2 configuration formula (`POSI_W=1.0 + AOI_W_NATL=2.0 + AOI_W_SO=2.0 + CHL1_W_EXTRA=3.0`) | `STATUS.md` headline-results table |
| Wave 6 composition (0/10 at 5/6, mean_cal 2.00 vs parent 2.40 / 2.70) | v3.1_closeout Wave 6 section |
| Carroll-6 names, source lines, optimized values | `docs/ecco_darwin_parameter_inventory.md` |
| `darwin_plankton.F` as Darwin 3 SMS kernel | Live `darwinproject/darwin3@darwin:pkg/darwin/darwin_plankton.F` (verified 2026-05-21) |
| BINN architecture details | Xu et al. 2025 paper text |
| Carroll 2020 DOI `10.1029/2019MS001888` | AGU/Wiley web fetch 2026-05-21 |
| Carroll 2022 DOI `10.1029/2021GB007162` | Project memory `reference_carroll_2022.md` |

Anything labeled "approximate" or "illustrative" in `figures.md` (e.g., Figure 2 bucket counts) needs recomputation from raw sweep JSONs before final figure rendering.

## If we later decide to submit externally

The LaTeX structure is already journal-friendly. To convert to AGU JAMES / GBC: swap `\documentclass{article}` for `\documentclass[draft]{agujournal2019}`, re-add the Key Points and Plain Language Summary sections, and add an author block + acknowledgements. For NeurIPS workshop: swap for the venue style file and trim to 4 pages.

For now, none of that — internal record only.
