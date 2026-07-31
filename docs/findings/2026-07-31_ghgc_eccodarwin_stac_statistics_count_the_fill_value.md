# The GHG Center's published ECCO-Darwin CO₂ flux statistics count the land fill value as data

**Date:** 2026-07-31 · **Source:** `US-GHG-Center/ghgc-docs`, user notebook
`eccodarwin-co2flux-monthgrid-v5_User_Notebook.ipynb`, cells 25 to 26, values as recorded in the
committed notebook output · **Verified arithmetically to ratio 1.000000** ·
**Verdict: a real, reportable defect in a NASA-published product page for our model. It does not
change the earlier assessment that the product is not scientifically useful to us.**

## What the published metadata says

The STAC `raster:bands` block for `eccodarwin-co2flux-monthgrid-v5-202001`:

```
statistics: mean 3.554192556042885e+19   stddev 4.786401658343999e+19
            maximum 1e+20   minimum -0.0035127835016991096
            valid_percent 0.0001903630604288499
histogram:  min -0.0035127835   max 1e+20
            buckets [338606, 0,0,0,0,0,0,0,0, 186706]
```

A mean air-sea CO₂ flux of **3.55e19 mmol m⁻² s⁻¹** is not a physical number. The real field is
order 1e-4.

## The cause, confirmed exactly

`1e20` is the MITgcm/NetCDF land fill value, and it is being counted as valid data. If a fraction
`f` of pixels sit at 1e20 and the rest near zero, the moments are predictable in closed form:

| quantity | predicted from `f = 186706/525312 = 0.355419` | published | ratio |
|---|---|---|---|
| mean = `f · 1e20` | 3.554193e+19 | 3.554193e+19 | **1.000000** |
| stddev = `1e20 · √(f(1−f))` | 4.786402e+19 | 4.786402e+19 | **1.000000** |

Both match to six figures. **35.54% of the grid is land fill, and the published mean and standard
deviation are entirely that fill.** There is no residual to attribute to the ocean signal.

`valid_percent` is broken in a second, separate way: it reports **0.00019%**, which implies about
**one** valid pixel, while the same block's own histogram shows **338,606 non-fill pixels, 64.46%**.
The two fields in the same JSON contradict each other.

## The consequence inside the notebook

Cell 26 builds the colorbar from exactly those statistics:

```python
rescale_values = {"max": mean + 2*stddev, "min": histogram["min"]}
# -> {'max': 1.3127e+20, 'min': -0.00351}
```

but the tiles are actually rendered with a hardcoded `rescale=-0.0007,0.0007` (cells 29 and 30).
So **the displayed legend does not describe the displayed map**, and the mismatch is a factor of
**1.9e23**. The legend is labelled "10^19 Millimoles per meter squared per second" and reads roughly
0 to 13; the imagery underneath spans ±7e-4.

The zonal-statistics path is **not** affected. The Raster API `/statistics` endpoint masks fill
correctly (Coastal California returns `masked_pixels 245`, `valid_pixels 115`, means near −6.7e-5),
so the time series in the notebook is sound. The defect is confined to the STAC `raster:bands`
metadata and anything derived from it.

## A second, unverified observation

The tilejson reports `bounds: [-180.125, -90.124826629681, 179.875, 89.875173370319]`. The southern
bound is **below −90**, which is off the globe, and the whole grid is offset by 0.125°. For a
~1/3° product a half-cell offset would be 0.1667°. A 0.125° offset is the half-cell of a **0.25°**
grid, so the geotransform may have been written with the wrong cell size. **Not verified here**, and
worth checking against the source NetCDF before it is asserted.

## What this does and does not change

**Does not change:** the standing assessment in
`2026-07-23_data_sources_ghgcenter_earthmover.md` and `2026-07-24_ghgcenter_positioning.md` that
this product is **not scientifically useful to us**. It is a single derived flux variable, over
2020-2022 with zero overlap with our 1992-2018 tracer archive, and it is ECCO-Darwin's own output,
so using it to check ECCO-Darwin would be the model validating itself. That verdict stands and
should not be relitigated.

**Does change:** there is now a precise, cheap, verifiable contribution available. Lucas is an
active member of `US-GHG-Center`, the defect is in the public metadata for **our** model, and the
report writes itself: two numbers that reproduce to six figures, plus a second field that
contradicts its own histogram. Fixing it means setting nodata on the COGs or excluding the fill
before computing `raster:bands`.

**Do not overstate it.** This is a metadata and visualisation defect, not a data defect. The
underlying flux arrays are not shown to be wrong by anything here, and the zonal statistics path
demonstrably handles the fill correctly.
