# Mathematical audit of the grading metric — index of findings and what was done

Eight open mathematical questions under the DarwinDiff grading metric, each derived against the real
code and then handed to a hostile verifier instructed to refute it. 16 agents, 2.19M tokens,
470 tool calls, 0 errors.

**Four findings changed the repo the same day, and two of those were defects in work committed
earlier that day.** That is the point of running this before the manuscript rather than after.

---

## Applied

### 1. RETRACTED — "the `R_PICPOC` anchor-off control at 6/50 is itself chance-level"

Applied to `2026-07-28_session_evidence_log.md` §G2. The P = 0.078 came from a one-sample binomial
against the **rule-of-three floor** 3/50 = 0.06, a deliberately conservative upper bound on an
*unobserved* rate. This baseline was **measured** as 0/50, and with both sides measured the right
test is the 2×2: Fisher exact one-sided gives **p = 0.0133**.

Honest statement: 6/50 is far below the anchored 50/50 but is *slightly and detectably* above
untrained, not indistinguishable from it. **New standing rule: when a baseline is measured as a
sample, compare samples; reserve the rule-of-three floor for a genuinely unobserved rate.**

### 2. STRENGTHENED — the `R_PICPOC` zero is exact, global, and provable by inspection

Applied to `2026-07-29_gnfisher_structural_clause.md` §2a. Scaling `R_PICPOC` by **100×** leaves
DFe₁, DFe₂, P_diatom, POC₁ and POC₂ **bitwise identical**, while the PIC₁ positive control moves
97.6×. `{DFe, P₁..₅, POC}` is a closed block with no PIC/DIC/ALK term.

This is **global structural non-identifiability in the Raue sense**, not a local Fisher singularity.
It needs neither the Fisher matrix nor Rothenberg's regular-point hypothesis, and it is **immune to
the Gauss-Newton approximation** because the neglected residual-curvature term is zero in that row.

### 3. CORRECTED — the "10⁶ times more tightly constrained" CRLB ratio was a ridge artifact

Applied to the same doc §2b, four commits after it was published. `CRLB = diag(inv(F + ridge·I))`
with `ridge = 1e-6·λ_max`, so a direction carrying no information **cannot** report a CRLB above
`1/ridge`. Measured: the five non-`R_PICPOC` parameters sit at **0.994 to 1.000 of that floor**. The
"10⁶" was `1/(1e-6)`. Quote "unconstrained, at the ridge floor", never a ratio.

### 4. FIXED — the contract read registry metadata where it needed the run's actual map

`Param.scale` is metadata; the applied map is set by `PARAM_LOG_SCALE`, which defaults to empty and
therefore **linear**. `scav_rat` is declared `scale="log"` while every published run bounds it
linearly, so the contract was placing its untrained prior at 3.0e-7 instead of 1.515e-6 — a **factor
of five** error in exactly the quantity the measured prior control exists to settle. `Unknown` gained
an explicit `bounding_map` field.

### 5. FIXED — seed-level straddles that net to zero are no longer invisible

The `STRADDLE` flag fires only when cell-weighted minus per-AOI > 0, so it is silent whenever reverse
seeds cancel straddling ones. Archived example: `cocc_c` `scav_rat` has 2 straddling and 2 reversing
seeds, both rows print 7/10, no flag, exit 0. Tolerable for a **marginal** count and not for a
**joint** one, because a joint count is a conjunction over the same seeds and cancellation permutes
*which* seeds pass. Now printed unconditionally as information rather than as a flag.

### 6. CORRECTED — my own ladder addendum, and then re-tested

See `2026-07-29_preregistration_obsonly_and_ladder.md` §3.1b. The claim that ~94 % of cells are
constrained in shape but not magnitude is **false for four of six parameters**, because the PINN term
(`run_v3.0_joint_multi_aoi.py:1755-1771`) is **dense and absolute**, carrying `alpfe`, `scav_rat`,
`Smallgrow` and `Biggrow` at every ocean cell at weight 3.0. It survives only for `diatomgraz` and
`R_PICPOC`, which appear nowhere in that term.

The audit also found that **`diatomgraz` is ungradable in the pointwise arm**: the untrained free
field is uniform at the bounds midpoint, whose rel offset 0.3675 is inside the band, so its baseline
saturates and no `k*` exists. A pre-registered prediction of the whole untrained arm was then written
and **tested at n=10 (job 233723): all seven rows matched.**

---

## Verified as sound, no change needed

### 7. Paired versus unpaired null — nothing flips

The design is genuinely paired (identical initialisation per seed; Adam at lr=0 leaves weights
bit-identical), but pairing is the wrong lever and changes nothing. On every trained-versus-untrained
row the margins pin the 2×2: a zero baseline forces the discordant cell to zero, so McNemar collapses
to 2⁻ᵏ. `alpfe` 49/50, `scav_rat` 25/50 and 41/50, `R_PICPOC` 50/50 and the trio 25/50 all stay
decisive under the exact paired test (weakest 2.98e-08), and `diatomgraz` 35/50 stays not-above-chance
(0.500 paired versus the reported 0.447). **No headline claim changes.**

### 8. Rule of three — correct, and correctly conservative

3/N is the correct **one-sided** 95 % upper bound for 0 events in N trials, conservative by +3.17 %
relative at N=50 against the exact Clopper-Pearson `1 − 0.05^(1/50) = 0.0581551`. Because
`P(X ≥ k)` is strictly increasing in `p`, substituting an upper bound makes every reported P an
**upper** bound too. The two-sided caveat should be dropped: "95 % upper bound on the rate" is
one-sided by construction. Fixed the `3/30 = 0.10` typo at evidence log :570.

---

## Open, not yet applied

| # | Item | Where |
|---|---|---|
| A | **Exact prior pass probability.** The midpoint test is the `s → 0` limit of `P = Φ(z_hi/s) − Φ(z_lo/s)` with `z = logit(u(p))`. Implement `prior_pass_probability` alongside `prior_midpoint_offset`. | `carroll6.py:230-253` |
| B | **`fisher_gn` emits no `rank` and no `null_space`**, yet the manuscript clause rests on both. The `peraoi` path uses tolerance `1e-4·λ_max` while `fisher_gn` uses `1e-6` — two different implicit tolerances. | `identifiability_sloppiness.py` |
| C | **Annotate that `crlb[i] = 1/ridge` exactly when the Fisher diagonal is zero**, so finding 3 cannot recur. | same file |
| D | **Flags never touch the exit code.** Under the convention of gating on exit 0, a straddling run is still blessed. If straddles are meant to gate, they need a *status*, not a flag. | `verify_run.py` |
| E | **Truncated-map refinement to σ\*.** The closed form gives σ\* = 0.8203 nat (0.3563 dex) for an exact lognormal; under the *actual truncated sigmoid* map the requirement is about 9 % larger, ≈ **0.8924 nat (0.3876 dex)**. The hard maximum on `scav_rat`'s bounds is 2.30. Worth recording in `diagnostics.py` next to `sigma_threshold_for_band`. | `diagnostics.py` |
| F | **`joint_recovered` is `JOINT_RECOVERY_MODE`-dependent** while the row is labelled "cell-weighted [DO NOT QUOTE]". All 1795 local artifacts are `cellweighted` so nothing is wrong today, but the label is mode-dependent. | `verify_run.py:169` |

---

## What this exercise says about the method

The audit's own best evidence for itself is that it **broke things that were already committed**, and
two of them had been written hours earlier by the same session that commissioned the audit. A review
that only ever ratifies is not a review. The corrections here cost one afternoon and would have cost
a referee report otherwise.
