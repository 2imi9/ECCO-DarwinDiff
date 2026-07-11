# E2 calcite seed ensemble — hardened (n=10, Explorer H200)

**Source:** Explorer H200 seed array (job 8285893), portable AOI bundle (cuda/float32),
regularized closure (hidden 4, wd 0.01), epochs 200,
Marsh calcite target, eqpac upper-quartile-Ω hold-out (n_val=6, n_train=18).
**Local-only — not committed to GitHub.**

This hardens the single-seed make-or-break negative (`docs/findings/2026-07-10_e2_powered_result.md`)
into a **seed ensemble**: a *replication* against random closure init, not a power increase
(n_val is structurally fixed at ~6 by the ≤0.16-dex within-region Ω range). A PASS needs
delta = (learned − null) anomaly-R² **> 0** AND the K_num ladder shrinking as kh grows.

## Verdict: ROBUST NEGATIVE (no seed beats the null)

- delta (learned − null) = **-0.482 ± 0.000**  (range [-0.483, -0.482])
- seeds with delta < 0 (closure loses to null): **10/10**
- seeds with delta > 0: 0/10 · full-pass (delta>0 AND K_num-shrinks): 0/1

The learned closure fails to beat a constant-through-transport null across every seed — the
decisive negative is **robust to random init**, not a single unlucky/lucky seed. The
identifiability limit on the Ω-modulation of `R_PICPOC` holds out-of-sample and out-of-seed.

**Read the seed variance correctly:** the null R² is seed-*independent* by construction (the
`EnvCalciteClosure` is zero-initialized, so the untrained null is the constant g=1 closure
regardless of seed). The seed variance lives in the *learned* R² (different inits → slightly
different converged closures), and it is tiny (delta σ ~5e-5) — training consistently moves the
closure *away* from g=1 to fit the train cells and *hurts* held-out prediction (learned R² < 0,
below the basin-mean baseline), because there is no within-region Ω signal to learn.

## Per-seed

| seed | learned R² | null R² | delta | K_num ladder (50/200/800) | full-pass |
|---|---|---|---|---|---|
| 0 | -0.017 | +0.465 | **-0.482** | -0.48/-0.48/-0.48 | no |
| 1 | -0.017 | +0.465 | **-0.482** | — | — |
| 2 | -0.017 | +0.465 | **-0.482** | — | — |
| 3 | -0.017 | +0.465 | **-0.482** | — | — |
| 4 | -0.017 | +0.465 | **-0.482** | — | — |
| 5 | -0.017 | +0.465 | **-0.483** | — | — |
| 6 | -0.017 | +0.465 | **-0.482** | — | — |
| 7 | -0.017 | +0.465 | **-0.482** | — | — |
| 8 | -0.017 | +0.465 | **-0.483** | — | — |
| 9 | -0.017 | +0.465 | **-0.483** | — | — |
