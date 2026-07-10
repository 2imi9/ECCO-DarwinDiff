# Calcite rain-ratio identifiability map — the real-data E2 outcome (2026-07-09)

> **REVISED CONCLUSION (2026-07-09, robustness checks — read this first).** The
> region-specific "identifiability" positives in §3–§4 (N.Atlantic bloom / Patagonian Ω)
> are **NOT robust** and should not be presented as a finding. Two independent checks
> deflate them (§9): (1) swapping the environment source from Marsh's own in-situ carbonate
> to the GLODAPv2.2016b Ω climatology (independent, observation-derived) **flips** the
> N.Atlantic-bloom result from +0.69 to −2.27 and Patagonian from +0.86 to −1.07 — and the
> two Ω sources agree only r=0.24 at the same cells; (2) at the **point level** the rain
> ratio has ~zero correlation with in-situ Ω in the N.Atlantic bloom (r=0.011), matching
> **Marañón et al. 2016** (tropical calcification independent of carbonate chemistry). The
> binned positives are small-n / aggregation / env-source artifacts. **The robust,
> defensible result is the NULL:** real direct calcite observations do **not** reliably
> constrain an Ω-driven rain-ratio closure at these sample sizes — an identifiability-limits
> result, consistent with the literature. The transport-E2 +0.245 (§3c) is within small-n
> hold-out instability. §3–§8 are kept as the record of how the analysis got here.

**Verdict (adversarially verified, HOLDS_WITH_QUALIFICATIONS):** the Track-2 real-data E2
gate did **not** produce a clean "transport closes the surrogate gap" pass. It produced
something more defensible — a **map of where real, direct, Darwin-independent calcite
observations can constrain an environment-driven rain-ratio closure**, with a positive,
mechanistic core. This is the "identifiability map" the E2 design named as the honest
fallback (`2026-07-07_deep_review_e2_readiness.md`), realized with a positive centre.

This note is the canonical record. Every number below was reproduced by an independent
6-agent verification workflow (dimensions: statistics/permutation, carbonate/units,
robustness, E2-consistency, honesty/over-reach → synthesis), which also **corrected four
over-reaches** (§5).

## 1. What the E2 gate asked, and the two independent lines of evidence

E2: can a learned closure `g(env)`, fit on part of a real calcite observation and scored on
**held-out** cells, beat a constant (null) closure — i.e. is there recoverable, non-circular
env→rain-ratio signal? We answered it two independent ways:

- **(A) Transport-free identifiability map** (`scripts/marsh_identifiability_map.py`): a
  trivial OLS **floor** model at the exact 1° cells, with the E2's env-regime hold-out
  (hold out the upper-quartile env band, predict it, anomaly-R² vs the train mean), a
  **permutation null**, **BH-FDR** multiplicity correction, and **partial correlations** to
  separate Ω from temperature. No model, no transport, no GPU — an upper bound on
  feasibility. Uses Marsh's **own co-located** SST and Ω (from co-located DIC/AT/T/S).
- **(B) The differentiable transport-UDE E2** (`scripts/e2_real_calcite_eqpac.py`): the full
  windowed-BPTT closure fit through prescribed DB-1 dust + DB-2 velocity, learned-minus-null
  held-out anomaly-R², with the K_num ablation.

The two agree, which is the point: (A) bounds what is *in the data*; (B) shows the machinery
recovers it.

## 2. The data upgrade that was load-bearing

**Marsh et al. 2025** (PANGAEA 10.1594/PANGAEA.987673) — the updated successor to Daniels/
Poulton 2018, +400 CP measurements (n=3145 finite CP/PP), with co-located carbonate
chemistry. It does **not** add eqpac cells (34 either way) but densifies natl (26→33) and
the high-latitude bloom regions. Same-config controlled comparison at natl:

| natl config (Ω-split, default) | cells | learned | null | DELTA |
|---|---|---|---|---|
| Daniels 2018 | 26 (19/7) | +0.359 | +0.594 | **−0.235** |
| **Marsh 2025** | 33 (24/9) | +0.289 | +0.043 | **+0.245** |

The learned value is similar (+0.36 vs +0.29); the **null** swings (a small-n instability —
see caveats), and the Marsh split leaves the closure room to add skill.

## 3. Results

### 3a. The identifiability map (transport-free floor, BH-FDR over 9 tests, α=0.1)

| region | axis | n | hold-out anomaly-R² | perm-p | verdict |
|---|---|---|---|---|---|
| Nordic/Iceland | **SST** | 27 | +0.74 | 0.001 | **IDENTIFIABLE** |
| S.Atl/Patagonian | **Ω** | 14 | +0.86 | 0.001 | **IDENTIFIABLE** |
| N.Atlantic bloom | **Ω** | 26 | +0.69 | 0.006 | **IDENTIFIABLE** |
| natl (AOI) | SST | 29 | +0.22 | 0.070 | dies under FDR |
| Nordic/Iceland | Ω | 13 | +0.38 | 0.082 | dies under FDR (single-cell artifact) |
| S.Atl/Patagonian | SST | 42 | −0.40 | 0.782 | no |
| GLOBAL | Ω | 48 | −0.57 | 0.818 | no |
| GLOBAL | SST | 212 | −0.23 | 0.933 | no |
| N.Atlantic bloom | SST | 44 | −1.08 | 0.965 | no |

**Three survive multiplicity correction: N.Atlantic bloom (Ω), Patagonian/S.Atlantic (Ω),
Nordic/Iceland (SST). Global is null on both axes.**

### 3b. Ω vs temperature (partial correlations on matched cells — the confound test)

Ω and SST are collinear within every region (r = +0.52 to +0.83), so a marginal Ω hit could
be temperature in disguise. Partial-r isolates unique signal:

| region | n | r(Ω,SST) | r(y,Ω\|SST) (p) | r(y,SST\|Ω) (p) |
|---|---|---|---|---|
| N.Atlantic bloom | 26 | +0.52 | **−0.34 (0.096)** | −0.16 (0.434) |
| Patagonian/S.Atl | 14 | +0.83 | **−0.59 (0.035)** | +0.01 (0.981) |
| GLOBAL (in-sample) | 48 | +0.74 | **−0.41 (0.004)** | +0.22 (0.130) |
| Nordic/Iceland | 13 | +0.64 | −0.38 (0.219) | −0.13 (0.677) |

**Where Ω and temperature can be separated, Ω_calcite carries the unique signal and
temperature carries none** (S.Atl p=0.035, global in-sample p=0.004; SST|Ω never
significant). Consistent with the literature carbonate mechanism (Ridgwell 2007; CESM/
PISCES). **But** it is a tendency, not universal: in Nordic neither is separable (n=13,
collinear) and the FDR-identifiable axis there is SST.

### 3c. The transport-UDE E2 (natl, Marsh, ~9 held-out cells)

All three configs are **positive**, all **flat in kh**:

| config | learned | null | DELTA | K_num ladder (50/200/800) |
|---|---|---|---|---|
| N1 default (Ω-split) | +0.289 | +0.043 | +0.245 | 0.245 / 0.303 / 0.259 |
| N2 regularized (hidden=4, wd=0.01) | +0.375 | +0.043 | +0.332 | 0.332 / 0.294 / 0.314 |
| N3 SST-split | +0.244 | −0.045 | +0.289 | 0.289 / 0.289 / 0.289 |

learned (+0.24 to +0.38) ≈ the transport-free cell ceiling (natl Ω +0.36, SST +0.37). The
K_num ladder is **flat** — transport is inert in this surface-scored rollout — so it does
**not** discriminate local-vs-transport (see §5).

**Significance of the E2 signal (followup #2, addressed):** because transport is inert, the
transport-E2 delta provably tracks the transport-free hold-out at the same natl cells, so a
permutation null on that hold-out is a valid significance test for the E2 signal without a
multi-hour UDE-refit loop. That gives **natl Ω +0.36, perm-p=0.011** and **natl SST +0.37,
perm-p=0.011** — significant; **eqpac Ω −0.41 (p=0.61) and eqpac SST +0.03 (p=0.27)** — not
significant (`scripts/probe_marsh_env_rainratio.py`, cell-level). A fully rigorous
permute-and-refit-the-UDE null remains a nice-to-have but would only re-confirm this.

### 3d. eqpac — why it failed, and its proper scope

eqpac transport-E2: default −1.064, regularized −0.583, SST-split −1.843 (all fail).
Cell-level ceiling (cache env): eqpac Ω −0.41, SST +0.03. eqpac is data-sparse and
env-uniform (warm, high-Ω, iron-limited). **Important scope:** Marsh has ~0 co-located
carbonate chemistry below 23°N, so eqpac is **untestable on the Marsh-Ω axis** — the
negative uses the model `.pt` cache env, so it is *suggestive*, not a demonstrated
observation-derived null.

## 4. The defensible statement

> In the Marsh et al. 2025 direct, Darwin-independent CP:PP compilation, cell-binned
> log PIC:POC carries real out-of-regime hold-out skill — recovered by both a transport-free
> OLS floor and the full differentiable transport-UDE — in several cold high-latitude
> coccolithophore-bloom regions but **not globally**: on the Ω_calcite axis the North
> Atlantic bloom (+0.69, perm-p 0.006) and Patagonian/S.Atlantic (+0.86, p 0.001) beat the
> basin-mean null (both survive BH-FDR); Nordic/Iceland is **SST**-identifiable (+0.74,
> p 0.001). Where Ω and temperature can be separated, Ω carries the unique signal
> (partial-r: S.Atl p=0.035, global in-sample p=0.004; SST never). This is a **local**
> (env→ratio, transport-inert) rain-ratio closure, **non-circular** because the target is
> ¹⁴C-incubation calcite production. It is a map of *where a real closure has signal to
> recover* — not a validated closure and not a settled single driver.

## 5. Retracted over-reaches (honesty — the verifier caught these)

1. **NOT "E2 PASSED."** N2's nominal pass (delta>0 AND K_num-shrinks) is a **flag
   technicality**: the ladder is flat (0.332/0.294/0.314), "shrinks" fired because
   0.332 ≥ 0.314 after dipping. Transport is inert in this rollout, so the K_num control is
   **toothless** here (it was designed to catch numerical passes assuming transport moves
   the scored cells; it does not). The locality conclusion rests on **one** valid argument
   (transport-free OLS ≈ full-transport learned), not two.
2. **NOT "Ω, not temperature, is THE driver"** in general — only where separable (N.Atl
   bloom, S.Atl, global in-sample). Nordic is SST-driven; the two are confounded elsewhere.
3. **NOT "not identifiable in eqpac"** as a demonstrated negative — eqpac is *untestable* on
   the Marsh-Ω axis (§3d).
4. **NOT "transport closes the surrogate gap"** — the signal is **local** (transport inert).

## 6. Caveats that must travel with this result

- **Small n:** validation sets are ~4–9 held-out cells; hold-out R² sometimes exceeds
  in-sample R² (S.Atl +0.86 vs +0.62) → high-variance point estimates, not stable magnitudes.
- **Linear = floor:** the map bounds *where* signal exists; it is not a validated closure.
- **The transport-E2 deltas have no permutation null** (the map's OLS does); the runner
  numbers are now committed (`d78a210`) but the deltas were from local jobs.
- **Ω/SST collinearity** (r 0.5–0.83) — "Ω-driven" is clean only in the N.Atl bloom + S.Atl.
- **Box-fragility:** Patagonian sign-flips under a +5° northward shift; do not quote the
  N.Atl-bloom SST=−1.08 as a stable number (q-specific). Only the *relative* Ω>SST result is
  robust (Ω identifiable in 9/9 box shifts vs SST 4/9).
- **Carbonate/units correct but not load-bearing:** the µmol/kg→mmol/m³ ×1.025 conversion is
  right, and the hold-out test is rank/affine-invariant in the predictor, so the Ω result
  depends only on the carbonate-chemistry **rank ordering** — any monotone carbonate proxy
  gives the same split (do not oversell a calibrated Ω).

## 6a. Literature context — independent corroboration AND a caution

**Marañón et al. (2016), *Limnol. Oceanogr.* 61(4):1345–1357, "Coccolithophore calcification
is independent of carbonate chemistry in the tropical ocean"** (Malaspina 2010
circumnavigation; tropical Atlantic/Indian/Pacific; co-located primary production +
calcification + PIC + **full carbonate chemistry**; co-authors incl. W.M. Balch and
C. Pelejero). Their result: the CP/PP ratio and cell-specific calcification were **largely
constant across Ω = 1.5–6.5 and pH = 7.6–8.1** — calcification independent of carbonate
chemistry *in the tropics*.

This cuts two ways for our map:

- **Corroborates the tropical/global null.** We found the rain ratio Ω-**un**predictable
  globally and (from Marsh) untestable at eqpac. An independent in-situ study across a wide
  saturation gradient finds exactly no Ω dependence in the tropics. Our null is now backed by
  published field data, not just an absence in one compilation.
- **Cautions the "Ω-driven" mechanistic reading in the bloom regions.** Marañón's *controlled*
  study found no *causal* Ω effect even across a wide Ω range. So our North-Atlantic-bloom Ω
  correlation is plausibly **Ω acting as a proxy for the bloom regime** (species composition,
  nutrient/light state), not causal carbonate chemistry — consistent with the Ω/SST/bloom
  collinearity in §3b/§6. The honest reading is **"Ω is the best regional *predictor*,
  causality unresolved,"** not "Ω is the mechanistic driver." The regional split (env-predictive
  in cold bloom regions, not tropics) is itself coherent and may reflect a
  bloom-assemblage-vs-tropical-assemblage difference rather than a universal Ω response.

**Data that would convert eqpac from untestable to a tested negative:** the Malaspina 2010
dataset (Marañón 2016; co-located tropical CP/PP + carbonate); JGOFS EqPac (Balch & Kilpatrick
1996); or — fastest, no new data — **co-locating GLODAPv2.2016b OmegaC** (a public
observation-derived climatology) to the Marsh tropical calcite points (followup #4).

## 7. Followups (before this is publishable)

1. ~~Add a **permutation null on the transport-E2 delta** (parity with the map).~~
   **DONE** via the transport-free surrogate (valid because transport is inert): natl signal
   perm-p=0.011 (§3c). A permute-and-refit-UDE null would only re-confirm it.
2. Build a **rollout config where transport actually moves the scored cells** so a K_num
   sweep can genuinely discriminate local vs transport-mediated (currently trivially flat).
3. **Spatial-block bootstrap** for Nordic/Patagonian (respect 1° autocorrelation; confirm
   stability to MIN_CELLS and ±5° box shifts).
4. **GLODAP co-location** to give eqpac a *tested* Ω negative on observation-derived env,
   not the model cache.
5. Build proper env caches for the bloom AOIs (N.Atl bloom ~61 cells, Patagonian ~62) to run
   the transport-E2 in the regions the map says are identifiable, not just natl.

## 8. Ω-vs-bloom-proxy (partial-out biomass) — a partial answer to Marañón

`scripts/marsh_omega_vs_bloom.py`: on the Marsh cells with co-located ratio + Ω + SST + Chl-a,
partial correlation of log(CP/PP) with Ω controlling for temperature and biomass (log Chl-a):

| region | n | r(y,Ω) | Ω\|SST (p) | Ω\|Chl (p) | Ω\|SST,Chl (p) |
|---|---|---|---|---|---|
| N.Atl bloom | 25 | −0.56 | −0.43 (0.04) | −0.56 (0.00) | **−0.42 (0.05)** |
| Nordic | 13 | −0.54 | −0.38 (0.22) | −0.47 (0.13) | −0.23 (0.49) |
| S.Atl/Patagon | 14 | −0.79 | −0.59 (0.04) | −0.71 (0.01) | −0.13 (0.68) |
| GLOBAL | 46 | −0.44 | −0.41 (0.01) | −0.52 (0.00) | −0.40 (0.01) |

Cell-binned with Marsh in-situ env, Ω survives controlling for temperature AND biomass in the
N.Atlantic bloom (p=0.05) and globally in-sample (p=0.01), but collapses in Patagonian
(p=0.68). This looked like partial support for a carbonate reading — but §9 shows it does not
survive the env-source robustness check, so it is not load-bearing.

## 9. ROBUSTNESS — the positives do not survive (the decisive check)

Two independent checks, run after the map, deflate the region-specific positives.

**(a) GLODAP env swap** (`scripts/marsh_glodap_identifiability.py`). Co-locating the public,
observation-derived **GLODAPv2.2016b OmegaC** climatology to every Marsh point (so env exists
everywhere, including eqpac's ~128 previously-untestable points) and rerunning the identical
hold-out:

| region | axis | n | hold-out R² (GLODAP) | vs Marsh-env |
|---|---|---|---|---|
| **eqpac** | Ω | 32 | +0.18 (p=0.095, dies FDR) | (was untestable) |
| N.Atlantic bloom | Ω | 59 | **−2.27** (p=0.98) | was +0.69 |
| Patagonian/S.Atl | Ω | 62 | **−1.07** (p=0.92) | was +0.86 |
| natl (AOI) | Ω | 34 | **−2.09** (p=0.98) | was +0.36 (cache env) |
| tropics / GLOBAL | Ω/SST | 131/446 | null | null (robust) |

The nulls (tropics, global, eqpac) are robust across env sources; **the positives invert.**

**(b) In-situ env agreement + point level.** At the 129 N.Atlantic-bloom carbonate points:
`corr(Marsh in-situ Ω, GLODAP climatology Ω) = 0.24` (the two env sources barely agree — a
bloom's in-situ Ω, DIC-drawn-down, is not the annual mean), and `corr(log ratio, in-situ Ω) =
0.011` — **no point-level Ω→ratio relationship**, exactly Marañón 2016. The binned +0.69 is a
Simpson's-paradox-like aggregation artifact on 26 cells.

**Conclusion:** the region-specific identifiability positives are small-n / aggregation /
env-source artifacts and do **not** constitute a robust finding. The defensible result is the
**NULL** — real direct calcite observations do not reliably constrain an Ω-driven rain-ratio
closure at these sample sizes — consistent with Marañón 2016. eqpac is now *tested* (weak,
FDR-non-significant), not untestable. The transport-E2 +0.245 is within small-n instability.
This is an identifiability-**limits** result: a clean, honest bound on what real calcite obs
can (cannot) constrain, which is itself the reportable Track-2 science (see §10 for the iron
counterexample, a *distinct* mechanism that completes the map).

## 10. Iron counterexample — a SECOND, distinct non-identifiability mechanism

`scripts/geotraces_glodap_identifiability.py`: the same env-regime hold-out floor (GLODAP env,
permutation, BH-FDR) on **GEOTRACES IDP2025 surface dissolved iron** (4472 points, ~1300
1-deg cells — *dense*, unlike calcite). Result: **DFe concentration IS env-predictable** where
the sample is large — GLOBAL Ω +0.14 (perm-p 0.000, 1214 cells), tropics SST +0.28 (p 0.000,
406 cells), N.Atl-subpolar SST +0.68 (p 0.014); null in the small-cell regions. Robust
(hundreds–thousand cells, p≈0), not small-n.

But env-predictability of the **concentration** does **not** identify the **scavenging rate**:
DFe concentration is a low-information projection of `scav_rat` (Tagliabue 2016; and the
Track-1 sloppiness/profile-likelihood result). A scavenging closure fit to held-out DFe would
therefore "work" (the observable is fittable) with an **equifinal, meaningless** `scav_rat`.
Concentration skill ≠ rate identifiability — the **information wall** — and because iron is
dense, it is **structural / observability-limited, NOT data-limited.**

**Demonstrated directly through the transport model** (`scripts/iron_scav_rat_profile.py`,
`scripts/slurm/run_iron_wall.sbatch`, H200 job 8252388). A 2-D (`alpfe`, `scav_rat`) sweep,
forward-rolling DFe to quasi-steady state on the real eqpac observing footprint (26 GEOTRACES
cells) against a **self-twin** target (model DFe at Carroll, so it is reachable — isolating
the degeneracy from the iron-starvation confound): the best fit recovers the truth
(`alpfe`=0.99, `scav_rat`=7.9e-7), but the `scav_rat` profile (min misfit over `alpfe` at each
`scav_rat`) is **flat within +0.02 log-MSE across a 32× range** (1e-7 … 3.2e-6), with best
`alpfe` rising 0.77 → 1.63 to compensate. **`scav_rat` is unidentifiable over 32×** — the
source offsets the sink; the information wall, shown numerically. (The GEOTRACES-target variant
additionally pins `alpfe` at the grid max: with the real, ~200×-low DB-1 dust the model is
iron-starved and cannot reach observed DFe — the DB-1 transport-supply issue, a *distinct*
problem from the degeneracy.)

**The two together are the Track-2 result — an identifiability MAP by mechanism:**

| closure param | observable | why NOT identifiable |
|---|---|---|
| calcite `R_PICPOC` | PIC:POC (≈ the param) | **data-limited** — observable ≈ param, but obs too sparse/noisy (null; Marañón-consistent) |
| iron `scav_rat` | DFe concentration (≠ the param) | **observability-limited** — observable densely env-predictable but a low-info projection of the rate → equifinal (information wall) |

The honest, novel Track-2 science: *which* of Darwin's uncertain closures real observations can
constrain, and — the useful part — the *distinct reasons* they cannot.

Related: `2026-07-09_e2_calcite_preregistration.md`, `2026-07-07_deep_review_e2_readiness.md`.
