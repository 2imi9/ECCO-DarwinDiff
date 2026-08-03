# Pre-registration — adequacy-weighted routing

**Written:** 2026-08-03, **before** any arm was submitted.
**Rule artifact:** `docs/findings/2026-08-03_adequacy_rule.json`
**Rule script:** `scripts/analysis/emit_adequacy_rule.py` (asserts it never reads the answer)
**Lever:** `FET_AOI_W_<AOI>` in `scripts/run_v3.0_joint_multi_aoi.py` (default 1.0 = no-op)

## The claim being tested

Weighting AOIs by Fisher information made recovery **worse** (`scav_rat` 26/50 → 11/50, job
256953). The post-mortem named the reason and did not fix it:

> information is not helpfulness — a Fisher diagonal measures sensitivity, not whether the
> residual it is driven against is correct

This pre-registration supplies the missing factor and tests it. **Adequacy** is the relative
residual of the box against Darwin, per observable block:

    rho(a, b) = ||model(theta) - d|| / ||d||

`rho >= 1` means the residual is at least as large as the signal: **no parameter value makes
the box match**, so gradient spent there is spent on an unreachable target.

The measurement is not new and not tuned for this experiment. It exists at two independent
evaluation points, derived a week apart, and they agree on the ordering:

| FeT block | eqpac | natlsubpolar | southernoceanpac |
|---|---|---|---|
| at the recovered optimum (2026-07-28) | **>= 1.0** (clipped) | 0.621 | 0.554 |
| at the prior midpoint (2026-08-03, this rule) | **1.347** | 0.915 | 0.883 |
| `scav_rat` per-AOI recovery, flagship | **8/50** | 19/50 | 49/50 |
| `scav_rat` per-AOI recovery, per-parameter trunks | **6/50** | 43/50 | 49/50 |

The ordering of adequacy matches the ordering of recovery in both rows, and eqpac's residual
exceeds its signal at **both** evaluation points. This is the basin where `scav_rat` has never
recovered — at any capacity, at 2000 or 4000 epochs, under every intervention tried.

**This is a diagnosis competitor, not a confirmation.** Fisher conditioning (`ind349`) puts
eqpac at 35 and natl at 51, i.e. it ranks natl as *worse* conditioned than eqpac, which
inverts the true recovery order. Adequacy gets that pair right. If adequacy is also wrong, the
experiment below says so.

## H1 (primary)

Zeroing the Darwin-pattern FeT term in the basin whose iron residual exceeds its signal
(eqpac) **improves** `scav_rat` per-AOI ≥2-of-3 recovery against an otherwise identical
control.

## Arms

All arms: `flagship_geo1.sh`, shared trunk, `DINN_HIDDEN_DIM=16`, 2000 epochs, n=50 seeds
(0–49). The **only** variable is `FET_AOI_W_*`.

| tag | `FET_AOI_W` (eqpac, natl, sopac) | role |
|---|---|---|
| `adq_ctrl` | 1, 1, 1 | control; must reproduce the flagship ≈26/50 |
| `adq_eq0` | **0**, 1, 1 | treatment — drop the inadequate block |
| `adq_so0` | 1, 1, **0** | **falsifier** — drop the *most adequate* block, which is also the *largest* (1296 cells vs eqpac's 1071) |
| `adq_null` | 1, 1, 1 | untrained, `NB23_LR=0` |

**One null is correct here and it is deliberate.** The 2026-08-03 finding that untrained
baselines must be architecture-matched applies because *architecture* changed between those
arms. Here every arm has an identical network and differs only in loss weights, and an
untrained arm takes no gradient at all — so the loss weights cannot affect it. A second null
would be the same experiment run twice.

## Pass rule, fixed in advance

H1 is **supported** only if **both** hold:

1. `adq_eq0` beats `adq_ctrl` on `scav_rat` per-AOI ≥2-of-3 at Fisher exact **P < 0.01**
   (the bar this project uses everywhere else, and the bar the per-parameter architecture
   effect failed at P = 0.0128).
2. `adq_so0` does **not** beat `adq_ctrl` at P < 0.01.

If (1) holds and (2) fails, the effect is "reducing FeT loss anywhere helps" — a statement
about loss balance, **not** about adequacy — and must be reported as such.

## Controls that must hold for the intervention to count as surgical

- `alpfe` stays ≥ 45/50 in every trained arm. It recovers 49–50/50 and does not depend on
  eqpac's iron pattern; a collapse means the lever is not confined to the FeT term.
- `R_PICPOC` stays ≥ 45/50 in every trained arm. This is the reason the rule normalises
  **within a block across basins** rather than absolutely: POC and PIC are saturated in all
  three basins, so an absolute adequacy cut would have zeroed the Darwin-pattern terms that
  `R_PICPOC` recovers from. The emitted rule gives POC/PIC contrast 1.0 and leaves them alone.
- Every arm must pass `verify_run.py` at exit 0. Numbers from an arm that does not are not
  reported.

## Predictions, recorded so they can be wrong

- `adq_ctrl` ≈ 26/50, reproducing the flagship.
- `adq_eq0` > `adq_ctrl`, with the gain in the **natl** leg. eqpac is dead either way, so the
  mechanism is that eqpac's unreachable residual stops polluting the shared trunk.
- `adq_so0` ≤ `adq_ctrl` — dropping the most adequate iron block should hurt.
- If the mechanism is right, `adq_eq0` recovers part of the per-parameter trunk gain
  (26 → 45) at **1/4.7 the parameters**, because both interventions act on the same leg:
  per-parameter trunks *isolate* the bad gradient, adequacy weighting *removes* it.

## What this cannot show

It cannot show eqpac's iron is misspecified **in Darwin**. `rho` is measured for the 0-D box
against Darwin's field, so a large residual is a property of the surrogate, not evidence about
the GCM. It also cannot rank input channels, for the same reason the information rule could
not: a channel changes the parameterisation rather than the residual.

`rho` at the prior midpoint additionally conflates "the model cannot reach this" with "we
started far away" — at `theta_0`, `R_PICPOC` is 0.7525 against Carroll's 0.04245, which is why
PIC's residual there is ~10^3. The within-block normalisation is what contains that: a
globally bad starting point inflates all three basins together and cancels, and only the part
that **varies across basins** survives into a weight. FeT is the only block where anything
survives.
