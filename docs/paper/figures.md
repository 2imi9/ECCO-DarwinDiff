# Paper #1 — figure specifications + Claude Design prompts

Each figure has: (i) what it shows, (ii) data source in the repo, (iii) a ready-to-paste prompt for Claude Design, and (iv) where it slots into `main.tex`.

The paper targets science-journal standards: vector format (PDF or EPS) preferred, 300 dpi minimum for any raster fallback, colorblind-safe palettes (e.g., Wong / Okabe-Ito), monochrome-printable when possible. Use serif fonts to match the body text.

Save rendered figures into `docs/paper/figures/` as `figN_<short_name>.pdf` (or `.png` for raster fallback).

---

## Figure 1 — DarwinDiff training pipeline (architecture diagram)

**Slots into:** Section 3 Methods, between §3.1 (SMS kernel) and §3.2 (DINN architecture). Reference in text as `Figure~\ref{fig:pipeline}`.

**What it shows:** end-to-end data flow from per-cell environmental covariates to backprop, illustrating the BINN-style pattern adapted to marine BGC.

**Data source:** schematic; no numerical data required.

**Claude Design prompt:**

> Create a horizontal pipeline diagram in clean academic-paper style. Aspect ratio approximately 2.5:1, vector output (PDF/SVG), serif typeface to match journal body text, colorblind-safe accent palette (use Okabe-Ito or similar).
>
> Left-to-right flow with labeled solid arrows:
>
> 1. Input box (light gray): "Per-cell environmental covariates — SST, mixed-layer depth, windspeed, latitude"
> 2. Arrow → Box (blue accent): "DINN: per-cell 1×1-conv MLP, ~454 weights (baseline) or ~9.4K (DINNDeep)"
> 3. Arrow labeled "6 raw values per cell" → Box (light gray): "Sigmoid bounding into Carroll PARAM_BOUNDS"
> 4. Arrow labeled "θ ∈ Carroll-6 per cell" → Larger box (orange accent): "Differentiable PyTorch SMS kernel — carroll6_step / carroll6_carbonate_step, 200 forward-Euler steps over 5–7 prognostic tracers (DFe, Ps, Pl, POC, PIC; +DIC, ALK in carbonate extension)"
> 5. Arrow labeled "predicted tracer fields" → Diamond comparison node: "z-scored MSE loss"
> 6. Separate input arrow into the comparison node from a small box (light gray): "ECCO-Darwin v05 target fields"
>
> A dashed red arrow labeled "backpropagation through SMS via autograd" goes from the loss diamond all the way back to the DINN box at the start.
>
> Caption (to be placed below the figure in the LaTeX): "Figure 1. DarwinDiff training pipeline. A per-cell neural network predicts Carroll-N parameters from local environmental covariates; sigmoid bounding maps them into Carroll's published physical ranges; a differentiable PyTorch reimplementation of Darwin's source-minus-sink kernel advances the BGC state via forward-Euler integration; the z-scored MSE loss against ECCO-Darwin v05 outputs backpropagates through the entire chain to the network weights via autograd."

---

## Figure 2 — Cal-grade distribution across 857 seeds (the 5/6 ceiling)

**Slots into:** Section 4.3 Results, immediately before Table~\ref{tab:five-six-events}. Reference as `Figure~\ref{fig:ceiling}`.

**What it shows:** histogram of how many Carroll-N parameters each seed recovered at Cal-grade; the empty bar at 6/6 is the headline.

**Data source:** per-seed result JSONs in `D:\runs\bcr_*\*\seeds_*.json`. Bucket counts are computed by counting Cal-grade flags per seed across the 857 total. Exact bucket counts are pending computation from the raw JSONs.

**Approximate bucket counts (illustrative until computed):**
| Cal-grade count per seed | Approx. seeds |
|---|---|
| 0 | ~50 |
| 1 | ~150 |
| 2 | ~250 |
| 3 | ~250 |
| 4 | ~155 |
| 5 | **2** (highlighted) |
| 6 | **0** (highlighted with annotation) |

**Claude Design prompt:**

> Create a vertical bar chart in clean academic-paper style. Aspect ratio 1.6:1, vector output (PDF/SVG), serif typeface, monochrome-friendly with one accent color (Okabe-Ito red, `#D55E00`) reserved for the two emphasized bars.
>
> X-axis: integer counts 0 through 6, labeled "Carroll-N parameters recovered at Cal-grade (per seed)".
> Y-axis: number of seeds (linear scale), labeled "Number of seeds out of 857".
>
> Bars (heights illustrative until exact counts are computed from raw JSONs):
> - 0: ~50 (neutral gray fill)
> - 1: ~150 (gray)
> - 2: ~250 (gray)
> - 3: ~250 (gray)
> - 4: ~155 (gray)
> - 5: 2 (red accent fill, with a small text label "2 seeds (0.24%)" above it)
> - 6: 0 (visually shown as a thin red outline of an empty bar with an arrow annotation pointing to it labeled "0/857 — structural ceiling")
>
> Title above plot: "v3.1 sweep: Cal-grade distribution (857 seeds, 86 configurations)"
>
> Caption (LaTeX): "Figure 2. Distribution of Carroll-N parameters recovered at Cal-grade per seed, across 857 seeds in 86 single-lever configurations. Zero seeds reach all six (the structural 5/6 ceiling); only two seeds (0.24%) reach five, both unreproduced at $n{=}20$ (see Section~\ref{sec:results-ceiling})."

---

## Figure 3 — Basin C iron-pair recovery scatter ($n{=}40$)

**Slots into:** Section 4.2 Results, after the prose describing the F2 config recovery. Reference as `Figure~\ref{fig:basinC-scatter}`.

**What it shows:** the recovered $(\alpha_\text{fe}, r_\text{scav})$ values for each of the 40 seeds at the F2 configuration, plotted against Carroll's published optimum and the Cal-grade region.

**Data source:** per-seed `recovered_carroll6` arrays in `D:\runs\bcr_*\seeds0-9\`, `D:\runs\bcr_*\seeds10-19\`, `D:\runs\bcr_*\seeds20-29\`, `D:\runs\bcr_*\seeds30-39\`. 40 (alpfe, scav_rat) pairs total.

**Carroll's published optimum** (from `docs/ecco_darwin_parameter_inventory.md`): $\alpha_\text{fe} = 0.92831$, $r_\text{scav} = 10.41124 \times 0.005 / 86400 \approx 6.026 \times 10^{-7}$ s$^{-1}$.

**Cal-grade region:** $\pm 40\%$ of Carroll's optimum on both axes.
**Excellent region:** $\pm 10\%$ of Carroll's optimum on both axes.

**Claude Design prompt:**

> Create a scatter plot in clean academic-paper style. Aspect ratio 1.2:1 (slightly taller than wide), vector output (PDF/SVG), serif typeface, colorblind-safe palette.
>
> X-axis: recovered `alpfe` (iron dust solubility, dimensionless), linear scale spanning [0.05, 1.0] (Carroll's published parameter bounds).
> Y-axis: recovered `scav_rat` (iron scavenging rate, s$^{-1}$), log scale spanning [3e-8, 3e-6] (Carroll's published parameter bounds).
>
> Plot 40 small filled dots (charcoal `#333333`, alpha 0.7) representing the 40 seed recoveries at the F2 configuration. Mark Carroll 2020's published optimum (alpfe=0.92831, scav_rat=6.026e-7) as a large red star (`#D55E00`, size 200, with a thin white edge for visibility).
>
> Two shaded rectangular regions, both centered on Carroll's optimum:
> - Light yellow (`#F0E442`, alpha 0.3): Excellent region, ±10% of Carroll on both axes.
> - Light blue (`#56B4E9`, alpha 0.2): Cal-grade region, ±40% of Carroll on both axes.
>
> Add a text box in the upper-left corner with summary: "F2 config, n=40\n38/40 (95%) in Cal-grade\n4 batches of 10 seeds"
>
> Title: "Basin C iron-pair recovery, F2 configuration"
>
> Caption (LaTeX): "Figure 3. Iron-pair recovery at the F2 configuration (\texttt{POSI\_W}=1.0, \texttt{AOI\_W\_NATL}=2.0, \texttt{AOI\_W\_SO}=2.0, \texttt{CHL1\_W\_EXTRA}=3.0) across $n{=}40$ seeds in four independent 10-seed batches. The red star marks Carroll 2020's published optimum; shaded regions show $\pm 10\%$ (Excellent, light yellow) and $\pm 40\%$ (Cal-grade, light blue) bounds. 38 of 40 seeds (95\%) fall within the Cal-grade region for both \texttt{alpfe} and \texttt{scav\_rat}."

---

## Figure 4 — Per-parameter recovery distribution (box plot)

**Slots into:** Section 4.3 Results, before or after Figure 2. Reference as `Figure~\ref{fig:per-param-dist}`.

**What it shows:** for each of the six Carroll-N parameters, the distribution of recovered values normalized by Carroll's optimum, across all 857 seeds. Allows the reader to see which parameters cluster near Carroll (iron pair) versus broadly distributed (the other four).

**Data source:** for each parameter, extract `recovered_value / carroll_optimum` across all 857 seeds. Carroll's optima per `docs/ecco_darwin_parameter_inventory.md`:
- alpfe: 0.92831
- scav_rat: 10.41124 × 0.005 / 86400 ≈ 6.026e-7 s⁻¹
- Smallgrow: 0.66098 d⁻¹
- Biggrow: 0.43148 d⁻¹
- diatomgraz: 0.83003
- R_PICPOC: 0.04245

**Claude Design prompt:**

> Create a vertical box-plot panel in clean academic-paper style. Aspect ratio 1.8:1 (wider than tall), vector output (PDF/SVG), serif typeface, colorblind-safe.
>
> X-axis: six categorical positions labeled `alpfe`, `scav_rat`, `Smallgrow`, `Biggrow`, `diatomgraz`, `R_PICPOC` (use the monospace font for parameter names).
> Y-axis: normalized recovered value (recovered / Carroll's optimum), centered at 1.0 (Carroll), log-symmetric scale spanning roughly [0.1, 10.0]. Label: "Recovered value / Carroll 2020 optimum (log scale)".
>
> For each parameter, draw a standard box plot across the 857 seeds: median line, IQR box (charcoal fill, alpha 0.4), whiskers at 1.5×IQR, outliers as small open circles.
>
> Reference elements:
> - Horizontal solid line at y=1.0 across the full width (Carroll's optimum).
> - Shaded horizontal band at y ∈ [0.6, 1.4] (light blue, alpha 0.15) labeled "Cal-grade band (±40%)" on the right margin.
> - Shaded horizontal band at y ∈ [0.9, 1.1] (light yellow, alpha 0.20) labeled "Excellent band (±10%)".
>
> Title: "Carroll-N recovery distributions across 857 seeds"
>
> Caption (LaTeX): "Figure 4. Distribution of recovered Carroll-N parameters across the v3.1 sweep, normalized by Carroll 2020's published optima. Box plots show the IQR and whiskers at 1.5$\times$IQR across 857 seeds; the shaded bands indicate Cal-grade ($\pm 40\%$) and Excellent ($\pm 10\%$). The iron pair (\texttt{alpfe}, \texttt{scav\_rat}) clusters near unity; the other four parameters span broader distributions consistent with the parameter-conservation framing of the 5/6 ceiling."

---

## Optional Figure 5 — Wave 6 composition test bar chart

**Slots into:** Section 4.4 Results, alongside Table~\ref{tab:wave6} (figure vs table is editorial choice). Reference as `Figure~\ref{fig:wave6}`. May be omitted to save space; the table is sufficient.

**What it shows:** mean Cal-grade count for the composed configuration versus its two parent configurations.

**Data source:** Table~\ref{tab:wave6} numbers (mean_cal column).

**Claude Design prompt:**

> Create a horizontal grouped bar chart in clean academic-paper style. Aspect ratio 1.4:1, vector output, serif typeface, colorblind-safe palette.
>
> Three bars stacked vertically (or horizontal, your choice):
> - "w2e_peraoi_lam0.1 (parent 1)" — value 2.40, neutral gray fill
> - "c_chl40_posi15 (parent 2)" — value 2.70, neutral gray fill
> - "w6_combo (composed)" — value 2.00, red accent fill (Okabe-Ito red)
>
> X-axis (or Y if vertical): "Mean Cal-grade count (out of 6)", linear scale 0–4.
> Reference line at the composed value (2.00) with a thin dashed line continuing across; annotate "regresses below either parent".
>
> Title: "Wave 6 composition test: combining the two 5/6 lever families"
>
> Caption (LaTeX): "Figure 5. Mean Cal-grade count for the Wave 6 composed configuration versus its two parent configurations ($n{=}10$ each). The composition regresses below either parent on the headline metric, the strongest evidence of the structural 5/6 ceiling. See Table~\ref{tab:wave6} for the full per-parameter breakdown."

---

## Style notes (apply uniformly across all figures)

- **Color palette:** Okabe-Ito 8-color palette is the default (colorblind-safe, monochrome-printable). Reserve `#D55E00` (red-orange) for emphasis; use neutral grays for non-emphasized elements.
- **Typeface:** serif (matches journal body text). Avoid sans-serif except for very small annotations.
- **Resolution:** vector (PDF or SVG) for the journal submission. PNG fallback at 300 dpi minimum.
- **Aspect ratio:** keep figures landscape when reasonable to fit standard column widths.
- **Legend / annotations:** inline where possible; avoid separate legend boxes when a single text label suffices.
- **No 3D effects, no drop shadows, no gradients.** Standard journal aesthetic.
