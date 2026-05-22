# Paper #1 — DarwinDiff workshop / journal manuscript

LaTeX source for the DarwinDiff proof-of-concept manuscript. Target venue is AGU JAMES or GBC (matches Carroll 2020/2022 venue lineage) for full-paper submission; a workshop-scale version (the same content trimmed to fit) can target NeurIPS Climate Change AI or ML4PS workshops.

## What's here

| File | Purpose |
|---|---|
| [`main.tex`](main.tex) | Main LaTeX source. Default class is portable `article`; comments inside indicate how to swap for `agujournal2019.cls` (AGU) or NeurIPS workshop style files. |
| [`references.bib`](references.bib) | BibTeX bibliography. All entries verified against AGU/Wiley/arXiv or project memory notes. |
| [`figures.md`](figures.md) | Per-figure specifications with ready-to-paste prompts for Claude Design. Five figures total (4 required + 1 optional). |
| `figures/` | (To be populated) — rendered figure files (PDF/SVG preferred; PNG fallback at 300 dpi). |

## Status

- **Draft**: complete first pass. All numerical claims verified against [`STATUS.md`](../../STATUS.md) and [`docs/findings/v3.1_closeout.md`](../findings/v3.1_closeout.md).
- **Figures**: specifications complete; rendered figures pending Claude Design generation per the prompts in `figures.md`.
- **Author block**: `[Authors TBD]` — names added only with explicit consent per project convention.
- **Venue**: not yet finalized. Top three candidates listed below.
- **Submission**: not started. Preprint to ESSOAr / arXiv is the immediate first step.

## Build

The LaTeX source is portable to standard `latexmk` and `pdflatex` toolchains.

```bash
cd docs/paper
latexmk -pdf main.tex                     # full build with bib
# or
pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

For Overleaf: upload `main.tex`, `references.bib`, and (when generated) the `figures/` directory.

## Venue swap

The default `\documentclass[11pt,letterpaper]{article}` is a neutral baseline. To convert:

| Target | Swap | Notes |
|---|---|---|
| **AGU JAMES / GBC** | `\documentclass[draft]{agujournal2019}` | Download `agujournal2019.cls` from AGU. The Key Points and Plain Language Summary sections are already structured for this. |
| **NeurIPS workshop** (Climate Change AI, ML4PS, AI4Science) | `\documentclass{neurips_2024}` (or year-appropriate) | Workshop typically requires `\usepackage{neurips_2024}`. Trim to 4 pages of content; the Background and parts of Methods are the natural cuts. |
| **GMD (Geoscientific Model Development)** | `\documentclass{copernicus}` | Copernicus class. Methods-focused journal, good fit for the framework contribution. |
| **arXiv preprint** | Keep `article` class as is | Simplest path; submit alongside venue submission. |

## Target venues (under consideration)

Listed in order of strategic fit:

1. **AGU JAMES** — *Journal of Advances in Modeling Earth Systems.* Carroll 2020's venue. Methods-friendly, accepts framework papers. Rolling submission. Full paper, ~10-12 pages typeset.
2. **AGU GBC** — *Global Biogeochemical Cycles.* Carroll 2022's venue. Biogeochemistry-forward audience. Rolling submission. Full paper.
3. **NeurIPS Climate Change AI Workshop** — strong tradition of differentiable-Earth-system-modeling papers. Annual deadline typically late September. 4-page workshop format (a trimmed version of `main.tex`).
4. **NeurIPS ML4PS Workshop** — Machine Learning for the Physical Sciences. Similar deadline and format to CCAI.
5. **GMD** — *Geoscientific Model Development.* Methods-only journal, good fit for the framework contribution. Slower review than AGU venues but allows longer methods exposition.
6. **arXiv / ESSOAr preprint** — should happen *regardless of venue choice* as the first publication step, prior to or concurrent with submission.

## Verified vs estimated claims

Everything numerical in the draft is anchored. Cross-references:

- **857 seeds / 86 configs / 5 waves + Wave 6 composition** — `STATUS.md` line ~9 and `docs/findings/v3.1_closeout.md` Summary.
- **Basin C iron-pair 38/40 at $n{=}40$** — `STATUS.md` headline-results table; v3.1_closeout headline table.
- **2/857 = 0.24% break to 5/6** — v3.1_closeout headline table.
- **0/857 at 6/6** — v3.1_closeout headline table; STATUS.md current-state bullet.
- **F2 config formula** (`POSI_W=1.0 + AOI_W_NATLSUBPOLAR=2.0 + AOI_W_SOUTHERNOCEANPAC=2.0 + CHL1_W_EXTRA=3.0`) — STATUS.md headline-results table.
- **Wave 6 composition (0/10 at 5/6, mean_cal 2.00 vs parent 2.40 and 2.70)** — v3.1_closeout Wave 6 section.
- **Carroll-6 names, source lines, and optimized values** — `docs/ecco_darwin_parameter_inventory.md`.
- **`darwin_plankton.F` as SMS-kernel filename in Darwin 3** — live `darwinproject/darwin3@darwin:pkg/darwin/darwin_plankton.F`, verified 2026-05-21.
- **BINN architecture details** — Xu et al. 2025 paper text (project memory note `binn_paper_reference.md`).
- **Carroll 2020 DOI (`10.1029/2019MS001888`)** — verified 2026-05-21 via AGU/Wiley.
- **Carroll 2022 DOI (`10.1029/2021GB007162`)** — verified from project memory `reference_carroll_2022.md`.

Anything explicitly labeled "approximate" or "illustrative" in `figures.md` (e.g., Figure 2 bucket counts) requires recomputation from raw sweep JSONs before final figure rendering.

## Authorship and acknowledgements

Per project convention: no personnel names added to public artifacts without explicit consent. The author block in `main.tex` is `[Authors TBD]` with a corresponding-author placeholder. The acknowledgements section is institutional-only until consent is captured.

## Contributing

This branch is `2imi9/paper-1-workshop-draft` per [`CONTRIBUTING.md`](../../CONTRIBUTING.md). PR opens as **draft** until figures land and the author block is finalized. Non-squash merge.
