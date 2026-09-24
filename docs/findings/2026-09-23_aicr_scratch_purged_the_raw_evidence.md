# AICR `/scratch` purged the raw outputs behind several headline numbers

**Date:** 2026-09-23 · **Cost:** read-only `ssh` listing, no compute · **Status:** live

## What was checked

`docs/findings/2026-08-13_results_manifest.json` lists 15 run directories. Eight of them live on
AICR `/scratch/qi_zim_neu`, which the cluster purges after 30 days. A read-only listing on
2026-09-23 found every one of those directories **present but empty** (`find -type f` returns 0):

| directory | what it held |
|---|---|
| `mvd/mvd_daniels`, `mvd/mvd_marsh` | the `R_PICPOC` compilation A/B, 50/50 → 30/50 |
| `mvdrep/mvd_daniels`, `mvdrep/mvd_marsh`, `mvdrep/mvd_prior` | its disjoint-seed replication, 98/100 → 50/100 |
| `sorep/so_rep` | the Southern Ocean `scav_rat` replication (job 352450) |
| `som/som_anchor`, `som/som_noanchor` | the Southern Ocean Marsh-anchor arms |

The same listing found these directories empty too, although the manifest does not name them:
`pcf` (job 408789, the 2026-08-20 province measurement), `alpfebound` (job 276927, the `alpfe`
bound experiment), `collapse`, `flagwin` and `kerg`.

## What survives

- **Local copies**, now backed up to the gitignored, OneDrive-synced
  `runs/_evidence_backup_2026-09-23/`: `n50e2k_percell_trio` (the flagship), `n50e2k_anchor_off`,
  `n50_anchor_off`, `collapse/collapse_n50`, the `ctrl_n50` runs, `so_only`, `so_rep`,
  `som_anchor`, and the `gs_obsonly` untrained priors.
- **Committed tables.** Every lost run's graded counts are in its dated finding note, and the
  province analysis's per-cell summaries are committed as
  `docs/findings/2026-08-20_province_dispersion_{flagship,soonly}.json`.

So no number is lost, but the Marsh A/B, the `alpfe` bound experiment, the Kerguelen and window arms,
and the province run can no longer be re-graded from raw per-seed files.

## What to do

- Treat AICR `/scratch` as a 30-day cache, not storage. Copy every run directory that a finding
  quotes to durable storage (local disk plus OneDrive, or Explorer `/projects`) when the finding is
  written.
- Before a manuscript claims that every number traces to a run directory, check that the directory
  still exists and is non-empty.
