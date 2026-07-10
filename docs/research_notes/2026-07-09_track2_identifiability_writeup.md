# Track-2 write-up — what real observations can (and cannot) constrain in Darwin's BGC closures

*Reference write-up, 2026-07-09 (symbolic-distillation oracle diagnosis added 2026-07-10). A
results summary in write-up format, not a submitted manuscript. The working record (how the
analysis got here, including a deflated over-claim) is in `2026-07-09_calcite_identifiability_map.md`.*

## Summary

Track-2 asks whether real ocean observations can constrain the uncertain closures in
ECCO-Darwin's biogeochemistry. The answer, across the **three** closures we can target — iron
scavenging, calcite rain ratio, and phytoplankton growth — is a clean **identifiability-limits**
result: real observations do **not** sharply constrain any of them, and, usefully, they fail for
**three distinct reasons** (observability-, data/support-, and structural-limitation). This is a
map of *what is observable*, which is itself the contribution. Caveat carried throughout: the
make-or-break out-of-sample transport E2 was under-powered, so these verdicts rest on a
transport-free floor + an in-sample identifiability oracle, not on the transport gate (still open).

## Motivation

ECCO-Darwin's Green's-functions calibration (Carroll et al.) fixes a handful of BGC parameters
that are individually uncertain. Track-1 showed these are only partly identifiable from real
data through a 0-D box (a surrogate that homogenizes, so held-out *data* validation is
blocked). Track-2's premise was that adding **prescribed spatial transport** (Darwin's own
velocities, no new GCM runs) would let real, spatially-structured observations constrain the
closures where the box could not. The make-or-break test (E2): does a learned closure, fit on
part of a real observation and scored on **held-out** cells through transport, beat a constant
(null) closure?

Three closures have real, Darwin-independent observations to target:

- **Calcite** — the rain ratio `R_PICPOC` (PIC:POC). Observation: direct ¹⁴C calcite-production
  measurements (Marsh et al. 2025, the updated Poulton/Daniels compilation).
- **Iron** — the scavenging rate `scav_rat`. Observation: dissolved-iron concentration
  (GEOTRACES IDP2025).
- **Growth** — the phytoplankton growth rates `Smallgrow`/`Biggrow`. Observation: primary
  production (14C / satellite NPP).

## Method

For each closure we ran two mutually-checking analyses, all on the shared 1° grid, with the
same honesty protocol (env-regime hold-out = extrapolate to an unseen environmental band;
anomaly-R² against the train mean; permutation null; a robustness sweep over the environment
source, aggregation level, and box definition; and, for the earlier correlation-map analysis,
BH-FDR multiplicity correction — note the distillation-oracle exponents below are reported as
bootstrap CIs, *not* FDR-adjusted p-values, so the several per-basin/pooled oracle tests are not
multiplicity-corrected):

1. **Transport-free floor** — a trivial linear model at the observation cells. It bounds what
   signal is *in the data*, independent of the transport machinery.
2. **Differentiable transport-UDE** — the full windowed-BPTT closure fit through prescribed
   DB-1 iron forcing + DB-2 velocity, learned-minus-null held-out anomaly-R² with a K_num
   (numerical-diffusion) control.
3. **Symbolic-distillation identifiability oracle** — an independent, gradient-free test of
   whether the candidate mechanistic law is recoverable *on the support the data actually
   span*. It distills the closure's driver→output law by bootstrap regression against a
   physics-anchored candidate (a Monod bank for iron; a power law `ratio = R0·Ω^n` for
   calcite) and returns a verdict only when the mechanism is (a) significant, (b) stable
   across bootstraps, and (c) **distinguishable from its degenerate confounder on the visited
   support** — a Monod from a straight line only above the half-saturation knee, a power law
   from a constant only over a spanned driver range. Its role here is to convert "the signal
   is weak" into a quantitative statement of *why* — is the driver even excited?

The machinery is verified: div-free transport, mass-conserving semi-implicit vertical
diffusion, a checkpointed BPTT trainer, and a full-suite gate. An adversarial-review workflow
and a separate verification workflow (both multi-agent) hardened the harness and the claims.

## Result — an identifiability map, by mechanism

| Darwin closure | observable | verdict | why |
|---|---|---|---|
| calcite: **Ω-modulation** of `R_PICPOC` (scalar `R_PICPOC` itself *is* recoverable) | PIC:POC production ratio | Ω-dependence **untestable** | **data-limited** (within-region Ω support ≤0.16 dex everywhere — confirmed on independent in-situ Ω) |
| iron `scav_rat` | DFe concentration (**≠ the parameter**) | not identifiable | **observability-limited** (structural; not rescued by a particulate observable either) |
| growth `Smallgrow`,`Biggrow` | phyto biomass / NPP | not identifiable | **structurally unobservable** (loss-degenerate; total NPP gives only the biomass-weighted mean) |

**Calcite — data-limited (specifically: the *Ω-dependence* of the rain ratio is untestable).**
Two scopes must be kept separate. The **scalar** `R_PICPOC` is *already* recoverable — Track-1 lands
it ≈ Carroll's value once the contaminated Southern-Ocean ratio target is sanitized. What real data
cannot constrain is whether an **environmental driver modulates** it — the closure `ratio = R0·Ω^n`.
`R_PICPOC` is a *production* parameter and the Daniels/Marsh 14C ratios are a matched *production*
observable (unlike iron, no low-information projection), so the limit here is not the observable's
kind but the environmental *excitation*. The correlation evidence is weak and underpowered, not a
demonstrated absence: in the N. Atlantic-bloom cells corr(log ratio, in-situ Ω) = 0.01 (n ≈ 26, 95 %
CI ≈ ±0.35 — a non-rejection), while in the best-sampled equatorial Pacific the in-situ correlation
is actually *positive* (+0.25 GLODAP, +0.59 cache) but over a 0.08-dex Ω range too small to fit a
curve. An initial binned analysis looked regionally positive but **inverted** when the environment
source was swapped from in-situ carbonate to the GLODAP climatology (the two agree only r = 0.24),
so those positives were small-n / aggregation artifacts. Net: real calcite data cannot constrain an
Ω-driven rain-ratio
closure at present sample sizes. **This null holds on fully independent in-situ carbonate data:**
recomputing Ω from GLODAPv3 bottle DIC/TAlk/T/S (NCEI 0315582, 2026; 838 eqpac + 1740 natl
bottles) rather than the model cache, the per-basin exponents are **non-significant** (eqpac CI
[−0.57, +3.02], natl [−8.32, +4.47], both spanning zero on ≤0.17-dex within-basin support). The
pooled fit's CI [−3.20, −0.27] formally *excludes* zero — a weak **negative** slope — but on only
0.29-dex support and as a **between-basin contrast** (a Simpson slope across two biomes at
different Ω levels; see below), so it is not evidence of a within-regime Ω-dependence. Either way,
the calcite verdict does **not** depend on model-derived Ω.
(The GLODAPv3 DIC/TAlk are internal-consistency-adjusted via the furthest-first crossover inversion
of Humphreys et al. 2026; those per-cruise adjustments — ≲12 µmol kg⁻¹ — correct systematic offsets
and *improve* consistency, so they cannot manufacture the narrow spatial Ω range, and the null is
robust to them.)

The symbolic-distillation oracle pins the *mechanism*, and it is a **support** limit, scoped to an
**Ω-power-law closure** `ratio = R0·Ω^n`. Run on the real pairs (Daniels rain ratio × Ω_calcite),
the exponent is **non-significant in every region because the within-region Ω support is far too
narrow** — eqpac spans only 0.08 dex (Ω 4.72–5.67, n = 34 cells), natl 0.08 dex (n = 26). A
locally-significant correlation does appear (eqpac Daniels r = +0.59, p < 0.001) but over so tiny an
Ω range (0.08 dex) that it cannot distinguish a power law from a line — the oracle flags it as
under-excited rather than trusting it, which is the honest call but should be read as *untestable
here*, not *disproven*.

**The pooled tests do not rescue this, and must not be over-read.** Pooling basins raises the Ω
*span* (Daniels 0.25 dex, Marsh + Southern Ocean 0.38 dex) but that span is **between-biome
contrast** — each individual biome is ≤0.16 dex — so a pooled exponent (Daniels `n` = +0.89, CI
[−0.23, +1.78]; Marsh `n` = −0.47, CI [−1.16, +0.16]; GLODAP `n` = −1.80, CI [−3.20, −0.27]) is a
**Simpson cross-basin slope** across biomes sitting at different mean Ω *and* different mean rain
ratio, not a within-regime Ω→ratio response. In fact the within-basin Marsh slopes are individually
significantly **positive** (eqpac `n` = +3.40, CI [+0.23, +6.48]; natl `n` = +11.10, CI [+6.60,
+17.64]) — the pooled slope only flips negative because the lower-Ω subpolar basin has a *higher*
mean rain ratio (geomean 0.056 at Ω ≈ 3.7) than the higher-Ω tropics (0.035 at Ω ≈ 5.2), i.e. a
between-basin intercept ordering. So the pooled slopes disagreeing in sign is the signature of a
between-group artifact, not a physical dependence, and we make **no** claim that the ratio is
Ω-flat or Ω-decreasing. (The 0.30-dex
"identifiability threshold" is a heuristic, not a power-analysis result; treat it as a flag that
the within-region range is too small to fit a curve, not as a hard pass/fail.)

**Honest calcite verdict, correcting an earlier over-statement.** Real calcite data — cache Ω *and*
independent in-situ GLODAPv3 Ω alike — **cannot test a within-region Ω-power-law rain-ratio closure,
because no region has enough within-region Ω range** (≤0.16 dex everywhere). The corroboration with
Marañón (2016) is directional (tropical calcification ≈ Ω-independent), not a within-regime
replication. **And the limit is not Ω-specific:** testing the other drivers Darwin plausibly keys on
— SST and coccolithophore (Chl2) fraction — with a Simpson-robust *within-biome* (biome-demeaned)
partial correlation, **no driver clears the bar** (a significant *and* sign-consistent within-biome
relationship). SST *is* well-excited within biomes (eqpac 4.8 °C, natl 8.3 °C, SO 9.7 °C, unlike Ω's
0.08 dex) yet does no better than Ω: both show a weak positive within-biome trend in the two
well-sampled biomes (eqpac r ≈ +0.4, natl ≈ +0.3) that the small Southern-Ocean sample (n = 12)
reverses, so nothing is robust. So the calcite limit is **a fundamental property of the
climatological record** — no candidate driver has consistent within-region variation — not an
artifact of choosing Ω. (The faint 2-of-3-biome positive trend is a hint that more, denser
co-located data could firm up, not a present constraint.)

**Iron — observability-limited (an information wall).** Unlike calcite, dissolved-iron
*concentration* is a low-information projection of the scavenging *rate*: many `scav_rat`
values reproduce the same concentration field (Tagliabue 2016; and Track-1's sloppiness /
profile-likelihood diagnostics). Empirically, DFe concentration **is** robustly
env-predictable (global Ω hold-out +0.14, permutation-p ≈ 0 on 1214 cells; iron is dense,
~1300 cells) — so a scavenging closure fit to held-out DFe would *appear* to work. But that
apparent skill does not identify the rate; it is the information wall in action. The
non-identifiability here is **structural, not a data-quantity problem** — more *dissolved* iron
data would not close it.

**A particulate:dissolved observable was tested as a way to break this wall — and it does not.**
The idea: the scavenging *sink flux* `scav_rat·DFe·POC` becomes particulate iron, so a
particulate:dissolved partitioning ratio might isolate the sink where concentration cannot. A
self-twin probe initially looked like a dramatic pass, but adversarial verification (5 skeptics)
showed it was **largely a construction artifact**: the observable `pFe/DFe` reduces algebraically to
`scav_rat·POC/W_SINK` (DFe cancels exactly), so the swept parameter appears as an explicit prefactor
— the "sharp well" is tautological and the apparent tightening is a grid artifact. Worse, the
degeneracy is only *relocated*: `(scav_rat, W_SINK)` are perfectly degenerate in the ratio, and a
real contaminated `Fe_TP` (biogenic Fe + labile-lithogenic Fe scaling with dust ∝ `alpfe`)
re-injects the `alpfe` dependence (verified numerically:
[`2026-07-10_iron_partitioning_breaks_the_wall.md`](../findings/2026-07-10_iron_partitioning_breaks_the_wall.md)).
What legitimately survives is only that `alpfe` cancels from a *pure* scavenged-Fe partitioning
observable — it removes the source confounder in principle, but does **not** make the rate
identifiable. So partitioning is **not** a positive-E2 lever; it reinforces the wall from a second
angle (the rate is unidentifiable from concentration *and* from any realistic particulate:dissolved
observable). This corrects an earlier over-claim in this write-up — a good example of why every
numerical identifiability result here goes through adversarial verification before it is built on.

**Growth — structurally unobservable, and a production observable does not rescue it.** Phytoplankton
growth rates (`Smallgrow`, `Biggrow`) were "unobservable by construction" in Track-1 because standing-
stock biomass is set by a growth-vs-loss balance. The natural fix — a *production* observable, since
`NPP/biomass = μ·f_fe·LIGHT` is the specific growth rate with the loss terms cancelled (the same
flux-over-stock idea as the iron partitioning attempt) — was scouted on the real eqpac footprint. It
does not work for the *real* observable: total NPP (what 14C/satellite actually measure) constrains only
the **biomass-weighted mean** growth rate, so the `{Smallgrow, Biggrow}` pair stays degenerate — in
eqpac the large-phytoplankton rate is unidentifiable regardless (large phyto is negligible there), and
total NPP adds nothing over biomass. Only a per-PFT production observable would split the pair, and no
instrument measures it (and the self-twin per-PFT "pass" is the same construction tautology as the iron
case). So growth is at best *aggregate*-observable-in-principle — the third closure, third limit.

## Honest scope

- This is **not** a "transport closes the gap" pass, **not** a recovered parameter, and **not**
  "made Darwin differentiable / learned real biology." It is a bound on observability.
- **The differentiable-transport machinery did not contribute to any delivered verdict.** The
  pre-registered make-or-break test (E2 — a learned closure fit on part of the data and scored on
  *held-out* cells through transport) came back **under-powered and non-discriminating** at these n:
  the transport-UDE deltas are within hold-out instability and the K_num control is inert (transport
  is decorative in the surface-scored rollout). Every verdict in this map therefore rests on a
  **transport-free floor + an *in-sample* bootstrap-CI oracle**, not on the out-of-sample transport
  E2. The title/framing should be read as "an identifiability study *motivated by* the differentiable
  approach," not "results obtained *through* it" — the make-or-break out-of-sample gate remains open.
- The result is corroborated by independent published field data (Marañón 2016) and by
  **independent in-situ carbonate data** (GLODAPv3, 2026), on which the calcite oracle returns the
  same null — so the calcite verdict does not depend on model-derived Ω.

## Why this is a useful result

An honest map of *which BGC closures real observations can constrain, and the distinct reasons
they cannot* is a contribution in its own right. It tells a modeler: iterating on the calcite
rain-ratio closure against the current calcite record is under-powered (get more/denser
co-located production+carbonate data — e.g. Malaspina/Marañón — before expecting a constraint),
while iterating on the iron scavenging closure against iron concentration is
**structurally** under-determined regardless of data volume (constraining the rate needs an
observable closer to the rate, not more concentration). It also delimits what a
differentiable-Darwin inversion can deliver, and where the observing system — not the method —
is the binding constraint.

## Next steps

- Send this framing to the collaborators; confirm the identifiability-limits result is the
  target Track-2 contribution (vs pivoting to a different closure/observable).
- Calcite: the oracle makes the lever explicit — the binding constraint is **Ω support**, not
  sample size or closure size, so the pre-registered "pool basins + smaller closure" E2 rerun
  will **not** recover identifiability (pooled Ω already spans only 0.25 dex), and is not worth
  the GPU. The only thing that would change the verdict is **wider Ω coverage**: co-locate a
  dataset that actually varies Ω (high-latitude / Southern-Ocean calcite, or a
  production+carbonate compilation spanning Ω well beyond the tropical 4–6 band). This is a
  data-staging question, not a compute or method one.
- Iron: formalize the information wall with a `scav_rat` profile-likelihood through the
  transport model (the concentration→rate equifinality made explicit), rather than the
  concentration floor alone.

## Provenance

Full data checksums, findings→commit mapping, software versions, and reproduction commands are in the [reproducibility appendix](2026-07-10_reproducibility_appendix.md).


Harness + analyses (branch `2imi9/status-handoff-2026-07-07`): `src/darwindiff/held_out_obs.py`,
`marsh_loader.py`, `geotraces_loader.dfe_aoi_1deg_grid`; `scripts/{e2_real_calcite_eqpac,
marsh_identifiability_map, marsh_glodap_identifiability, marsh_omega_vs_bloom,
geotraces_glodap_identifiability, probe_marsh_env_rainratio}.py`; the symbolic-distillation
oracle `scripts/symbolic_distill_probe.py` (+ `symbolic_distill_dynamics_probe.py`,
`calcite_omega_identifiability_real.py`, `tests/test_symbolic_distill.py`);
`docs/research_notes/2026-07-09_{e2_calcite_preregistration, calcite_identifiability_map,
parameter_conditioned_emulator_update}.md`; `docs/findings/2026-07-09_symbolic_distillation_identifiability_oracle.md`
+ `calcite_omega_identifiability_real.json`.
Lever scouts: `scripts/{iron_partitioning_scout, iron_partitioning_controls, growth_npp_scout,
glodap_omega_calcite, calcite_driver_scout}.py`; findings `docs/findings/2026-07-10_iron_partitioning_breaks_the_wall.md`,
`calcite_omega_glodap_marsh.json`.
Data (gitignored): Marsh 2025 (`data/marsh/`), GLODAPv3 (`D:\glodap\`), GEOTRACES
IDP2025 + ECCO-Darwin v05 native (on `D:`).
