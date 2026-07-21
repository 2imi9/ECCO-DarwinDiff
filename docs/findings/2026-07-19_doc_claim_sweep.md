# Documentation claim sweep — 2026-07-19 (PARTIAL)

> **READ THIS HEADER BEFORE USING THE REPORT BELOW.**
>
> **Nothing here has been applied.** Every "Replace with" block is a *proposal*. The repo is
> unchanged by this sweep.
>
> **The sweep is INCOMPLETE and its coverage is not uniform.** 114 docs were inventoried and fanned
> out over 29 audit groups, each finding adversarially verified by a separate agent instructed to
> default to refuting. Of 575 agents, **147 completed and 428 errored on a session usage limit**.
> Failed verifications return null and are filtered out rather than counted as confirmed — so the
> confirmed findings are sound, but **absence of a finding for a document means nothing**. Whole
> files (`v2.1_phase1_glodap.md`, `v2.2_phase2.md`, `cluster_roadmap.md`, the `nvidia_nebius_*`
> set, `2026-06-21_full_compute_budget.md`, and many more) had every verifier fail. They are
> unaudited, not clean.
>
> **The counts in the report's own header are slightly wrong.** Its prose says "77 confirmed …
> 26 blockers · 41 major · 10 minor". The structured result array says **75 confirmed — 27 blocker,
> 38 major, 10 minor**. Trust the structured numbers; the synthesising agent recounted by hand.
> (Recording this rather than silently fixing it: a miscount in the summary line of a document
> *about* miscounts is the same failure mode, one level up.)
>
> **Defect mix (structured):** stale-number 26 · contradicts-canonical-fact 20 · overclaim 18 ·
> uncited-gate-on-spend 6 · no-committed-artifact 5.
>
> **Most-affected files:** `2026-07-19_emulator_honest_bounds.md` (9), `CLAUDE_PROJECT_CONTEXT.md`
> (7), `2026-07-13_global_monthly_emulator.md` (7), `2026-07-14_emulator_loop.md` (6),
> **`README.md` (5)**, `rpicpoc_ratio_structural.md` (5), **`STATUS.md` (3)**.
>
> That README and STATUS.md — the public front page and the canonical results doc — carry 8
> confirmed defects between them is the headline, not the raw total.
>
> **Suggested order of work:** the 27 blockers in `README.md`, `STATUS.md`, `docs/index.md` and
> `CLAUDE_PROJECT_CONTEXT.md` first (highest readership, and `index.md` duplicates README's
> refuted calcite-port spend gate verbatim), then re-run the sweep after the limit resets to cover
> the ~74% of verifications that never ran.

---

# Documentation defect report — 2026-07-19 audit sweep

77 confirmed defects across 21 files. Each was adversarially verified (hedge check, historical-record check, artifact check) before landing here.

**26 blockers · 41 major · 10 minor**

The single largest cluster: a retracted claim was corrected in one place and left standing in the summary table, the glossary, the conclusion, and the sibling doc.

---

# BLOCKERS

## README.md

### `README.md:36` — overclaim
> The canonical results — including the first full six-parameter (6/6) recovery, with R_PICPOC unblocked by the `RATIO_MAX` ratio-target fix — and the known limits live in STATUS.md

**Why:** The 6/6 is real (`2026-06-24_rpicpoc_ratio_target_fix.md` L24, 3/10 seeds, verify_run-gated) but the source artifact's own title says "hits a structural ceiling" and L24 says "but NOT robust" — the README states it bare. It also calls this "the canonical results" while STATUS.md L11-13 frames the project as an identifiability study "not a '6/6 recovery' chase," L19 sets the honest target at 4 observable params, and L88-107 reports a 3-of-4 frontier with `diatomgraz` not recovered.

**Replace with:**
```markdown
The differentiable box model (`darwindiff.carroll6`), the per-cell networks (`darwindiff.networks`), and the ECCO-Darwin / GLODAP / GEOTRACES data loaders are all importable as the `darwindiff` package. Track 1 is framed as a surrogate-to-model **identifiability study** over the four observable parameters — the best operating point holds {`alpfe`, `scav_rat`, `R_PICPOC`} jointly in 7/10 seeds, with `R_PICPOC` unblocked by the `RATIO_MAX` ratio-target fix and `diatomgraz` not recovered on real data. The canonical results and the known limits live in **[STATUS.md][status_url]** and `docs/findings/`.
```

### `README.md:90` — stale-number
> A **structural 6/6 wall**: 0/856 seeds recover all six jointly across **856 seeds / 86 configs** — `R_PICPOC` (3%) is the lone unrecovered parameter. 5/6 now reproduces (above); breaking to 6/6 is the open problem.

**Why:** Contradicted by three sources including the README itself (L36). STATUS.md:113 states "`R_PICPOC` was never a '6/6 wall'"; `2026-06-24_rpicpoc_ratio_target_fix.md`:124 reports R_PICPOC 10/10 joint Cal; STATUS.md:104-107 names `diatomgraz`, not `R_PICPOC`, as the unrecovered parameter.

**Replace with (covers L90 and L91 in one edit):**
```markdown
- **Not a 6/6 chase — an identifiability study.** The honest target is **4 observable params** {`alpfe`, `scav_rat`, `diatomgraz`, `R_PICPOC`}; the growth pair {`Smallgrow`, `Biggrow`} is **unobservable by construction**, so it is excluded from the target rather than counted as a miss. The current frontier is **3-of-4**: the `geo1` operating point holds {`alpfe`, `scav_rat`, `R_PICPOC`} jointly in **7/10 seeds**.
- **`R_PICPOC` is no longer the blocker.** The earlier "structural 6/6 wall / needs the differentiable Darwin calcite port + native resolution" conclusion is **refuted** — both were tested and neither helped. The real causes were the absence of a direct real calcite observation (now supplied by the Daniels CP:PP / MODIS PIC anchor) and a contaminated Southern-Ocean ratio target (fixed by `RATIO_MAX=2`, giving `R_PICPOC` 10/10 joint).
- **`diatomgraz` is the unrecovered parameter** in the real-data sweep (best 4/10 = chance). It is constrained only through a steady-state biogenic-silica diagnostic back-solved from diatom biomass, and its profile likelihood is flat (span 0.039) without dense `POSi`. Adding the dense Darwin `POSi` (`TRAC16`) target recovers it **10/10** — a data-staging limit, not a structural wall.
```

### `README.md:91` — uncited-gate-on-spend
> ≥2-AOI recovery needs the differentiable Darwin calcite port + native resolution — not a box-scale estimator or seasonal lever.

**Why:** STATUS.md:113-115 quotes this exact phrase and marks it **refuted** — "both were tested and neither helped." Load-bearing on spend: `2026-06-21_full_compute_budget.md`:182 calls PORT "the only path to R_PICPOC / 6-of-6" and L248 says 6/6 "is gated *only* on" it. `docs/index.md:30` carries an identical uncorrected copy.

**Replace with:** (the bullet above, second item) — or standalone:
```markdown
≥2-AOI recovery was thought to need the differentiable Darwin calcite port + native resolution — that conclusion is **refuted**: both were tested and neither helped. The real blockers were a contaminated Southern-Ocean ratio target (fixed by `RATIO_MAX=2`) and the absence of a direct, real calcite observation; with both addressed `R_PICPOC` recovers and the first 6/6 lands — see [STATUS.md][status_url].
```
**Also fix:** `docs/index.md:29` (identical to README L36) and `docs/index.md:30` (identical to README L91).

---

## docs/CLAUDE_PROJECT_CONTEXT.md

> Note: this file is gitignored (`.gitignore:98`), untracked, and pasted verbatim into the claude.ai Project as live knowledge. It missed the 2026-06-27 archive sweep that banner-stamped every other doc carrying this framing. Edits land in the working tree only; do not `git add -f`.

### `docs/CLAUDE_PROJECT_CONTEXT.md:23` — stale-number
> **Structural 5/6 ceiling** confirmed across **1056 seeds** (856 v3.1 sweep + 200 v3.1.1 AOI ablation). Zero seeds at 6/6 in any configuration. Five independent pieces of evidence support parameter conservation as the binding limit.

**Why:** "Zero seeds at 6/6 in any configuration" is now false (`2026-06-24_rpicpoc_ratio_target_fix.md` TL;DR item 4: "6/6 achieved for the first time (3/10 seeds, verified)"). The mechanism — parameter conservation — was a data-pipeline bug: the SO PIC:POC target was contaminated by near-zero-POC cells (mean 4.7e7), collapsing the SO ratio loss to ~0. Only the historical count survives. Reinforced at L88, L202, L219.

**Replace with:**
```markdown
- **The "structural 5/6 ceiling" is RETRACTED (2026-06-24).** The historical sweep count stands — 0/1056 seeds reached 6/6 across the v3.1 (856-seed) and v3.1.1 (200-seed) sweeps — but the *mechanism* does not. The block was `R_PICPOC`, and its cause was a **data-pipeline bug, not parameter conservation**: the Southern-Ocean PIC:POC ratio-loss target was contaminated by near-zero-POC cells (per-cell `pic/poc` up to ~1e8, target mean 4.7e7), which inflated the loss-scale normalizer and silently collapsed the SO ratio term to ~0. Capping the target at a physical rain ratio (`RATIO_MAX=2`) recovers **`R_PICPOC` 10/10 joint Cal** (≈0.030–0.046 vs Carroll 0.0425), and **6/6 was achieved for the first time (3/10 seeds, verified)** — but is **not robust**. Do **not** claim a structural ceiling, "zero seeds at 6/6", or "parameter conservation as the binding limit". The current framing is a **surrogate-to-model identifiability study over 4 observable params** {`alpfe`, `scav_rat`, `diatomgraz`, `R_PICPOC`}; the growth pair {`Smallgrow`, `Biggrow`} is unobservable by construction and excluded from the target. The residual limit is a loss-landscape tradeoff, not undertraining (3000 epochs made `Biggrow` worse): you can robustly hold {`R_PICPOC`, iron pair, `diatomgraz`} **or** the growth pair, not all six. On real staged data the verified headline is the per-cell architecture being load-bearing — a per-cell DINN holds the trio {`alpfe`, `scav_rat`, `R_PICPOC`} 7/10 while a single global-scalar vector holds 0/10 (disjoint CIs). On `diatomgraz`: do **not** write that it "carries no observational signal" — its profile likelihood is flat (span 0.039) *without* dense POSi, it recovers 10/10 *with* dense Darwin POSi, and the bSi observable is a steady-state diagnostic back-solved from diatom biomass (i.e. circular).
```

### `docs/CLAUDE_PROJECT_CONTEXT.md:88` — overclaim
> ### The 5/6 ceiling — what's PROVED structural

**Why:** "PROVED structural" for a result later explained by a data-preprocessing bug. The five enumerated pieces of evidence at L90-96 all ran against the same contaminated SO target — correlated, not independent. Independently corroborated in-repo: `2026-06-10_scientific_revision_report.md`:92 ("'5/6 ceiling' mislabels a 6/6 cap … the reproducible ceiling is 2/6") and L94 (the "~5 effective constraints" mechanism at L97 was retracted in the paper at commit `0bfa15e` but survives here).

**Replace with:**
```markdown
### The 6/6 cap — an empirical bound over the configs tested, since partly broken

**Status: substantially superseded.** Treat the numbers below as the v3.1 1° sweep record, not as a structural law.

1. 0/856 seeds at 6/6 across 86 single-lever 3-AOI configs — an empirical upper bound (rule of three: 95% UB ~0.35%), not proof of impossibility.
2. `w2e_peraoi_lam0.1` (PER_AOI_DINN + λ=0.1) n=20 → 1/20 at 5/6
3. `c_chl40_posi15` (CHL1_W_EXTRA=4.0 + POSI_W=1.5) n=20 → 1/20 at 5/6
4. Wave 6 composition test: stacking both 5/6 lever families → 0/10 at 5/6, mean_cal 2.00
5. v3.1.1 AOI ablation (n=200): best 4+/n was 19/80 (24%) in 2-AOI eqp+natl, but 0/80 at 5+/6

**These five are NOT independent evidence.** All five ran against the same contaminated Southern-Ocean PIC:POC ratio target: near-zero-POC cells drove per-cell `pic/poc` up to ~1e8 (target mean 4.7e7), inflating the `mean(target²)` loss normalizer and silently collapsing the SO ratio term to ~0, so `R_PICPOC` was unconstrained there by construction. Capping the target (`RATIO_MAX=2`) recovers `R_PICPOC` at **10/10 joint Cal** and produced the **first joint 6/6 (3/10 seeds, verified)** — `docs/findings/2026-06-24_rpicpoc_ratio_target_fix.md`. The "5/6 ceiling" label also overstated the record: the mode was 2/6, 5/6 occurred 2/856 times and never reproduced.

**Current framing.** 6/6 is achievable but **not robust**. The binding constraint is a loss-landscape identifiability tension: across 8 lever classes you can robustly recover {`R_PICPOC`, iron pair, `diatomgraz`} OR the growth pair {`Smallgrow`, `Biggrow`}, not all six — and longer training does not help. The reproducible core remains the iron pair (38/40 Cal-grade at F2). Do **not** repeat the retracted "~5 effective constraints, the 6th is the residual sink" mechanism (retracted at commit `0bfa15e`); the per-parameter data behaves like ~2–3 effective constraints.
```

---

## docs/emulator_guide.md

### `docs/emulator_guide.md:151` — contradicts canonical fact 2
> Rollout-aware training (`--rollout-train-k`) is the single largest horizon lever measured so far, extending the useful horizon from ~2 months to ~9 months.

**Why:** The ~9-month horizon was retracted 2026-07-19. `2026-07-19_emulator_honest_bounds.md`:278-280: beats a correctly-binned climatology at one step only (+0.240), zero by step 2 (−0.018), negative thereafter. STATUS.md:58 carries the retraction; this guide — explicitly "for new contributors and for automated agents resuming the project" — does not. It is the sole live doc still asserting it.

**Replace with:**
```markdown
Rollout-aware training (`--rollout-train-k`) is the single largest lever measured so far, but what it buys is **stability, not horizon**. Against a correctly-binned seasonal climatology (delta_t = 1200 s) the emulator beats the baseline at **one step only** — one step is a ~2-month operator, scoring +0.240 — is at zero by step 2 (−0.018), and is negative thereafter. **An earlier version of this guide claimed rollout-aware training extended the useful horizon from ~2 months to ~9 months; that ~9-month figure is RETRACTED as of 2026-07-19.** It was inflated because pre-correction cubes derived time from `times_days` under a wrong 900 s `delta_t`, scrambling 94% of month-of-year bins and producing a near-time-mean rather than a true seasonal climatology. What the lever does deliver is mass conservation: rollout-trained k8 holds a mass ratio of 1.000 at every horizon while single-step-trained k1 diverges to 3.05e8 by 12 steps. Physics also holds in both arms (`neg_frac = 0.000` at every horizon). See docs/findings/2026-07-19_emulator_honest_bounds.md.
```
**Adjacent:** L146-148 quote 12-month persistence +0.441 / climatology −0.265 from the same pre-correction diagnostic; corrected k8 12-step is −0.748.

---

## docs/findings/2026-07-13_global_monthly_emulator.md

### `:19` — contradicts canonical facts 3 & 4
> Skill vs. persistence (linear space) | **+0.520** | +0.469 | +0.426 | +0.519 | +0.531 | +0.452 | +0.524

**Why:** Presented throughout (title, L6 "at monthly cadence") as a monthly operator's skill. `2026-07-19_results_matrix.md` C6: "The operator is not a one-month operator. Only 48.4% of consecutive training pairs are truly 1 month apart." The doc was revised on 2026-07-19 (two dated corrections at L27 and L43-53) and the cadence mislabel was left. Note: the +0.0026 figure is log-space 3-D, not this run — cite the dt result as an adjacent-configuration warning, not this run's measured value.

**Replace with:**
```markdown
| Skill vs. persistence (linear space, **one step ≈ 2 months** — see cadence note) | **+0.520** | +0.469 | +0.426 | +0.519 | +0.531 | +0.452 | +0.524 |

> **CADENCE CORRECTION (2026-07-19).** These are **single-step** values, and a step here is **not one month**. The cube is the tracer-intersection series: 158 timesteps across 26.83 years, median consecutive spacing **59 days** (validation-split median **61 days ≈ 2.0 months**), with only 48.4% of pairs genuinely one month apart and 51.6% spanning 2–7 months, all trained as single steps. The "156 months" in the Grid line below is a **step count, not 156 elapsed months**. What +0.520 measures is a **~2-month operator**, and this doc's title and framing overstate the cadence. See `2026-07-19_emulator_honest_bounds.md` (Defect 2) and `2026-07-19_results_matrix.md` (C5, C6).
>
> **How much this matters is measured, but on an adjacent configuration.** On the monthly 3-D flagship, a matched 2×2 (log space, 3 seeds) found the mixed-Δt-trained model scores **+0.0026** on a true-one-month validation subset versus **+0.4756** for a model trained on the same number of genuinely one-month pairs (`2026-07-19_two_negatives.md`). Δt-uniformity — not data volume, which is flat from n=55 — is the live lever. **No uniform-Δt control has been run on this global-surface linear-space configuration**, so +0.520 should not be assumed to collapse the same way; its true one-month skill is **unmeasured**.
```

---

## docs/findings/2026-07-19_emulator_honest_bounds.md

> Four blockers in this file, all the same root: the doc corrected its own body tables and left its summary tables, its conclusion, and its "what this session-arc disproved" table asserting the retracted numbers.

### `:29` — contradicts canonical fact 2
> True for single-step training. Rollout-aware k8 training reaches ~9 months above climatology.

**Why:** Stated as a settled control result in the summary table, while the same document's corrected-calendar k8 table shows −0.292 vs climatology at 9 steps and L280 says the ~9-month horizon "is retracted." The top-of-file banner (L5-7) is scoped explicitly to the headline claim quoted below it, not to this row.

**Replace with:**
```markdown
| "the rollout is dead by 6 months" | scratch, 2026-07-17 | **WALK-BACK WITHDRAWN — the original claim was, if anything, generous** | The "k8 reaches ~9 months" walk-back was an artifact of the 0.75× calendar. Scored against correctly-binned climatology (job 167823), k8 is above the baseline at **one step only** (~2.0 months, +0.240); it is at zero by step 2 (−0.018) and **−0.292 at 9 steps (~17.7 months elapsed)**. What rollout-aware training buys is *stability* — mass ratio 1.000 at every horizon, against k1's divergence to 3.05 × 10⁸ — not horizon. |
```

### `:301` — contradicts canonical fact 2
> | **Rollout-aware training (k8)** | useful horizon ~2 mo → ~9 mo (log, vs climatology) | **LOAD-BEARING — #1** |

**Why:** The levers summary table survived the retraction 50 lines above it, still asserting "~9 mo … vs climatology" — the exact baseline the retraction disproved. The verdict column is correct (L285-288); only the effect text is wrong.

**Replace with:**
```markdown
| **Rollout-aware training (k8)** | buys *stability*, not horizon: mass ratio 1.000 at every horizon vs **3.05 × 10⁸** for k1 at 12 steps; +0.240 vs +0.108 at one step (~2 mo, log, vs correctly-binned climatology), at/below climatology from step 2. The "~9-month horizon" is retracted. | **LOAD-BEARING — #1** |
```

### `:350` — contradicts canonical fact 9
> The binding constraint on everything (capacity saturates, two "add information" attempts hurt, calibration stuck at 0.24, diffusion adds nothing) is **~110 training pairs**.

**Why:** The learning curve was run after this doc was written and is flat from n=55 (`2026-07-19_two_negatives.md`: +0.4700 / +0.4701 / +0.4657 at n=55/82/110). STATUS.md:73 records data quantity as "not a lever." Four independent negatives are attributed to one unmeasured data-volume cause; the measured lever is Δt-uniformity.

**Replace with:**
```markdown
> **RETRACTED 2026-07-19 (Slurm array 168270).** This section previously claimed the binding constraint on everything was **~110 training pairs**. The learning curve has since been run and **refutes that**: skill is flat from n=55 (+0.4700 at n=55, +0.4701 at n=82, +0.4657 at n=110 — all inside the seed spread σ≈0.005–0.011). **The project is not data-bound.** See `2026-07-19_two_negatives.md` §1.

The four negatives grouped here (capacity saturates, two "add information" attempts hurt, calibration stuck at 0.24, diffusion adds nothing) do **not** share a single measured cause, and pair *count* is not it. The one lever measured to move skill is **Δt uniformity**: a uniform-dt-trained model scores **+0.4756** on true monthly pairs where the flagship scores **+0.0026**. What follows about the cube's non-uniform spacing still matters — but as a **data-quality** argument, not a data-volume one. The union rebuild is worth doing because it gives **perfectly uniform monthly spacing**, not because it gives 323 steps instead of 158.
```

### `:379` — uncited-gate-on-spend (canonical fact 9)
> That single experiment gates everything downstream, and nothing we have run so far tests it.

**Why:** The gated experiment ran the same day (git: doc last touched 06:36, learning curve landed 13:21/13:50) and came back flat. The gate was placed on an assumption that turned out false, in a section headed "the highest-value fix available."

**Replace with:**
```markdown
**RESOLVED 2026-07-19 (Slurm array `168270`) — and it came back flat.** The learning curve was run at n=27/55/82/110 pairs, 3 seeds per point, everything else matched: +0.4167 → **+0.4700 → +0.4701 → +0.4657** (log space, vs persistence). The curve **saturates at n≈55**; doubling from 55 to 110 pairs buys +0.0001 then −0.0044, both inside the seed spread (σ ≈ 0.005–0.011). **We are not data-bound, and data volume is not the lever** — so the "roughly doubles the data" half of the argument above is refuted for skill purposes. What survives is the *other* half: the union cube is 323 steps at **100% uniform monthly spacing**, and Δt-uniformity is the measured lever — the flagship scores **+0.0026** on genuinely-monthly pairs against **+0.4756** for a uniform-Δt-trained model. Rebuild the cube for the Δt structure, not for the timestep count. See `2026-07-19_two_negatives.md` §1; the per-arm `lcurve_n*_s*.json` results live on `/scratch/qi_zim_neu/` and are not committed.
```

### `:388` — contradicts canonical fact 4
> Its skill is real in log space at monthly cadence and largely an artifact at daily cadence.

**Why:** The doc's own body (L58-77) establishes the validation median step is 61 days, and L386 — the immediately preceding clause — correctly says "one step (~2 months)". The controlling 2×2 (`2026-07-19_two_negatives.md`:194-204) gives +0.0026 on true monthly pairs, one seed negative. This is the sentence the whole document builds to.

**Replace with:**
```markdown
Its skill is real in log space only on the mixed-Δt monthly cube — i.e. as a ~2-month operator (median validation step 61 d); on genuinely one-month pairs it has essentially no skill over persistence (+0.0026, vs +0.4756 for an otherwise-identical model trained on uniform one-month pairs), and its daily-cadence skill is largely a linear-metric artifact.
```

---

## docs/findings/2026-07-14_emulator_loop.md

> Four blockers, all the retracted ~9-month horizon. The 2026-07-19 revision pass edited lines 42, 72 and 75 and left the number standing in all of them, so the doc actively presents ~9 months as current truth.

### `:42` — contradicts canonical fact 2
> Rollout-aware training at k=8 is the #1 *useful-horizon* lever (~2 mo → ~9 mo; k=1 diverges, mass ratio 99.6 at 9 mo, while k=8 stays stable at +0.25).

**Why:** The row is stamped "Superseded (2026-07-19)" but the superseding text itself asserts the retracted horizon and the buggy-calendar +0.25. A correction that restates the retracted claim reads as verified.

**Replace with:**
```markdown
**Superseded (2026-07-19)** — k=4 wins *only* on this short-horizon, persistence-referenced metric. Rollout-aware training at k=8 remains load-bearing, but for **stability, not horizon**: against a correctly-binned seasonal climatology (delta_t = 1200 s) k=8 beats climatology at **one step only** (+0.240, a ~2-month operator) and is at or below it from step 2 onward (−0.018 at step 2, negative thereafter). **The earlier "~2 mo → ~9 mo useful horizon" and the "+0.25 at 9 mo" are RETRACTED** — both came from buggy 900 s calendar bins that inflated skill-vs-climatology by +0.37 to +0.78, and "9 mo" was itself 9 *steps* ≈ 17.7 months, which corrects to −0.292 (see `2026-07-19_emulator_honest_bounds.md`). What survives is mass conservation: k=8 holds mass ratio 1.000 at every horizon tested, while k=1 diverges (99.58 at 9 steps, 3.05e8 at 12). Long-horizon skill must be referenced to a correctly-binned **climatology**, never persistence alone.
```

### `:72` — contradicts canonical fact 2
> rollout-aware training (k=8) later proved the **#1 horizon lever** (~2 mo → ~9 mo)

**Why:** "Proved" asserts a controlled-rerun-overturned number as established fact. The inline "(revised 2026-07-19)" tag means the doc was edited past the retraction date while leaving the claim.

**Replace with:**
```markdown
Since single-model *input* tweaks are exhausted — but note the rollout-k row above was rejected on **single-step** skill, and rollout-aware training (k=8) is still the **#1 lever**, though what it buys is **mass stability, not horizon** (k=8 holds mass ratio 1.000 at every horizon while k=1 diverges to 3.05e8 by 12 steps; the earlier "~2 mo → ~9 mo" horizon claim is **RETRACTED (2026-07-19)** — against a correctly-binned seasonal climatology the emulator beats the baseline at **one step only** (+0.240, ~2 months) and is at or below climatology from step 2, see `2026-07-19_emulator_honest_bounds.md`) — the substantive upgrades are (revised 2026-07-19):
```

### `:75` — contradicts canonical fact 2
> **Rollout-aware training (k=8)** — useful horizon ~2 mo → ~9 mo (k=1 diverges, mass ratio 99.6 at 9 mo; k=8 stable at +0.25).

**Why:** Wrong on three axes. The horizon is retracted; "+0.25" is the buggy-calendar +0.253 whose corrected value is −0.292; "9 mo" is 9 *steps* ≈ 17.7 months. The 99.58 mass ratio is the k1 arm, not k8.

**Replace with:**
```markdown
0b. **Rollout-aware training (k=8)** — the #1 *stability* lever, not a horizon lever. Against a correctly-binned seasonal climatology the emulator beats the baseline at **one step only** (+0.240; one step ≈ 2 months elapsed, since the validation split has a median gap of 61 days), is at zero by step 2 (−0.018), and is negative thereafter (step 9 ≈ 17.7 months: **−0.292**). The earlier "~2 mo → ~9 mo useful horizon" is **RETRACTED** — an artifact of the delta_t=900 s calendar bug, which scrambled the climatology month-bins and inflated skill by +0.37 to +0.78 at every horizon. What survives is stability: k=8 holds a mass ratio of 1.000 at every horizon while k=1 diverges (99.58 at step 9, 3.05e8 at step 12), and neg_frac = 0.000 in both arms. Long-horizon skill must **co-report a correctly-binned climatology**, never persistence alone. Corrected numbers: docs/findings/2026-07-19_emulator_honest_bounds.md.
```

### `:80` — contradicts canonical fact 2
> Honest overall claim: a ~9-month, **ensembled, rollout-trained, log-space, physically-valid (0% negatives)** seasonal BGC surrogate of ECCO-Darwin v05

**Why:** This is the doc's stated bottom line, and it is the exact sentence retracted on 2026-07-19. The doc received two dated correction blocks that address only the "intrinsic ceiling" framing.

**Replace with:**
```markdown
Honest overall claim: an **ensembled, rollout-trained, log-space, physically-valid (0% negatives)** BGC surrogate of ECCO-Darwin v05 whose useful horizon is **one step**. Against a correctly-binned seasonal climatology it scores **+0.240 at one step** and is at or below climatology from step 2 onward. Note that one step is a **~2-month** operator (median validation gap 61 days), not a monthly one. The earlier "~9-month horizon" in this document is **RETRACTED (2026-07-19)** — it came from comparison against a mis-binned climatology (the delta_t=1200 s calendar bug put 93.7% of month bins in the wrong month). All validation is **self-consistency vs v05 only** — never against real observations.
```

---

## docs/findings/rpicpoc_ratio_structural.md

> Four blockers. The doc is `Status: COMPLETE` with no supersession banner, and it drives a compute ask off a conclusion refuted nine days later. A sibling branch already archived it with a banner; that never landed here.

### `:1` — stale-number
> R_PICPOC: the wall is calcite forward-model fidelity, not the estimator or information (box scale)

**Why:** Refuted at root by `2026-06-24_rpicpoc_ratio_target_fix.md`, which explicitly names this doc as the finding it explains away. Same 1° box, same calcite physics, `RATIO_MAX=2` → R_PICPOC 10/10 joint Cal, genuine per-AOI. Still propagating: `docs/findings/index.md:18`, `carroll6_5pft_2layer.py:245`, `probe_env_rain_ratio.py:23` all cite it as live.

**Replace title + status block with:**
```markdown
# R_PICPOC ratio loss: the eqpac-only recovery — SUPERSEDED (the "forward-model wall" was a contaminated SO ratio target)

> **SUPERSEDED 2026-06-24 — read [`2026-06-24_rpicpoc_ratio_target_fix.md`](2026-06-24_rpicpoc_ratio_target_fix.md) first.**
> This note's headline conclusion — that the residual ≥2-AOI wall is *calcite forward-model
> fidelity*, requiring the differentiable Darwin calcite port plus native resolution — is
> **retracted**. The real cause was a data-pipeline bug in this note's own experiment: the
> Southern-Ocean PIC:POC ratio-loss target was contaminated by near-zero-POC cells (per-cell
> `pic/poc` up to ~1e8, target mean 4.7e7), which inflated the `mean(target²)` scale
> normalizer and silently collapsed the SO ratio term to ~0, leaving R_PICPOC unconstrained
> there. Capping the per-cell target (`RATIO_MAX=2`) recovers **R_PICPOC 10/10 joint Cal,
> genuine per-AOI (no straddle), ≈0.030–0.046 vs Carroll 0.0425** — at the **same 1° box with
> the same calcite physics**. It also produced the project's first 6/6 events (3/10 seeds,
> verified). The spatial-ratio numbers quoted below as Darwin targets (natl ~0.9, SO ~1.4)
> are wrong: the corrected ratio-of-means targets are eqpac 0.033 / natl 0.68 / SO 0.0067.
> **Still valid from this note:** the steady-state orthogonality argument (`mort_total`
> cancels in `PIC_1/POC_1`), the eqpac 10/10 result, the coccolith-only backfire, and the
> seasonal-axis exclusion. Everything downstream of "the residual wall is forward-model
> fidelity" — including the deck/roadmap ask — is superseded. The current binding constraint
> is the growth pair {Smallgrow, Biggrow}, not R_PICPOC.

**Date:** 2026-06-15 (night) · **Status:** SUPERSEDED (see banner). Historical record of the
ratio-loss campaign; retained for the orthogonality derivation and the 25-arm structural sweep.
```

### `:48` — stale-number
> **Darwin's realized PIC/POC ratio varies ~23×** (eqpac ~0.033 ≈ Carroll 0.0425; natl ~0.9, SO ~1.4 — coccolithophore bloom zones)

**Why:** SO 1.4 is ~200× off the recomputed 0.0067 and is the contamination artifact itself; natl 0.9 vs 0.68. The stated 23× doesn't follow from its own numbers (1.4/0.033 = 42×). The project's own ADR already corrected this by name: the "N Atl 0.9 / SO 1.4" figures were "rpicpoc_ratio_structural.md prose mislabeling a *recovered degenerate* R_PICPOC as Darwin's realized ratio." (The ~23× itself is a real number elsewhere — the eqpac↔natl *median* spread.)

**Replace with:**
```markdown
> **SUPERSEDED 2026-06-24 — see `2026-06-24_rpicpoc_ratio_target_fix.md`.**
> Result 2's diagnosis below is wrong. The ≥2-AOI block was NOT calcite forward-model
> fidelity: the Southern-Ocean PIC:POC ratio-loss target was contaminated by near-zero-POC
> cells (per-cell `pic/poc` up to ~1e8, target mean 4.7e7), which inflated the loss-scale
> normalizer and silently collapsed the SO ratio term to ~0. Capping the target
> (`RATIO_MAX=2`) recovers R_PICPOC 10/10 joint Cal, genuine per-AOI. Do not cite the numbers
> in this paragraph.

The ratio loss recovers R_PICPOC **only in eqpac**, because the box's calcite is a
*rigid* readout (`PIC_1/POC_1 = R_PICPOC` everywhere), while **Darwin's realized
PIC/POC ratio varies ~100× across the three AOIs** (ratio-of-means, recomputed directly
from the v05 target caches on 2026-06-24: eqpac 0.033 ≈ Carroll 0.0425; natl 0.68;
SO 0.0067; the eqpac↔natl *median* spread is the ~23× figure quoted elsewhere in `docs/`).
The values "natl ~0.9 / SO ~1.4" previously printed here were **not** Darwin's realized
ratios — they were *recovered degenerate* R_PICPOC fits from the sweep table above, and the
SO number is the contamination artifact itself (~200× above the true 0.0067). All three true
values sit below the 0.8 coccolithophore rain-ratio ceiling. Correspondingly, the SO column
of the sweep table (0.21 / 1.37 / 1.5) was produced under the contaminated SO target and
carries no information about R_PICPOC.
```

### `:96` — overclaim
> Confirms exhaustively: **no laptop estimator/structural lever recovers R_PICPOC in ≥2 AOIs.** … The ≥2-AOI block is the calcite forward-model gap, not the estimator.

**Why:** "Exhaustively" over 25 arms was falsified by one later laptop-scale estimator fix. `RATIO_MAX` is a loss-target data fix — squarely the estimator side the doc excludes. The 25 arms all shared the same contaminated SO target: 25 replications of one bug, not 25 independent exclusions.

**Replace with:**
```markdown
> **SUPERSEDED (2026-06-24):** the ≥2-AOI block described below turned out to be an
> estimator/data bug, not a calcite forward-model gap — see
> `docs/findings/2026-06-24_rpicpoc_ratio_target_fix.md`.

Across these 25 arms, **no lever tried here recovered R_PICPOC in ≥2 AOIs.** The ratio
loss is the lone lever that recovers R_PICPOC without the mutex (eqpac, dose-robust);
every *magnitude* anchor still wipes the iron pair. This is **not** an exhaustive
exclusion: all 25 arms shared the same Southern-Ocean PIC:POC ratio target, later found
contaminated by near-zero-POC cells (per-cell `pic/poc` up to ~1e8, target mean 4.7e7),
which inflated the loss-scale normalizer and silently collapsed the SO ratio term to ~0,
leaving R_PICPOC unconstrained there. Capping the per-cell target (`RATIO_MAX=2`) — a
loss-target fix squarely on the *estimator* side — recovers R_PICPOC per-AOI (≥2 AOI)
**10/10**, verified via `scripts/verify_run.py` (exit 0) with no straddle artifact. So the
25 arms are 25 replications of one contaminated observable, not 25 independent exclusions,
and the reading that "the ≥2-AOI block is the calcite forward-model gap, not the estimator"
is **retracted**.
```

### `:114` — uncited-gate-on-spend
> This **sharpens** the talk's ask: R_PICPOC needs *native-resolution + richer calcite physics (the differentiable Darwin port)*, not a cheap laptop lever and not merely "more compute for the same box."

**Why:** This is the compute ask itself, resting entirely on the refuted conclusion. A cheap box-scale lever *was* sufficient, and the environmental rain-ratio gating mechanism proposed here as the fix is separately REFUTED as a recovery tool (3/10, straddle artifact). Lines 116-122 script a quotable verbal answer for a live talk on the refuted premise.

**Replace with:**
```markdown
> **SUPERSEDED (2026-06-24) — do not quote the conclusion below.** The "≥2-AOI wall is
> calcite forward-model fidelity" reading was **wrong**, and the compute ask built on it is
> withdrawn. The eqpac-only recovery was a **data-pipeline bug**, not missing physics: the
> Southern-Ocean PIC:POC ratio-loss target was contaminated by near-zero-POC cells (per-cell
> `pic/poc` up to ~1e8, target mean 4.7e7), which inflated the loss-scale normalizer
> `mean(target^2)` and silently collapsed the SO ratio term to ~0. Capping the per-cell
> target at a physical rain ratio (`RATIO_MAX=2`, a one-line filter) yields **R_PICPOC 10/10
> joint Cal, genuine per-AOI (no straddle), ~0.030-0.046 vs Carroll 0.0425**, robust across
> cap 2-5. See `docs/findings/2026-06-24_rpicpoc_ratio_target_fix.md`.
>
> Two specific corrections:
> 1. **Native resolution + the differentiable Darwin calcite port were both tested and
>    neither helped.** R_PICPOC was never a 6/6 wall and is not a justification for that
>    spend (STATUS.md).
> 2. **Environmental rain-ratio gating — the Ω/temperature-dependent calcite mechanism
>    proposed here as the fix — is REFUTED as a recovery tool** (env-ON: R_PICPOC 3/10 with a
>    straddle artifact, worse than the simple data fix).
>
> What survives: the flat-ratio box genuinely cannot reproduce Darwin's spatial PIC:POC
> spread. But that was never required — the 6/6 criterion is Carroll's **single global**
> scalar, which the data fix recovers.

This does **not** justify a native-resolution or Darwin-calcite-port ask. The correct
reading is that R_PICPOC's box-scale non-recovery was a **fixable design issue on both the
estimator and the observation-pipeline side** — first the wrong observable (separate PIC/POC
magnitudes → the iron-pair mutex), then a contaminated ratio target in the Southern Ocean.
Both were fixed without new physics and without new resolution.

If asked whether it was a design error vs compute: *"Design error, twice over. The
separate-magnitude anchors were the wrong observable — a PIC:POC ratio loss identifies
R_PICPOC orthogonally to the iron pair, because `mort_total` cancels at steady state. When
that still only worked in eqpac, we assumed missing calcite physics; it was actually a
contaminated Southern-Ocean ratio target collapsing that term in the loss. Capping it
recovers R_PICPOC 10/10 per-AOI against Carroll's global scalar. We tested both the
richer-calcite and native-resolution hypotheses and neither was the lever."*

The residual limit is **not** R_PICPOC: it is a structural identifiability tension between
{R_PICPOC, iron pair, `diatomgraz`} and the growth pair {`Smallgrow`, `Biggrow`}, which 8
lever classes (including 3000 epochs) fail to break. Any forward compute ask should be
argued on its own merits, not on R_PICPOC.
```

---

## docs/findings/posi_dense_diatomgraz.md

### `:116` — stale-number
> **`R_PICPOC` is the entire 6/6 wall, and it is cluster-gated.** 0/20 under Eppley, the *sole* miss in all four 5/6 seeds.

**Why:** Superseded twice. `rpicpoc_ratio_structural.md` recovered R_PICPOC 10/10 in eqpac at box scale with no cluster; `2026-06-24_rpicpoc_ratio_target_fix.md` recovered it 10/10 joint Cal on the *same* 3-AOI config and produced the first 6/6, with the cause "a data-pipeline bug, not missing physics." "Cluster-gated" is the exact inversion. Repeated at L128-131 and L147-153 as the AICR case.

**Replace with:**
```markdown
**`R_PICPOC` was the entire 6/6 wall at this operating point — but it was *not* cluster-gated.** *(Superseded 2026-06-15 and 2026-06-24 — see `rpicpoc_ratio_structural.md` and `2026-06-24_rpicpoc_ratio_target_fix.md`. The "cluster-gated / AICR case" reading below is retained as the state of knowledge on 2026-06-11 and is now known to be wrong.)* Under Eppley it was 0/20 here, the *sole* miss in all four 5/6 seeds, and two box-scale attempts to crack it both failed by the *same* mutex:

    - Separate calcite sinking (`W_SINK_PIC=0.30`) alone did **not** move it (0/10).
    - A **PIC magnitude anchor on the Eppley config** (`PIC_ABS_W ∈ {0.02, 0.1}`, n=10 each)
      **does** recover it (0→8/10) — but wipes the entire iron pair (18→0/10, 20→0/10) *and*
      `diatomgraz` (20→1/10). Net mean *drops* 3.85→2.5.

**What actually broke it (added 2026-06-24).** The mutex above is real but is an artifact of anchoring PIC and POC *magnitudes separately* — each pins `mort_total`. A per-cell **PIC:POC ratio** loss identifies `R_PICPOC` orthogonally (`mort_total` cancels at steady state), and that lever is *laptop-feasible*: `rpicpoc_ratio_structural.md` recovered `R_PICPOC` 10/10 in eqpac while keeping the iron pair (8/10), on the box, with no cluster. The remaining failure outside eqpac was then traced to a **data-pipeline bug, not missing information**: the Southern-Ocean ratio target was contaminated by near-zero-POC cells (target mean 4.7e7), which collapsed that loss term to ~0. Capping the target (`RATIO_MAX=2`) recovers `R_PICPOC` **10/10 joint Cal at this same 1° box scale** and produced the project's **first 6/6**. The box had the information all along; the target did not.

**The residual wall is the growth pair.** Post-fix, 6/6 is achieved but *not robust*: across 8 lever classes you can robustly recover {`R_PICPOC`, iron pair, `diatomgraz`} **or** the growth pair {`Smallgrow`, `Biggrow`}, not all six. Longer training does not help. **Do not cite this section as the AICR / cluster-gating case.**
```

### `:130` — uncited-gate-on-spend
> breaking it needs the information the box does not have (seasonal cycle, native resolution), not another laptop lever. **This is the AICR case, backed by an exhaustive box-scale exclusion.**

**Why:** An explicit justification for paid AICR time, asserted as "exhaustive" while the ratio observable — the lever that actually worked, at box scale — had not been tried. `rpicpoc_ratio_structural.md` (4 days later) lists it as one of "two untested ideas." Repeated at L148-153 as "the strongest motivation for native-resolution + seasonal fitting in the Schultz/Jon deck."

**Replace with:**
```markdown
R_PICPOC under pattern-only z-loss is degenerate with the iron budget at the box scale *under the levers tested here* — loss weight, AOI mix, architecture, IC, Eppley physics, and the PIC magnitude anchor.

> **RETRACTED (2026-06-24) — do not use this passage to justify cluster/AICR time.** This note originally read "breaking it needs the information the box does not have (seasonal cycle, native resolution), not another laptop lever. This is the AICR case, backed by an exhaustive box-scale exclusion." That exclusion was **not** exhaustive. A PIC:POC **ratio** observable was still untested when this was written — `rpicpoc_ratio_structural.md` (2026-06-15) flagged it as an open idea and then found it to be the lone lever that recovers R_PICPOC without the iron mutex — and it is what broke the wall, at the **same 1° box**, with no seasonal cycle and no native resolution. The Southern-Ocean PIC:POC ratio target was contaminated by near-zero-POC cells (target mean 4.7e7), which inflated the loss-scale normalizer and silently collapsed the SO ratio term, leaving R_PICPOC unconstrained. Capping the per-cell target (`RATIO_MAX=2`) recovers **R_PICPOC 10/10 joint Cal, genuine per-AOI (no straddle), ≈Carroll 0.0425**, and produced the project's first 6/6 events. **R_PICPOC was never fundamentally unidentifiable and was never cluster-gated: it was a contaminated observation in the loss.** The residual box-scale ceiling is the growth pair {`Smallgrow`, `Biggrow`}; see STATUS.md ("R_PICPOC was never a '6/6 wall'"; cluster goals are *not* gated on R_PICPOC or 6/6).
```

### `:136` — stale-number
> **`R_PICPOC` is the one parameter no laptop-scale lever (loss weight, architecture, IC, or forward-model physics) has recovered.**

**Why:** Directly falsified by a laptop-scale loss lever (`RATIO_W` PIC:POC ratio loss, 10/10 eqpac with the iron pair surviving 8/10) and by the `RATIO_MAX` target fix (10/10 joint). Presented in bold as the doc's revised thesis with no correction note.

**Replace with:**
```markdown
**Thesis (revised — superseded 2026-06-15/06-24, see below).** "Parameter conservation" is *not* a fixed effective count: forward-model fidelity injects genuine identifying information and raises the recovered count (2.0 → 3.85/6) while making 5/6 reproducible rather than a fluke. As of this experiment the hard cap appeared sharply localized on `R_PICPOC`, which no lever tried *here* (loss weight, architecture, IC, or Eppley forward-model physics) had recovered.

> **SUPERSEDED.** The `R_PICPOC` wall described in this doc has since been broken, and it was **not** cluster-gated. (1) `rpicpoc_ratio_structural.md` (2026-06-15, box scale) shows a **laptop-scale loss lever** — the `RATIO_W` PIC:POC *ratio* observable, under which `mort_total` cancels at steady state so `R_PICPOC` is pinned orthogonally to the iron pair — recovers `R_PICPOC` in eqpac **10/10** with the iron pair surviving 8/10. (2) `2026-06-24_rpicpoc_ratio_target_fix.md` shows the residual ≥2-AOI block was a **data-pipeline bug**, not missing physics or resolution: the Southern-Ocean ratio target was contaminated by near-zero-POC cells (target mean 4.7e7), collapsing the SO ratio term to ~0. Capping it (`RATIO_MAX=2`) gives **10/10 joint Cal, genuine per-AOI, `R_PICPOC` ≈ 0.030–0.046 vs Carroll 0.0425**, and the project's first 6/6 — though 6/6 is **not robust** (3/10 seeds), the binding constraint being a structural tension between {`R_PICPOC`, iron pair, `diatomgraz`} and the growth pair. Read the "cluster-gated" and "exhaustive box-scale exclusion" language above as a snapshot of 2026-06-11 belief, not a current claim.
```

---

## docs/findings/pre_scaleup_verification.md

### `:73` — stale-number
> So R_PICPOC is structurally unidentifiable *jointly* — not for lack of resolution, but because the box's PIC production (R_PICPOC × mortality) cannot represent Darwin's spatially-varying calcite:organic ratio.

**Why:** Falsified at the same 1° box: `RATIO_MAX=2` yields R_PICPOC 10/10 joint Cal, no straddle. The 6/6 criterion is Carroll's *single global* scalar — Carroll himself used one — so the box's inability to reproduce the spatial spread was never the identifiability blocker. This doc even flags the ratio loss at L64-65 as "the untested laptop lever remaining."

**Replace with:**
```markdown
So the box cannot represent Darwin's spatially-varying calcite:organic ratio with one scalar — its PIC production (R_PICPOC × mortality) is flat by construction. **This was originally read as R_PICPOC being structurally unidentifiable *jointly*; that reading is SUPERSEDED** (`2026-06-24_rpicpoc_ratio_target_fix.md`). At this *same* 1° box, capping the per-cell PIC:POC ratio-loss target (`RATIO_MAX=2`) — which removes near-zero-POC cells whose contaminated target mean (~4.7e7) had collapsed the Southern-Ocean ratio term through the loss-scale normalizer — recovers **R_PICPOC 10/10 joint Cal, genuine per-AOI (no straddle), 0.030–0.046 vs Carroll 0.0425**, robust across cap 2→5. The wall was a contaminated observation in the loss, not missing physics or missing resolution. Reproducing Darwin's ~100× spatial spread was never the recovery criterion — Carroll used a single global R_PICPOC, so recovering ≈0.0425 is the target; the box's flat ratio is a forward-fidelity limitation, not an identifiability blocker.
```

### `:78` — uncited-gate-on-spend
> Together these say the fix is **coccolithophore-resolved calcite at native resolution** … That is precisely the mechanism the native-res B200 run targets, now empirically grounded by two laptop experiments rather than asserted.

**Why:** This is the stated B200 spend argument. STATUS.md:113-114 refutes the conclusion verbatim. The prescribed mechanism (environmental rain-ratio gating) scored 0/10 with R_PICPOC 3/10 and a straddle artifact — *worse* than the simple data fix. Note: the fidelity leg's *measurements* (0.033/0.676/0.0067) are correct; it is the inference that was invalidated.

**Replace with:**
```markdown
### Synthesis — what the two probes did and did not establish

> **SUPERSEDED (2026-06-24) — this section's B200 spend argument no longer holds.** Kept as
> the 2026-06-18 decision record.

The 1° box cannot hold Darwin's 100× PIC:POC spread with one R_PICPOC scalar (fidelity),
and coccolith-only calcite at 1° fails the mutex (coccolith probe). Both measurements
stand. The inference drawn from them — that the fix was therefore
**coccolithophore-resolved calcite at native resolution**, and that the native-res B200 run
was the mechanism this pointed to — **was wrong, and was refuted six days later at the same
1° box.**

- **`RATIO_MAX=2` broke the wall without any resolution or physics change**
  (`2026-06-24_rpicpoc_ratio_target_fix.md`): the Southern-Ocean PIC:POC ratio-loss target
  had been contaminated by near-zero-POC cells (per-cell `pic/poc` up to ~1e8, target mean
  4.7e7), which collapsed the SO ratio term through the loss-scale normalizer. Capping the
  per-cell target gives **R_PICPOC 10/10 joint Cal, genuine per-AOI (no straddle)**, robust
  across cap 2–5.
- **The prescribed mechanism was tested and lost.** Environmental rain-ratio gating scored
  **0/10 6-of-6 with R_PICPOC 3/10 and a straddle artifact**, i.e. *worse* than the simple
  data fix. STATUS.md: the "needs the differentiable Darwin calcite port + native
  resolution" conclusion is **refuted — both were tested and neither helped.**
- **The fidelity probe's numbers survive; its conclusion does not.** The box genuinely
  cannot reproduce Darwin's spatial rain-ratio spread. But Carroll's 6/6 criterion is a
  *single global* R_PICPOC ≈ 0.0425, which the flat-ratio box does recover. Spread mismatch
  was never the thing blocking recovery, so it was never evidence for a resolution upgrade.

**Net effect on the B200 ask:** this section should not be read as grounding it. The
native-res Explorer/B200 goals below remain legitimate on their own merits (global seasonal
throughput, compiled-memory and GPU-util checks) and are explicitly **not** gated on
R_PICPOC or on "6/6".
```

---

## docs/findings/modis_arc/phase2a_modis_pic_integration.md

### `:9` — overclaim
> **MODIS-Aqua L3m PIC v2022.0 is the independent observation that breaks the circularity.** Same Balch-Gordon algorithm Carroll's Green's functions implicitly target

**Why:** Its own companion doc from the same session lists exactly this as an OPEN question for Lauderdale, later resolved in the negative: v05 calibration assimilates SOCAT fCO2, GLODAP bottles and BGC-Argo only — no PIC, no ocean colour. The corrected apples/oranges framing already exists in the same directory (`meeting_deck_2026_05_lauderdale.md:104`). Cited as live rationale by `run_v3.0_with_modis_pic.py:300-302` and `sweep_modis_pic.py:3`.

**Replace with:**
```markdown
3. **MODIS-Aqua L3m PIC v2022.0 was hypothesized to be the independent observation that breaks the circularity — this was subsequently falsified (2026-05-19).** Carroll's v05 Green's-functions calibration assimilates SOCAT fCO2, GLODAP bottle profiles (NO3, PO4, SiO2, O2, DIC, alkalinity) and BGC-Argo only — **no PIC and no ocean-colour product** (confirmed by Lauderdale, 2026-05-19; cross-checked against Carroll et al.'s v05 evaluation report, Zenodo 10627664 §3). The Balch-Gordon retrieval therefore does *not* target the same quantity Carroll-6 was tuned against: satellite-retrieved PIC, model-simulated PIC, and wet-lab-measured PIC are different quantities (apples-to-oranges), so MODIS is a complementary observation, not a circularity-breaking anchor. Window overlap is not evidence of a shared calibration target. Blending MODIS and Darwin PIC anchors was later falsified as a 6/6 path — the basin mutex is binary at any non-trivial Darwin anchor weight. See `meeting_deck_2026_05_lauderdale.md`.
```
**Also fix:** the same false premise is duplicated at L71-77 of this doc and in the code comment at `scripts/run_v3.0_with_modis_pic.py:300-302`.

### `:58` — stale-number
> **MODIS-Aqua PIC anchor predicts a 20× larger R_PICPOC target in eqpac.** That's still below Carroll's 0.04245, but much closer to it than the Darwin v05 anchor implied.

**Why:** Arithmetically impossible and empirically inverted. Darwin's eqpac PIC:POC is 0.033, so 20× is ~0.66 — an order of magnitude *above* Carroll's 0.0425. `master_comparison.md` shows modis-W1 driving R_PIC to 0.2203; `overnight_2026_05_19.md`:122 calls 0.196 "a 4.6x over-shoot." The predicted alpfe/diatomgraz benefit never materialized (0/10 and 0/10 across M1-M3, L1-L3). Contradicts point 2 immediately above it in the same doc.

**Replace with:**
```markdown
3. **MODIS-Aqua PIC anchor implies a ~20× larger R_PICPOC target in eqpac — which lands far ABOVE Carroll's 0.04245, not below it.** Darwin's eqpac PIC:POC ratio-of-means is 0.033, so a 20× MODIS anchor implies a target of ~0.6. **This prediction was subsequently tested and refuted** (see `overnight_2026_05_19.md`): under the MODIS anchor R_PICPOC drifts to 0.196–0.22 at low weight (a 4.6× over-shoot of Carroll) and to ~0.6 at W=1.0, and the hoped-for alpfe/diatomgraz rescue never materialized — alpfe 0/10 and diatomgraz 0/10 across M1–M3 and L1–L3. MODIS PIC and Carroll's published R_PICPOC are *different targets*, not closer approximations of the same one.
```

---

# MAJOR

## README.md

### `README.md:34` — contradicts canonical fact 2
> 2. **Emulator** *(not started)* — a neural stand-in for ECCO-Darwin for long-timescale climate runs.

**Why:** Built, evaluated and released (STATUS.md L38-50: `opt3d_seed{0..5}.pt`, HF v0.1.0, 947 MB, tagged; `docs/model_card_opt3d.md`). "For long-timescale climate runs" is the retracted horizon — the model card says "Do not use this for multi-month forecasting." README last committed 2026-06-25, predating the Track-2 build. **The HF release is PRIVATE** — replacement text must not imply a public download.

**Replace with:**
```markdown
2. **Emulator** *(v0.1.0, released; narrow scope)* — a neural stand-in for ECCO-Darwin v05. A 6-member FNO2d ensemble (`opt3d_seed{0..5}.pt`, Hugging Face `2imi9/darwindiff-emulator`, private) that beats a correctly-binned seasonal climatology by **+0.240 at one step and is at or below it from step two onward** — a one-step operator, not a long-timescale climate emulator. One step is a **~2-month** interval (validation median gap 61 days); on genuinely-monthly pairs it scores **+0.0026**. An earlier "~9-month horizon" claim was retracted on 2026-07-19 after a calendar bug (`delta_t` is 1200 s, not 900 s) was found in our own evaluation. See [`docs/model_card_opt3d.md`](docs/model_card_opt3d.md) and `docs/findings/2026-07-19_emulator_honest_bounds.md`.
```

---

## STATUS.md

### `STATUS.md:20` — overclaim
> The growth pair {`Smallgrow`, `Biggrow`} is **unobservable by construction** — no real-world data constrains phytoplankton growth rates

**Why:** The document contradicts itself: `2026-07-09_track2_identifiability_writeup.md`:184-187, STATUS.md:203-204 and `NEXT_SESSION.md`:46-47 all give the defensible version — *degeneracy*, not absence ("total NPP constrains only the biomass-weighted mean growth rate"). L20 is the strictly stronger, referee-falsifiable form. Also: neither parameter has ever been profiled (job array 8479481), so the verdict is structural, not measured. (Note: the audit's premise that NPP is used in the loss is wrong — `PRIMPROD_W` defaults to 0.0 and its target is Darwin's own diagnosed primProd. The finding stands on the self-contradiction.)

**Replace with:**
```markdown
The growth pair {`Smallgrow`, `Biggrow`} is **degenerate under the available observables** — the real production observable (14C / satellite NPP) constrains only the *biomass-weighted mean* growth rate, so the pair cannot be split without a per-PFT production measurement that no instrument provides — so it is excluded from the target, not counted as a miss. This is a structural argument (`docs/research_notes/2026-07-09_track2_identifiability_writeup.md`), **not** a measured profile: neither `Smallgrow` nor `Biggrow` has ever been profiled (job array `8479481`, in flight). Do **not** write "no real-world data constrains phytoplankton growth rates" — growth-rate observations exist; the limitation is degeneracy of the pair, not absence of data.
```
**Also fix:** `main.tex:83-85` and `main.tex:286-287` carry the same overclaim on the referee-facing surface.

### `STATUS.md:105` — no-committed-artifact (canonical fact 8)
> This is a **settled identifiability verdict**, not an open task: it is profile-likelihood-flat / structurally non-identifiable from the present staged data

**Why:** This is the claim the same document's 2026-07-19 warning box (L24-36) says must not be made, 70 lines above. Worse than flagged: 13 artifacts *are* now committed under `docs/findings/silicate_scope/`, and they **refute the inference** — `fim_alpfe_nosi.json` gets the identical "FLAT → STRUCTURAL non-identifiability" verdict (span 0.0235) for a parameter recovered 9-10/10. `2026-07-19_silicate_fim_artifact_audit.md` §6-7 records that the convergence guard rejects 9 of the 13, with all three `diatomgraz` arms pinned to a grid edge.

**Replace with (covers L104-107):**
```markdown
- **`diatomgraz` — not recovered** in the real-data sweep (best 4/10 = chance). Treat this as a
  **limit of the present observable set, not a settled structural verdict** —
  [#152](https://github.com/2imi9/ECCO-DarwinDiff/issues/152) stays open. What is defensible:
  `diatomgraz` is constrained only through a **steady-state biogenic-silica diagnostic**
  (`silica.py:78`, algebraically back-solved from diatom biomass, so partly circular), not a
  prognostic silicate cycle; its profile likelihood is **FLAT (span 0.039)** in the loss *without*
  dense POSi; and adding **dense Darwin POSi (`TRAC16`)** — a model-derived, not observational,
  target — recovers it **10/10** (20/20 under Eppley, `docs/findings/posi_dense_diatomgraz.md`).
  Do **not** promote FLAT to "structurally non-identifiable": the committed profiles under
  `docs/findings/silicate_scope/` assign the same FLAT verdict to `alpfe` (span 0.0235), a
  parameter this project recovers 9–10/10, so a flat span does not imply unrecoverable — and 9 of
  those 13 runs are rejected outright by the convergence/bracketing guard, with all three
  `diatomgraz` arms pinned to a grid edge. See
  `docs/findings/2026-07-19_{diatomgraz_claim_audit,silicate_fim_artifact_audit}.md`.
```

### `STATUS.md:106` — contradicts canonical fact 8
> In principle it is an **iron-pair tradeoff** recoverable via the dense Darwin POSi (`TRAC16`) target, which is **not staged**; that is a future data-staging option, not a Track-1 blocker.

**Why:** TRAC16 is staged, wired, run, and **active in the current config**: 289 monthly native LLC270 snapshots on disk; `llc270_loader.py:73` registers `"POSi": "TRAC16"`; `run_v3.0_joint_multi_aoi.py:386-392,720,972-987` implements the gated loss term; `run_identifiability.sbatch:12-15` exports `POSI_DARWIN_W=0.5` in the very config that produced the current numbers. STATUS.md's own callout at L29 already states the 10/10.

**Replace with:**
```markdown
Profile-likelihood is **FLAT** (span 0.039) in the loss *without* dense Darwin POSi; adding the dense Darwin POSi (`TRAC16`) observable — which **is** staged and was run (289 monthly native LLC270 snapshots on disk, registered in `TRAC_MAPPING` in `llc270_loader.py`, driven by the `POSI_DARWIN_W` lever, and active at `POSI_DARWIN_W=0.5` in the current config) — recovers it **10/10** (20/20 under Eppley). Its identifiability is therefore carried by that single observable channel, not absent. But that target is Darwin's *own* field, and our bSi observable is a steady-state diagnostic algebraically back-solved from diatom biomass (`silica.py:78`) in a box with no prognostic SiO₂ — so the 10/10 is **model-circular**, which is why it does not constitute a real-data recovery. The gap is a prognostic silicate cycle / independent dissolved-SiO₂ observation (~6,968 in-AOI GLODAPv3 bottles available vs the 11 real bSi bottles now in the loss), not data staging — [#152](https://github.com/2imi9/ECCO-DarwinDiff/issues/152), `docs/findings/posi_dense_diatomgraz.md`, `docs/findings/2026-07-19_diatomgraz_claim_audit.md`. (The span-0.039 profile JSON is not yet committed; re-run with `--out` and commit it before the manuscript leans on it.)
```
**Also:** `main.tex:156,269,454` carry the same "not staged" error.

---

## docs/NEXT_SESSION.md

### `docs/NEXT_SESSION.md:16` — overclaim
> ## Shape: two papers, both now at a COLLABORATION gate (not a compute gate)

**Why:** Paper #1 has an outstanding compute precondition. Arrays 8479481+8482504 completed 2026-07-19 and the artifact landed, but `2026-07-19_silicate_fim_artifact_audit.md` §5-6 shows it is unusable — `theta*` under-converged and manufacturing the silicate signal, `diatomgraz`'s span at a grid bound, `min(profile) >= loss_star` failing by 10.5% on the four `si` runs — and lists four required re-runs. The doc doubles down at L56 and L64.

**Replace with:**
```markdown
## Shape: two papers — Paper #2 at a COLLABORATION gate, Paper #1 still behind a COMPUTE gate

- **Paper #1 has an outstanding compute precondition.** The profile-likelihood / Fisher evidence for `diatomgraz`, `Smallgrow` and `Biggrow` (plus the bSi-ablation arm) has no usable committed artifact. Explorer arrays `8479481` + `8482504` completed 2026-07-19 and the JSON landed under `docs/findings/silicate_scope/`, but the result **cannot be quoted**: `theta_star` is under-converged and manufactures the apparent silicate identifiability gain, `diatomgraz`'s profile minimum sits at the grid bound (span 0.0595, not interior), and the `min(profile) >= loss_star` check fails by 10.5% on the four `si` runs. A re-run with a convergence assertion, widened grids and a hardened `theta_star` is required before submission — see `docs/findings/2026-07-19_silicate_fim_artifact_audit.md` §6. Until it lands, do **not** write "diatomgraz carries no observational signal"; the defensible framing is that it is constrained only through a steady-state biogenic-silica *diagnostic*, that the profile is FLAT (span 0.039) without dense POSi, and that dense Darwin POSi recovers it 10/10 — noting the bSi observable is circular.
- **Paper #2 is at the collaboration gate** — waiting on Jon for a direction decision, with no compute outstanding.
```

### `docs/NEXT_SESSION.md:18` — overclaim (canonical fact 8)
> **Paper #1 (Track-1 identifiability/recovery study) — submission-quality** since 2026-07-05.

**Why:** A manuscript with a required-before-submission item outstanding is not submission-quality. Beyond the missing JSON, `2026-07-19_silicate_fim_artifact_audit.md` shows the recovered artifact is formally invalid (9/13 rejected; four `si` profiles return minima 7.3 below `loss_star`; §4 falsifies the underlying inference via `alpfe`). File last committed 2026-07-12, before the audits; no hedge anywhere in it.

**Replace with:**
```markdown
- **Paper #1 (Track-1 identifiability/recovery study) — draft complete, NOT submission-ready.** Draft text frozen 2026-07-05; **blocked on evidence as of 2026-07-19.** The profile-likelihood artifact from Explorer arrays `8479481`/`8482504` is committed under `docs/findings/silicate_scope/`, but the convergence + bracketing guard in `scripts/identifiability_sloppiness.py` **rejects 9 of its 13 files** (four `si`-arm profiles return minima 7.3 below `loss_star`; `diatomgraz`'s optimum flips from the left grid edge to the right between arms). The inference pattern also fails: the better-converged `nosi` arm calls `alpfe` FLAT (span 0.0235), and `alpfe` is recovered 9–10/10 — so a FLAT span is **not** evidence of structural non-identifiability. Do **not** write "`diatomgraz` carries no observational signal." Defensible framing only: `diatomgraz` is constrained through a steady-state biogenic-silica **diagnostic**, not a prognostic silicate cycle; the bSi observable is **circular** (`src/darwindiff/silica.py:78`); dense Darwin POSi recovers it 10/10. See `docs/findings/2026-07-19_silicate_fim_artifact_audit.md` §6 for the four required re-runs.
```

---

## docs/CLAUDE_PROJECT_CONTEXT.md (cont.)

### `:15` — contradicts canonical fact 2
> **Track 2 — Emulator** (future): neural-network stand-in for Darwin's biogeochemistry kernel, 10-100× faster for long climate runs.

**Why:** Three defects. "Future" is stale (released v0.1.0). "For long climate runs" is the retracted horizon. The 10-100× has **no committed benchmark** — a whole-repo grep finds only box-model GPU-vs-CPU projections and torch.compile eager ratios; `2026-05-23_compute_ladder.md`:139 lists "measured speedup" as an **unmet Gate-5 criterion**. The only measured inference number is 7.45 ms/global step at 2.29 GB, never expressed as a ratio.

**Replace with:**
```markdown
2. **Track 2 — Emulator** (released, not future): an FNO2d neural-network stand-in for Darwin's biogeochemistry kernel — `v0.1.0`, 2026-07-19, 🤗 `2imi9/darwindiff-emulator` (PRIVATE), 6-member log-space rollout-k8 ensemble. **Its useful horizon is exactly 1 step** (+0.240 vs a correctly-binned seasonal climatology; at or below climatology from step 2), so it is **not** usable for long climate runs — the earlier "~9-month horizon" is retracted. Every "single-step" number describes a **~2-month operator** (validation median gap 61 days); on true monthly pairs the flagship scores **+0.0026**. Measured inference cost is **7.45 ms/global step at 2.29 GB**; **no speedup ratio against Darwin has been benchmarked** — that remains an unmet Stage-5 gate criterion, so quote no "N× faster" figure. All Track-2 results to date are synthetic self-twin against v05 output.
```

### `:51` — stale-number
> **Cal-grade** = recovered value within ±40% of Carroll. **Excellent** = within ±10%.

**Why:** `diagnostics.py:46` sets `BAND_EXCELLENT_MAX = 0.05`; STATUS.md:163 and `results_matrix.md:22` both say ≤5%. `git log -L46,46` shows the constant was introduced at 0.05 and never held 0.10 — the doc was wrong on arrival. Any Excellent-grade count generated in the Claude Project against ±10% over-reports.

**Replace with:**
```markdown
**Cal-grade** = recovered value within ±40% of Carroll. **Excellent** = within ±5%. (Canonical thresholds live in `diagnostics.band_of`: *Excellent* ≤ 5%, *Cal-grade* ≤ 40%, *Loose* ≤ 80%, *Drifted* > 80%.)
```
**Also:** `docs/findings/posi_dense_diatomgraz.md:34` has the same ±10% error.

### `:221` — stale-number
> **Treat the user's hardware as fixed (5090 Laptop 32GB)** unless they say otherwise. Don't assume cluster access until they confirm Engaging onboarding has happened.

**Why:** Cluster access is active on two systems. `cluster_setup.md:12-16`: Explorer (H200 144 GB ×32) is the "Active near-term path", access granted June 2026; Engaging is a separate Jon-side option the project did not take. This instruction makes the Claude Project decline cluster-scale suggestions that are already routine. Compounded at L141 and L173.

**Replace with:**
```markdown
6. **Two hardware tiers, both live.** Local RTX 5090 Laptop (32 GB) for development, small-segment fits, and diagnostics; **Northeastern Explorer (H200 144 GB ×32) is active** and is where native-resolution and multi-seed throughput work runs. **AICR (B200)** is the future path, gated on a PI project proposal. Cluster-scale suggestions are in scope by default — but note a *single* fit is launch-bound and runs at the same speed on 5090 / H200 / B200, so the cluster buys throughput and memory, not per-fit latency. MIT ORCD Engaging is a separate Jon-side option the project did not take; do not treat it as a gate.
```

---

## docs/emulator_guide.md (cont.)

### `:81` — contradicts canonical fact 3
> the monthly 3-D run **survives** the transform (+0.432 linear → +0.365 log), while the daily eqpac run **collapses** (+0.3000 → +0.0361)

**Why:** "Monthly 3-D run" / "monthly 3-D flagship" (L118) reads as a one-month-step result; the validation split has a median gap of 61 days. A grep of the whole guide for "61 day|median gap|2-month|0.0026" returns zero hits. The guide is meticulous about metric space and entirely silent on cadence.

**Replace lines 81-84 with:**
```markdown
  log-space control is decisive and run-specific: the mixed-cadence 3-D run **survives** the
  transform (+0.432 linear → +0.365 log), while the daily eqpac run **collapses** (+0.3000 →
  +0.0361) and the global daily run in log space reads +0.005, i.e. a null. **Read the 3-D numbers
  as a ~2-month operator, not a monthly one** — that validation set has a median gap of 61 days.
  On genuinely-monthly pairs the same flagship scores **+0.0026**, no skill over persistence, while
  a model trained only on 1-month pairs scores **+0.4756**; Δt uniformity, not the transform, is
  what governs that gap. The honest claim for the daily emulator is therefore that it predicts
  bloom dynamics, not the chlorophyll field.
```
**And L118:** `| mixed-cadence 3-D flagship (~2-month operator; +0.0026 on true monthly pairs) | +0.432 | +0.365 | survives (-15%) |`
**And L123:** "the mixed-cadence 3-D result holding up while the daily one collapses".

### `:132` — overclaim (canonical fact 7)
> The carbonate system passes independently (pCO2 380.8 emulator vs 380.3 v05 µatm).

**Why:** Retracted in `2026-07-19_emulator_honest_bounds.md`, which strikes the prior claim through and labels it "RETRACTED 2026-07-19 — this reads the number backwards": with Revelle ~10, 0.51 µatm implies a ~0.05% DIC error, i.e. near-persistence. The check passes but is uninformative. DIC (0.376) and ALK (0.305) are the two lowest per-tracer skills.

**Replace with:**
```markdown
The carbonate system passes, but the check is uninformative: with a Revelle factor of ~10, the 0.51 µatm agreement (pCO2 380.8 emulator vs 380.3 v05) implies a DIC error of only ~0.05% over one step — evidence that DIC and ALK are very nearly persistent at this cadence, not that the emulator learned carbonate chemistry. Consistently, DIC (0.376) and ALK (0.305) are the two lowest of the six per-tracer skill scores. Treat this as a null result, not as corroboration. Run `scripts/physics_verify.py` as a third validator — it requires no reference data — before treating any `MAKE` run as usable, and read its checks against a v05 control column, since a check without a baseline cannot separate "learned" from "copied".
```

---

## docs/ecco_darwin_parameter_inventory.md

### `:64` — overclaim
> Replacing such scalars with MLP-predicted spatial fields … is a structurally cheap upgrade per parameter that reaches well past the Green's functions ceiling

**Why:** No result in this repo supports "reaches well past". `2026-06-24_rpicpoc_ratio_target_fix.md`:80-85 characterizes a ceiling *at* six ("No scalar or per-AOI weighting, and no extra epochs, satisfies all six robustly"). A repo-wide grep finds no >6-parameter recovery; `nvidia_nebius_fix_list.md:84` calls Carroll-103 "the multi-year follow-on direction," and `2026-05-21_jon_meeting_brief.md:15` says the other ~94% "we leave there too." This sentence is the doc's scoping argument.

**Replace with:**
```markdown
Replacing such scalars with MLP-predicted spatial fields, which is what DarwinDiff's parameter-learner does, removes the *cost* barrier that confines Green's functions to a handful of parameters at a time: an additional parameter costs an extra channel on the MLP head rather than a fresh ensemble of recompiled forward runs. Whether that converts into more *recovered* parameters is unproven. DarwinDiff has so far only targeted the same Carroll-6, and its own results characterize a structural ceiling there — 8 lever classes all show the same R_PICPOC/iron ↔ growth-pair trade, and no weighting or epoch budget satisfies all six robustly (`docs/findings/2026-06-24_rpicpoc_ratio_target_fix.md`). Identifiability is also parameter-specific rather than uniformly cheap: the per-cell-vs-global ablation shows per-cell fields are load-bearing for only some parameters, and `diatomgraz` has a flat profile-likelihood (span 0.039) absent dense POSi. Extending past the six is a scoping hypothesis and a multi-year follow-on direction, not a demonstrated capability.
```

---

## docs/findings/2026-07-13_global_monthly_emulator.md (cont.)

### `:20` — stale-number (canonical fact 1)
> Anomaly-R² vs. climatology | +0.391 | +0.766 | +0.762 | +0.406 | +0.349 | +0.610 | +0.245

**Why:** All climatology-relative numbers were computed against month-of-year bins from the 0.75× `times_days` axis; 150/158 timesteps (94.9%) land in the wrong bin. Measured inflation elsewhere is +0.374 to +0.777 (k8), up to +12.5 (k1). Worse: the 2026-07-19 caveat at L27 *endorses* this row as the trustworthy climatology co-report.

**Replace with:**
```markdown
| Anomaly-R² vs. climatology (**RETRACTED — see note**) | ~~+0.391~~ | ~~+0.766~~ | ~~+0.762~~ | ~~+0.406~~ | ~~+0.349~~ | ~~+0.610~~ | ~~+0.245~~ |

> **CORRECTION (2026-07-19) — the anomaly-R² row is invalid.** These values were scored against a
> month-of-year climatology whose bins were derived from the `times_days` axis, built at 900 s
> instead of v05's true 1200 s (fixed at root in PR #186; pre-2026-07-19 cubes are **not**
> retroactively corrected). Every cube time is 0.75× truth and the month-of-year bins are wrong for
> 150 of 158 timesteps (94.9%). A mis-binned climatology degenerates toward a time-mean, i.e. a
> **baseline that is too weak**, so all six per-tracer values and the overall +0.391 are
> **overstated by an unquantified amount**. Measured inflation elsewhere ranges **+0.374 to +0.777**
> (k8) and up to **+12.5** (k1) — the correct values are not recoverable by subtracting a constant,
> and this row should not be quoted until re-scored. Two further caveats: (a) the validation set has
> a **median gap of 61 days**, so these are **~2-month-operator** numbers; (b) the
> skill-vs-persistence row above is calendar-free and **unaffected**. See
> `2026-07-19_results_matrix.md` (row C4).
```

### `:22` — contradicts canonical facts 1 & 3
> **Grid:** 680 × 1441 (0.25° global, latitude −80° to 89.75°); 456,873 valid ocean cells; 156 months.

**Why:** "156 months" asserts a contiguous monthly series. The corrected recount gives 158 timesteps, only 48.4% genuinely one month apart (median 59 d, max 212 d). A contiguous monthly series over the 26.83-yr span would be 323 steps. These are steps, not months. (No committed artifact confirms 156 vs 158 for *this* pre-seam-correction cube, so preserve the stored count and fix only the unit.)

**Replace with:**
```markdown
- **Grid:** 680 × 1441 (0.25° global, latitude −80° to 89.75°); 456,873 valid ocean cells; **156 timesteps — not 156 contiguous months.** **Caveat (2026-07-19):** the cube's stored `times_days` axis was built with a 900 s timestep; v05 runs at 1200 s, so every stored time is 0.75× the truth (derive time as `iters * 1200 / 86400`). Recomputed on the correct axis, the six-tracer intersection cube spans 26.83 years with non-uniform spacing (median 59 d, max 212 d); only ~48% of consecutive pairs are genuinely one month apart. **The learned operator is therefore not a one-month operator**, and every horizon label in this document is a **step count, not a month** (median validation step ≈ 61 d ≈ 2.0 months). See `2026-07-19_emulator_honest_bounds.md` and `src/darwindiff/llc270_loader.py` (fixed in PR #186).
```

### `:36` — overclaim (canonical fact 4)
> **Seed variance — the headline is bankable.** Five seeds at modes 32 / width 64 give **+0.5165 ± 0.0023**

**Why:** Seed variance measures reproducibility of a training procedure, not validity of the metric's label. "Bankable" asserts safety to build on; the same flagship scores +0.0026 on true one-month pairs (per-seed [0.0107, 0.0314, −0.0344], one seed negative). (The +0.5165 is linear-space mixed-val and the +0.0026 log-space uniform-val, so it is not a like-for-like deflation — the replacement says so.)

**Replace with:**
```markdown
**Seed variance — reproducible, but see the Δt caveat below.** Five seeds at modes 32 / width 64 give
**+0.5165 ± 0.0023** (linear space; seeds: +0.5204, +0.5139, +0.5165, +0.5146, +0.5170). The result is not a
lucky seed; the spread is ±0.5% of the mean.

> **CAVEAT (2026-07-19) — this is not a monthly operator.** The seed spread measures the
> *reproducibility of the training procedure*, not the validity of the metric's label. The validation
> pairs have a **median gap of ~61 days**, so every "single-step" number here describes a **~2-month
> operator**. In the 2×2 Δt experiment (`2026-07-19_two_negatives.md`), this same flagship
> configuration scores **+0.0026 on true one-month pairs** (log space, per-seed [+0.0107, +0.0314,
> −0.0344], one seed negative), while a model trained on the *same number* of genuinely one-month
> pairs scores **+0.4756**. Those figures are log space and the +0.5165 headline is linear, so they
> are not a like-for-like deflation — but the direction is unambiguous: at true monthly cadence this
> configuration is indistinguishable from persistence. Δt-uniformity, not seed count or data volume,
> is the lever.
```

### `:74` — stale-number (canonical fact 1)
> Persistence skill relative to climatology is −0.27 globally, compared with +0.22 over the equatorial Pacific and +0.98 at daily cadence

**Why:** All three are climatology-relative and therefore corrupted-binning numbers, used here to argue persistence is a weak global baseline — i.e. to justify reading +0.520 as a genuine gain. Because inflation varies by configuration, the cross-region *ordering* the paragraph depends on cannot be recovered from these values.

**Replace with:**
```markdown
2. **Persistence is a weaker baseline globally than in the equatorial-Pacific subdomain — but the numbers that supported this are retracted.** This finding previously read "Persistence skill relative to climatology is −0.27 globally, compared with +0.22 over the equatorial Pacific and +0.98 at daily cadence." **All three figures are withdrawn (2026-07-19).** They are skill-vs-climatology scores computed against a corrupted month-of-year binning: `rollout_verify.month_of_year()` derived its bin from `times_days`, built at 900 s where v05 runs at 1200 s, so 150 of 158 timesteps (94.9%) landed in the wrong bin. The resulting "climatology" is much closer to a time-mean — a baseline that is too weak, which **inflates** skill-vs-climatology (measured inflation +0.374 to +0.777). Because inflation varies by configuration, the *relative* ordering across region and cadence does not survive either: it cannot be asserted from these numbers that persistence is a weaker baseline globally than over the equatorial Pacific. That comparison requires a re-run on the corrected `iters * 1200 / 86400` axis and has not been done. Until then, the +0.520 headline should be read as **skill vs. persistence in linear space only** — a calendar-free metric — and not as evidence of a gain over a seasonal baseline. The load-bearing claim that survives is the sign and uniformity of the persistence-relative result.
```

### `:76` — no-committed-artifact
> see `docs/findings/emulator_*_scored.md`, distinct from the +0.22 persistence-vs-climatology figure

**Why:** The pointer is dangling: the glob matches zero files at HEAD or on main. The two matching files exist only on the unmerged `overnight/2026-07-10-experiments` branch, and one states "Local-only — not committed to GitHub." **But** the claim it supports *is* backed by committed files — this is a stale cross-reference, not an unsupported number. Redirect the citation; do not weaken the claim.

**Replace with:**
```markdown
see `docs/findings/2026-07-13_daily_surface_emulator.md` and the metric-space controls table in `docs/findings/2026-07-19_results_matrix.md` §1, distinct from the +0.22 persistence-vs-climatology figure
```

### `:98` — contradicts canonical fact 2
> beating persistence on all six tracers with a stable multi-step rollout, and runs natively on the B200.

**Why:** "Stable" is contradicted by the doc's own numbers two lines below the caveat — max relative mass drift 1.008 and max negative fraction 0.41. The L27 caveat opens with "Rollout: stable over six steps" and qualifies only the persistence-relative framing. Per fact 2 the emulator is at or below climatology from step 2. Same phrasing at L79 as "the load-bearing claim." (The sibling `2026-07-13_daily_surface_emulator.md:47` was already patched; this doc was missed.)

**Replace with:**
```markdown
beating persistence on all six tracers at a single step, and runs natively on the B200. The six-step rollout is persistence-relative only and is not stable in the physical sense: the worst tracer's domain mean drifts by approximately its own magnitude (maximum absolute relative mass drift 1.008; maximum negative fraction 0.41), and no climatology baseline is co-reported for the rollout. Against a correctly-binned seasonal climatology the emulator's useful horizon is one step, so the multi-step result must not be read as a multi-month horizon.
```

---

## docs/findings/2026-07-13_daily_surface_emulator.md

### `:28` — stale-number (canonical fact 1)
> persistence skill vs. climatology ≈ +0.95, compared with +0.22 at monthly cadence over the same region

**Why:** Both are climatology-relative and inflated (measured +0.374 to +0.777, up to +12.5). They frame the doc's entire premise — "persistence is a near-perfect baseline" — so the framing that makes +0.408 impressive rests on a baseline the delta_t fix invalidated. The doc's only correction banner (2026-07-16) predates the calendar-bug discovery. Bonus defect: "+0.22 at monthly cadence" violates fact 3.

**Replace with:**
```markdown
At daily cadence, persistence is a very strong baseline, because consecutive days barely differ — the emulator's job is to add value on top of near-perfect autocorrelation, not to beat a seasonal mean.

> **Retracted framing (2026-07-19):** this section previously quantified that premise as "persistence
> skill vs. climatology ~ +0.95, compared with +0.22 at monthly cadence over the same region." **Both
> numbers are withdrawn.** They were scored against a climatology binned by month-of-year derived from
> the corrupted time axis (`delta_t` was 1200 s, not 900 s; ~94% of month bins misassigned), which
> makes the climatology behave like a time-mean and therefore **overstates any skill-vs-climatology
> figure** — measured inflation on comparable numbers ranges +0.374 to +0.777 (k8) and up to +12.5
> (k1). The "+0.22 at monthly cadence" label is separately wrong: the validation set has a **median
> gap of 61 days**, so that figure describes a ~2-month operator. The *qualitative* premise — daily
> persistence is a harder baseline to beat — survives; the magnitudes do not, and no corrected values
> have been computed. See `2026-07-19_emulator_honest_bounds.md`. The persistence-relative skill below
> (+0.408) is calendar-free and unaffected, though still subject to the linear-vs-log correction above.

Can the emulator beat it, and is a daily next-step surrogate worth building?
```
**Also affected in the same file:** L44 (anomaly-R² +0.973) and L68 (+0.97).

### `:70` — overclaim (canonical fact 2)
> the value it adds over persistence is real but modest, and is likely to be larger over multi-day rollout horizons than in single-step prediction.

**Why:** A forward extrapolation with no supporting measurement, running the wrong way against fact 2 — and contradicted by the doc's own L47 ("should not be extrapolated to longer horizons"). `2026-07-19_emulator_honest_bounds.md`:246: at 12 months the rollout reads +0.441 vs persistence *while* −0.265 vs climatology. The persistence-relative margin widens because persistence degrades faster, not because the emulator adds value — exactly the masking artifact L47 warns about.

**Replace with:**
```markdown
the value it adds over persistence is real but modest in single-step prediction. **No multi-day rollout skill was measured here against climatology, so nothing can be said about how that value scales with horizon.** The later global-monthly rollout audit (`2026-07-19_emulator_honest_bounds.md`) shows why the intuitive expectation is unsafe: skill *vs. persistence* does widen with horizon (+0.441 at 12 months) precisely while skill *vs. climatology* goes negative (−0.265) — the widening is persistence degrading, not the emulator adding value. Any longer-horizon claim for this configuration requires a climatology-co-reported rollout evaluation that has not been run.
```
**Also:** L77-78 ("where the emulator's advantage over persistence should widen") carries the same defect.

---

## docs/findings/2026-07-19_emulator_honest_bounds.md (cont.)

### `:17` — no-committed-artifact
> All numbers below were re-derived from the raw result JSONs on `/scratch/qi_zim_neu/` on 2026-07-19, not copied from prior prose. Provenance is given per section.

**Why:** `git ls-files` finds none of `physics_3d.json`, `cal_ab.json`, `de3d_ensemble.json`, `de_eqpac_ensemble.json`, `eqpac_ctl_linear.json`, `eqpac_ctl_log.json`, `d3_ctl_log.json`, `bench.json`. A repo-wide grep for the headline values (0.240, 0.0361, 1.89) returns nothing. `cluster_setup.md:284` confirms `/scratch/qi_zim_neu` is 30-day purge, no backup. The sentence is not false — it honestly names its source — but it asserts rigor while the provenance chain is self-deleting. The fix is a disclosure, not a retraction.

**Replace with:**
```markdown
All numbers below were re-derived on 2026-07-19 from the raw result JSONs written by the cluster jobs, not copied from prior prose. Provenance is given per section by filename.

**Reproducibility caveat — these artifacts are NOT in the repo.** Every result JSON cited below (`physics_3d.json`, `cal_ab.json`, `de3d_ensemble.json`, `de_eqpac_ensemble.json`, `eqpac_ctl_linear.json`, `eqpac_ctl_log.json`, `d3_ctl_log.json`, `bench.json`) lives only on `/scratch/qi_zim_neu/`, which is a **30-day-purge, un-backed-up volume** (see `docs/cluster_setup.md`). Once purged, no number in this document can be re-checked against its source. Until these JSONs are committed under `docs/findings/`, treat every headline here as **unverifiable from the repo alone** — the same reproducibility gap the companion diatomgraz audit names as a standing project error mode. Re-deriving the numbers honestly is necessary but not sufficient; the artifact must survive.
```

### `:247` — stale-number
> At 12 months the single-step rollout reads **+0.441 vs persistence** (looks strong) and **−0.265 vs climatology** (worse than the seasonal mean).

**Why:** −0.265 is a buggy-calendar climatology number quoted bare, 120 lines after this doc states the defect "affects every skill-vs-climatology number this project has reported" and five lines before its own corrected k1 table gives −4.582 at 6 steps and −27.065 at 12. Understates the drift by one to two orders of magnitude, in the paragraph arguing climatology must be co-reported. "12 months" is also 12 steps ≈ 24 months elapsed.

**Replace with:**
```markdown
The historical illustration of this problem quoted **+0.441 vs persistence** and **−0.265 vs climatology** at a nominal "12-month" horizon (linear space, 2026-07-14 rollout diagnostic). **Both halves of that label are now known to be wrong.** The climatology figure was scored against bins built on the buggy 900 s calendar, and the horizon was a step count, so the nominal "12 months" was ~24 months elapsed. On the corrected calendar the single-step (k1) arm reads **−4.582 vs climatology at 6 steps (~11.8 months)** and **−27.065 at 12 steps (~23.7 months)**. The drift is one to two orders of magnitude larger than the old number implied. (The corrected table is LOG space and the superseded pair was linear, so the two are not strictly commensurate; the sign and order of magnitude are not in question.) Every long-horizon Track-2 number quoted historically is vs persistence. **Long-horizon skill reported against persistence alone is misleading and must co-report a correctly-binned climatology.**
```

### `:315` — contradicts canonical fact 2
> A century in 9 seconds is worthless when the trajectory reaches the climatology floor at ~9–12 months.

**Why:** The corrected table has the floor at step 2 (−0.018, ~3.9 months elapsed). "~9–12 months" traces to the OLD buggy-bin column (+0.253 at 9 steps, +0.028 at 12). The rhetorical point survives; the horizon is the retracted one.

**Replace with:**
```markdown
**This does not matter.** A century in 9 seconds is worthless when the trajectory falls to the climatology floor after a single ~2-month step (+0.240 at step 1; −0.018 by step 2, ~3.9 months elapsed). Speed was never the bottleneck; rollout fidelity is.
```

### `:330` — contradicts canonical fact 2
> The ~9-month figure is a bound to be re-measured on a longer split, not a precision estimate.

**Why:** Treats ~9 months as surviving-but-imprecise. It is retracted outright — the corrected table has it at −0.292 at 9 steps. The legitimate part of the bullet (n_starts=15 on a 47-month split) survives; only the framing is the defect.

**Replace with:**
```markdown
- **The long-horizon numbers rest on limited independent starts.** n_starts=15 on a 47-month val split still means overlapping trajectories at long lead. This limits the confidence interval on the *corrected* numbers — it is not a reason to expect a longer horizon to reappear. The ~9-month horizon is retracted outright, not merely imprecise: against a correctly binned seasonal climatology the emulator beats the baseline at one step only (+0.240, ~2 months), is at zero by two steps (−0.018), and is −0.292 at 9 steps. A longer split would sharpen the error bars on those values; it would not restore a multi-month bound.
```

---

## docs/findings/2026-07-14_emulator_loop.md (cont.)

### `:6` — contradicts canonical fact 3
> Headline baseline: global-monthly (surface) skill vs persistence **+0.5204** (seed 0), bankable at **+0.5165 ± 0.0023** over n=5 seeds

**Why:** Four dated 2026-07-19 correction blocks in this file address metric space, the ceiling claim, and persistence-vs-climatology — none mentions cadence. L78 actively re-endorses these values in the present tense. `2026-07-19_emulator_honest_bounds.md`:342 lists the identical numbers against a cube with median validation step 61 days.

**Replace with:**
```markdown
Headline baseline: single-step (surface) skill vs persistence **+0.5204** (seed 0), reproducible at **+0.5165 ± 0.0023** over n=5 seeds. **Cadence caveat (2026-07-19): despite the "monthly" label, this is NOT a one-month operator.** The stored cube is not a contiguous monthly series — the validation split has a **median step of 61 days**, so every "single-step" number below describes a **~2-month** transition. On true uniform one-month pairs this flagship scores **+0.0026** (vs **+0.4756** for a uniform-dt-trained model). Read "global-monthly" throughout this document as "one step of the stored cube ≈ 2 months".
```

### `:26` — stale-number
> the **persistence** baseline alone flatters long-horizon results (at 12 months persistence reads +0.441 while climatology reads −0.265), so co-report climatology.

**Why:** −0.265 is a pre-fix climatology number; the corrected calendar A/B (job 167823) gives −27.065 for k1 and −0.748 for k8 at 12 steps. Repeated three times in this doc (L26, L42, L75), each time inside a passage arguing for honest baselines. The magnitude is load-bearing: −0.265 reads as "mildly worse than the seasonal mean" when the truth is catastrophic divergence.

**Replace with:**
```markdown
the **persistence** baseline alone flatters long-horizon results — but the "+0.441 vs persistence / −0.265 vs climatology at 12 months" pair once quoted here is **RETRACTED (2026-07-19)**: it was scored against a climatology binned with the buggy 900 s `delta_t`, which puts 93.7% of month bins in the wrong bin. Against a correctly-binned seasonal climatology (`delta_t` = 1200 s; job 167823, `cal_ab.json`), 12 *steps* is ~23.7 months, where the single-step (k=1) rollout reads **−27.065** (mass ratio 3.05 × 10⁸ — diverged) and the rollout-trained k=8 arm reads **−0.748**. The emulator beats a true seasonal climatology at **one step (~2 months, +0.240)** only. So co-report climatology — the corrected numbers make that case far more starkly than the figures originally cited here.
```

---

## docs/findings/2026-07-14_3d_emulator.md

### `:9` — contradicts canonical fact 3
> **Verdict: MAKE. Overall skill vs persistence +0.507 (linear space)** (mean per-channel +0.396, linear space).

**Why:** L3 frames this as a "depth-resolved global-monthly emulator"; +0.507 is a single-step score on the 158-timestep cube where only 48.4% of pairs are one month apart. The MAKE verdict is issued on a number whose cadence label is wrong by ~2×. The doc's single commit is itself a retroactive-correction pass, so it is live and amendable. (The +0.0026 was measured on the *surface* flagship — cite it as a shared-cube inference, not this run's measurement.)

**Replace with:**
```markdown
- **Verdict: MAKE. Overall skill vs persistence +0.507 (linear space, single step)** (mean per-channel +0.396, linear space).
  - **Cadence label — this is not a monthly operator.** The +0.507 is a *single-step* score on the 158-timestep cube, of which only **48.4% of pairs are genuinely one month apart** (median gap 59 d; median 61 d on the validation split). Like every single-step number in this project, it describes a **~2-month operator**, and the "global-monthly" framing above is wrong by roughly 2×. On the surface flagship — same cube, same mixed-Δt structure — the identical training configuration scores **+0.0026 vs persistence on genuinely one-month pairs**, versus **+0.4756** for a uniform-Δt-trained model (`2026-07-19_two_negatives.md`). That control has **not** been run for this 3-D configuration, so do not transfer the number; but the shared cube means the cadence caveat applies here in full. **The MAKE verdict is established at ~2-month cadence only; skill at true monthly cadence is unproven for this run.**
```

---

## docs/findings/index.md

### `:18` — stale-number
> the PIC:POC ratio observable recovers `R_PICPOC` in eqpac without the iron-pair mutex; the ≥2-AOI wall is calcite forward-model fidelity.

**Why:** The causal attribution was refuted nine days later. A grep of index.md for "ratio_target_fix", "RATIO_MAX", "2026-06-24" returns zero hits — the index does not even link the superseding result. Unlike the version-milestone entries, this line carries no date or version tag and reads in present tense.

**Replace with:**
```markdown
- [Ratio loss (structural)](rpicpoc_ratio_structural.md) — **SUPERSEDED (2026-06-24, causal attribution only).** The PIC:POC ratio observable recovers `R_PICPOC` in eqpac without the iron-pair mutex; the eqpac-only limit was originally attributed to calcite forward-model fidelity, but that attribution is refuted below. The ratio-loss mechanism itself stands.
- [Ratio-target fix — the R_PICPOC wall broken](2026-06-24_rpicpoc_ratio_target_fix.md) — the ≥2-AOI wall was a **data-pipeline bug, not missing calcite physics**: the Southern-Ocean ratio target was contaminated by near-zero-POC cells (per-cell `pic/poc` up to ~1e8, target mean 4.7e7), inflating the `mean(target²)` scale normalizer and collapsing the SO ratio term to ~0. With `RATIO_MAX=2`, `R_PICPOC` recovers **10/10 joint Cal, genuine per-AOI across all three AOIs** (`verify_run.py` exit 0). First 6/6 follows but is **not robust** (3/10 seeds).
```

---

## docs/findings/alk_anchor_rpicpoc_mutex.md

### `:260` — stale-number
> This is the **same conclusion as the PIC anchor reached** (R_PICPOC is box-scale unidentifiable), via a subtler failure mode.

**Why:** `2026-06-24_rpicpoc_ratio_target_fix.md` reports R_PICPOC ≈0.030-0.046 vs Carroll 0.0425, 10/10 joint Cal with no straddle, robust across cap 2-5 — at box scale. It was unidentified under a contaminated observation, not unidentifiable. The ALK-specific null is still valid; only the generalization needs retracting.

**Replace with:**
```markdown
This is the **same conclusion as the PIC anchor reached** — absolute-magnitude anchors (PIC, ALK) give no box-scale handle on the `R_PICPOC` / `mort_total` split — via a subtler failure mode. **[Retracted 2026-06-24, general claim only:** the broader reading that `R_PICPOC` is box-scale *unidentifiable* does not hold. `docs/findings/2026-06-24_rpicpoc_ratio_target_fix.md` shows the PIC:POC **ratio** observable does identify it at box scale once the Southern-Ocean ratio target is decontaminated of near-zero-POC cells (`RATIO_MAX=2`): `R_PICPOC` ≈ 0.030–0.046 vs Carroll 0.0425, **10/10 joint Cal with genuine per-AOI recovery — no straddle**, robust across the ratio cap 2→5 and weight 1→2. The wall was a contaminated observation, not an information limit. The ALK-anchor null documented here stands as written — ALK is informationally equivalent to PIC for this split — and so does the methodological catch about cell-weighted straddling; only the generalization to "box-scale unidentifiable" is retracted. Note also that the 6/6 achieved there is *not* robust (3/10 seeds); the residual wall is the growth pair {Smallgrow, Biggrow}.]**
```

### `:261` — uncited-gate-on-spend (canonical fact 9)
> It **strengthens** the cluster-gated / AICR framing rather than weakening it.

**Why:** A NULL box-scale result converted into positive support for cluster spend with no evidence that scale is the binding constraint. Falsified 9 days later at the *same* 1° box, *same* 3-AOI v3.2 Eppley operating point. Fact 9 (learning curve flat from n=55) further undercuts volume as the lever. L263-266 immediately double down ("stands and is now *better* supported").

**Replace with:**
```markdown
It does **not**, by itself, license any inference about compute scale. This experiment tested one observable (absolute ALK) and found it informationally equivalent to PIC for the `R_PICPOC` / `mort_total` split; that is a statement about the observable, not about resolution, seed count, or data volume, and no evidence here identifies scale as the binding constraint.

**Superseded in part (2026-06-24):** `R_PICPOC` recovers **10/10 joint Cal, genuine per-AOI (no straddle), R_PICPOC ≈ 0.030–0.046 vs Carroll 0.0425** at this **same 1° box scale and the same 3-AOI v3.2 Eppley operating point**, once a contaminated Southern-Ocean PIC:POC ratio target (target mean 4.7e7) is capped at a physical rain ratio (`RATIO_MAX=2`). `R_PICPOC` was never fundamentally unidentifiable — the wall was a contaminated observation in the loss, so the "exhaustive box-scale exclusion" framing above does not hold. The residual constraint is a structural loss-landscape tradeoff — {R_PICPOC, iron pair, diatomgraz} **or** the growth pair, not all six — and longer training makes it worse. Volume is likewise not the lever: the learning curve is flat from n=55.
```

### `:265` — overclaim
> exhaustive box-scale exclusion") stands and is now *better* supported (a 7th exclusion: real + model alkalinity, absolute-anchored, across a dose sweep).

**Why:** "Exhaustive box-scale exclusion" claims the search space is closed after 7 exclusions. The 8th lever tried (`RATIO_MAX=2`) broke the wall outright, and none of the 7 tested the observation-quality axis that mattered. Counting exclusions is not evidence of exhaustiveness.

**Replace with:**
```markdown
**Decision: NO-GO on adding a line to the talk.** The alkalinity anchor supplies no independent handle on the `R_PICPOC × mort_total` split. This is the 7th box-scale lever excluded — but "exhaustive box-scale exclusion" overstates it: seven negative results are inductive evidence that the *tested* levers fail, not proof that the box-scale search space is closed. The deck's framing should read "R_PICPOC is the sole 6/6 wall, cluster-gated, with seven box-scale levers excluded to date."

> **SUPERSEDED (2026-06-24) — the wall is broken, and it was broken by a box-scale lever.**
> `docs/findings/2026-06-24_rpicpoc_ratio_target_fix.md`: the Southern-Ocean PIC:POC
> ratio-loss target was contaminated by near-zero-POC cells (per-cell `pic/poc` up to
> ~1e8, target mean 4.7e7), which inflated the loss-scale normalizer and silently
> collapsed the SO ratio term to ~0. Capping the target (`RATIO_MAX=2`) recovers
> `R_PICPOC` **10/10 joint Cal, genuine per-AOI (no straddle)** on this same 1° 3-AOI
> Eppley config, and produced the project's first 6/6. The 8th lever was an
> *observation-quality* axis that none of the seven exclusions probed — which is
> precisely why counting exclusions never established exhaustiveness. Current canonical
> framing (STATUS.md): **"`R_PICPOC` was never a '6/6 wall.'"**
>
> **What survives:** the alkalinity null itself. The per-AOI straddle decomposition, the
> Darwin-ALK-source control (a100d), and the dose sweep (a300) remain valid. The
> methodological catch below (report `R_PICPOC` recovery per-AOI, not only as the joint
> cell-weighted mean) is unaffected, and proved load-bearing for grading the RATIO_MAX arms.
```

---

## docs/findings/compute_time_compiled_h200.md

### `:7` — overclaim
> **Per-epoch cell-fit** `t = a + b·cells` @ 200 steps: a = 40.9 ms, b = 17.5 ns/cell, R² = 0.2142 (n=8).

**Why:** b×105,300 cells = 1.84 ms, 4.5% of the 40.9 ms intercept, while two identical 10,000-cell repeats differ by 1.2 ms. R²=0.214 at n=8 gives p≈0.25. Decisively, the generating script's own docstring (`measure_compute_time.py:184-185`) says the fit's purpose is a *regime* diagnostic — "b·cells << a across the swept range => flat / launch-bound" — but the markdown template (L233-236) emits a, b, R² and drops the interpretation. Extrapolating b to LLC270's 947,700 cells yields a 16.5 ms cell term the data cannot support.

**Replace with:**
```markdown
- **Per-epoch cell-fit** `t = a + b·cells` @ 200 steps: a = 40.9 ms, b = 17.5 ns/cell, R² = 0.2142 (n=8). **Read this as flat — the slope is not resolved above run-to-run noise, and `b` is not a usable scaling law.** Across the full swept range b·cells = 1.8 ms at 105,300 cells, i.e. 4.5 % of the 40.9 ms intercept, while two repeats of the identical 10,000-cell config differ by 1.2 ms — the entire fitted cell effect over a 37× size increase is comparable to the replicate spread of a single config (R² = 0.21 at n = 8 is not statistically significant). The regime is therefore **launch-bound** (b·cells ≪ a): a 37× increase in cells (2,853 → 105,300) moves the epoch only 38.5 → 42.4 ms, so per-epoch cost is set by kernel-launch / Python-loop overhead, not problem size. Do not extrapolate `b` beyond the swept range; the measured claim is flatness, not a per-cell coefficient.
```
**Note:** this file is generated — `scripts/measure_compute_time.py:233-236` needs the same fix or regeneration reintroduces the bare coefficients.

---

## docs/findings/memory_scaling_compiled.md

### `:9` — overclaim
> **Fit** `peak = a + b·(cells·steps)`: a = 13.1 MB, b = 82.9 B per cell·step, R² = 0.99485 (n=20).

**Why:** Two of the 20 rows are compile-warmup artifacts: at 2,000 cells the train peak *falls* from 72.2 MB (50 steps) to 17.9 MB (100 steps), and their forward-only peaks are 109× and 55× the same-cell-count values elsewhere. `measure_memory_scaling.py:193` compiles fresh per call with no warmup pass. Refitting without them: a = 4.17 MB, b = 84.30, R² = 0.99969. The slope survives (1.7% shift); the intercept and R² are artifacts.

**Replace with:**
```markdown
- **Fit** `peak = a + b·(cells·steps)`, compile-warmup rows excluded: a = 4.2 MB, b = 84.3 B per cell·step, R² = 0.99969 (n = 18). The 2,000×50 and 4,000×50 rows are **dropped**: their forward-only peaks (63.4 / 63.8 MB) are 109× and 55× the same-cell-count values at larger step counts, and their train peaks *fall* as steps double (72.2 → 17.9 MB; 81.6 → 35.6 MB). That is the first-shape `torch.compile` autotune allocation — the script builds a fresh compiled step per call with no warmup pass — not a memory law. Fitting all 20 rows inflates the intercept to 13.1 MB and drops R² to 0.99485. The slope is insensitive to the choice (82.9 vs 84.3 B per cell·step), and the intercept is <1% of every prediction below, so the extrapolations are unchanged either way.
```

---

## docs/findings/posi_dense_diatomgraz.md (cont.)

### `:3` — stale-number
> recovers the iron pair + `diatomgraz` together — best 3-AOI recovery in the project, reproducible at n=20.

**Why:** mean 3.85/6 with 0/20 at 6/6 is no longer the project best. The 2026-06-24 scheduled-ratio arm ran the *same* 3-AOI config and reached mean cal 4.7 with per-AOI 10/10 on four parameters plus the first strict per-AOI 6/6 — and every number there is verify_run-gated, which these laptop runs are not (one arm was interrupted by laptop sleep at ~epoch 750). Repeated at L109.

**Replace L3 with:**
```markdown
**Date:** 2026-06-11 · **Status:** valid prior result; the recovery headline is **SUPERSEDED** by `docs/findings/2026-06-24_rpicpoc_ratio_target_fix.md`. Dense POSi recovers `diatomgraz` (n=10 dose sweep); **Eppley temperature limitation breaks the `alpfe`↔silica mutex and recovers the iron pair + `diatomgraz` together — mean 3.85/6, 0/20 at 6/6, reproducible at n=20.** These are ungated laptop runs. The 2026-06-24 scheduled-ratio arm, on this same 3-AOI Eppley config and gated through `scripts/verify_run.py` (exit 0), is the project best: mean cal 4.7, per-AOI 10/10 on `R_PICPOC`, `alpfe`, `scav_rat` and `diatomgraz` simultaneously, and the first strict per-AOI 6/6.
```
**And L109 (item 6):**
```markdown
6. **Best multi-AOI recovery as of 2026-06-11 — since superseded.** mean 2.00 (baseline) → 3.85/6, 70% of seeds ≥4/6, and the first *reproducible* 5/6 events at 3-AOI. `scav_rat` now lands in 20/20. The 2026-06-24 `RATIO_MAX` fix later beat this on the same 3-AOI config (mean cal 4.7, four parameters per-AOI 10/10, first strict per-AOI 6/6, `verify_run.py` exit 0), so this is no longer the project best.
```

---

## docs/findings/pre_scaleup_verification.md (cont.)

### `:43` — no-committed-artifact
> **Memory scaling holds at 5×.** Measured **21.24 GB at 64M cell·step** vs **21.25 GB predicted** by the 356 B/(cell·step) fit … (The harness + fit live on the unmerged PR #102 branch.)

**Why:** PR #102 merged (`feba052`) — the harness and fit *are* committed, so the parenthetical hedge is itself stale — but `memory_scaling.json` tops out at 12.8M cell·step / 4.25 GB, 5× smaller than the claimed validation point. `git grep` across all reachable commits finds no artifact that ever held a point beyond 12.8M. The arithmetic is self-consistent (the run plausibly happened), but the output was never committed. Load-bearing: it is what shrinks the LLC270 gap 14.8× → 2.96× and sizes the B200 ask.

**Replace with:**
```markdown
- **Memory scaling at 5× — measured once, artifact not committed.** A laptop run at
  **64M cell·step** (160,000 cells × 400 steps) reported **21.24 GB peak**, against
  **21.25 GiB predicted** by the committed 356.44 B/(cell·step) eager fit
  (reproducible from `docs/findings/memory_scaling.json`).
  **Caveat — this datapoint has no committed artifact.** The committed sweep
  (`scripts/measure_memory_scaling.py`, `memory_scaling.json`, merged in PR #102 /
  `feba052`) tops out at 32,000 cells × 400 steps = **12.8M cell·step / 4.25 GB**, and no
  JSON, CSV, or figure anywhere in repo history records the 64M point. Treat "the linear
  law does not bend at 5×" as **unverified pending re-run** — and with it the claimed
  shrink of the LLC270 extrapolation gap from 14.8× to 2.96×. Until the sweep is re-run
  with `--cells 160000 --steps 400 --out` and the JSON committed, the defensible
  extrapolation anchor is the 12.8M measured max, i.e. a **14.8× gap**. NB `torch.compile`
  cannot run on this Windows laptop, so these are *eager* upper bounds; the compiled
  constant was later measured on Explorer H200 at **82.9 B/(cell·step)**, 4.3× below eager,
  which supersedes the 356-based figures for sizing the B200 ask.
```

---

## docs/findings/rpicpoc_ratio_structural.md (cont.)

### `:82` — no-committed-artifact
> `%LOCALAPPDATA%\ddeck\alkabs\campaign_rpicpoc.py` → `D:\runs\rpicpoc_camp\`, 21 arms, per-AOI scored. **Result: 0/10 co-recovery … in every arm**

**Why:** The 25-arm exclusion — the doc's central evidence — has no committed artifact. `git ls-files` shows no `campaign_rpicpoc.py`, `probe_ratio_gradient.py`, or `probe_seasonal_feasibility.py` (the latter two supply the "∂(ratio)/∂R_PICPOC ≈ 1" and "max|Δ| = 0.000" claims at L27 and L69). No run JSON anywhere. None gated through `verify_run.py`. The `RATIO_W` loss itself *is* committed — only the campaign evidence is missing.

**Replace with:**
```markdown
`%LOCALAPPDATA%\ddeck\alkabs\campaign_rpicpoc.py` → `D:\runs\rpicpoc_camp\`, 21 arms,
per-AOI scored. **Recorded result: 0/10 co-recovery (R_PICPOC + iron pair Cal in ≥2
AOIs) in every arm** — combined with the r2/r10/r2c/r10c sweep, 25 structural arms.

> **Provenance caveat — UNVERIFIED, and SUPERSEDED.** Neither the campaign driver
> (`campaign_rpicpoc.py`) nor the probe scripts (`probe_ratio_gradient.py`,
> `probe_seasonal_feasibility.py`) is committed to this repo; they exist only under
> `%LOCALAPPDATA%` on one machine. The run JSONs exist only under `D:\runs\`. None of
> these numbers was gated through `scripts/verify_run.py`. The "25 arms, all 0/10"
> exclusion is a lab-notebook record, not a reproducible result, and must not be cited as
> exhaustive evidence. (The `RATIO_W` loss itself *is* committed, in
> `scripts/run_v3.0_joint_multi_aoi.py` — it is the campaign evidence that is missing.)
>
> It has since been **overturned**: `2026-06-24_rpicpoc_ratio_target_fix.md` (all numbers
> gated through `verify_run.py`, exit 0) shows the ≥2-AOI failure was a contaminated
> Southern-Ocean PIC:POC ratio target — near-zero-POC cells drove per-cell `pic/poc` up to
> ~1e8 (target mean 4.7e7), inflating the loss-scale normalizer and silently collapsing the
> SO ratio term to ~0. Capping the target (`RATIO_MAX=2`) recovers R_PICPOC 10/10 per-AOI.
> The conclusion drawn below — that the residual wall is calcite forward-model fidelity —
> does **not** hold as stated.
```

---

## docs/findings/modis_arc/phase2a_modis_pic_integration.md (cont.)

### `:7` — overclaim
> This is a systematic, regime-dependent bias in Darwin v05's PIC field.

**Why:** Treats a satellite retrieval as ground truth while the doc's own Risks section (L190) concedes Balch-Gordon "is known to overestimate PIC in cyanobacteria-dominated regions" and that eqpac — the AOI carrying the 20× headline — is exactly that. The cross-check was later completed and came back against MODIS-as-truth (>25× overestimate vs in-situ). The claim propagated into `run_v3.0_with_modis_pic.py:301` and `sweep_modis_pic.py:4,8`.

**Replace with:**
```markdown
This is a large, regime-dependent discrepancy between the two fields — but its attribution is unresolved, and it must not be read as a demonstrated Darwin v05 bias. MODIS PIC is a Balch-Gordon backscatter retrieval, not ground truth, and it is known to overestimate PIC wherever non-coccolithophore backscatter dominates; eqpac — the AOI carrying the 20× headline — is a high-cyanobacteria regime and is exactly such a case (see §5.1). Treat the ratio as a model-vs-retrieval discrepancy of unknown split. UPDATE (superseding this doc): the cross-check called for in §5.1 was completed and came back against MODIS-as-truth — satellite PIC overestimates in-situ PIC by >25× in high-latitude/diatom regimes (`2026-06-24_rpicpoc_observability_deep_research.md`), and Carroll's v05 targets contain no satellite PIC at all (`2026-06-11_darwin_utilization_audit.md:116`). The MODIS-anchored sweep this doc proposes was run and drove R_PICPOC to ~0.22, roughly 5× ABOVE Carroll's 0.0425, at 0/10 for 5/6 (`master_comparison.md`). The MODIS/PACE anchors are shelved; Sections 3-4 are retained as a record of the reasoning, not as a live plan.
```

### `:184` — stale-number
> Best case: 5/6 or 6/6 with R_PICPOC + alpfe + diatomgraz all Cal-grade. If the hypothesis holds, this is the project's first 6/6 path that doesn't require unreleased PACE PIC.

**Why:** The sweep this section prescribes was executed the same day and came back negative on every arm — 0/30 at 5/6 at W=1.0, 0/10 at low weight. The Status line at L3 still reads "pending application", so a refuted hypothesis is presented as the live forward plan.

**Replace with:**
```markdown
**Hypothesis (as written before the sweep):** with MODIS PIC replacing Darwin v05 PIC, R_PICPOC still lands Cal-grade BUT alpfe + diatomgraz are no longer pulled out.

**REFUTED — 2026-05-19.** The sweep was run the same day and the hypothesis failed on every arm. At W=1.0 (M1/M2/M3) the result is 0/30 at 5/6; at low weight (L1-L4, W=0.01-0.3) it is 0/10 at 5/6, best arm L4 at mean_cal 2.40. R_PICPOC and the basin-A trio never co-recover: with the POC anchor on, R_PICPOC is driven to ~0.2 and lands 0/10; with it off, R_PICPOC recovers 10/10 but biomass collapses (Smallgrow 1/10, Biggrow 2/10). Swapping the observation anchor does not dissolve the 2-basin mutex. See `overnight_2026_05_19.md` §2.3-2.4 and §4.

The project's first 6/6 came later and by a different route — the RATIO_MAX ratio-target fix and the iron-partitioning / loss-weighting correction — not from a satellite PIC anchor. What survives from this document is Section 2: the Darwin-v05-vs-MODIS PIC magnitude diagnostic.
```
**Also replace L3:** `**Status:** SUPERSEDED — the integration sweep this doc prescribes was run on 2026-05-19 and came back negative on every arm. Kept as the design record for the MODIS PIC anchor and for the Darwin-vs-MODIS magnitude diagnostic in Section 2, which stands. See docs/findings/modis_arc/overnight_2026_05_19.md.`

---

# MINOR

### `README.md:100` — stale-number
> [Project status][status_url] — canonical live results, the 5/6 ceiling, known limits

**Why:** `[status_url]` resolves to STATUS.md (README:242), which no longer contains "5/6" anywhere — grep returns zero hits, and the only "6/6" occurrences negate it. The README points readers at STATUS.md for a result STATUS.md has retired.

**Replace with:**
```markdown
- [Project status][status_url] — canonical live results, the 4-observable identifiability target, known limits
```

### `docs/CLAUDE_PROJECT_CONTEXT.md:141` — stale-number
> | 4 | MIT ORCD Engaging cluster — native multi-AOI, partial time-resolved | Free if accepted |

**Why:** Overtaken by events. Explorer H200 and AICR B200 were granted directly, and the Stage-4 deliverable (native LLC270 3-AOI joint fit) already shipped (PRs #122/#123). `cluster_setup.md:14` also flags "AICR = MIT ORCD follow-on" as a conflation — AICR is Northeastern's. The "no skipping" rule at L148 blocks correctly-scoped proposals against a ladder the project stepped off.

**Replace with:**
```markdown
| 4 | ~~MIT ORCD Engaging~~ → **NU Explorer (H200 144 GB ×32)** — native multi-AOI, partial time-resolved | Free (NU RC, access granted June 2026) — **DONE, ladder stepped off here** |

> **Ladder status (2026-07-19).** Stages 4-7 were overtaken by events; this table is retained only as a record of the May-2026 plan. MIT ORCD / Engaging was **dropped** in favour of NU Explorer, and **AICR is Northeastern's** AI Compute Resource (B200), **not** an MIT-ORCD follow-on — the "Engaging first, AICR second" gate no longer applies. Both Explorer (`ssh explorer`) and AICR (`qi_zim_neu`, b200-batch) access are **active**. The Stage-4 deliverable already landed: the native LLC270 multi-AOI joint fit is run, verified (`verify_run` exit 0) and reported (PRs #122/#123). **Do not treat this ladder as a gate on new proposals.**
```
**Also in the same pass:** L173, L221, L230 carry the same stale gate; Stage 5 reproduces the AICR/MIT conflation.

### `docs/CLAUDE_PROJECT_CONTEXT.md:202` — stale-number
> **5/6 ceiling** — empirical finding that no configuration reaches all 6 Carroll-6 params Cal-grade simultaneously

**Why:** A glossary entry preserving the refuted framing as a defined project term — the most durable way for a retracted claim to survive, since it gets reused as vocabulary rather than re-examined as a result. The adjacent L205 entry *does* carry a "falsified as a tier" hedge, so the author hedges when aware.

**Replace with:**
```markdown
- **5/6 ceiling** — *retired term (superseded 2026-06-24; kept here only so the old vocabulary resolves).* The original definition — "no configuration reaches all 6 Carroll-6 params Cal-grade simultaneously" — is **refuted**. The Southern-Ocean PIC:POC ratio-loss target was contaminated by near-zero-POC cells (target mean 4.7e7), which collapsed the SO ratio term to ~0 and left `R_PICPOC` unconstrained; capping it (`RATIO_MAX=2`) recovers `R_PICPOC` **10/10 joint Cal, genuine per-AOI**, and produced the first verified strict per-AOI 6/6 (3/10 seeds). It was a data-pipeline bug, not missing physics or a structural wall. The project is now framed as a **surrogate-to-model identifiability study over 4 observable params**; the growth pair is excluded by construction. What remains is a characterized **growth-pair** identifiability ceiling, not a "6/6 wall." Do not reuse "5/6 ceiling" as a live project term.
```

### `docs/ecco_darwin_parameter_inventory.md:109` — arithmetic
> Individual tunable values, arrays expanded over plankton, groups, and matrix dimensions | **657**

**Why:** The itemization doesn't sum. The 28 addends at L119 sum to 203, not 207; the column then totals 653, not 657. The addend count matches the 28 tunable names at L101, so the list is presented as complete. L139 asserts these numbers are "exact." Ground truth is not recoverable in-repo — the source namelists are in an external clone. (Severity note: this is documentation arithmetic in a scoping doc, not a scientific overclaim.)

**Replace with:**
```markdown
| Individual tunable values, arrays expanded over plankton, groups, and matrix dimensions | **~657 (not internally reconciled)** |

> **Reconciliation gap (flagged 2026-07-19):** the itemized breakdown below does not sum to 657. The `&DARWIN_TRAIT_PARAMS` row lists 28 addends totalling **203**, but the column total uses **207**; summing the listed addends gives 20+29+5+46+203+350 = **653**. Whether the error is a mistyped addend or the 207 itself cannot be determined from this repo — the source namelists (`data.darwin`, `data.traits`) live in an external clone of `MITgcm-contrib/ecco_darwin`. Treat the expanded-value count as approximate (~650) until re-audited. The "exact" claim in Caveats applies to the distinct-name count, not this one.
```

### `docs/ecco_darwin_parameter_inventory.md:127` — stale-number
> **Darwin 3**: … Tunable knobs ≈ 101 distinct names at the namelist level

**Why:** Contradicts the doc's own audited figure 23 lines earlier ("exactly 100", L104), the per-namelist table sum (100), and Appendix C (L223). "101" appears nowhere else in the repo. The "≈" is not an uncertainty hedge here — the parallel Darwin 1 sentence uses "≈ 103" for an exact figure.

**Replace with:**
```markdown
**Darwin 3**: parameters exposed via namelist files (`input_darwin/data.darwin`, `data.traits`). Tunable knobs = 100 distinct names at the namelist level (657 individual values once arrays are expanded over plankton, groups, and matrix dimensions), with most being arrays. **No recompile needed to vary them.**
```

### `docs/ecco_darwin_relationship.md:64` — stale-label
> | `DINNDeep` (production) | **SST + MLD + windspeed + latitude** (4 channels) | ~9.4K | Within-AOI fits where maximum r matters. Notebook 15.

**Why:** The numbers are correct; the label is not. `dinn_design.md:139` — the doc this table cites — says DINNDeep "saturates on biomass tracers (r → 1.0) but recovers fewer calibration-grade Carroll-6 params than the baseline; from v2.2.x onward, the project trains DINN baseline only by default." The relationship doc carried over only the extrapolation clause. The use-case text inverts the finding: high r is the saturation trap, not a selection criterion.

**Replace with:**
```markdown
| `DINNDeep` (not the default) | **SST + MLD + windspeed + latitude** (4 channels) | ~9.4K | Studied in notebooks 15–20. Saturates on biomass tracers (r → 1.0) while recovering *fewer* calibration-grade Carroll-6 parameters than the baseline — high r here signals an under-constrained fit, not a better calibration. Doesn't extrapolate across spatial blocks (held-out r = 0.301 on FeT vs 1.000 in-distribution). From v2.2.x onward the project trains the DINN baseline only by default; see [`docs/dinn_design.md`](dinn_design.md). |
```
**Also:** L59 ("Two production NN variants") → "Two per-cell NN variants".

### `docs/findings/2026-06-24_rpicpoc_ratio_target_fix.md:5` — stale-status
> Code behind NEW default-OFF flags (`RATIO_MAX`, `RATIO_AOI_W_*`, `RATIO_SCHED_START`, `USE_ENV_RAIN_RATIO`); legacy reproduces bitwise when unset. Uncommitted

**Why:** Commit `ce76c3c` — the commit that added this doc — also committed every piece of code the status line calls uncommitted. All four flags are live and default-OFF. The stale status also masks the real gap: it is the *results*, not the code, that have no committed artifact (grep for `RATIO_SCHED_START` / `4.7e7` in `.json`/`.csv` returns nothing; the runs are on purge-eligible Explorer scratch).

**Replace with:**
```markdown
Code behind NEW default-OFF flags (`RATIO_MAX`, `RATIO_AOI_W_*`, `RATIO_SCHED_START`, `USE_ENV_RAIN_RATIO`); legacy reproduces bitwise when unset. Code COMMITTED (`ce76c3c`); results NOT committed — the n=10 tables below have no artifact in-repo and trace only to `/projects/schultz/qi.zim/runs/rpicpoc_*` on NU Explorer (purge-eligible scratch)
```

### `docs/findings/memory_scaling_compiled.md:16` — stale-number
> | 2,000 | 50 | 0.07 | 0.06 | 1.1 |

**Why:** The "AD overhead 1.1×" (and 1.3× at L20) is a warmup artifact sitting in a table where every other row reports 16×-117×. Read at face value it says autograd is essentially free, which the same table contradicts at 8,000×50 (16.3×). The train-peak column is contaminated too — 0.07 GB at 50 steps vs 0.06 GB at 400 steps is impossible for a retained autograd graph.

**Replace lines 16 and 20 with:** `| 2,000 | 50 | — † | — † | — † |` and `| 4,000 | 50 | — † | — † | — † |`, then append below the table:
```markdown
† **Invalid — torch.compile warmup, not a measurement.** `measure_memory_scaling.py` builds the compiled per-step fresh per call and resets the CUDA peak counter immediately before the first execution, so Inductor's one-time compilation workspace is charged to these two cells. Raw JSON: forward peak 63,376,896 B (2,000×50) and 63,832,064 B (4,000×50) against 582,656 B and 1,157,632 B at every other step count — ~100× and ~55× inflated. The train peaks are contaminated too, visible as a physically impossible non-monotonicity (72.2 MB at 2,000×50 exceeds 68.1 MB at 2,000×400). Contamination stops at 8,000 cells; the clean 50-step AD overhead is 16.3×, and the eager table (`memory_scaling.md`) shows a uniform 38.0×. Re-measure with a discarded warmup pass before trusting these cells.
```

### `docs/findings/pre_scaleup_verification.md:35` — overclaim
> **Provably result-neutral:** an eqpac time-mean recovery (250 ep) is bit-identical pre/post; all 21 2-layer + seasonal tests pass

**Why:** The bit-identical run is a single-block time-mean integrator with `spinup_cycles=0` — a regime *disjoint* from where the `>= 0` clamp actually bites (SEASONAL mode at upper `PARAM_BOUNDS` under multi-cycle spin-up, which is why it was added). The source comment in `carroll6_5pft_2layer.py` is correctly scoped ("a no-op for well-behaved trajectories"); the doc stripped the scope and upgraded it to "provably." Repo precedent accepts this defect class (`2026-07-07_param_conditioned_emulator_decision.md:127`).

**Replace with:**
```markdown
**Result-neutral on everything tested — but that is empirical coverage, not a proof:** an eqpac time-mean recovery (250 ep, seed 0, zero spin-up cycles) is bit-identical pre/post, and all 21 2-layer + seasonal tests pass (incl. the reduce-to-plain-integrate allclose), so no published recovery number moves. The floor does, by construction, change trajectories in exactly the regime it was added for — upper `PARAM_BOUNDS` under multi-cycle seasonal spin-up — which the bit-identical time-mean run (single-block, `spinup_cycles=0`) does not exercise; that regime is covered only by the new `test_param_bound_extremes_stay_nonnegative_under_spinup`, which fails pre-fix.
```

### `docs/findings/stage1_per_aoi_gating_2aoi.md:45` — overclaim
> Only diatomgraz improved (+15pp) — the one param that appears to want single-regime isolation.

**Why:** 8/20 vs 11/20; s.e. of the difference ~16pp, so +15pp is ~0.96 s.e. (McNemar best case p=0.25). No CI, no test. The doc is internally inconsistent — it reads −15pp (Smallgrow) as a collapse. The mechanistic gloss is contradicted by the project's own later evidence: `posi_dense_diatomgraz.md` (six days later) shows diatomgraz 0/10 → 10/10 from adding dense POSi in a *three*-AOI multi-regime config — driven by observable availability, the opposite of regime isolation.

**Replace with:**
```markdown
Only diatomgraz moved the other way (+15pp, 8/20 → 11/20) — but that delta is inside binomial noise at n=20 (s.e. of the difference ~16pp; no significance test was run, and the paired per-seed JSONs are untracked), so it should not be read as a positive gating effect. It in particular does not support a "wants single-regime isolation" story. Later work shows diatomgraz recovery is governed by observable availability, not AOI regime isolation: its profile-likelihood is FLAT (span 0.039) in the geo1 loss without dense POSi, and it goes 0/10 → 10/10 when dense Darwin POSi is added in a three-AOI, multi-regime config (`posi_dense_diatomgraz.md`, 2026-06-11).
```

---

# Patterns worth naming

Following the three-actor framing in `2026-07-19_diatomgraz_claim_audit.md`.

## Mine (the author's): the adjective carries the argument

Across 14 of these, a superlative does load-bearing work the measurement underneath cannot support — **"provably"** (one AOI, zero spin-up cycles, in a regime disjoint from where the guard fires), **"exhaustively"** (25 arms sharing one contaminated target), **"bankable"** (seed variance certifying a mislabelled operator), **"PROVED structural"**, **"settled identifiability verdict"**, **"independent"** (a carbonate check satisfied by persistence), **"the entire 6/6 wall"**. Strip the adjective and every one of these sentences becomes true. The tell is that the adjective always appears in the sentence that gets quoted downstream — into a deck, a compute ask, or a Claude Project.

A specific variant: **counting replications as exclusions.** The 25-arm campaign, the seven ALK exclusions, and the five "independent pieces of evidence" for the 5/6 ceiling all ran against the same contaminated Southern-Ocean ratio target. N negative results from one bug is one negative result. Nothing in the workflow distinguished "we tried N things" from "we tried N things that could each have failed independently."

## The agent's: correcting the paragraph, not the claim

The single largest cluster here — roughly 30 defects — is a retraction that landed in exactly one place. `2026-07-19_emulator_honest_bounds.md` retracts the ~9-month horizon in its body and then asserts it in its own summary table (`:301`), its own "what this session-arc disproved" table (`:29`), its speed section (`:315`), and its "what is NOT established" list (`:330`). `2026-07-14_emulator_loop.md` received four dated 2026-07-19 correction blocks and kept the retracted number at lines 42, 72, 75 and 80 — including inside a row stamped "Superseded (2026-07-19)", so the *correction itself* restates the retracted claim and reads as verified.

Three predictable landing sites survive every correction pass: **summary tables, glossaries, and conclusions.** They restate rather than derive, so they never get re-read when the derivation changes. `CLAUDE_PROJECT_CONTEXT.md:202` is the pure case — a refuted result surviving as a *defined term*, which is the most durable form, because vocabulary gets reused rather than re-examined.

A second agent-shaped failure: **fixing the flagged span and leaving its sibling.** README:90 and :91 are the same defect, one bullet apart. Nine of the verdicts above explicitly had to flag adjacent lines the auditor's own scope missed.

## The project's: numbers that outlive their evidence

Three structural conditions produce most of the rest.

**Provenance that expires.** Every headline in `2026-07-19_emulator_honest_bounds.md` traces to `/scratch/qi_zim_neu/` (30-day purge, no backup). The 25-arm R_PICPOC exclusion traces to `%LOCALAPPDATA%` on one laptop. The 64M cell·step memory validation that shrinks the LLC270 gap 14.8× → 2.96× has no artifact in any commit in repo history. The project's own rule is stated in `2026-07-19_results_matrix.md` — "if a number is not traceable to a file in the provenance column, it does not belong here" — and it is violated by the doc that states it.

**Gitignored docs drift furthest.** `CLAUDE_PROJECT_CONTEXT.md` holds six defects including two blockers, and is the only file here that missed the 2026-06-27 archive sweep which banner-stamped every other doc carrying the 5/6-ceiling framing. It is untracked, so no commit ever forces anyone to reread it — and it is pasted verbatim into a context with no repo access to check it. `docs/index.md` carries verbatim copies of two README blockers for the same reason: nobody diffs it.

**Unit laundering.** A step became a month, and every Track-2 number inherited it: "156 months" is 156 steps, "9 mo" is 9 steps ≈ 17.7 months, "monthly flagship" is a ~2-month operator scoring +0.0026 at true monthly cadence. The docs are meticulous about metric space (linear vs log is labelled everywhere) and silent on cadence — the axis nobody thought to label is the one that moved by 2×.

**And the expensive composite:** a contaminated loss target became "the ≥2-AOI wall is calcite forward-model fidelity," which became "this is the AICR case, backed by an exhaustive box-scale exclusion," which became a scripted verbal answer for a live talk and a line-item in the compute budget calling PORT "the only path to 6-of-6." Six documents, one uncapped per-cell ratio. The chain from data bug to spend justification took nine days and was never broken by anything except a later run that happened to try the untested lever.