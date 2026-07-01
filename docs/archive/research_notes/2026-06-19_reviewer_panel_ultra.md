# DarwinDiff `main.tex` — Multi-Agent Reviewer-Panel Red-Team

> **⚠ SUPERSEDED FRAMING (2026-06-27).** Point-in-time record; data stands, framing corrected by [STATUS.md](../../../STATUS.md). The project is a surrogate-to-model identifiability study over **4 observable params**; the growth pair is unobservable by construction. **R_PICPOC is recoverable** with a real calcite anchor (the '6/6 wall / 5/6 ceiling / needs the Darwin port' framing is refuted). The dimensional surrogate gap (box homogenizes) — not calcite physics — is the real limit.


*Generated 2026-06-19 by the `paper_reviewer_panel` skill run as a Workflow fan-out
(8 grounded reviewer lenses + completeness critic + per-finding adversarial verify +
dedup/rank synthesis; 123 agents). Run cold against the `b064c76` snapshot of
`docs/paper/main.tex` (the pre-fix "Structural 5/6 Ceiling" version; manuscript is
untracked — `git show b064c76:docs/paper/main.tex`). 98 verified objections merged to 62.
Cross-checked against the two prior hand-reviews (`2026-06-10_paper_refinement_report.md`,
`2026-06-10_scientific_revision_report.md`): this run reproduced all 12 of their
load-bearing objections AND surfaced the net-new ones marked ★ below.*

## Bottom line

The central claim **survives only after substantial restatement**:

1. **"Recovery from existing v05 observations" does not hold as stated.** The loss is
   z-scored spatial-pattern MSE against ECCO-Darwin v05's *own model output*, so this is a
   surrogate-to-model **identical-twin identifiability** study, not recovery from
   observations. Restate as: *"a differentiable 5–7-tracer box proxy, fit to v05 model
   output, identifies the iron pair to within ±40% reproducibly, conditional on fixed ICs
   and ~94 fixed background parameters."*
2. **"Structural 5/6 ceiling" does not survive as an intrinsic law.** 0/856 at 6/6 has a
   rule-of-three 95% upper bound of 0.35%, which *exceeds* the observed 5/6 rate (0.23%) —
   the data cannot separate "true 6/6 rate = 0" from "as rare as the 5/6 events that did
   occur." Downgrade to an **empirical 4/6 reproducible ceiling** (69 seeds, 8.1%); drop
   "structural", "intrinsic", "under any single-loss optimization."

**Highest-leverage single fix:** reframe the evaluation honestly as a surrogate-to-model
identifiability study, AND add one independent identifiability check (finite-difference /
adjoint Jacobian, Hessian/Fisher sloppiness eigenspectrum, or a held-out channel/AOI). This
one move de-fangs the largest must-fix cluster at once (M01/M02/M03/M04/M13).

## Top attacks (most likely to land)

### rebuttal_diff 5 — needs a new experiment / reframe

- **M01** — Recovery metric conflates recovery skill with structural proxy bias: a 5–7-of-39-tracer advection-free 0-D box fit to a 23-yr advective mean may recover the value that best compensates for missing tracers/transport, not Darwin's value. Validity asserted, never demonstrated. *(Abstract; §Method l.73; Limitations l.259)*
- **M02** — Self-recovery, not observational recovery: loss is z-scored pattern MSE vs v05's own output; no held-out validation. "Recoverable from existing v05 observations" conflates model output with observations. *(Fig1 caption; §Method Training l.75; §4.7 l.219)*
- **M03 ★** — The causal claims ("the 3-AOI loss landscape was *actively destroying* them") have **no landscape evidence**: no loss-surface slice, no initialize-at-Carroll's-truth test, no multi-restart test. A failed lever-stack doesn't establish a loss maximum at 6/6. *(abstract l.42; §4.5 l.170; §4.7(ii) l.215; §4.6 l.182)*
- **M04 ★** — No identifiability analysis (Hessian/Fisher/sloppiness/profile-likelihood); the gradient could be loss-geometry/optimizer artifact. Equifinality/sloppy-model literature uncited — unknown whether the "5/6 ceiling" is a renamed known phenomenon. *(§gradient l.114,134; fig l.164)*
- **M05** — "Structural/intrinsic ceiling under *any* single-loss optimization" over-reads a finite-sample null (rule-of-three 0.35% > observed 0.23%; 0/80, 0/40 only bound below ~3.75–7.5%). "Any" unsupported. *(abstract l.42; §results l.147–159)*
- **M06 ★** — 38/40 is the winner of an 86-config selection (no multiple-comparison correction) AND its 3-AOI ablation "control" is the **same F2 result reused**, so "adding the SO destroys recovery" is the expected **regression of an order statistic** against a cherry-picked max. Wilson CI on 38/40 = [0.835, 0.986]. *(tab1 l.106; §4.3 l.138; §4.7 l.187)*

### rebuttal_diff 4 — needs real analysis / reframe

- **M07** — No advection + steady-state mismatch: box integrated 50 d "to near-steady state" fit to a 23-yr advective mean; recovered local rates absorb missing transport in exactly the regimes driving the key swings. "Near-steady" unquantified. *(§Method l.69,73; l.75; l.259)*
- **M08 ★** — AOI swings (diatomgraz 100→0, scav_rat 0→95) are the **signature of structural model error, not informative regional signal**; the benign "each AOI carries signal" reading can't be distinguished from "each AOI carries different proxy bias." Discussion(ii)'s diagnostic value rests on the benign reading. *(§4.7(i)-(ii) l.213–215; Discussion(ii) l.253)*
- **M09** — Recovered growth/grazing absorb omitted Eppley/PAR/co-limitation if the SMS kernel lacks those terms; Smallgrow/Biggrow non-commensurate with Carroll's reference-condition max rates. Rate-law form never stated. *(§Method l.73,69)*
- **M10** — No confidence intervals anywhere; n=40 cannot distinguish 100% from ~91% or 0% from ~9%; prose differences never tested. *(all tables)*
- **M11** — Named obs channels conflate v05 model fields with observations: DFe is a fitted v05 tracer; bSi is a steady-state diagnostic of the model's own Si budget (circular) yet drives the diatomgraz/SO claim; CO2 flux is computed inside the box AND used as a target. *(§Method l.79; §4.7(ii) l.215)*
- **M12 ★** — Reference mismatch: graded against Carroll 2020 optima but fit to v05 (Carroll 2022/Darwin-3); the "inherits bit-for-bit" claim is uncited. If v05 re-tuned, the grading reference isn't the generating value. *(§1 l.57)*
- **M13** — Every number is one DINN pipeline scored against the same v05 climatology it trained on; "recovery" = optimizer self-consistency. No independent estimator, no held-out channel/AOI. *(§Method l.75)*
- **M14** — GF solves a different inverse problem on different data (real in-situ obs, absolute misfit, joint IC+param); this uses z-scored pattern MSE vs model output with ICs pinned, 6 params only — strictly easier; "partial replacement of GF" is a mis-comparison. *(abstract; §1 l.57–59; §5 l.257)*
- **M15 ★** — alpfe (solubility) is degenerate with dust deposition flux (only the product sets the iron source), so recovered alpfe absorbs any box-vs-Darwin flux mismatch while scoring Cal-grade. The strongest result is the most exposed. *(§Method l.73)*
- **M16 ★** — Iron-pair "joint" recovery = **scav_rat alone**: alpfe is 100% in every ablation column, so P(alpfe ∧ scav) = P(scav) and the iron-joint row (95/1/75/0) equals scav_rat exactly. The "38/40 first reproducible JOINT recovery" bundles an always-passing parameter with the only one that varies. *(tab4 l.197–204)*
- **M17** — The mutex "most actionable predictive finding" is never operationalized: no threshold, basin width, decision rule, or worked a-priori prediction. *(§4.6 l.182)*
- **M18 ★** — No classical inverse-method baseline: missing MITgcm/ECCO **adjoint (4D-Var)** — the model's own native inverse machinery — and EnKF/MCMC BGC calibration; GF itself is cited via a popular-science *Eos* item, not Menemenlis 2005 JTECH. *(§1 l.57–60; refs)*

## The rest (M19–M63), grouped

**Statistics / inference:** M19 pooled per-param rates over non-exchangeable configs; M20 ★ per-cell field → scored scalar reduction never stated (extra DoF); M21 5/6-events double standard; M22 Wave-6 n=10 "direct evidence" with CI [0,0.28]; M23 model-output ≠ real-obs identifiability; M42 ★ 16/80 joint requires maximal nesting (independence expectation 13.6); M43 survivorship CVs; M44 "reproducible" = within-config seed-robustness; M53 five-evidence non-independence + single-seed over-count.

**Framing / over-claim:** M24 7-min-vs-multi-day not like-for-like; M25 ★ R_PICPOC (max 20%) fails the authors' own 25% bar yet is kept "recoverable"; M26 "5/6" overstates the reproducible 4/6; M27 novelty over BINN is only a domain port; M28 "partial replacement of GF" over-frames; M29 targets treated as precise truth but growth params have only a range; M52 ★ per-AOI mnemonic self-contradicts (alpfe 100% in all configs, can't be "carried"); M59 unhedged "first."

**Physical model / obs operator:** M30 5-PFT→2-box surjection unstated; M31 ★ bSi steady-state invoked in the *most* non-steady Si regime (SO) — where the diatomgraz conclusion is drawn; M35 ★ diatomgraz 0.33 is *outside* the Cal band [0.498,1.162] — a hard-fail attractor, contradicting the "compromise" story; M40 eqp scav_rat "no signal" is a biased estimate not absence; M41 ±40% band linear-space on multiplicative params.

**Reproducibility:** M34 architecture under-specified + which net produced headline; M36 ★ mutex law vs F2 (POSI_W undefined) unreconciled; M45 F2 levers / Basin C base undefined; M46 sigmoid bounds not tabulated; M47 per-config loss weights not given; M49 code/data a bare private-repo pointer; M50 diagnostic closures unstated; M51 λ_consistency form/values unstated; M60 no software/seed pinning; M61 AOIs name-only.

**Numerical consistency:** M37 missing 0/6,1/6 buckets (reported-only mean 2.30 vs claimed 2.41); M38 "four" vs five-item list; M39 "200 additional seeds" (160 new); M48 ★ Table-4 %s vs integer counts; M54 0/80 framed as whole-extension; M55 R_PICPOC 0.042 vs 0.0425; M56 "43%" vs 42.5%; M57 ★ 103−6=97 vs "~94"; M58 ★ "fourth basin" off by one; M62 orphan/uncited bib (raissi2019pinn + 6 infra entries); M63 ★ 3-AOI mean-k row 2.52 ≠ marginals 2.53.

★ = net-new vs the two prior hand-reviews.
