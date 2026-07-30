# A UDE cannot break the iron degeneracy, because the degeneracy is a gauge symmetry

**Date:** 2026-07-30 · **Method:** 6 independent design angles, each hostilely screened, then
judged (13 agents, 1.99M tokens) · **Run:** `wf_72272c5b-4f8` ·
**Verdict: NO. Five of six angles were screened RE-ENCODES-THE-DEGENERACY. The skeptic survived,
with three corrections. The productive move is to fix the gauge and estimate what survives it.**

Jon asked for the UDE to be aimed at the iron closure specifically, on the grounds that
concentration pins the ratio and not the two rates on their own. That instinct is right and the
consequence is stronger than expected: it rules out the UDE as a way to recover the rate.

## 1. The result, stated exactly

Write the scavenging sink in the general learned form

```
S(x) = r0 * g_theta(x)
```

for **any** function `g` and any weights inside it. `S` is homogeneous of degree one in `r0`, so
the map

```
(alpfe, r0)  ->  (lambda * alpfe, lambda * r0)
```

leaves the predicted dissolved-iron field unchanged. A neural network placed inside a
multiplicative sink lives entirely inside that orbit. **It does not remove a dimension from the
orbit. It adds free directions along it.** That is the whole argument, it applies to every
architecture, and it is why five of six proposals failed the same way.

This also predicts the DOF ladder's inverted U rather than merely being consistent with it:
6 free values give trio 0/50, 406 shared give 25/50, 1218 per-AOI give 3/50, 17,106 free per-cell
give 0/40. Capacity added along a flat direction cannot help and does hurt.

## 2. Three corrections the screen forced, all accepted

**It is sloppy, not structural.** The first draft called this an exact structural
non-identifiability. It is not exact. In the shipped 2-layer box at Carroll values, scavenging
carries **79.7%** of the steady-state surface iron sink; biological uptake and the L1-L2 exchange
carry the other **20.3%** and neither is homogeneous in `r0`. Co-scaling the pair by 16x moves
steady-state surface DFe monotonically by **0.187 dex**. So the orbit is nearly flat, not flat,
and that gap is the only reason an experiment remains worth running.

**The 1.000000 aliasing figure was an artifact of our own initialization, not a fact about the
ocean.** With a zero-init readout, `dS/db = eps * dS/dlog_r0` exactly, on any dataset. Gauge-fixing
the same closure on the same data takes `corr(level, readout bias)` from **1.000000 to 0.3078** and
`corr(level, p)` from 0.9652 to 0.0048, both clearing the pre-registered 0.95 gate. A number that
flips from FAIL to PASS under a pure reparameterization cannot carry a veto. It is an instruction:
**gauge-fix by construction.**

**The "observations-only scav_rat is 0/50" premise is an aggregation artifact that points at a
basin.** This reproduces, independently, what
`2026-07-30_per_aoi_legs_vs_their_own_null.md` measured the same day from the artifacts: `scav_rat`
clears its own untrained null in `southernoceanpac` at 42/50, 39/50 and 50/50 across all three
observations-only arms against untrained 0/50, and is 0/50 in both other basins. Two independent
routes to the same correction.

## 3. A verified bug this exposed

`src/darwindiff/closures.py:130`

```python
self.log_r0 = nn.Parameter(torch.tensor(math.log(base * self.POC0)))
```

**Confirmed by reading the file.** The learned scavenging closure carries a *free* multiplicative
level, which is exactly redundant with `scav_rat`, so `(scav_rat, r0) -> scav_rat * r0` is a
one-dimensional exact redundancy. **Any profile likelihood of `scav_rat` computed against this
closure is flat by theorem rather than by measurement.** This is a bug independent of whether any
UDE is ever built, and it means no existing result using `ScavClosure` can support a statement
about `scav_rat`'s identifiability.

## 4. The design that follows

Replace only the **shape** of the sink, and delete the free level:

```
S(x)           = (86400 * scav_rat) * DFe(x) * POC(x) * G_theta(x)
log G_theta(x) = h_theta(x) - mean_support[h_theta]
h_theta(x)     = (p - 1) * log(POC(x)/POC0) + eps * tanh(MLP_w(log10 DFe + 4, log10 POC/POC0))
```

Two mandatory constraints:

- **`log_r0` is removed.** The level belongs to `scav_rat` alone.
- **`log G` is mean-centred over a fixed reference support**, recomputed each forward pass and not
  per batch, so `G` is mean-zero in log space, `scav_rat` carries the entire geometric-mean level,
  and `theta` carries only shape. The gauge is then closed by construction and training cannot
  re-open it.

At initialization the readout is zero and `p = 1`, so `G = 1` bitwise and the closure reproduces
the current bilinear sink to round-off. That is the cleanest untrained null in the project.

Hook it into `carroll6_ude_tendency` beside the existing `ffe_closure` and `calcite_closure`
kwargs. **Not** through `transport.py`, which is blocked on issue #192 (`kh=50` is m^2/s in an
m^2/day framework, an 86400x error) and whose iron budget is void until that is fixed.

## 5. What may and may not be claimed

**May:** that the degeneracy is a one-parameter multiplicative gauge symmetry, written exactly;
that the **level** of the sink is unidentified from concentration and no multiplicative closure can
change that; that the **shape** survives the gauge and is a legitimate estimand; that `scav_rat` is
regionally identifiable in the Southern Ocean against its own null.

**May not**, and these phrases are banned from anything this produces: "breaking the degeneracy",
"recovering the scavenging rate", "learning the iron closure from data", "making Darwin
differentiable". The correct framing is **constraining the shape of the scavenging law while
reporting the rate as unidentified, with the gauge stated.**

## 6. Grafts worth keeping from the rejected angles

- **A parameter-rescaling admissibility test, and it should go into `src/darwindiff/contract.py`
  beside `ALIASING_GATE`.** If a closure change rescales a graded parameter by more than its
  registry bounds span, the Cal-grade target is void before a single epoch runs. The ligand
  proposal fails it outright: `scav_rat`'s bounds span 100x and the ligand rescale is 61x to 2001x.
  It fires before training and cannot be argued around, which makes it more discriminating than the
  aliasing gate.
- **The depth axis is the observable we already own and are discarding.** Concentration at one
  level gives one number; a profile gives shape. The 0-D box homogenizes exactly that.
- **A three-control requirement for any pinned-coordinate or prior-loaded architecture:**
  architecture-matched untrained, plus pin-only with zero free parameters, plus a prior sweep. This
  is the correct generalization of the `diatomgraz` 35/50 retraction.
- **Source-side observables are a measured null for the binding leg.** The dust-anchor A/B already
  ran: `alpfe` 10/10, `scav_rat` 0/10, medians 3.76e-7 against 3.75e-7. Wire the Black 2020 anchor
  as a cheap bound on the source, not as a route to `scav_rat`.

## 7. For Jon

The scavenging degeneracy holds up under everything thrown at it, and it can now be written down
exactly: a source scalar over a sink rate is a multiplicative symmetry of the steady state, and any
learned sink inherits it, so a network inside the sink cannot remove it and only adds free
directions along it. That matches the Tagliabue table and it matches the fits. What can be done is
fix the symmetry by construction, so the rate carries the whole level and the network carries only
the shape, and then ask whether real iron data resolves any shape at all. That is what is being
run, in the Southern Ocean first, because that is the one basin where the rate clears its own
untrained baseline. The answer is pre-registered as no. If it is no, the result is a clean
statement about what the iron observing system can and cannot constrain, which is worth having
either way.
