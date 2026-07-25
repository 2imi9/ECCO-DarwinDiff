# Two-anchor OSSE — the alpfe↔scav_rat break is VERIFIED (conditional) (2026-07-22)

Decisive test from the Fable joint-inversion methods synthesis: does {dust-deposition SOURCE anchor + 234Th
export-FLUX SINK anchor} break the rank-1 alpfe↔scav_rat degeneracy? Self-twin OSSE, steady-state upper-ocean Fe
box with Darwin's fixed-ligand free-iron scavenging, export E as the lumped-removal nuisance.
Script: `scripts/analysis/two_anchor_osse.py`.

## Verdict: (a-) BREAK CONDITIONAL — verified, with the partition tax
| obs set | E | \|ρ(alpfe,scav)\| | CRLB(log scav) | reading |
|---|---|---|---|---|
| DFe only | — | singular | ∞ | rank-1 null (the ridge), scav_CV 1.12 |
| +Dust anchor | pinned | 0.75 | 0.45 | **dust cleanly pins alpfe** (source axis collapses) |
| +Th flux | pinned | 0.26 | 0.17 | Th flux pins the sink — IF export pinned |
| +Th flux | **free** | 0.00 | **∞** | export nuisance destroys scav (partition tax) |
| **+Dust +Th flux** | **pinned** | **0.195** | **0.164** | **BOTH identified** (ρ 1→0.2, scav_CV 0.14) |
| +Dust +Th flux | free | — | ∞ | scav still confounded with export |

## What it means (honest)
1. **The degeneracy IS breakable.** Two out-of-manifold anchors take alpfe↔scav_rat from rank-1 (CRLB ∞) to both
   individually identified (|ρ| → 0.195, scav recovered to CV 0.14). This is the core wall of the whole project,
   verified breakable in an OSSE.
2. **alpfe is the cheap, unconditional win.** The soluble-Fe deposition anchor pins alpfe REGARDLESS of the export
   nuisance — data-in-hand (GA03/MERRA-2/EMIT), out-of-manifold, no partition needed.
3. **scav_rat's break is CONDITIONAL on the export partition.** The 234Th flux is lumped (scavenging + export); with
   export E as a free nuisance, scav_rat stays confounded (CRLB ∞). Pinning E — via the UVP5 particle field + POC
   flux — recovers scav_rat. The "partition tax" the Fable methods workflow flagged is real and load-bearing.
4. Consistent with everything else this session: DFe alone (and the too-flat v05 profile,
   [[2026-07-22_column_osse_result]] / profile-fidelity MIXED) is combination-only; the break needs the two
   independent measurement TYPES ([[data_acquisition_roadmap]] items: dust anchor + Black/Cochran flux + Fox/Rufas
   remin + UVP5 for the partition).

## Caveats
Idealized analytic box (arbitrary units) — proves the identifiability GEOMETRY (rank 1→2 under the two anchors +
the partition), not real-data recovery. Real confounds (Fe:C uptake variability, ~5–15 effective-N sink
determinations, deposition uncertainty) are being pressure-tested in the running open-problems Fable workflow
(wzugg5lld). Next: run against the real box forward + push to cluster for the n≥50-seed / parameter-sweep record.
