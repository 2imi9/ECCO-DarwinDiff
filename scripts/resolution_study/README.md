# Resolution-study analysis tooling (2026-07-12)

Scripts that produced the resolution-sharpening + 5-AOI generalization findings
(`docs/findings/2026-07-12_resolution_sharpening.md`,
`docs/findings/2026-07-12_resolution_generalization_5aoi.md`). They operate on the per-run JSON
summaries emitted by `scripts/emulator_poc.py --out ...` and the `--dump-fields` .npz field files.

- `analyze_grid.py <glob>...` — group runs by config (grid/modes/width/forcing/k/epochs), print
  mean±std skill, per-tracer skill, rollout stability. The primary aggregation table.
- `common_grid_control.py <native_fields>... <coarse_fields> --aoi-bounds latmin latmax lonmin lonmax`
  — the load-bearing like-for-like resolution test: area-average native predictions onto the 1° grid
  and compare absolute physical RMSE against the 1°-origin model on the identical field + persistence
  baseline. This is what showed the z-skill "sharpening" was capacity, not resolution.
- `horizon_decay.py <label> <glob>...` — per-step rollout skill decay (native vs 1°) from the stored
  6-step rollout MSE; shows resolution gives no durable multi-step benefit (and worsens npac).
- `read_results.py <glob>...` — quick per-run + aggregate skill summary.

Runs live on B200 `~/emulator_poc/runs/` (180+ JSONs). All results LOCAL; self-consistency vs
ECCO-Darwin v05, not real obs.
