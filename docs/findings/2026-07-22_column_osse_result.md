# OSSE self-twin: does a 1-D column break alpfe↔scav_rat? — RESULT (2026-07-22)

The cheap go/no-go from the bottleneck solution map ([[2026-07-22_iron_bottleneck_solution_map]]), run on a
synthetic self-twin so the identifiability GEOMETRY is isolated from real-data confounds. Script:
`scripts/analysis/column_osse_identifiability.py` (pure numpy/scipy, no external data). Idealized LINEAR iron
column: surface dust source (alpfe) + first-order scavenging sink (scav_rat) + prescribed mid-depth
remineralization + vertical diffusion (kz); 25 m grid resolves the ~56 m e-folding depth.

## Verdict: (a-) — the profile breaks the PRIMARY degeneracy, but is not self-sufficient
The vertical DFe profile carries the information that separates the dust SOURCE from the scavenging SINK — the
0-D box cannot. But the profile then trades the alpfe↔scav_rat degeneracy for a NEW scav_rat↔remineralization
degeneracy. It works only if remineralization is prescribed (which v05 output supports).

## The numbers (CRLB on log10 scav_rat; <0.3 decades = identifiable)
| Fit | CRLB(log scav) | scav recovery CV | reading |
|-----|----------------|------------------|---------|
| 0-D box (surface scalar) | 4.2e6 | 0.97 | rank-1 null — unidentified (ridge, as documented) |
| 1-D column (kz, remin known) | 0.005 | 0.004 | scav_rat pinned to ~0.4% — degeneracy broken |
| column + kz nuisance | 0.005 | — | survives an unknown vertical diffusivity |
| column + kz + **remin** nuisance | **inf** (4th Fisher eig = 0) | — | scav_rat↔remin0 becomes an EXACT null |

Box Fisher eigenvalues [800, 2.8e-14] (rank-1). Column [53272, 40] — the second eigenvalue is bounded away
from zero, i.e. genuinely rank-2. The regime scan (scav 0.05–20 /yr, Damköhler 36–14000) shows the column is
better-conditioned as scavenging strengthens (sharper profile), and adds rank across the *entire* realistic
range — this is not a cherry-picked point.

## What it means (honest)
1. **The vertical profile is a real, regime-robust lever.** It moves scav_rat from CRLB 4.2e6 (box, along the
   ridge) to 0.005 (column) — the largest single identifiability gain any candidate produced. The mechanism is
   exactly the literature's: alpfe sets the profile AMPLITUDE, scav_rat sets its SHAPE (e-folding sqrt(kz/scav)).
2. **kz is not the binding confound; remineralization is.** An unknown vertical diffusivity does not break it
   (CRLB stays 0.005). An unknown deep remineralization source DOES — scavenging (deep sink) and remin (deep
   source) are exactly degenerate when both float. This reproduces Pham & Ito 2018 in miniature.
3. **The mitigation is in hand.** v05 outputs POC / POFe / primprod, so remineralization can be PRESCRIBED from
   the model's productivity fields rather than fitted — putting us back in the identifiable (kz-nuisance-only)
   regime. This makes "prescribe remin from v05" LOAD-BEARING, not optional, for the real-data column build.
   Residual risk: if the prescribed remin is biased, scav_rat absorbs the error (conditional recovery).

## Caveats (do not over-claim from a self-twin)
- Idealized LINEAR column. Real iron adds ligand-binding, colloidal pumping, variable-with-depth kz, and
  biological uptake — richer confounds than the single remin amplitude tested. The self-twin proves the
  geometry is favourable and identifies remin as the first binding confound; it does not prove real-data success.
- Recovery CV 0.004 is a best case (5% noise, correct model form). Real DFe profiles are sparser and the model
  is mis-specified; expect looser real recovery.

## Concrete next step
Build the real-data 1-D column fit with remin PRESCRIBED from v05 POC/primprod, kz prescribed or lightly fit,
fitting the full-depth GEOTRACES Fe_D profile + v05 3D FeT. Layer the aeolian-contrast weighting + dust prior
([[2026-07-22_iron_bottleneck_solution_map]] #1/#2) underneath to pin the alpfe leg. Predicted: scav_rat
tightens materially vs the surface-only box IF the prescribed remin is accurate — the one thing to validate first
is v05 remin fidelity against the observed profile curvature. This is a Track-2 (vertically-resolved surrogate)
build, correctly attributed. See [[project_paramlearner_improvement_plan]].
