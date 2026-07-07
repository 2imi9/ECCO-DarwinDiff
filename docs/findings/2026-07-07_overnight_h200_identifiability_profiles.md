# Overnight H200 identifiability profiles — VERIFIED (2026-07-07)

Ran the profile-likelihood identifiability diagnostic (`scripts/identifiability_sloppiness.py`, shared-θ over
the 3 AOIs eqpac/natlsubpolar/southernoceanpac, `grid=11`, `opt-steps=600`, config
`run_identifiability.sbatch`: RATIO_W=2, RATIO_MAX=2, POSI_W=1, AOI weights 1/2/2, DARWIN_IC=1) on **Explorer
H200** for the trio params. **All 3 jobs `COMPLETED` clean (~52 min each; job IDs 8211101/8211102/8211103;
outputs `/projects/schultz/qi.zim/runs/dd-fim_82111{01,02,03}.out`).** Fresh H200 reproduction — this is the
overnight cluster verification.

## Verdict thresholds (from the script, lines 391-398)

`rel_span = (maxLoss − bestLoss)/bestLoss` over the profiled grid:
- **FLAT** `< 0.05` — structural non-identifiability (param invisible; new observable needed). *(the diatomgraz signature)*
- **SHALLOW** `0.05–0.5` — weak practical non-identifiability (more same-type data helps only marginally).
- **CURVED** `≥ 0.5` — param **IS constrained** (routing/pooling/seeds licensed).

## Result

| Param | rel_span | Verdict |
|---|---|---|
| `alpfe` | **0.207** | SHALLOW — weakly constrained |
| `scav_rat` | **0.196** | SHALLOW — weakly constrained |
| `R_PICPOC` | **46.6** | **CURVED — genuinely constrained** |

## Interpretation (honest)

**The two IRON params are the sloppy/under-constrained pair; the calcite ratio is genuinely constrained.**
This is not a flat re-confirmation — it *maps directly onto today's meeting findings and Jon's papers*:

- `alpfe` / `scav_rat` SHALLOW ⇒ the global-θ likelihood is only weakly curved along iron. This is exactly
  **Tagliabue 2016** (Jon's reference): iron models agree on *concentration* but the *source/sink rate is
  under-constrained* — concentration doesn't sharply pin the iron rate. It also is the H200-confirmed form of
  the **`alpfe` honesty caveat**: its profile is flat/one-sided → *"consistent with a homogeneous forcing
  scalar, not sharply identified."*
- `R_PICPOC` CURVED ⇒ genuinely constrained, because it has a **direct calcite ratio anchor** (Daniels/`RATIO_W`).
  So identifiability tracks the *observational constraint*: sparse/indirect iron → sloppy; a direct ratio
  observation → constrained.

## Scope (do not overclaim)

- This is the **global shared-θ** profile lens. It **reproduces the known sloppiness** on fresh H200 runs and
  adds the iron-vs-calcite constraint contrast — a verification, plus a clean corroboration of Tagliabue.
- It is **not** the per-cell demonstration. The finding that `scav_rat`/`R_PICPOC` *require* per-cell (8/0, 9/0
  vs global-scalar) is the separate per-cell-vs-global ablation ([PR #158](https://github.com/2imi9/ECCO-DarwinDiff/pull/158),
  already verified). The two lenses together = the full picture: iron rate is globally sloppy *and* needs
  spatial structure; R_PICPOC is globally constrained by its anchor *and* needs per-cell routing.
- The shared-θ global optimum reproduced the known **"global fit prefers low `alpfe`"** behavior under full
  loss (θ\*: `alpfe`=0.082, 0.91 off Carroll 0.928; `scav_rat` 4.4e-7 0.27 off; `R_PICPOC` 0.033 0.23 off) —
  the loss-weighting signature from [[finding_ironpair_structural_diagnostic]], not a new result.
