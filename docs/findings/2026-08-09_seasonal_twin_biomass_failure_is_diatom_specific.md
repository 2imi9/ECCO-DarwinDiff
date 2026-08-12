# The seasonal twin's biomass failure is a diatom-specific grazing sink

**Date:** 2026-08-09 | **Status:** measured and independently verified, bounded
to the reduced box | **Optimizer:** none | **Cluster compute:** none |
**Preregistration:**
`docs/findings/2026-08-09_prereg_seasonal_twin_phytoplankton_process_budget.md`

## Result in one sentence

The chemical-restoring seasonal targets do not lose phytoplankton generally:
they drive only the diatom pool toward zero, without one clamp event, because
the box's biomass-independent linear grazing term supplies 57% to 68% of the
diatom's cycle-1 gross loss in every AOI under both fixed and astronomical
light. The four ungrazed PFTs remain nonzero.

## 1. Evidence boundary

The diagnostic reran the two previously frozen target constructions at Carroll
truth:

- one-year chemical-only restoring with constant `LIGHT=1`;
- the identical closure with preregistered astronomical monthly light.

Both used all three canonical AOIs, `dt=0.25 d`, 122 steps/month, eight cycles,
Eppley temperature growth, and exactly zero phytoplankton restoring. Per-cell,
per-PFT process tensors were retained for cycles 1, 2, 7, and 8. No parameter
was fit or changed.

The independent verifier checked 1,786,512 raw tensor cells and reproduced:

- `net = growth - linear mortality - quadratic mortality - grazing`;
- `actual increment = net + clamp correction`;
- `final - initial = actual increment`;
- exact zero phytoplankton closure;
- both prior target reports with maximum absolute state difference **0.0**.

Maximum normalized residual was `6.46e-6` for the process identity and
`3.70e-6` for the inventory identity. The compressed tensor bundle, summary,
and verification receipt are:

- `docs/findings/2026-08-09_seasonal_twin_phytoplankton_process_budget.pt.gz`;
- `docs/findings/2026-08-09_seasonal_twin_phytoplankton_process_budget.json`;
- `docs/findings/2026-08-09_seasonal_twin_phytoplankton_process_budget_verification.json`.

## 2. The collapse happens in cycle 1 and only to the diatom

Cycle-1 diatom inventory retention (`final / initial`) is:

| construction | EqPac | North Atlantic | Southern Ocean |
|---|---:|---:|---:|
| chemical + fixed light | 1.13e-6 | 2.81e-4 | 1.20e-3 |
| chemical + astronomical light | 1.23e-6 | 5.04e-8 | 1.44e-7 |

Thus the first year removes 99.88% to 99.999995% of the diatom inventory. The
floor does not cause this result: clamp correction, raw-negative events, and
clamp event fraction are all exactly zero in every recorded cycle and cell.

The other four PFTs do not collapse. Under fixed light their cycle-8 means are
about 0.417-0.421 for the large-eukaryote pool and 0.692-0.698 for each small
pool. Under astronomical light they remain about 0.356-0.420 and 0.598-0.697.
The target gate's tiny Chl1 values are therefore a diatom-specific failure, not
a shorthand for all phytoplankton.

## 3. Grazing is the dominant diatom loss in all six cells

Cycle-1 diatom loss composition is:

| construction | AOI | signed balance | linear share | quadratic share | grazing share |
|---|---|---:|---:|---:|---:|
| fixed light | EqPac | -0.121 | 0.135 | 0.191 | **0.674** |
| fixed light | North Atlantic | -0.085 | 0.125 | 0.251 | **0.624** |
| fixed light | Southern Ocean | -0.101 | 0.133 | 0.205 | **0.662** |
| astronomical | EqPac | -0.139 | 0.137 | 0.180 | **0.683** |
| astronomical | North Atlantic | -0.343 | 0.138 | 0.178 | **0.685** |
| astronomical | Southern Ocean | -0.043 | 0.115 | 0.314 | **0.571** |

The production algebra explains why this can become an absorbing near-zero
state:

```text
dP_diatom / dt = P * (
    MU_DIATOM * f_Fe * light * gamma_T
    - M_LIN
    - diatomgraz * G0_GRAZE
    - M_QUAD * P
)
```

At Carroll truth, the biomass-independent loss floor is
`M_LIN + diatomgraz*G0_GRAZE = 0.05 + 0.83003*0.30 = 0.299009 d-1`.
Because the box has no explicit zooplankton state, that grazing pressure does
not relax as grazer biomass changes; it remains linear in diatom biomass down
to arbitrarily small `P`. Zero is therefore absorbing.

This is consistent with, but sharper than, the standing surrogate-gap record:
Darwin carries two prognostic zooplankton groups, while this box absorbs them
into a single linear diatom-only loss term.

## 4. Why the aggregate preregistered branch is `mixed-or-other`

The preregistration intentionally classified the all-PFT total first. That
total becomes nearly balanced by cycle 2 because the four non-diatom pools
settle to nonzero states while the diatom contributes almost no remaining
flux. At cycle 8, a ratio of tiny diatom fluxes also looks close to one and
`final / initial` can look stable from one near-zero year to the next. Those
late ratios do not reverse the cycle-1 inventory loss.

Accordingly, the frozen decision tree returns `mixed-or-other` and directs the
analysis to the per-PFT attribution. The per-PFT attribution is unambiguous:
grazing is the dominant diatom loss in all six AOI-by-light cells.

## 5. Consequence for issue #239

Do not tune astronomical-light amplitude or the chemical-restoring timescale.
Do not launch a recovery factorial or a B200 cost gate. The next bounded test
must ask whether the diatom-free state is structurally inevitable under the
linear grazing closure and then scope a physically defensible grazer or biomass
transport mechanism. Direct restoring to Darwin diatom biomass is not
authorized because it would make the target construction circular.

This finding does not establish a Darwin grazing budget, show that light is
irrelevant in Darwin, or choose endpoint versus time mean. It explains only why
these two reduced-box seasonal target constructions fail their Chl1 gate.
