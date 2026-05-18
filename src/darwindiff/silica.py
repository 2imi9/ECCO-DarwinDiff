# -*- coding: utf-8 -*-
"""Biogenic silica (bSi) diagnostic for the 15-tracer 2-layer Carroll-6 box.

Computes steady-state bSi_1 and bSi_2 fields from the existing diatom state,
without extending the integrator's tracer vector. Diatoms uptake silicate
and build siliceous frustules; when they die or are grazed, the frustule
material enters the particulate biogenic silica pool, sinks, and slowly
dissolves at depth back to silicic acid.

**Why a diagnostic, not a tracer.** Extending the 15-tracer state to 17
tracers would invalidate every cached IC file (`darwin_ic_cache_*.npz`),
retest every integrator path, and revalidate v2.7 / v2.8 results. The
2-layer box already assumes steady state (200 forward-Euler steps at
dt=0.25 day = 50 days is ~5x the sinking timescale 1/W_SINK = 10 d), so
the bSi pools relax to their steady values within the integration window
regardless. Computing bSi diagnostically from the final state is
exact at steady state and a good approximation otherwise.

**Production.** Only diatoms produce biogenic silica. At each cell:

    bSi_production = R_SI_C * (mort_diatom + graze_diatom)
    mort_diatom    = M_LIN * P_diatom + M_QUAD * P_diatom^2
    graze_diatom   = g_diatom * G0_GRAZE * P_diatom
                     (where g_diatom = params[I_DIATOMGRAZ])

The grazing term carries `diatomgraz` directly, so bSi production has
the `diatomgraz` parameter in it.

**L1 steady state.** Surface bSi sinks at W_SINK (same as POC):

    0 = R_SI_C * (mort + graze) - W_SINK * bSi_1
    => bSi_1 = R_SI_C * (mort_diatom + graze_diatom) / W_SINK

**L2 steady state.** Subsurface bSi receives sinking flux from L1,
dissolves slowly, and continues sinking to deep:

    bsi_sink_in_L2 = W_SINK * bSi_1 * (h1 / h2)
    0 = bsi_sink_in_L2 - R_SI_DISSOL * bSi_2 - W_SINK * bSi_2
    => bSi_2 = W_SINK * bSi_1 * h1 / [h2 * (R_SI_DISSOL + W_SINK)]

With defaults (h1=50, h2=950, W_SINK=0.10/d, R_SI_DISSOL=0.015/d),
bSi_2 / bSi_1 ~ 0.046 — most biogenic silica in the model lives in L1.

**Why this constrains `diatomgraz`.** Absolute-units bSi observation
anchors bSi_1 magnitude, which equals R_SI_C * (mort + graze) / W_SINK.
mort depends only on P_diatom (constants from carroll6); graze depends
on P_diatom * g_diatom. With P_diatom spatial pattern already
constrained by the Chl1 z-score loss, absolute bSi pins
P_diatom_absolute * g_diatom — and since the chl normalization
quasi-pins absolute biomass (within the z-score scale ambiguity),
g_diatom becomes identifiable.

**Literature values.** R_SI_C = 0.13 mol Si / mol C (Brzezinski 1985 —
typical diatom Si:C; varies 0.10-0.40 under Fe limitation). R_SI_DISSOL
= 0.015 / day at thermocline temperatures (Tréguer & De La Rocha 2013).
"""

from __future__ import annotations

import torch

from darwindiff.carroll6 import G0_GRAZE, M_LIN, M_QUAD, W_SINK

R_SI_C: float = 0.13
"""Si:C molar ratio in diatom-produced biogenic silica. Brzezinski 1985,
typical value; the actual ratio varies 0.10-0.40 across regimes (higher
under Fe limitation per Hutchins & Bruland 1998). The Carroll/Darwin
calibration target is the global mean R_PICPOC, so a single global R_SI_C
matches that abstraction level."""

R_SI_DISSOL: float = 0.015
"""Subsurface bSi dissolution rate (1/d). Tréguer & De La Rocha 2013
review; slower than POC remineralization (R_REMIN=0.05/d in the v2.7
2-layer model). Silica frustules dissolve over ~70-day timescales in the
upper twilight zone."""


def diagnostic_bsi_steady(
    p_diatom: torch.Tensor,
    g_diatom: torch.Tensor,
    h1: float = 50.0,
    h2: float = 950.0,
    w_sink: float = W_SINK,
    r_si_c: float = R_SI_C,
    r_si_dissol: float = R_SI_DISSOL,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Compute steady-state biogenic silica fields in both layers.

    Args:
        p_diatom: diatom biomass [N_seeds, H, W] (mmol C / m^3). Read from
            the integrated state at ``state[I_DIATOM]``.
        g_diatom: `diatomgraz` parameter [N_seeds, H, W] from
            ``bounded_params(...)[I_DIATOMGRAZ]``. Per-cell, per-seed.
        h1, h2: layer thicknesses (m). Defaults match carroll6_5pft_2layer.
        w_sink: particulate sinking rate (1/d). Default matches carroll6.
        r_si_c: Si:C ratio (mol Si / mol C). Default 0.13.
        r_si_dissol: subsurface bSi dissolution rate (1/d). Default 0.015.

    Returns:
        ``(bsi_1, bsi_2)`` — both tensors shape [N_seeds, H, W],
        units mmol Si / m^3. Differentiable through p_diatom and g_diatom
        (g_diatom carries the diatomgraz gradient).
    """
    mort_diatom = M_LIN * p_diatom + M_QUAD * p_diatom * p_diatom
    graze_diatom = g_diatom * G0_GRAZE * p_diatom
    production = r_si_c * (mort_diatom + graze_diatom)
    bsi_1 = production / w_sink
    bsi_2 = (w_sink * bsi_1 * h1) / (h2 * (r_si_dissol + w_sink))
    return bsi_1, bsi_2
