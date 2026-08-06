# `scav_rat` does NOT transfer to Kerguelen-Crozet — and the basin was not the regime I thought it was

**Date:** 2026-08-06 · **Job:** 287354 (`dd-kerg`, 10 array tasks) ·
**Artifacts:** `/scratch/qi_zim_neu/kerg/{kg_base,kg_null}` · **AOI:** `kerguelen` (−65..−45 N,
40..80 E), new · **Template:** single-AOI `so_only`, the one that established `scav_rat` in the
Southern Ocean · `verify_run` **exit 0**.

**Verdict: NO. Kerguelen-Crozet has MORE dissolved-iron coverage than the Southern Ocean Pacific
box where `scav_rat` is established — 18/20 one-degree bins against 13/14 — and recovers
`scav_rat` 2/50 under the geometric collapse (10/50 arithmetic, and the geometric reading is the
required one). `alpfe` is 0/50, worse than its own untrained null. The failure mode is the rank-1
degeneracy: both iron parameters slide DOWN together, which is the ridge direction.**

**Two corrections to my own reasoning fall out of it, and both are in §6.** The basin is NOT "the
same HNLC scavenging-dominated regime" I selected it on — its surface iron median is 0.54 nM
against southernoceanpac's 0.08 nM, nearly 7x, because Kerguelen-Crozet is the classic natural
iron-FERTILISATION region. And the obvious rescue hypothesis, that it lacks the vertical iron
structure the Southern Ocean result depends on, is FALSE: it looks true when you pool samples
(ratio 0.91) and is false per station (2.00, an ordinary gradient). The pooled statistic inverts
the answer, and that trap is worth more than the hypothesis was.

## 1. The measurement

Single-AOI, flagship config otherwise, n=50 trained + 50 untrained. Counts are
arithmetic / geometric / median against the architecture-matched null:

| band | `scav_rat` | `alpfe` | `R_PICPOC` |
|---|---|---|---|
| ≤0.10 | 0 / 0 / 0 | 0 / 0 / 0 | 1 / 1 / 1 |
| ≤0.20 | 2 / 0 / 1 | 0 / 0 / 0 | 2 / 2 / 2 |
| ≤0.30 | 5 / 1 / 1 | 0 / 0 / 0 | 2 / 2 / 2 |
| ≤0.40 | **10 / 2 / 2** | **0 / 0 / 0** (null 11/10/9) | 2 / 3 / 2 |

The only cell with a small P is `scav_rat` 10/50 arithmetic at 0.40 (P = 0.00067). Under the
**geometric** collapse — the required reading for `scav_rat` — it is **2/50, P = 0.81**. This is
exactly the pattern the pooler rule exists to catch, and it is why the arithmetic number is not
quotable on its own.

`alpfe` at 0.40 is **0/50 against an untrained 11/50**: training makes it worse than not training.

## 2. The failure mode is the ridge

Median recovered value as a multiple of Carroll:

| | `alpfe` | `scav_rat` | `R_PICPOC` |
|---|---|---|---|
| untrained null | 0.540x | 2.452x | 17.783x |
| trained | **0.157x** | **0.348x** | 2.348x |

The fit *moves* — a long way, in every parameter — so this is not a dead optimisation. It moves
**both iron parameters down together**: `alpfe` 0.540 → 0.157 and `scav_rat` 2.452 → 0.348.

That is the rank-1 alpfe↔`scav_rat` degeneracy direction. Reducing the source and reducing the
sink together leaves surface dissolved iron roughly unchanged, so the observable cannot tell the
pair apart, and the fit slides along the ridge until it hits something else. It overshoots Carroll
on both and lands below the band.

The Southern Ocean single-AOI run, on the same template, does not do this. Whatever pins the ridge
there is not present here, and it is not iron coverage — Kerguelen has 40% more.

## 3. Why this was worth running anyway

The hypothesis was specific and reasonable: `scav_rat` is established in one HNLC,
scavenging-dominated basin, so a second basin of the same regime with **more** iron data should
also work. If it did, `scav_rat` would go from "regionally identifiable in one place" to a
property of the regime — a real frontier extension rather than a robustness check.

It does not. That is a cheap, decisive answer to a question that would otherwise have been assumed
either way, and it is the second independent line of evidence today that **iron data density does
not predict recovery** (the first being that eqpac holds the most bins of any AOI and recovers
`scav_rat` least).

## 4. Confounds, stated

- **The calcite anchor is thin here.** `n_daniels_cells_per_aoi` is **6** for Kerguelen, against 34
  in eqpac and 26 in natlsubpolar. `R_PICPOC` is 2/50 where it is 50/50 in the three-AOI runs, and
  6 cells is the obvious reason. So this run is not a fair test of `R_PICPOC`, only of the iron
  pair — though a weak `R_PICPOC` is unlikely to explain `alpfe` going below its own null.
- **Single-AOI removes the multi-AOI constraint.** The published trio result is a joint fit over
  three basins, and multi-AOI is documented as load-bearing. The comparison that matters is against
  the Southern Ocean **single-AOI** run, which used the same template and did recover — so the
  single-AOI setting is controlled for, not a confound.
- **No Black anchor.** `BLACK_ALPFE_W` was off, so `n_black_programs_per_aoi` is 0. That was
  deliberate: Kerguelen's Black cluster has σ/value 7.29 against the 0.73 needed, so the term would
  have been inert. It is not the missing pin.
- **One submission, no replication.** A null result needs replication less urgently than a positive
  one, but it has none.

## 5. What this leaves

`scav_rat` remains regionally identifiable in exactly one basin, the Southern Ocean Pacific, and
that result still has no replication of its own. The regime hypothesis is refuted for the one
alternative basin the data supports.

The open question moves to **what pins the ridge in southernoceanpac and not in Kerguelen**. The
depth result (2026-07-31: `so_sub` 33/50 vs `so_surf` 14/50) says the Southern Ocean signal is
vertical structure in dissolved iron, so the obvious next check was whether Kerguelen lacks it.
**That check was run — see §6. It does not lack it, and the hypothesis is dead.**

## 6. Addendum — the vertical-structure explanation was tested and does NOT hold

§5 proposed the obvious next check: the Southern Ocean signal is depth structure in dissolved iron
(2026-07-31, `so_sub` 33/50 vs `so_surf` 14/50), so does Kerguelen lack that structure?

**Measured, and the answer depends entirely on how you aggregate — which is the finding.**

Pooling all QC-good `Fe_D_CONC` samples in each AOI and taking the ratio of the subsurface
(50–1000 m) median to the surface (≤50 m) median:

| AOI | pooled sub/surf | surface median |
|---|---|---|
| southernoceanpac | 2.84 | 0.08 nM |
| eqpac | 2.53 | 0.17 nM |
| natlsubpolar | 2.04 | 0.29 nM |
| **kerguelen** | **0.91** | **0.54 nM** |

That looks decisive — Kerguelen alone has no vertical gradient, and it is the one basin that fails.
It is also **wrong**. Computing the ratio **per station** and taking the median over stations that
sample both layers:

| AOI | stations with both | median ratio | IQR | frac > 1.5 |
|---|---|---|---|---|
| southernoceanpac | 14 | 2.42 | [1.46, 2.73] | 0.71 |
| eqpac | 27 | 2.30 | [1.71, 3.22] | 0.89 |
| natlsubpolar | 13 | 2.28 | [1.48, 2.82] | 0.69 |
| **kerguelen** | **32** | **2.00** | **[1.05, 3.94]** | **0.62** |

Kerguelen has a perfectly ordinary per-station vertical gradient. The pooled 0.91 is a pooling
artifact: Kerguelen is a natural iron-fertilisation region (the KEOPS/CROZEX plateau and island
wakes), so it carries many high-surface-iron stations that inflate the pooled SURFACE median, while
a different subset of stations dominates the pooled SUBSURFACE median. Pooling across stations with
very different iron regimes compares two different populations and inverts the answer.

**So the vertical-structure hypothesis does not explain the Kerguelen null.** What survives is
weaker and should not be over-read: Kerguelen has the lowest per-station median gradient of the
four (2.00 against 2.28–2.42) and by far the widest spread (IQR 1.05–3.94 against ~1.3 wide
elsewhere), and the smallest fraction of stations with a clear gradient (0.62 against eqpac's 0.89).
Whether that heterogeneity is what defeats a shared per-cell network is speculation and is not
tested here.

**The trap is worth more than the hypothesis.** Anyone comparing iron vertical structure between
AOIs from this file will reach for the pooled ratio, get 0.91 for Kerguelen, and conclude the basin
is vertically homogeneous. It is not. Compute it per station.

Related, and it undermines the premise this AOI was chosen on: Kerguelen's surface iron median is
**0.54 nM**, against 0.08 nM in southernoceanpac — nearly 7x. It was selected as "the same HNLC,
scavenging-dominated regime", and it is not iron-limited in the same way at all. That is a domain
error on my part in choosing it, independent of how the fit behaved.
