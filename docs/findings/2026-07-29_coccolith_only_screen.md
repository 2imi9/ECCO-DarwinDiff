# R_PICPOC 50/50 is structure-dependent — it does NOT survive Darwin's actual calcification structure (2026-07-29)

**Bottom line: with a one-lever change that makes the box's calcite source match Darwin
(`COCCOLITH_ONLY=1`), `R_PICPOC` per-AOI recovery goes from 10/10 to 0/10 in a matched local
control pair, and the fitted value lands at ~24x Carroll. The flagship's `R_PICPOC` 50/50 is
therefore conditional on the box's *bulk* `mort_total` calcite closure, which is not Darwin's
structure. The iron pair (`alpfe`, `scav_rat`) is unaffected by the switch itself, but is
destroyed by the PIC-magnitude anchor the switch's docstring prescribes.**

All three arms are `grade_recovery.py` gate-VERIFIED (**exit 0**, n=10/10 seeds each). Every number
below is grader output or a forward-probe recompute — none is read from a log or a prior doc.

## Why this was worth testing

`src/darwindiff/carroll6_5pft_2layer.py:479` selects the calcite source term:

```python
calcite_mort_src = mort_lge if USE_COCCOLITH_ONLY_CALCITE else mort_total_1
```

The default (`False`) applies the single `R_PICPOC` scalar to the mortality of **all five** PFTs.
Darwin restricts calcification to a subset. Verified directly in the v05 configuration this study
targets, `ecco_darwin/v05/llc270/input/data.traits`:

```
 7: HASPIC   =  0, 2*1, 4*0,
36: R_PICPOC =  0.0, 2*4.1886E-2, 4*0.0,
```

Seven plankton types (5 phytoplankton + 2 zooplankton, from `ISPHOTO` l.2 / `ISPRED` l.14);
**only types 2 and 3 carry PIC and a non-zero rain ratio.** The v04 generator agrees
(`v04/llc270_JAMES_paper/code_darwin/darwin_generate_phyto.F:476-486`: `R_PICPOC(np) = 0` unless
`diacoc(np) == 2`, then `R_PICPOC(np) = 0.04245` for `np` in {2,3,8}), and the v06 namelist keeps a
per-group array (`v06/llc270/input_darwin/data.darwin:223`,
`a_R_PICPOC(:) = 2*4.19E-2,1*0.05,3*4.19E-2`).

The flagship `n50e2k_percell_trio` ran with the flag **off** — its own run JSON records
`"use_coccolith_only_calcite": false`. So the 50/50 was obtained under a calcification structure
that differs from Darwin's, using a switch the repo already ships.

## Recipe (reconstructed flagship geo1; the lever is the only difference between A and C)

The exact flagship env lives on Explorer (`/projects/schultz/qi.zim/runs/n50e2k_percell_trio`) and is
not reachable from here. It was reconstructed from two committed sources: the saved config of the
local anchors-only ablation run `D:/runs/anch_pinn` — documented in
[`2026-07-21_anchors_only_ablation.md`](2026-07-21_anchors_only_ablation.md) as *"geo1 flagship config
with the new `DARWIN_PATTERN_W=0` lever plus `POC_SUB_W=0`, `CHL1_W_EXTRA=0`"*, i.e. the flagship
minus exactly three levers — plus the flagship override row in
[`2026-07-24_reproducibility_methods_appendix.md`](2026-07-24_reproducibility_methods_appendix.md)
(`GEOTRACES_W=1, DANIELS_RPICPOC_W=1, PINN=3, POC_SUB_W=3, CHL1_W_EXTRA=3, DARWIN_PATTERN_W=1, 2000ep`).
`scripts/run_v3.0_joint_multi_aoi.py`, RTX 5090 laptop, `torch.compile` on:

```
AOIS=eqpac,natlsubpolar,southernoceanpac      AOI_W = {eqpac 1, natl 2, sopac 2}
GEOTRACES_W=1.0   GEOTRACES_SUB_W=1.0   NB23_PINN_WEIGHT=3.0   NB23_FET_WEIGHT=1.0
POC_SUB_W=3.0     CHL1_W_EXTRA=3.0      DARWIN_PATTERN_W=1.0   DANIELS_RPICPOC_W=1.0
POSI_W=1.0        POSI_DARWIN_W=0.0     RATIO_W=0.0            DARWIN_IC=1
USE_EPPLEY_T=1    A_E_EPPLEY=0.0633     T_REF_EPPLEY=15.0      DINN_HIDDEN_DIM=16 (per-cell, SST only)
NB23_N_EPOCHS=2000   NB23_SEEDS=0..9    DARWIN_DATA_ROOT=D:/ecco_darwin_v5
```

| arm | dir | `COCCOLITH_ONLY` | `PIC_ABS_W` | wall clock (10 seeds x 2000 ep) |
|---|---|---|---|---|
| **C — control** | `D:/runs/cocc_c` | 0 | 0 | 717 s |
| **A — the test** | `D:/runs/cocc_a` | **1** | 0 | 710 s |
| **B — docstring pairing** | `D:/runs/cocc_b` | **1** | **0.02** | 631 s |

Arm B exists because the flag's docstring warns that `COCCOLITH_ONLY` must be paired with
`PIC_ABS_W > 0` or "the optimizer finds a degenerate `(R_PICPOC, mort_lge)` pair." The flagship has
`PIC_ABS_W=0`, so honouring the docstring and holding everything-else-identical are mutually
exclusive; both were run.

## Graded result (per-AOI >=2-of-3 Cal+, the honest metric; `verify_run` gate exit 0 on all three)

| param | **C control** (cocco OFF) | **A** (cocco ON) | **B** (cocco ON + PIC anchor) | flagship n=50 (reference) |
|---|---|---|---|---|
| `alpfe` | **10/10** | **10/10** | **1/10** | 49/50 (98 %) |
| `scav_rat` | 7/10 | 9/10 | 4/10 | 25/50 (50 %) |
| `diatomgraz` | 0/10 | 0/10 | 0/10 | 3/50 (6 %) |
| **`R_PICPOC`** | **10/10** | **0/10** | 1/10 | **50/50 (100 %)** |
| `R_PICPOC` median | 0.0528 (1.24x Carroll) | **1.012 (23.9x)** | 0.149 (3.5x) | — |
| iron pair per-AOI | 7/10 | 9/10 | 0/10 | — |

Carroll: `alpfe` 0.92831, `scav_rat` 6.025e-7 s^-1, `diatomgraz` 0.83003, `R_PICPOC` 0.04245.
`R_PICPOC` per-AOI medians in arm A: eqpac 1.067, natl 0.999, sopac 0.954 — the blow-up is uniform,
not one bad basin, and it is not a bound artifact (`PARAM_BOUNDS` ceiling is 1.5).

**The control is the load-bearing part.** Same reconstruction, same seeds, same 2000 epochs, one
lever: `R_PICPOC` 10/10 -> 0/10. That rules out reconstruction drift as the explanation, and it also
shows the reconstruction reproduces the flagship's `R_PICPOC` behaviour (10/10 vs the published
50/50) before the lever is thrown.

## Mechanism — the box cannot realize the calcifier fraction the switch depends on

At quasi-steady state the box's surface rain ratio is `PIC_1/POC_1 = R_PICPOC * (W_SINK/W_SINK_PIC)`
with the bulk closure, and `R_PICPOC * f_lge * (W_SINK/W_SINK_PIC)` under coccolith-only, where
`f_lge = mort_lge / mort_total_1`. `W_SINK_PIC = W_SINK` here, so the switch multiplies the realized
ratio by `f_lge`. The `DANIELS_RPICPOC_W` term matches that realized ratio to real CP:PP data
(the run reports geomean 0.0392 in eqpac from 34 cells / 123 samples, 0.0336 in natl from 26 / 116;
no Southern-Ocean coverage, so the term auto-gates off there). The anchor therefore identifies
`R_PICPOC * f_lge`, and `R_PICPOC` inflates by `1/f_lge`.

Forward probe at Carroll parameters, no fitting, 200 Euler steps, CPU
(box integrated from the Darwin target caches; script kept in the session scratchpad):

| AOI | box `f_lge` | box bulk PIC:POC, cocco OFF | box bulk PIC:POC, cocco ON | Darwin bulk PIC:POC | Darwin Chl2 share |
|---|---|---|---|---|---|
| eqpac | 0.1155 | 0.0424 | 0.00490 | 0.0332 | 0.215 |
| natlsubpolar | 0.1154 | 0.0425 | 0.00490 | 0.6758 | 0.888 |
| southernoceanpac | 0.1154 | 0.0424 | 0.00490 | 0.0067 | 0.156 |

`f_lge` is **flat to four significant figures across all three basins.** The docstring's promise —
*"with PFT-specific scaling the cross-AOI PIC differences come naturally from `P_lge` abundance"* —
is false in this 0-D box: gating the calcite source rescales the ratio by a constant ~0.115
everywhere instead of spreading it. Darwin's own Chl2 share does vary (0.215 / 0.888 / 0.156), which
is why the mechanism is right in principle; the box just cannot represent it. This independently
reproduces the 2026-06-24 forward probe recorded in
[`ADR 0001`](../adr/0001-differentiable-darwin-calcite-port.md) (~12 % flat, 0.0424 -> 0.0049), from a
different script.

Note the observed inflation (~24x) is larger than the naive `1/f_lge` ~ 8.7x, because `f_lge` is
itself re-optimized: the per-cell DINN is free to move growth and grazing, so the anchor is satisfied
along a `(R_PICPOC, f_lge)` ridge rather than at fixed composition. That is precisely the degenerate
pair the docstring warns about.

## Arm B — the prescribed pairing does not rescue it, and it costs the iron pair

Adding `PIC_ABS_W=0.02` pulls `R_PICPOC` from 1.012 down to 0.149, so the absolute PIC anchor does
break part of the `(R_PICPOC, mort_lge)` scale degeneracy — but 0.149 is still 3.5x Carroll, well
outside the Cal band (<=0.0594), and recovery stays at 1/10. Meanwhile `alpfe` collapses from 10/10
to **1/10** (median 0.225, 0.24x Carroll) and the iron pair goes to 0/10. This reproduces the
historical note in ADR 0001 that the coccolith-only mitigation "backfires — it breaks the iron pair,"
now with a matched control in the same session. So there is no operating point in this screen where
coccolith-only calcite and the trio coexist.

## Honest read

1. **The 50/50 is structure-dependent, and the dependence is not subtle.** It requires the box's
   bulk `mort_total` calcite closure. Under Darwin's own subset-of-PFTs structure the same loss,
   same anchor, same seeds give 0/10.
2. **This does not make the flagship number wrong, and it does not make the Daniels anchor
   circular.** The anchor is real and Darwin-independent, and the epoch-matched anchor-off control
   (`n50e2k_anchor_off`, 6/50) still shows it drives the recovery. What changes is the *scope* of the
   claim: what recovers is the box's bulk rain ratio, and it agrees with Carroll's `R_PICPOC` only
   because the box's bulk closure happens to make those the same quantity. Under Darwin's structure
   Carroll's 0.04245 is a *per-calcifier* trait, and the box has no way to compare like with like.
3. **The right disclosure is a structural-caveat sentence, not a retraction.** Something like: the
   surrogate applies the rain ratio to bulk mortality whereas Darwin applies it to two of seven
   plankton types; the recovered `R_PICPOC` is therefore a bulk-equivalent rain ratio, and matching
   Darwin's per-PFT structure requires a calcifier pool the 0-D box does not resolve.
4. **Do not read the n=10 counts as rate estimates against n=50.** Arm C's `scav_rat` 7/10 sits
   above the flagship's 50 %, which is the known n=10 seed-luck spread (the AICR flagship-full n=10
   gave 9/10 against the same 25/50); `alpfe` 10/10 vs 98 % and `diatomgraz` 0/10 vs 6 % are
   consistent. The `R_PICPOC` 10/10 -> 0/10 contrast is the only comparison this screen is powered
   to make, and it is made *within* the screen, control against test.
5. **The fix is not a weight.** Both the unpaired and the docstring-paired variants fail, in
   different ways. Making coccolith-only work needs a calcifier pool whose share varies across
   basins — a higher-dimensional surrogate, i.e. the Track-2 direction ADR 0001 already reached by a
   different route.

## Provenance

- Runs: `D:/runs/{cocc_c,cocc_a,cocc_b}` (10 seed JSONs each, not tracked); logs
  `D:/runs/cocc_{a,b,c}.log`.
- Grading: `scripts/grade_recovery.py --expect-seeds 10 --params alpfe,scav_rat,diatomgraz,R_PICPOC`,
  **exit 0** on all three directories.
- Primary source for Darwin's calcification structure: `ecco_darwin` repo,
  `v05/llc270/input/data.traits` (l.7 `HASPIC`, l.36 `R_PICPOC`),
  `v04/llc270_JAMES_paper/code_darwin/darwin_generate_phyto.F:476-486`,
  `v06/llc270/input_darwin/data.darwin:223`.
- Forward probe inputs: `D:/ecco_darwin_v5/cache/eqpac_targets_*.pt` at `CARROLL_VALUES`.
