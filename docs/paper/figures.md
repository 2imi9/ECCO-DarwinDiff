# Paper figures — workflow + specifications

## Tool split (corrected 2026-05-22)

Statistical / data-driven figures should be rendered from the actual sweep JSONs using matplotlib so the numbers in the figure match the numbers in the prose. Claude Design is reserved for the one conceptual diagram (Figure 1).

| Figure | Type | Tool |
|---|---|---|
| Fig 1. Training pipeline | Conceptual block-and-arrow diagram | **Claude Design** (rendered SVG checked into `figures/fig1_pipeline.svg`) |
| Fig 2. Cal-grade distribution (857 seeds) | Bar chart | **matplotlib** — `make_figures.py` |
| Fig 3. Basin C iron-pair scatter (n=40) | Scatter | **matplotlib** — `make_figures.py` |
| Fig 4. Per-parameter recovery box plot | Box plot | **matplotlib** — `make_figures.py` |
| Fig 5. Wave 6 composition bar (optional) | Bar chart | **matplotlib** — `make_figures.py` |

## Render Figure 1

The SVG is already rendered and checked in at `figures/fig1_pipeline.svg`. To wire into LaTeX, convert to PDF:

```bash
cd docs/paper/figures
rsvg-convert -f pdf fig1_pipeline.svg > fig1_pipeline.pdf
# or via Inkscape:
inkscape --export-type=pdf fig1_pipeline.svg
```

`main.tex` references `figures/fig1_pipeline` (no extension), so LaTeX picks up the PDF automatically once it exists.

If you ever need to re-render via Claude Design from scratch, the prompt is preserved at the bottom of this doc.

## Render Figures 2-5

Use the `make_figures.py` script in this directory.

```bash
# illustrative figures (immediate visual check; uses headline numbers)
cd docs/paper/figures
python make_figures.py

# real data once you have an aggregated JSON
python make_figures.py --aggregated path/to/aggregated_v3.1.json

# subset
python make_figures.py --figures 3,4
```

Outputs PDF + PNG side-by-side for each figure (`fig2_ceiling.pdf`, `.png`, etc.).

### Aggregated input schema

The script accepts an aggregated sweep JSON with this shape:

```json
{
  "seeds": [
    {
      "config": "F2_basinC_seed0",
      "seed": 0,
      "recovered": {
        "alpfe": 0.94,
        "scav_rat": 6.1e-7,
        "Smallgrow": 0.71,
        "Biggrow": 0.46,
        "diatomgraz": 0.81,
        "R_PICPOC": 0.052
      },
      "cal_grade": {
        "alpfe": true,
        "scav_rat": true,
        "Smallgrow": true,
        "Biggrow": true,
        "diatomgraz": true,
        "R_PICPOC": false
      }
    },
    ...
  ]
}
```

The `cal_grade` flags can be omitted if the script should compute them from `recovered / CARROLL_OPTIMA` against the ±40% Cal-grade band; the script handles both layouts.

To produce this JSON from the raw per-seed JSONs in `D:\runs\bcr_*\`, write a small aggregator (left as a project-side task — paths and exact JSON field names vary across sweep waves).

### What's "illustrative" vs real

The script labels titles `[Illustrative]` whenever it falls back to placeholder data. Real data is loaded only if `--aggregated <path>` is provided and exists. Wave 6 numbers (Figure 5) are real and hard-coded from `docs/findings/v3.1_closeout.md`.

## Style notes (uniform across all figures)

- **Palette**: Okabe-Ito colorblind-safe; reserve vermillion `#D55E00` for emphasis.
- **Typeface**: serif (matches LaTeX body).
- **Format**: PDF preferred (vector), 300 dpi PNG fallback.
- **No 3D effects, no drop shadows, no gradients.**

## Original Claude Design prompt for Figure 1 (archived)

Kept here for re-rendering. The SVG output is what's actually in the repo at `figures/fig1_pipeline.svg`.

> Create a horizontal pipeline diagram in clean academic-paper style. Aspect ratio approximately 2.5:1, vector output (PDF/SVG), serif typeface, colorblind-safe accent palette (Okabe-Ito).
>
> Left-to-right flow with labeled solid arrows:
>
> 1. Input box (light gray): "Per-cell environmental covariates — SST, mixed-layer depth, windspeed, latitude"
> 2. Arrow → Box (blue accent): "DINN: per-cell 1×1-conv MLP, ~454 weights (baseline) or ~9.4K (DINNDeep)"
> 3. Arrow labeled "6 raw values per cell" → Box (light gray): "Sigmoid bounding into Carroll PARAM_BOUNDS"
> 4. Arrow labeled "θ ∈ Carroll-6 per cell" → Larger box (orange accent): "Differentiable PyTorch SMS kernel — carroll6_step / carroll6_carbonate_step, 200 forward-Euler steps over 5–7 prognostic tracers (DFe, P_s, P_l, POC, PIC; +DIC, ALK in carbonate extension)"
> 5. Arrow labeled "predicted tracer fields" → Diamond comparison node: "z-scored MSE loss"
> 6. Separate input arrow into the comparison node from a small box (light gray): "ECCO-Darwin v05 target fields"
>
> A dashed red arrow labeled "backpropagation through SMS via autograd" goes from the loss diamond all the way back to the DINN box at the start.
>
> No 3D effects, no drop shadows. Monochrome-friendly. Caption is added in the LaTeX, not in the figure.
