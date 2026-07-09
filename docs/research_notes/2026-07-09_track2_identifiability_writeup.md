# Track-2 write-up — what real observations can (and cannot) constrain in Darwin's BGC closures

*Reference write-up, 2026-07-09. A results summary in write-up format, not a submitted
manuscript. The working record (how the analysis got here, including a deflated over-claim)
is in `2026-07-09_calcite_identifiability_map.md`.*

## Summary

Track-2 asks whether real ocean observations can constrain the uncertain closures in
ECCO-Darwin's biogeochemistry through a differentiable transport model. The answer, from the
two closures we can target with real data, is a clean **identifiability-limits** result: real
observations do **not** sharply constrain either closure — and, usefully, they fail for **two
different reasons**. This is a map of *what is observable*, which is itself the contribution.

## Motivation

ECCO-Darwin's Green's-functions calibration (Carroll et al.) fixes a handful of BGC parameters
that are individually uncertain. Track-1 showed these are only partly identifiable from real
data through a 0-D box (a surrogate that homogenizes, so held-out *data* validation is
blocked). Track-2's premise was that adding **prescribed spatial transport** (Darwin's own
velocities, no new GCM runs) would let real, spatially-structured observations constrain the
closures where the box could not. The make-or-break test (E2): does a learned closure, fit on
part of a real observation and scored on **held-out** cells through transport, beat a constant
(null) closure?

Two closures have real, Darwin-independent observations to target:

- **Calcite** — the rain ratio `R_PICPOC` (PIC:POC). Observation: direct ¹⁴C calcite-production
  measurements (Marsh et al. 2025, the updated Poulton/Daniels compilation).
- **Iron** — the scavenging rate `scav_rat`. Observation: dissolved-iron concentration
  (GEOTRACES IDP2025).

## Method

For each closure we ran two mutually-checking analyses, all on the shared 1° grid, with the
same honesty protocol (env-regime hold-out = extrapolate to an unseen environmental band;
anomaly-R² against the train mean; permutation null; BH-FDR multiplicity correction; and a
robustness sweep over the environment source, aggregation level, and box definition):

1. **Transport-free floor** — a trivial linear model at the observation cells. It bounds what
   signal is *in the data*, independent of the transport machinery.
2. **Differentiable transport-UDE** — the full windowed-BPTT closure fit through prescribed
   DB-1 iron forcing + DB-2 velocity, learned-minus-null held-out anomaly-R² with a K_num
   (numerical-diffusion) control.

The machinery is verified: div-free transport, mass-conserving semi-implicit vertical
diffusion, a checkpointed BPTT trainer, and a full-suite gate. An adversarial-review workflow
and a separate verification workflow (both multi-agent) hardened the harness and the claims.

## Result — an identifiability map, by mechanism

| Darwin closure | observable | verdict | why |
|---|---|---|---|
| calcite `R_PICPOC` | PIC:POC (**≈ the parameter**) | not identifiable | **data-limited** |
| iron `scav_rat` | DFe concentration (**≠ the parameter**) | not identifiable | **observability-limited** |

**Calcite — data-limited.** The rain ratio *is* essentially the parameter (a steady-state
identity makes standing-stock PIC:POC equal the production ratio Daniels/Marsh measure). But
the observations are sparse and the environmental signal does not survive scrutiny: the rain
ratio shows **no point-level correlation with in-situ Ω** in the best-sampled region (r = 0.01),
matching Marañón et al. (2016), who found tropical calcification independent of carbonate
chemistry across Ω = 1.5–6.5. An initial binned analysis looked regionally positive, but it
**inverted** when the environment source was swapped from in-situ carbonate to the GLODAP
climatology (the two agree only r = 0.24), so those positives were small-n / aggregation
artifacts. Net: real calcite data cannot sharply constrain an environment-driven rain-ratio
closure at present sample sizes.

**Iron — observability-limited (an information wall).** Unlike calcite, dissolved-iron
*concentration* is a low-information projection of the scavenging *rate*: many `scav_rat`
values reproduce the same concentration field (Tagliabue 2016; and Track-1's sloppiness /
profile-likelihood diagnostics). Empirically, DFe concentration **is** robustly
env-predictable (global Ω hold-out +0.14, permutation-p ≈ 0 on 1214 cells; iron is dense,
~1300 cells) — so a scavenging closure fit to held-out DFe would *appear* to work. But that
apparent skill does not identify the rate; it is the information wall in action. The
non-identifiability here is **structural, not a data-quantity problem** — more iron data would
not close it.

## Honest scope

- This is **not** a "transport closes the gap" pass, **not** a recovered parameter, and **not**
  "made Darwin differentiable / learned real biology." It is a bound on observability.
- The differentiable machinery is sound and verified, but at these small calcite sample sizes
  (validation sets ~4–9 cells) the transport-UDE deltas are within hold-out instability and the
  K_num control is non-discriminating (transport is inert in the surface-scored rollout). The
  robust evidence is the transport-free floor + the cross-source robustness, not any single UDE
  delta.
- The result is corroborated by independent published field data (Marañón 2016) and by an
  independent observation-derived environment product (GLODAPv2.2016b).

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
- Calcite: co-locate a denser tropical production+carbonate dataset (Malaspina 2010 / Marañón
  2016; JGOFS EqPac) to convert the currently-weak equatorial-Pacific test into a firmer
  tested negative.
- Iron: formalize the information wall with a `scav_rat` profile-likelihood through the
  transport model (the concentration→rate equifinality made explicit), rather than the
  concentration floor alone.

## Provenance

Harness + analyses (branch `2imi9/status-handoff-2026-07-07`): `src/darwindiff/held_out_obs.py`,
`marsh_loader.py`, `geotraces_loader.dfe_aoi_1deg_grid`; `scripts/{e2_real_calcite_eqpac,
marsh_identifiability_map, marsh_glodap_identifiability, marsh_omega_vs_bloom,
geotraces_glodap_identifiability, probe_marsh_env_rainratio}.py`;
`docs/research_notes/2026-07-09_{e2_calcite_preregistration, calcite_identifiability_map}.md`.
Data (gitignored): Marsh 2025 (`data/marsh/`), GLODAPv2.2016b (`data/glodap/`), GEOTRACES
IDP2025 + ECCO-Darwin v05 native (on `D:`).
