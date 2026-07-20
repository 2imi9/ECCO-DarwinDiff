# The silicate-scope identifiability artifact — recovered, and NOT usable as-is

Explorer arrays `8479481` + `8482504` completed successfully (all tasks exit `0:0`, last file
written 18:30 on 2026-07-19) and produced the 13-file Fisher/profile-likelihood artifact that
[the diatomgraz audit](2026-07-19_diatomgraz_claim_audit.md) identified as Paper #1's missing
evidence. The files are now committed under [`silicate_scope/`](silicate_scope/).

**They cannot be used to support the silicate claim.** Two of the three headline readings are
optimiser artifacts, and the third falsifies the inference pattern the claim rests on.

Working directory was `/projects/schultz/qi.zim/ecco-darwindiff`, not `$HOME` or `/scratch` — worth
recording, since the outputs are invisible from the paths the handoff note pointed at.

---

## 1. What was measured

Six Carroll-6 parameters × {`si`, `nosi`} (silicate in / out of the loss), plus a `realbsi` arm for
`diatomgraz` fitted against real GEOTRACES bSi. Each run reports a joint optimum `theta_star`, the
Hessian spectrum at `theta_star` and at Carroll's values, and an 11-point profile likelihood with a
`profile_rel_span` and a `verdict` string.

| param | span `nosi` | span `si` | gain | verdict (`si`) |
|---|---|---|---|---|
| `alpfe` | 0.0235 | 0.2068 | +0.1833 | SHALLOW |
| `scav_rat` | 0.0511 | 0.1956 | +0.1445 | SHALLOW |
| `Smallgrow` | 0.0050 | 0.1313 | +0.1263 | SHALLOW |
| `Biggrow` | 0.0049 | 0.1260 | +0.1211 | SHALLOW |
| `diatomgraz` | 0.0282 | **0.0595** | +0.0313 | SHALLOW |
| `R_PICPOC` | 47.5446 | 46.6434 | −0.9012 | CURVED |

Read naively this says *"adding silicate improves identifiability for five of six parameters."*
That reading does not survive a convergence check.

---

## 2. BLOCKER — the design *guarantees* the profile out-optimises θ\*, and that manufactures the silicate signal

### Root cause (found 2026-07-19, later than the rest of this document)

This is not bad luck in one arm. It is structural:

```python
# theta_star: 600 steps from Carroll
theta1, l1 = optimise(to_uncon(carroll.reshape(6, 1)), steps=args.opt_steps)   # --opt-steps 600

# profile: starts FROM theta_star, then optimises 300 MORE steps per grid point
u0 = to_uncon(theta_star.reshape(6, 1)).expand(6, G)
_, prof_losses = optimise(u0, steps=max(150, args.opt_steps // 2))             # = 300
```

Every profile grid point receives **600 + 300 = 900 steps** of optimisation, starting from θ\*,
while θ\* itself receives **600**. The profile is therefore *strictly better optimised than the
baseline it is compared against*. `min(profile) < loss_star` is **guaranteed** whenever those extra
300 steps still make progress — i.e. whenever θ\* has not converged at 600 steps.

So the measured "convergence gap" is a direct readout of **how far θ\* was from convergence in that
arm**, and `rel_span`, which is normalised by that too-high baseline, is inflated by the same amount.

This makes the conclusion below stronger, not weaker: the silicate "improvement" is a measurement of
optimiser shortfall, and the harder `si` loss (more terms, `POSI_W=1.0`, `POSI_DARWIN_W=0.5`)
converges *less* well in 600 steps than the `nosi` loss — which is exactly the observed pattern.

The profile likelihood fixes the profiled parameter on a grid and re-optimises the other five. By
construction its minimum **cannot** be below `loss_star` — at `p = θ*_p` it must return `loss_star`
itself. Comparing the two:

| run | `loss_star` | min(profile) | gap |
|---|---|---|---|
| `alpfe_si` | 68.997 | 61.694 | **−7.303** |
| `Smallgrow_si` | 68.997 | 61.765 | **−7.232** |
| `Biggrow_si` | 68.997 | 61.732 | **−7.265** |
| `scav_rat_si` | 68.997 | 61.843 | **−7.154** |
| `alpfe_nosi` | 67.778 | 66.304 | −1.474 |
| `scav_rat_nosi` | 67.778 | 66.275 | −1.503 |
| `diatomgraz_si` | 68.997 | 68.965 | −0.032 ✓ |
| `R_PICPOC_si` | 68.997 | 69.000 | +0.004 ✓ |
| *(others)* | 67.778 | 67.773 | −0.005 ✓ |

In the `si` arm the profile search finds solutions **7.3 lower** than the joint optimum — a 10.5%
improvement on a loss whose entire reported profile span is 0.06–0.21 relative (≈ 4–14 absolute).
The baseline is wrong by more than the effect being measured.

**And the contamination lines up exactly with the claim.** Splitting on convergence:

| group | convergence gap | span gain |
|---|---|---|
| `alpfe`, `scav_rat`, `Smallgrow`, `Biggrow` | ≈ **−7.2** | **+0.121 … +0.183** |
| `diatomgraz` | −0.032 ✓ | +0.031 |
| `R_PICPOC` | +0.004 ✓ | none (−0.90) |

The four parameters that appear to gain from silicate are precisely the four whose profile escaped a
bad `theta_star`. **Both parameters whose fits actually converged show no meaningful gain.** The
apparent silicate benefit is consistent with being an artifact of optimiser escape, not of the added
observable.

(The 4-vs-2 split is the statistic, not a rank correlation — the four gaps are near-tied at −7.2, so
Spearman over five points, +0.600, is uninformative about their internal ordering.)

This does not prove silicate is useless. It proves **this experiment cannot tell us either way.**

---

## 3. BLOCKER — four profile minima sit on a grid edge

A profile whose minimum lands on the boundary has not bracketed the optimum, so its span is a lower
bound and its verdict is not trustworthy:

| run | grid | argmin | |
|---|---|---|---|
| `alpfe_si` | [0.05, 1] | 0.05 | **left edge** |
| `diatomgraz_nosi` | [0.05, 1] | 0.05 | **left edge** |
| `diatomgraz_realbsi` | [0.05, 1] | 0.05 | **left edge** |
| `diatomgraz_si` | [0.05, 1] | 1.0 | **right edge** |

`diatomgraz` is the worst case: **the `nosi` arm puts its optimum at the bottom of the range and the
`si` arm puts it at the top.** Adding silicate flips the preferred value from one extreme to the
other. That is not a refinement of an estimate; it is an unstable fit.

**Resolved: the upper edge is physical, the lower edge is not.** `diatomgraz` is a *palatability* —
dimensionless, a multiplier on `G0_GRAZE` — with `bounds=(0.05, 1.0)` in the `carroll6.PARAMS`
registry. **1.0 is a genuine physical ceiling** (fully palatable), so `diatomgraz_si`'s right-edge
minimum must be reported as **"optimum at the upper physical bound"** — widening the grid past 1.0
would be meaningless. The lower bound 0.05 is a *search* bound with no physical basis (palatability
can approach 0), so the three left-edge cases (`diatomgraz_nosi`, `diatomgraz_realbsi`, `alpfe_si`)
genuinely do need wider grids.

These are different defects requiring different fixes, and the raw "4 profiles on an edge" count
conflates them.

`theta_star` also disagrees with the profile argmin by up to 11× (`alpfe_nosi`: θ\* = 0.9994 vs
argmin 0.0910), which is the same under-convergence seen from another angle.

---

## 4. The independent finding — FLAT does not imply unrecoverable

Set the convergence problem aside; the `nosi` arm is the better-converged one, and it says:

> **Four of six parameters are FLAT** (span < 0.05): `Biggrow` 0.0049, `Smallgrow` 0.0050,
> `alpfe` 0.0235, `diatomgraz` 0.0282.

`alpfe` is FLAT by this diagnostic — and `alpfe` is a parameter this project **recovers 9–10/10**
(native-LLC270 eqpac, issue #110). `Smallgrow` and `Biggrow` are flatter still.

So within our own data, **a FLAT profile-likelihood span does not imply a parameter is
unrecoverable.** That is exactly the inference the `diatomgraz` claim depends on. The audit already
established that the *number* (span 0.039) lacked a committed artifact; this shows the *reasoning*
does not hold either, using the strongest counter-example available — a parameter we demonstrably
recover.

**Consequence for Paper #1.** The defensible framing in the audit doc must be weakened further. It is
still true that `diatomgraz` is constrained only through a steady-state bSi diagnostic, and that
dense Darwin POSi recovers it 10/10. It is **not** supportable to present a FLAT span as evidence of
structural non-identifiability without also explaining why the same diagnostic calls `alpfe` FLAT.

---

## 5. The one arm worth rebuilding on — with its own caveat

`diatomgraz_realbsi` is the only run fitted against a **real** observable (GEOTRACES bSi) rather than
a model-derived one, so it is the only arm that avoids the circularity the audit identified (bSi
back-solved from diatom biomass). It reports span **0.1177**, SHALLOW.

**It does not pass the guards either.** Its `rel_grad_norm` is much the best in the set (0.012 vs
1.624 for the `si` arm), which is what first made it look clean — but that statistic is not the
convergence test. Its profile gap is −0.010 against a `loss_star` of 0.832, i.e. **1.2% relative**,
so it fails the same check as the `si` arm, just less severely. Its minimum is also on the left grid
edge.

Ranking all runs by *relative* profile gap:

| runs | relative gap | |
|---|---|---|
| `Biggrow/Smallgrow/diatomgraz_nosi` | 0.007% | pass |
| `diatomgraz_si` | 0.046% | pass |
| `diatomgraz_realbsi` | **1.2%** | fail |
| `alpfe/scav_rat_nosi` | 2.2% | fail |
| the four `si` runs | **10.5%** | fail badly |

So `realbsi` is the arm to *rebuild on*, not an arm to quote. Recording this because the first draft
of this document called it "the best-converged run" on the strength of `rel_grad_norm` alone — the
same substitution of a plausible-looking statistic for the actual test that this whole document is
about.

---

## 6. Required before any of this enters Paper #1

1. **Fix the step-budget asymmetry — this is the actual bug.** θ\* must be optimised at least as hard
   as any profile point. Three options, cheapest first:
   - raise `--opt-steps` until θ\* converges (the profile then cannot beat it), and/or
   - after computing the profile, adopt `min(profile)` as the new baseline and re-optimise θ\* from
     the best profile point until the gap closes;
   - run the profile from a *fresh* init rather than from θ\*, so the two are optimised
     symmetrically.
2. **Re-run with the convergence assertion.** Added — see §7. It will now refuse to emit a verdict
   rather than emitting a wrong one.
3. **Widen the grids** so every profile minimum is interior. `diatomgraz` needs to extend past 1.0
   (or its upper bound must be justified as physical, in which case an edge minimum should be
   reported as "at bound", not as a span).
4. **Re-run the silicate ablation** once 1–3 hold. Only then is "does silicate improve
   identifiability" answerable. Note one negative eigenvalue at θ\* in every run (and 2–3 at
   Carroll's values), consistent with not being at a minimum — the Hessian spectrum is not
   interpretable until θ\* converges either.

---

## 7. The pattern — again

The jobs exited `0:0`. The JSON is well-formed. Every file carries a confident `verdict` string
("FLAT → STRUCTURAL non-identifiability"). Nothing anywhere tripped. The artifact would have gone
into the manuscript as the fix for a known evidence gap, and it would have carried a conclusion its
own numbers contradict.

This is the third instance today of the same shape — after the `delta_t` bug and the `diatomgraz`
legend caption: **a claim that was never wrong *enough* to trip anything, propagating until
something forced a check.** The lesson from the audit doc was "claims that gate spending should carry
a committed artifact." This adds the obvious corollary:

> **A committed artifact is not evidence unless something checked that it converged.**

The concrete fix is cheap and is the reason a guard is worth more than a rule: the script already had
`loss_star` and the profile losses in the same scope. One comparison, and the run would have failed
loudly instead of emitting a verdict.

That guard is now in [`scripts/identifiability_sloppiness.py`](../../scripts/identifiability_sloppiness.py)
(§7 of this document's requirement list). It adds `valid`, `convergence`, and `bracketing` blocks to
the output JSON and replaces the verdict with `INVALID -> <reason>` when either check fails.

**Replaying the 13 committed artifacts through it: 9 are rejected.** Only `Biggrow_nosi`,
`Smallgrow_nosi`, `R_PICPOC_nosi`, and `R_PICPOC_si` survive — and `R_PICPOC` is the one parameter
whose span (≈47) was never in question.

The script itself was also untracked: it existed only in a detached-HEAD worktree
(`.claude/worktrees/competent-stonebraker-a9c3c0`) and on Explorer, despite having produced Paper #1's
identifiability evidence. Both copies were byte-identical (`md5 b514f9d8…`), so the version now
committed is exactly the one that ran.
