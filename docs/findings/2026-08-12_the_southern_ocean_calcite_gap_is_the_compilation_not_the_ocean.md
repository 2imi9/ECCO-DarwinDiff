# The Southern Ocean has calcite observations after all: the gap is in Daniels 2018, not the ocean

**Date:** 2026-08-12 · **Cost:** one local script, no cluster · **Status:** measured, reproducible

## The claim this touches

Several live claims rest on the Southern Ocean having **zero** calcite observations, which is why
`R_PICPOC`'s `southernoceanpac` leg is described as inherited through the shared DINN rather than
locally anchored:

- `ind330` — "R_PICPOC's Southern Ocean leg is INHERITED through the shared DINN, not local: it
  recovers with zero Daniels cells"
- `ded177` — "southernoceanpac is not a counterexample to the f_calc mechanism — it has zero
  Daniels cells"
- `ind329` — the sopac median 1.268× Carroll offset, which no local observation can currently falsify
- The 2026-07-30 SO pre-registration, whose amendment sets `DANIELS_RPICPOC_W=0.0` *because* the
  basin has no coverage

## The measurement

Both compilations were loaded and counted against the model's own AOI bounds
(`southernoceanpac` = lat −65…−50, lon −180…−100, `ecco_darwin_loader.py:117-123`):

| compilation | total points | eqpac | natlsubpolar | **southernoceanpac** | south of 45°S |
|---|---|---|---|---|---|
| Daniels 2018 (the anchor in use) | 2,765 | 207 | 123 | **0** | 369 |
| **Marsh 2025** (PANGAEA 10.1594/PANGAEA.987673) | 3,160 | 207 | **168** | **65** | 484 |

The 65 Southern Ocean points span **lat −60.00 to −51.00, lon −150.00 to −138.02** — comfortably
inside the AOI rather than clipping its edge.

Marsh et al. 2025 is the direct successor to Daniels: it *expands* the same Poulton et al. 2018
database of pelagic CaCO3 rate measurements from isotopic tracer uptake (its own header says so).
So this is the same measurement type, not a different quantity being substituted in.

**The data has been on disk the whole time** at `data/marsh/Marsh_etal_2025_coccolith_calcification.tab`,
with a working loader at `src/darwindiff/marsh_loader.py`. Nothing was downloaded for this note.

## What changes

**"Zero Southern Ocean calcite coverage" is a property of the Daniels 2018 compilation, not of the
ocean.** Every claim above must be reworded from "the Southern Ocean has no calcite observation"
to "the Daniels anchor has no Southern Ocean coverage". The claims remain *true as measurements of
the runs that were performed* — those runs used Daniels — but their stated reason is wrong, and the
implied impossibility is false.

**`ind329` becomes falsifiable.** The sopac 1.268× offset is currently unfalsifiable because there
is no local anchor to check it against. With 65 Marsh points there is one.

**It opens a real experiment**, and a well-targeted one: the Southern Ocean is the single basin
where `scav_rat` is established (`so_only` geometric 49/50 vs untrained 0/50). Adding a local
calcite anchor there tests whether `R_PICPOC`'s SO leg is genuinely inherited or merely
unmeasured — and it does so in the basin whose behaviour the project most depends on.

**The North Atlantic also gains**, 123 → 168 points (+37%), which bears on the natl leg that drives
the arithmetic-vs-geometric pooler split.

## The binned cell counts — the gate, now closed

Points are not cells, so the raw counts above were binned to the shared 1° grid at
`depth_max = 50 m` (the flagship's `DANIELS_DEPTH_MAX`) through
`build_aoi_climatology`, which Marsh's loader delegates to the Daniels machinery — the same
binning, different points.

| AOI | Daniels cells | Marsh cells |
|---|---|---|
| eqpac | 34 | 34 |
| natlsubpolar | 26 | **33** |
| **southernoceanpac** | **0** | **12** |

**Positive control:** the Daniels column reproduces the repo's own quoted figures (eqpac 34,
natl 26, sopac 0) exactly, so the method is validated against a known answer before being trusted
on a new one.

**The Southern Ocean anchor is real: 12 cells carrying 42 observations** (2–4 obs per cell,
median 4). Their rain-ratio values:

| | value |
|---|---|
| min | 0.02153 |
| **median** | **0.04520** |
| max | 0.13966 |
| Carroll `R_PICPOC` | 0.04245 |
| Darwin v05 live (`data.traits`) | 0.0418860 |

The observed Southern Ocean median sits **6.5% above Carroll** and **7.9% above the value v05
actually integrates** — comfortably inside the ±40% band, and a much closer match than the
equatorial Pacific, where the recovered leg runs 1.518× Carroll. That is worth noting on its own:
the one basin with no anchor turns out to be the one whose observed ratio most nearly matches the
global constant.

12 cells is small. For scale, the whole anchor union across all three AOIs is 112 of 2,851 cells
(3.93%), and `diatomgraz`'s bSi anchor operates on **11** cells, so 12 is not out of family for
this project — but it is a weak anchor and must be reported as one.

## What this does NOT say
2. **It does not retract any recovery number.** Every reported run used Daniels; those runs are what
   they are. This changes what is *possible next*, not what was measured.
3. **It does not validate Marsh as a drop-in replacement.** Coverage is necessary, not sufficient:
   the values, methods and uncertainties need the same scrutiny Daniels received before the anchor
   weight is switched.
4. **The currently running `so_rep` replication is unaffected** — it runs `DANIELS_RPICPOC_W=0.0`
   by design, and its pre-registered prediction that `R_PICPOC` stays 0/50 stands unchanged.

## Next steps

1. ~~Bin the SO points and report the cell count~~ — **done above: 12 cells, 42 observations.**
2. Pre-register a `so_only` + Marsh-SO-anchor arm against the `so_rep` control now in flight, and
   test `ind330` (is the SO `R_PICPOC` leg inherited, or merely unmeasured?) directly. The control
   already exists and is running, which is the cheap half of an A/B.
3. Reword `ind330`, `ded177` and `ind329` from "the ocean has none" to "Daniels has none".
4. Separately assess whether Marsh should replace Daniels as the *default* anchor everywhere: it
   adds 7 natl cells (26 → 33) and leaves eqpac unchanged. That is a bigger change than this note
   licenses and needs its own A/B, because every published `R_PICPOC` number is Daniels-based.

## Provenance

Found by the 2026-08-12 evidence sweep (axis `calcite-rpicpoc`), which flagged Marsh 2025's stated
coverage envelope (81°N–64°S) as inconsistent with a zero-Southern-Ocean claim and recommended
exactly this check. Counts here were computed directly, not taken from the sweep.
