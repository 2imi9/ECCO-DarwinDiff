# Two-anchor iron inversion — RED-TEAM (honest bounds) (2026-07-22)

Adversarial Fable workflow (5 lenses, all CONFIRMED, no invented refs) on the two-anchor design. It TEMPERS
the OSSE "verified break" ([[2026-07-22_two_anchor_osse_verified]]): the OSSE proved the *geometry* (rank 1→2
with export pinned); the red-team bounds what REAL DATA delivers.

## Corrected claim (use this, not "point-identifies")
**The two-anchor design breaks the rank-1 degeneracy in DIRECTION (lifts the ridge into a bounded basin) and
bounds each parameter to a factor of a few — NOT point-identification.** alpfe is the decisive-direction (strong)
leg; scav_rat is honestly bounding, and combination-only until two data additions land.

## Why (paper-grounded)
- **scav_rat partition is systematically biased, doesn't average down with N.** Isolating scavenging = Th flux
  minus uptake minus export. Two killers: (1) cellular Fe:C varies ~40× (Twining 2021) and NPP×Fe:C on bulk POC
  OVER-subtracts uptake ~2× because 58–74% of surface particulate C is detrital, not living (Bates & Hawco 2026)
  — needs an ATP/SXRF *living-biomass* proxy; this bias is SYSTEMATIC. (2) Particulate-Fe export is
  lithogenic-contaminated (Th partition coeff varies ~20×, Le Gland 2019) — needs particle-class-resolved Fe:Th.
  Residual = NET scavenging (Bacon-Anderson reversible), must be labeled a net rate. **Expected scav_rat: factor
  ~2 posterior, combination-only until the living-fraction + particle-class data (which Darwin's POC/NPP fields do
  NOT supply) are added.**
- **alpfe (source) bounds to factor ~2–3** — an absolute deposition row sidesteps the near-zero solubility model
  skill but still inherits the dust-field spread (observed solubility 0.02–98%, dust flux 3.5×).
- **Honest posterior width is partition-dominated (~factor 2), not the ~1.4 that N~10 counting stats suggest.**
  Report the Fe:C partition error propagated, not just Th counting statistics.

## Per-lever verdicts
- **δ56Fe iron isotopes: NO-GO for now.** Darwin's FIXED ligand freezes the scav-vs-colloidal-pumping split that
  carries the sink isotope signal (König & Tagliabue 2021); and uptake + scavenging fractionate dissolved δ56Fe
  the SAME direction → δ56Fe recreates the lumped-removal degeneracy. Its real strength is source apportionment,
  which the dust anchor already does out-of-manifold. Cost large (tracer doubling + 6–7 knobs). Gate behind a cheap
  OSSE (fixed-vs-dynamic-ligand ablation) before any port; hold as a v2 bet.
- **R_PICPOC: PARTIAL cross-check.** Size-fractionated PIC:POC (<53µm coccolithophore pathway, ~82% PIC, Subhas
  2023) = independent second calcite anchor with a different error structure from Daniels → adds rank, but it's
  standing-STOCK and needs a stock→export conversion. Daniels stays primary.
- **diatomgraz: COMBINATION-ONLY.** bSi:POC conflates diatom silicification (Si:C quota) with grazing palatability
  because silicification IS the anti-grazing defense (Pančić 2019: 6× silica → 4× less grazing) — both push bSi
  the same way. Needs a diatom RATE anchor (³²Si production + dilution grazing), which the stock datasets lack.
- **Fe' row: keep OUT** — under fixed ligand it's a deterministic function of DFe, zero rank. Only INDEPENDENT
  ligand data (CLE-AdCSV) would help.

## Dust-anchor construction (the strong leg — build first)
Use **Xu & Weber 2021 (GBC, 10.1029/2021GB007049) Al-inverse soluble-Fe deposition** (constrained by in-ocean
dissolved Al, so disciplined by the same class of data the inversion sees — decouples alpfe from atmospheric
dust-model spread). Place the anchor in a **dust-DOMINATED AOI (Saharan N. Atlantic)** where Al-inverse/GESAMP/GA03
agree best; set Fe:Al regionally from GA03 aerosol solubility (~1–2% Saharan); enter as a DISTRIBUTION (per-cell
variance = Al-inverse ensemble + GESAMP envelope). **Citation caution:** 37.2±11 Gmol/yr in Xu & Weber is soluble
ALUMINUM, not Fe — do not cite a specific soluble-Fe number to that paper without checking the Al→Fe conversion source.

## Build order
1. **Dust source anchor (Xu-Weber way)** — highest value, data in hand, decisive on source DIRECTION. The strong leg.
2. **Sink anchor** — build ONLY with (a) ATP/SXRF living-biomass uptake correction + (b) sinking-particle-class
   Fe:Th; propagate the Fe:C partition error; present scav_rat as BOUNDING (factor ~2 net rate), never point-ID.
3. **R_PICPOC size-fractionated cross-check** — low effort, independent 2nd calcite anchor beside Daniels.
4. **δ56Fe fixed-vs-dynamic-ligand OSSE** — cheap decision gate, expectation NO-GO, confirm before any v2 port.
5. **Do NOT build:** same-DFe Fe' row; diatomgraz-from-bSi:POC; full δ56Fe port ahead of the OSSE.

## Note on the running B200 self-twin
The B200 real-box validation uses SYNTHETIC anchors (clean partition) → it will confirm the GEOMETRY (rank 1→2),
which is OPTIMISTIC vs real data. It validates the design's identifiability structure; this red-team bounds the
real-world magnitude. Do not report the B200 self-twin number as real-data recovery.
