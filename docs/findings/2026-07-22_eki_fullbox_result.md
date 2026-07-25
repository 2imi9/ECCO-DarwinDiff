# Full-box EKI: estimator-independence confirmed on the real geo1 box (2026-07-22)

The #187 deliverable, Fable-vetted and built as `scripts/analysis/eki_fullbox_trio.py`: promote the
analytic EKI prototype to the REAL geo1 box + real anchors, as a **method-independence** check (closes the
"single-method / DINN+autograd artifact" reviewer attack), NOT a discovery. Result JSON:
`docs/findings/2026-07-22_eki_fullbox_trio.json`.

**Setup.** Reuse `identifiability_sloppiness._import_runner()` to expose the exact geo1 bundles + `aoi_loss`
(real GEOTRACES surf/sub DFe + Daniels CP:PP; NB23_N_EPOCHS=0, no training). Forward
`G(u[3,J]) -> obs[d=8,J]` = per-AOI mean-log {surface DFe, subsurface DFe, PIC:POC at Daniels cells};
trio {alpfe, scav_rat, R_PICPOC} varied in log space, growth held at Carroll. Run the unit-tested
`eki_core.eki` (J=256, 30 iters, wide log-uniform prior). CPU/GPU-local on the 5090.

## Result — EKI matches backprop on all three trio params

| param | EKI posterior mean | Carroll | rel.off | band | backprop (flagship n=50) |
|---|---|---|---|---|---|
| **alpfe** | 0.999 | 0.928 | 0.08 | **Cal-grade** | 49/50 Cal-grade |
| **R_PICPOC** | 0.036 | 0.0425 | 0.14 | **Cal-grade** (≈ real Daniels geomean 0.034–0.039) | 50/50 Cal-grade |
| **scav_rat** | 2.1e-7 | 6.0e-7 | 0.65 | **Loose** | 25/50 (the weak binding leg; equals the trio joint 25/50) |

**A derivative-free ensemble estimator, run through the real box + real anchors, reaches the SAME
identifiability verdict as backprop:** alpfe and R_PICPOC recover to Cal-grade (method-independent — the
recovery is not a DINN/autograd artifact), and scav_rat stays Loose (estimator-independent confirmation
that it is the binding leg). This is the concrete answer to "is the per-cell recovery a single-method
artifact?" — no; two independent estimators (gradient DINN + derivative-free EKI) agree.

## Honest caveats (per the Fable adjudication)

- **This is method-independence, NOT discovery.** It grades against Carroll and uses the same anchors, so
  it adds no new information — it confirms the estimator does not manufacture the result.
- **The EKI ensemble *spread* is not a calibrated posterior.** `eki_core.eki` is the ILS-2013 inversion
  *optimizer* (no inflation/localization); its ensemble collapses, so the reported CVs (alpfe 2%,
  scav_rat 6.4%, R_PICPOC 3.6%) and the alpfe↔scav_rat "sloppy axis" (which lands ~along alpfe here) are
  NOT quantitative posterior widths — only the **point estimates** are load-bearing. A calibrated
  credible interval (which would be the genuinely new deliverable) needs the EKS/sample stage (CES), which
  is future work. Do not quote the EKI CV as an uncertainty.
