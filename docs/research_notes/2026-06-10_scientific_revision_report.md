Confirmed: the c_chl40_posi15 n=20 retest (w6b, seeds 10-19, 10 JSONs) exists on disk, contradicting the closeout's L135/L142 "not yet retested." All key claims are now independently verified. I have what I need to write the report.

I've verified the load-bearing numbers directly: aggregated_v3.1.json gives **856 seeds / 86 configs** (canonical); the honest distribution (mode 2/6, mean 2.41, 79.7% at 2-3/6, 2/856 at 5/6, 0/856 at 6/6) is computable from that file alone; eqp5 alpfe Excellent = **7** (not 44); the "44" belongs to the eqp+natl n=80 run; and the c_chl40 n=20 retest exists on disk. Here is the report.

---

# DarwinDiff — Scientific-Revision Report

**Scope:** STATUS.md, public README (`origin/main`), `docs/findings/*.md`. Prepared for review by the author and Jon before any edits. Every number below is either quoted verbatim from the named file or recomputed by me from `docs/paper/figures/aggregated_v3.1.json` (the committed aggregation artifact) and, where noted, the run JSONs under `D:\runs\bcr_*`. I invent no values.

**Key arbiter established without ambiguity:** `docs/paper/figures/aggregated_v3.1.json` is the committed aggregation of the v3.1 sweep. It reports `total_seeds: 856`, `total_configs: 86`, and contains exactly 856 seed records. This settles the canonical denominator **from the documents alone — no `D:\runs` access is required** to fix the seed/config counts. I also recomputed every per-parameter and distribution figure below directly from it.

My independent recomputation from that JSON (load-bearing for §3):

| Quantity | Value (recomputed) |
|---|---|
| Seeds / configs | 856 / 86 |
| alpfe Cal+ | 717/856 = 83.8% |
| scav_rat Cal+ | 599/856 = 70.0% |
| Biggrow Cal+ | 400/856 = 46.7% |
| Smallgrow Cal+ | 243/856 = 28.4% |
| diatomgraz Cal+ | 84/856 = 9.8% |
| R_PICPOC Cal+ | 21/856 = 2.5% |
| iron-pair both Cal+ | 582/856 = 68.0% |
| Cal-count distribution | 0/6: 0.8%, 1/6: 11.2%, **2/6: 42.5% (mode)**, 3/6: 37.1%, 4/6: 8.1%, **5/6: 0.2% (2 seeds)**, **6/6: 0**; mean 2.41; 2-or-3/6 = 79.7%; ≤3/6 = 91.7% |

---

## 1. Accuracy corrections

### 1A. Numerical-consistency cluster — the seed/config denominator (HIGH)

The same v3.1 sweep is cited with **five seed totals (757, 837, 847, 856, 857)** and **three config counts (84, 85, 86)** across in-scope docs. This poisons every rate derived from it (the "0.24% break rate" is variously 2/837, 2/847, 2/857). **Standardize on 856 seeds / 86 configs** — the value in the committed `aggregated_v3.1.json`, corroborated by `docs/CLAUDE_PROJECT_CONTEXT.md` (L23, L91). All of `757/837/847/857` and `84/85` are wrong.

| Location | Verbatim | Fix to |
|---|---|---|
| STATUS.md L9 | "857 seeds across 86 configs" | 856 / 86 |
| STATUS.md L12 | "out of 847 seeds (0.24% break rate" | 856; rate 2/856 = 0.23% |
| STATUS.md L18 | "2/857 across all v3.1 work … 0 at 6/6 across 857 seeds and 86 configs" | 2/856; 856 / 86 |
| STATUS.md L29 | "a basin v3.1's 856-seed sweep never produced" | already 856 — keep |
| STATUS.md L35 | "v3.1 had 0 of 856" | already 856 — keep |
| STATUS.md L75 | "Across 757 seeds in v3.1" | 856 |
| README (origin/main), Reproduce | "857 seeds across 86 configs … 0/857 at 6/6" | 856 / 86; 0/856 |
| README (origin/main), Status & scope | "structural **5/6 ceiling** … 857 seeds across 86 configs" (Result-history table is fine) | 856 / 86 |
| v3.1_closeout.md L7 | "86 configs and 857 seeds … 2/857" | 856 / 86; 2/856 |
| v3.1_closeout.md L41–42 | "2 / 837 = 0.24%", "0 / 837" | 2/856 = 0.23%; 0/856 |
| v3.1_closeout.md L43–44 | "27 / 84", "40 / 84" | reconcile denominator to 86 (see §5 — the iron-pair-preservation denominator may legitimately be a config subset; needs the per-config manifest to confirm) |
| v3.1_closeout.md L134 | "837 seeds across 84 single-lever configs" | 856 / 86 |
| v3.1_closeout.md L138 | "847 total seeds in 85 configs" | 856 / 86 |

Note on internal split inside STATUS.md: L9/L18 (857) vs L29/L35 (856) vs L12 (847) — the file disagrees with itself three ways. Adopting 856 everywhere resolves it.

**Caveat I will not paper over:** `aggregated_v3.1.json` settles the *aggregate* at 856/86. It does **not** by itself prove the wave-by-wave bookkeeping (the closeout's wave table L28–32 sums to 89 configs; one Wave-4 config timed out at 6/10 seeds, L31; the c_chl40 n=20 retest "w6b" exists on disk but is excluded from every headline count). Whether 856 is "intended-860 minus the 4 missing Wave-4 seeds" or has another composition is **not derivable from the text** and would need a per-(config,seed) manifest enumeration of `D:\runs\bcr_*`. The headline number to cite is 856/86; the wave reconciliation is an §5 item.

### 1B. Numerical-consistency cluster — derived rates that round-mask the disagreement (HIGH/MEDIUM)

- **"0.24% break rate"** (STATUS L12; closeout L41) is computed against 847 and 837 respectively. 2/856 = **0.23%**. Recompute once on 856 and use 0.23% everywhere.
- **19/80 = 23.75%** quoted as "24%" (STATUS L25, L35) and "23.8%" (research note `2026-05-23_overnight_executed.md` L12/L23). LOW. Pick one rounding (recommend 23.8% to 1 dp, or 24% to 0 dp) and apply across STATUS and the research note. The README does **not** carry a percentage here, so it is not a party to this one.

### 1C. The eqp5 "44 Excellent" — arithmetically impossible AND wrong (HIGH)

STATUS.md **L36**, verbatim: "1-AOI eqpac | F2 base | 40/40 alpfe Cal+ **(44 Excellent)**; 40/40 diatomgraz Cal+; iron pair 0/40 | bcr_eqp5_20260523_0242/". 44 Excellent out of n=40 is impossible (Excellent ⊆ Cal+ ≤ 40).

**I scanned all 40 JSONs in `D:\runs\bcr_eqp5_20260523_0242`: alpfe = 33 Cal-grade + 7 Excellent = 40.** The true value is **7 Excellent**. The "44" was transcribed from the adjacent row's run: I scanned `D:\runs\bcr_5pft_eqp_natl_20260523_1058` (the 2-AOI eqp+natl n=80 row directly above, L35) and it is exactly 36 Cal-grade + **44 Excellent** = 80. **Fix: change "(44 Excellent)" → "(7 Excellent)" at L36.** The row's other figures (40/40 Cal+, 0/40 iron pair) check out against the data.

### 1D. README Smallgrow "below 25% everywhere" — false against the project's own data (HIGH)

README (origin/main), Status & scope, verbatim: "a structural **5/6 ceiling** … (`Smallgrow` stays below 25% Cal-grade everywhere)". I recomputed from `aggregated_v3.1.json`: **Smallgrow Cal+ = 243/856 = 28.4% aggregate**, with **42 of 86 configs ≥25%, 11 configs >50%, and two configs at 100% (a2_poc_020, a2_poc_050 = 10/10).** Single-AOI v2.x figures are 80–90% (STATUS L42/L54: 9/10; v2.8 findings L15: 9/10). "Everywhere/below 25%" is false on both the aggregate and per-config readings.

**Fix:** Drop the Smallgrow parenthetical. Smallgrow is *not* the dominant 5/6 blocker — STATUS's own diagnosis table (L77–85) names diatomgraz / R_PICPOC / alpfe+scav_rat. The genuinely near-unrecoverable params are **R_PICPOC (2.5%) and diatomgraz (9.8%)**. The same false "<25% everywhere" framing also appears in `docs/briefs/nvidia_nebius_audit_v3.1.1.md` L15 — correct both.

### 1E. v3.0 baseline "7/15" vs "5/15" (HIGH)

STATUS.md L40 and `docs/findings/pace_arc/meeting_deck` (L37, "7/15 … 47%") say **7/15 at 5/6**; `docs/findings/pace_arc/overnight_2026_05_19.md` L145 says **5/15** for "the project's best joint recovery". 7/15 is corroborated in ≥6 places (STATUS L40, deck L37, closeout L74, two notebooks, two scripts) and matches the "47%" cross-check (7/15 = 46.7%; 5/15 = 33.3%). **Standardize on 7/15; fix the lone 5/15 at overnight L145.** Caveat: L40 (PR #57) and L145 (PR #63 paired-anchor) may be *different configs* both labeled "best joint recovery" — disambiguate which is "best," and (see §2) attach the known v05-PIC-coincidence caveat to the PR #63 paired-anchor result.

### 1F. Cross-doc completeness gaps (MEDIUM/LOW)

- **Evidence-piece count: "five" (STATUS L18, README) vs "three" (closeout L132).** Not a contradiction of fact — the closeout predates v3.1.1 and the c_chl40 n=20 retest (its own L135 says c_chl40 "not yet retested"). **Fix:** update closeout L132–136 to the five-piece list, or add a dated note "this closeout predates v3.1.1 (PR #89)."
- **c_chl40 n=20 retest — closeout contradicts itself.** L58 reports the retest result ("0 additional 5/6, mean_cal 2.40, iron-pair 9/10; combined 1/20"); L135 and L142 say it was "not yet retested." **I confirmed the run exists on disk: `D:\runs\bcr_w6b_20260521_1018\c_chl40_posi15_n20\` (10 seeds, 10–19).** STATUS L14 already reports it. **Fix:** mark closeout L135/L142 resolved with the L58 result.
- **PER_AOI_DINN 2-AOI "3/10 at 5/6":** present in closeout L74 and dinn_design L147, absent from STATUS. STATUS's "falsified at 2-AOI" is the *correct* conclusion (3/10 < the 7/15 baseline), so this is a parity gap, not a contradiction. Optional: add the 3/10 figure to STATUS L57/L80 for parity. (I'd downgrade this finding from medium to low.)

---

## 2. Statistical / logic refinements

The project's own rule (STATUS L95): *"Recovery analyses report n=10 minimum and disclose seed variance … Avoid single-seed framing."* Several headline claims violate it or overreach.

1. **Two 5/6 single-seed events reified as composable "recipes" (STATUS L87).** L87 calls combining the two 5/6 interventions "the obvious next test for a **6/6 candidate**" — but the same document (L15, L121–128) already reports that exact composition (Wave 6) at **0/10 at 5/6, 0/10 at 4/6, mean_cal 2.00**. This is forward-looking framing of an already-falsified test built on two n=1 observations. **Tighten to:** *"Each 5/6 event is single-seed (1/20) and non-reproducing; the Wave 6 composition test (0/10 at 5/6, mean_cal 2.00) already falsified the combination and is consistent with both events being optimization noise."*

2. **"Five independent pieces of evidence" overcounts independence (STATUS L18).** Pieces (2) and (3) are the two single-seed events' own non-reproductions, and the "1/20" rate *includes the original winning seed in numerator and denominator*; piece (4) is the composition of those same two events. Three of the five are not independent of the two n=1 observations. The closeout's "three" (L132) is the more honest count. **Tighten:** present at most three independent lines — (a) 0/856 at 6/6 across the broad sweep, (b) the v3.1.1 AOI-ablation 0/80 at 5/6, (c) the two-event cluster (non-reproductions + Wave-6 composition) as **one** line — and stop calling the sub-items "independent."

3. **"5/6 ceiling" mislabels a 6/6 cap (STATUS L18, L73–89).** All five evidence items establish only **0 at 6/6**. The *reproducible* ceiling is 2/6 (iron pair, 38/40); the best-config ceiling is 4/6 (19/80 = 24% in eqp+natl); 5/6 occurs 2/856 times and never reproduces. Calling it a "5/6 ceiling" implies 5/6 is routinely achieved. **Tighten:** rename to a **"no-joint-6/6 cap"** and separate it from the "~5 effective constraints" claim (next point).

4. **"~5 effective constraints / 6th is residual sink" was retracted in the paper but survives in the live docs (STATUS L18/L57; closeout L9; CLAUDE_PROJECT_CONTEXT L97; cluster_roadmap L7).** Commit **0bfa15e** explicitly "replaced misleading 'approximately five effective DoF' claim with honest tier breakdown — 2 reliable (iron pair), ~1 partial (phyto growth), 2 essentially unrecovered." A ~5-constraint world predicts a 5/6 mode; the actual mode is **2/6 (42.5%)**. The per-param data (2 reliable: alpfe 84%, scav_rat 70%; ~1 partial: Biggrow 47%, Smallgrow 28%; 2 unrecovered: diatomgraz 10%, R_PICPOC 3%) behaves like ~2–3 effective constraints. **Retract "~5 effective constraints / residual sink" everywhere and replace with the tier framing.**

5. **n=200 ablation rates reported with no CI on n=40 subgroups (STATUS L22–27).** The "n=200" headline aggregates four unequal configs (40/80/40/40); the per-config rates (e.g. 0%, 75%, 95%, 24%) carry binomial CI half-widths of roughly ±7–15 pp at these n, none disclosed. **Tighten:** report each as count/n + CI (e.g. 3-AOI 95% = 38/40, 95% CI ≈ 83–99%), flag n=40 subgroups as small, and don't present "n=200" as a homogeneous sample.

6. **v2.4 "4/6 — project-first" has no n (STATUS L43).** It is a single-notebook (nb29) result per `v2.2_overnight_summary.md` L93. The adjacent v2.6 row discloses n=10; v2.4 discloses nothing — a direct L95 violation. **Tighten:** mark it single-seed and demote from the headline table, or add n + variance.

7. **Single-method, no independent validation — under-disclosed (README; STATUS).** Every rate is one pipeline (DINN→box) scored vs Carroll's published values; no independent estimator, no forward-Darwin held-out validation (STATUS L60, cluster-gated), block-CV deferred (`v3.0_multi_aoi_scoping.md` L111). README concedes "single-method recovery pipeline" but STATUS's "Known limitations" (L103–110) omits it. **Add a limitation** stating reported percentages quantify pipeline-vs-target agreement, not unbiased recoverability.

8. **Paired-anchor 5/6 is a known artifact, not flagged at the headline (STATUS L40).** `overnight_2026_05_19.md` L115–124 establishes the PR #63 paired-anchor 5/6 "works only because two independent errors cancel" (Darwin-v05 PIC bias × Carroll R_PICPOC coincidence). Where this result is presented as "best joint recovery," attach that caveat.

---

## 3. Proposed honest reframing (concrete wording)

These drafts lead with reproducible fixed-n rates, express the ceiling via reproducibility, report the honest distribution (commit 0bfa15e), and drop the cumulative-denominator wobble. All numbers are from `aggregated_v3.1.json` (recomputed) or verbatim STATUS rows; the one place a cumulative count is unavoidable uses 856/86.

### (a) STATUS.md — replacement for "Current state" headline block (L9–18)

> **Verified results from the v3.1 sweep set** (856 seeds across 86 configs; aggregation in `docs/paper/figures/aggregated_v3.1.json`, raw outputs in `D:\runs\bcr_*\`):
>
> - **Iron-pair recovery is reproducible: 38/40 (95%) at the F2 Basin C config** (POSI_W=1.0 + AOI_W_NATLSUBPOLAR=2.0 + AOI_W_SOUTHERNOCEANPAC=2.0 + CHL1_W_EXTRA=3.0), across four independent 10-seed batches (10/10, 10/10, 10/10, 8/10). This is the project's strongest reproducible claim.
> - **Per-parameter recoverability is a steep gradient, not a flat 5/6.** Across the 856-seed sweep: alpfe 84%, scav_rat 70% (the reliable iron pair); Biggrow 47%, Smallgrow 28% (partial phyto growth); diatomgraz 10%, R_PICPOC 3% (essentially unrecovered from v05 obs).
> - **The typical seed recovers 2 or 3 of 6 Carroll params** (mode 2/6 at 43%; 3/6 at 37%; 80% of seeds in the 2–3/6 band; mean 2.41). 4/6 is reached by 8% of seeds.
> - **The 6/6 cap is structural, stated by reproducibility:** 6/6 is **never observed** (0/856). 5/6 occurs in only **2 seeds (0.23%)** and **does not recur on retest** — `w2e_peraoi_lam0.1` 1/20 and `c_chl40_posi15` 1/20 — and the composition of the two 5/6 lever families (Wave 6) yields 0/10 at 5/6 (mean_cal 2.00), worse than either parent. The v3.1.1 AOI ablation independently produces 0/80 at 5/6.
> - **The best-config ceiling is 4/6, not 5/6:** the 2-AOI `eqp+natl` configuration reaches 19/80 (24%) at 4/6 — the project's highest 4+ rate — but never 5/6. AOI mix decides *which* 4 params recover; no mix lifts the cap to 6.
>
> **Framing:** this is partial recovery with a hard joint-6 cap, not "we get 5/6." Two parameters recover reliably, ~one partially, two are essentially unconstrained by current v05 observations. We characterize the cap as observational under-determination (the iron pair + phyto growth are the recoverable axes; diatomgraz and R_PICPOC lack independent constraints at the box-model scale), not as "~5 effective degrees of freedom."

### (b) Public README — replacement for "Status & scope" bullets and the "Reproduce" headline sentence

Status & scope:

> - **What works today:** the iron pair (alpfe, scav_rat) recovers reproducibly — **38/40 (95%)** at the Basin C config; two further parameters (Biggrow, Smallgrow) recover partially / config-dependently. The synthetic per-cell recovery demo runs end-to-end on a laptop / free Colab T4.
> - **Honest recovery profile:** across the 856-seed v3.1 sweep, the typical seed recovers **2 or 3 of 6** Carroll parameters (mode 2/6; mean 2.41). Per-parameter Cal-grade rates: alpfe 84%, scav_rat 70%, Biggrow 47%, Smallgrow 28%, diatomgraz 10%, R_PICPOC 3%.
> - **Known-blocked:** a structural cap on *joint* Carroll-6 recovery — **6/6 is never observed (0/856)** and 5/6 does not reproduce on retest (1/20 at each of two configs). diatomgraz and R_PICPOC are the near-unrecoverable params; the scav_rat–alpfe degeneracy and the 2-basin PIC mutex are the mechanisms. Full evidence in [STATUS.md][status_url].
> - **Caveat:** single-GPU (RTX 5090) prototype; **single-method pipeline** (no independent estimator or forward-Darwin held-out validation yet). Full-ocean recovery, time-resolved fitting, and the Track-2 emulator are gated on cluster access.

Reproduce headline sentence:

> The headline finding (a **structural cap on joint Carroll-6 recovery**: 0/856 at 6/6 across 86 configs of 3-AOI joint training, with 5/6 occurring in only 2 seeds and never reproducing on retest) and its full evidence table live in [STATUS.md][status_url].

---

## 4. Recommended fixed evaluation protocol

To end the moving-denominator problem, cite **one canonical, re-derivable statistic** going forward, in addition to the honest aggregate:

- **Config:** F2 Basin C, 3-AOI (`POSI_W=1.0`, `AOI_W_NATLSUBPOLAR=2.0`, `AOI_W_SOUTHERNOCEANPAC=2.0`, `CHL1_W_EXTRA=3.0`, `PER_AOI_DINN=0`, shared DINN + AOI-ID channel).
- **Seed batch:** the four contiguous 10-seed batches, seeds 0–39 (the four directories that back the 38/40 claim).
- **Metric:** iron-pair joint Cal+ rate = **38/40 (95%)**, with per-batch counts (10/10, 10/10, 10/10, 8/10) and a Wilson 95% CI (≈ 83–99%).
- **Why this one:** it is fixed-n, single-config, maps to named run directories, and is the project's only reproducible-at-n≥40 result. Cite it as *the* primary number; cite the 856-seed aggregate (mode 2/6, 0/856 at 6/6) as the secondary "no joint 6/6" statement; and cite each 5/6 event as its own 1/20, so no claim depends on the contested cumulative total.

**Manifest recommendation:** generate a single per-(config, seed) manifest (one row: config, seed, bcr_* path, 6-band verdict, k-of-6) from `aggregated_v3.1.json` and commit it. Every rate in STATUS/README/closeout should then cite a filterable column of that manifest rather than a prose count. (The 19/80 "4/6" and "R_PICPOC ∧ diatomgraz both Cal+ = 0 in v3.1" claims become trivially checkable this way, independent of N.)

**One pre-flight fix to the protocol's source list:** STATUS L39 names only **three** of the four batch directories (seeds 10-19, 20-29, 30-39); the seeds-0-9 batch is missing, and the closeout (L40) uses a *different* naming scheme (plain `seeds0-9…`). I confirmed on disk that only three `*basinC*` batch dirs exist (`arc6_basinC_seeds10-19`, `w2f_basinC_seeds20-29`, `e_basinC_seeds30-39`) — the seeds-0-9 batch that supplies the first 10/10 is **not present under any name**. The 38/40 *aggregate* is consistent across both docs, but the 4th batch's source is currently untraceable. **This needs run data / author memory to resolve** (see §5).

---

## 5. Open items needing run data or Jon's judgment

1. **Wave-by-wave reconciliation to 856/86.** The aggregate is settled (856/86), but the wave table (closeout L28–32) sums to 89 configs and the Wave-4 timeout (6/10 seeds, L31) plus the excluded w6/w6b retests mean the per-wave bookkeeping does not obviously reconstruct 856. *Needs a per-(config,seed) enumeration of `D:\runs\bcr_*`.* Does not block adopting 856/86 as the headline.

2. **The 4th iron-pair batch (seeds 0–9).** STATUS L39 lists only 3 dirs; no `*basinC*` seeds-0-9 directory exists on disk under either naming scheme. *Which run supplies the first 10/10 (and the 8/10) batch? Needs author memory or a disk re-scan.* The 38/40 number itself is consistent; only its source provenance is incomplete.

3. **Closeout iron-pair-preservation denominators "27/84" and "40/84" (L43–44).** These may legitimately be a config subset (single-lever, iron-pair-eligible configs), not the full 86. *Whether 84 is a real subset or a typo for 86 needs the per-config manifest.* I did not assume; I flagged it.

4. **PR #57 vs PR #63 "best joint recovery" (7/15).** Are STATUS L40 (PR #57 baseline) and overnight L145 (PR #63 paired-anchor) the *same* run or two configs both crowned "best"? 7/15 is the corroborated fraction either way, but disambiguating which config is "best" — and whether to attach the v05-PIC-coincidence artifact caveat — *is a judgment call for Jon*, since it bears on how the project's best pre-v3.1 result is presented in the paper.

5. **Whether to fold the c_chl40 n=20 retest (w6b, 10 seeds) into the headline denominator.** It exists on disk and is reported in STATUS L14 / closeout L58 but excluded from the 856 aggregate. *Author/Jon decision:* keep headline = the 856 single-lever sweep and report retests separately (cleaner), or fold to 866/87. Recommend the former, stated explicitly.

6. **The "~5 effective constraints" → tier-framing retraction (points §2.4, §2.3).** The paper already retracted it (0bfa15e); propagating that into STATUS/closeout/CLAUDE_PROJECT_CONTEXT/cluster_roadmap is a wording change, but *whether to also rename "5/6 ceiling" to "6/6 cap" project-wide* is a presentation decision for Jon — it touches the paper's framing, not just the live docs.

**Settleable from documents alone (no run data, no Jon needed):** the canonical 856/86 count and every per-param/distribution number in §3 (from `aggregated_v3.1.json`); the eqp5 "44 → 7 Excellent" fix (I verified against the eqp5 and eqp+natl JSONs); the Smallgrow ">25%" refutation; the "0.24% → 0.23%" recompute; the evidence-count and c_chl40-retest staleness in the closeout; and the §2 framing tightenings.

**Files referenced:** `C:\Users\Frank\OneDrive\Desktop\Github\ecco-darwindiff\STATUS.md`, `…\docs\findings\v3.1_closeout.md`, `…\docs\paper\figures\aggregated_v3.1.json`, README on `origin/main`; run data verified at `D:\runs\bcr_eqp5_20260523_0242`, `D:\runs\bcr_5pft_eqp_natl_20260523_1058`, `D:\runs\bcr_w6b_20260521_1018`.