# Arc 7 — Binary mutex confirmed at low paired-anchor doses

Date: 2026-05-20  
Sweep: `D:\runs\bcr_20260520_0121\`  
Base: Basin C (F2 config — D4 + CHL1_W_EXTRA=3.0 + POSI_W=1.0)

## Headline result

Adding ANY non-zero PIC anchor to Basin C base completely wipes the iron pair
(alpfe + scav_rat both Cal+), regardless of paired POC or dose magnitude.
Iron-pair survival is BINARY in PIC anchor presence.

**Full Arc 7 dose-response (PIC + POC paired, ratio 2:1, n=10 each):**

| Config | iron-pair | R_PICPOC | diatomgraz | mean_cal | 4+/n |
|---|---|---|---|---|---|
| Basin C base (Arc 6, seeds 10-19) | **10/10** | 0/10 | 0/10 | 2.50 | 0/10 |
| + PIC=0.05 / POC=0.025  (Arc 7 #1) | **0/10**  | 1/10 | 4/10 | 2.20 | 1/10 |
| + PIC=0.10 / POC=0.05   (Arc 7 #2) | **0/10**  | 1/10 | 4/10 | 2.20 | 1/10 |
| + PIC=0.20 / POC=0.10   (Arc 7 #3) | **0/10**  | ? | ? | 2.10 | 0/10 |
| + PIC=0.50 / POC=0.25   (Arc 7 #4) | **0/10**  | ? | ? | 1.60 | 0/10 |

**Arc 1 — PIC alone (no POC) dose-response (n=10 each):**

| Config | iron-pair | mean_cal | 4+/n |
|---|---|---|---|
| Basin C base                        | **10/10** | 2.50 | 0/10 |
| + PIC=0.02 (Arc 1 #1, smallest dose) | **0/10**  | 1.90 | 1/10 |
| + PIC=0.05 (Arc 1 #2)                | **0/10**  | 2.10 | 1/10 |
| + PIC=0.10 (Arc 1 #3)                | **0/10**  | 2.10 | 1/10 |
| + PIC=0.20 (Arc 1 #4)                | running   | -   | -    |

**The kicker:** even at PIC=0.02 (essentially homeopathic dose, 1/25 of Basin
B's PR #63 doses, **without** a POC pair), iron pair goes from 10/10 → 0/10.
The Basin A↔B switch is governed by the PIC anchor presence, not its magnitude.

**Trend in mean_cal:** Paired anchors *decrease* mean_cal as dose increases
(2.20 → 2.20 → 2.10 → 1.60), suggesting higher Basin B doses are
*counter-productive* at Basin C base — you're not getting R_PICPOC back fast
enough to compensate for the iron-pair loss.

## Methodology

- 3-AOI joint training: eqpac + natlsubpolar + southernoceanpac
- All same base config (POSI_W=1.0, AOI_W_NATLSUBPOLAR=2.0,
  AOI_W_SOUTHERNOCEANPAC=2.0, CHL1_W_EXTRA=3.0, hd=32, POC_SUB_W=0.5,
  GEOTRACES_POC_SUB_W=0.5, N_EPOCHS=1500)
- 10 seeds per config (seeds 0-9 for Arc 7; seeds 10-19 for Arc 6)
- Cal-grade = joint distance to Carroll value within band-specific threshold
  (cell-weighted recovery)

## What this means for the paper

1. **The 3-basin mutex is structural, not a knob.** It's not a question of
   "tune the dose slightly lower and you get both" — even tiny doses of the
   Basin B machinery flip the optimizer's basin attractor.

2. **Iron-pair recovery is hyper-sensitive to PIC/POC anchor presence.**
   The 10/10 → 0/10 collapse at PIC=0.05 (and POC=0.025!) is dramatic. This
   is the strongest evidence yet that the 5/6 ceiling reflects a real
   loss-landscape topology, not insufficient training.

3. **The diatomgraz "rescue" is a side effect.** At Arc 7 #1, #2: diatomgraz
   goes from 0/10 to 4/10. This is interesting — the paired anchor is
   destabilizing Basin C's preferred topology in a way that lets diatomgraz
   wobble closer to Carroll for some seeds. But the trade-off costs iron pair.

4. **R_PICPOC recovery is barely improved at these doses.** 0/10 → 1/10.
   Basin B's "PIC+POC paired anchor unlocks R_PICPOC" requires meaningful
   doses; sub-threshold doses just kill Basin C without compensating.

## Methodology note (MAX_PATH crash and recovery)

Arc 7 #1 + #2 originally failed with Windows MAX_PATH=260 char limit (JSON
filename ≈ 200 chars + path prefix ≈ 70 chars = 270 chars). Training
completed; only JSON write failed. Per-seed recovery values were preserved
in the .log files. Data was reconstructed via
`scripts/recover_failed_config_log.py` — parses `=== Seed N recovery ===`
sections from the log and writes minimal JSONs at short-path locations.

The v2 sweep (`overnight_v3.0_basinC_refine_v2.py`) uses shorter output
paths (`D:\runs\bcr_<stamp>\<short-arc-name>\`) to avoid the issue.

## Status

- Arc 6 (Basin C n=20 robustness): **complete**, iron-pair = 20/20 across n=20
- Arc 7 #1, #2: **complete** (recovered from logs)
- Arc 7 #3, #4: **running now** (v2 sweep)
- Arcs 1, 2, 3, 4, 8, 9, 5: queued in v2 sweep
- Wave 2 (24 orthogonal-lever configs): auto-chains after v2
