# Environmental covariate channels in the DINN input — result (2026-07-22, B200)

**Bottom line: the "add more environment" hypothesis is VALIDATED, and it lands the previously
non-identifiable `diatomgraz`. Adding MLD as a DINN input channel (beyond SST-only) recovers
`diatomgraz` 10/10 (from 3/10 = chance) by giving the Southern Ocean the mixing-depth signal SST
alone lacks. But covariates are parameter-specific and trade off: wind / SSS / pCO₂ / CO₂-flux
DESTROY `R_PICPOC`, and nothing rescues `scav_rat` (the sink leg still needs the Phase-2 anchor).
Best operating point: baseline + MLD only.** This is the lever that NN size and patch-overlap both
failed to move — because it adds *input information*, not capacity.

Setup: 5 arms, each n=10 seeds, 2000 epochs, on the verified geo1 anchors-only config
(GEOTRACES iron + Daniels calcite + POSi; PINN/pattern OFF; DUST_ANCHOR_W=0), B200 array job 178690.
The DINN is per-cell (`1×1` conv). Only the **input channels** change between arms. Grading = per-AOI
≥2-of-3 (`band_of` Cal+ ≤40%); **all 5 arms `verify_run` exit 0**. The baseline arm (SST-only, 1 channel)
reproduces the known geo1/dust-A result bit-for-bit (built-in sanity check that the channel edits are
default-off-identical).

## Result (per-AOI ≥2-of-3 recovery; medians)

| param | SST (baseline) | +MLD | +wind | +MLD+wind | +full† |
|---|---|---|---|---|---|
| **alpfe** | 10/10 (0.996) | 10/10 (0.987) | 10/10 (0.982) | 10/10 (0.957) | 10/10 (0.938) |
| **scav_rat** | 0/10 | 0/10 | 0/10 | 2/10 | 0/10 |
| **R_PICPOC** | **6/10** (0.059) | 5/10 (0.060) | **0/10** (0.216) | **0/10** (0.180) | **0/10** (0.380) |
| **diatomgraz** | **3/10** (0.45) | **10/10** (0.70) | **10/10** (0.65) | **10/10** (0.73) | 7/10 (0.61) |
| ρ(alpfe,scav) | −0.13 | +0.52 | +0.06 | +0.45 | +0.47 |

†full = MLD+wind+SSS+pCO₂atm+CO₂flux. Carroll refs: diatomgraz 0.830, R_PICPOC 0.0425, alpfe 0.928.

## The `diatomgraz` win is real and mechanistic (not a band-edge fluke)

Per-AOI `diatomgraz` (first seeds), SST-only vs +MLD:

| AOI | SST-only | +MLD | Carroll |
|---|---|---|---|
| eqpac | ~0.74 (Cal) | ~0.77 (Cal) | 0.83 |
| natlsubpolar | ~0.48 (Loose) | ~0.51–0.61 (Cal) | 0.83 |
| **southernoceanpac** | **~0.18 (Loose, 78 % off)** | **~0.65–0.71 (Cal)** | 0.83 |

With SST-only the Southern Ocean `diatomgraz` is stuck at ~0.18 — only eqpac recovers, so ≥2-of-3
fails (3/10). **MLD lifts the Southern Ocean into Cal-grade**, so all three AOIs recover (10/10). The
Southern Ocean is defined by deep winter convection; MLD is precisely the covariate that distinguishes
it, and the median shifts *toward* Carroll (0.45 → 0.70). The effect reproduces across three independent
covariate arms (MLD, wind, MLD+wind all → 10/10), so it is signal, not seed noise. Wind fixes the same
Southern-Ocean gap (natl stays Loose but eqpac+SO give 2-of-3).

## Control — is MLD physics, or just a location proxy? (both)

A skeptic's objection: MLD correlates with region (the Southern Ocean has the deepest MLD), so is the DINN
just using MLD as a location label? Ran an `AOI_ID`-channel control (a *pure* per-region location signal,
no MLD), n=10, `verify_run` exit 0:

| channel | diatomgraz | R_PICPOC | median diatomgraz |
|---|---|---|---|
| SST (baseline) | 3/10 | 6/10 | 0.45 |
| **+MLD** | **10/10** | 5/10 (safe) | 0.70 |
| +AOI_ID (pure location) | **6/10** | 0/10 | 0.54 |

A pure location channel recovers `diatomgraz` only **6/10** — better than SST (knowing "this is the Southern
Ocean" partly helps), but well short of MLD's 10/10. So MLD's benefit is **partly regional identification and
substantially physical**: the real mixing-depth field (with its within-region structure) beats a categorical
region label by 4 seeds. And `AOI_ID` also **breaks `R_PICPOC` (0/10)** — like wind and the full set — whereas
**MLD uniquely does not (5/10)**. So MLD is genuinely the sweet spot, not merely "any extra input channel";
the physical mixing field helps `diatomgraz` *without* the R_PICPOC collateral that a bare location signal
(or wind/carbonate covariates) causes.

## The trade-offs (why "just add everything" is wrong)

- **`R_PICPOC` collapses under wind / the full set.** 6/10 → 0/10, with the median blowing up to 0.22
  (wind) and 0.38 (full) — 5–9× Carroll's 0.0425, far outside the band. The extra channels give the
  per-cell DINN enough freedom to fit the other targets at `R_PICPOC`'s expense, overwhelming the Daniels
  calcite anchor. **MLD alone does NOT do this (6→5/10, median unchanged 0.06).** So MLD is the safe channel;
  wind/carbonate covariates are not.
- **`scav_rat` stays 0/10** across all arms (the lone 2/10 at MLD+wind is within noise). The binding sink
  leg is unmoved by *input* information — consistent with the observability-wall diagnosis; it needs the
  Phase-2 sink anchor (²³⁴Th flux + export partition), not more covariates.
- **`alpfe` stays 10/10** but its median drifts down with more channels (0.996 → 0.938) — robust, mildly perturbed.

## Interpretation

The covariate lever is **orthogonal to NN size and patch-overlap** (both of which failed): those change
*capacity*; covariates change *input information*. The params that improve are exactly the ones whose
per-cell field the DINN could not express from SST alone — `diatomgraz` in the Southern Ocean. This
sharpens the STATUS framing: `diatomgraz` was "not recovered on real data (best 4/10 = chance)" — but that
was a **practical, input-limited** miss, not a structural one. Given the right covariate (MLD), the POSi
(biogenic-silica) target *does* constrain it, 10/10.

**Recommended operating point: geo1 + MLD channel only** — recovers `diatomgraz` 10/10 with no collateral
damage (alpfe 10/10, scav_rat 0/10 unchanged, R_PICPOC 5/10 ≈ baseline). This turns the observable
denominator from 3-recoverable to a **4th** ({alpfe, R_PICPOC, diatomgraz} recover; scav_rat is the sole
observability-wall holdout awaiting the sink anchor).

## Honest caveats / next steps

1. `diatomgraz` recovery is against the **POSi diagnostic target** (steady-state biogenic silica back-solved
   from diatom biomass), not a prognostic Si cycle. The recovery is real against that target; whether it is
   *structural* identifiability needs a **profile-likelihood on diatomgraz with the MLD channel** (the
   SST-only profile was FLAT). That is the follow-up, and it is now well-motivated.
2. The `R_PICPOC`-vs-wind trade-off deserves a look: is it the DINN overfitting, or does wind carry a real
   confound with the calcite field? An MLD+Daniels-upweight arm could test whether R_PICPOC can be protected.
3. Do NOT globally re-headline `diatomgraz` as "identifiable" yet — headline it as **"input-limited, not
   structurally non-identifiable: recovers 10/10 once MLD is a DINN input"**, pending the profile-likelihood.

Artifacts: `/scratch/qi_zim_neu/covar/n10/arm{0..4}_*` (B200, all `verify_run` exit 0). Grader reproduces
the n=5 dust note bit-for-bit before use. Channel support added to `run_v3.0` (WIND/SSS/PCO2/CO2FLUX_CHANNEL
env flags; default off = SST-only bitwise-identical).
