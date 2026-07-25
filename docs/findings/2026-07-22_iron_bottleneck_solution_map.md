# Can the alpfe↔scav_rat bottleneck be broken? — solution map (2026-07-22)

Literature workflow (5 lenses × mine+adversarial-verify + synthesis, 11 agents, all citations verified real:
Somes 2021, König 2021, Frants 2016, Pasquier & Holzer 2017, Tagliabue 2016, Pham & Ito 2018, Transtrum
sloppy-systems OED). Question: is the rank-1 `alpfe`↔`scav_rat` degeneracy (the binding leg of the 25/50
joint) breakable, and by what?

## Verdict
Yes — but **only** by a new observable that projects source and sink differently (no estimator/architecture
change ever will; confirmed across 5 estimators + EKI). And **every genuinely degeneracy-breaking observable
needs a model extension, because the binding blocker is not the data — it is that the Track-1 surrogate is a
0-D box that homogenizes away the vertical/section structure that carries the information.** With existing v05
output you can *lift the combination toward two loosely-constrained directions* (aeolian-contrast + dust prior);
point-identifying `scav_rat` needs a depth-resolved (1-D column) surrogate or a new Darwin isotope/ligand tracer.

## Two corrections to earlier claims (report loudly)
1. **Dissolved:particulate partitioning is REFUTED, not a candidate.** The repo already found it a construction
   tautology in the box (pFe/DFe = scav_rat·POC/W_SINK; real Fe_TP re-injects alpfe) —
   `docs/findings/2026-07-10_iron_partitioning_breaks_the_wall.md`, adversarially re-verified here. Retract it.
2. **"Vertical profile usable with existing v05 output" was half-right.** The DATA is in hand (v05 FeT is full
   3D/50-level; GEOTRACES has full-depth Fe_D), but the Track-1 SURROGATE is a 0-D box with no depth mechanism.
   Using the profile requires building a **1-D column surrogate** — a model extension (a Track-2 payoff), not a
   quick Track-1 tweak.

## Ranked solutions (breaks-degeneracy × data-in-hand × effort)
| # | Solution | Recovers | Data status | Effort | Decisive paper |
|---|----------|----------|-------------|--------|----------------|
| 1 | **Aeolian-supply-contrast cell weighting** (high vs low dust gradient) | combination; pins alpfe, scav_rat stays sloppy | have model+obs | low | Somes 2021 |
| 2 | **Informative dust-deposition prior on alpfe** (external aerosol-Fe product) | **both** (conditional on prior) | have model+obs | low | Somes 2021 |
| 3 | **Vertical DFe profile shape** (1-D column fit to 50-level FeT + GEOTRACES full depth) | partial — tightens scav_rat | have obs, **need 1-D surrogate** | high | Somes 2021; Pham & Ito 2018 |
| 4 | Reparameterize to stiff combo (alpfe^-0.81·scav_rat^+0.59) + CI | **combination only** (relabels) | n/a | low | Raue 2009 / Transtrum |
| 5 | δ56Fe iron isotopes (new fractionating Darwin tracer) | partial | have obs, **need new tracer** | high | König 2021 (built it in PISCES) |
| 6 | Iron-binding ligand field / Fe_S | partial (may relocate) | Fe_S in-hand, ligand = extension | med–high | Somes 2021 |
| 7 | 230Th/231Pa scavenging proxy | pins scav_rat cleanly | need new tracer | high | NEMO-ProThorP |
| 8 | Transient/time-resolved fitting | partial in principle | need-new-obs | high | Tagliabue 2016 |

Hierarchical Bayes = #1 in Bayesian clothing (adds info only via the dust contrast it pools). Growth pair
stays unobservable; diatomgraz stays practically non-id.

## The one to build first
**The 1-D vertical-column surrogate fit (#3), gated behind a cheap OSSE self-twin runnable now on existing
output.** Rationale: #1/#2 only lift the combination (won't point-ID scav_rat); isotopes/Th-Pa need a new
tracer + v05 re-run (strictly costlier); #3 reuses data entirely in hand and is the minimal extension that can
add the missing rank. Honest framing: #3 is not a Track-1 tweak — it is the **first concrete Track-2 payoff**
(STATUS.md already says the section gradient is "homogenized away — re-motivating Track-2"; transport_helps_probe
n=5 PASS showed dynamics carry iron info the static box lacks).

**Minimal OSSE test (existing output only, ~a week):**
1. Synthetic DFe with known (alpfe, scav_rat). Fit two surrogates: (a) current surface-only 0-D box;
   (b) a 1-D column (surface dust-flux boundary + first-order scavenging + prescribed remin/W_SINK from v05).
2. Compare Fisher eigenvalues + recovered (alpfe, scav_rat) scatter over n≥10 seeds.
3. Predicted: surface-only stays rank-1 (one near-zero eigenvalue, ~2.7-decade ridge); the column fit adds a
   second non-null eigenvalue and recovers scav_rat **iff** profile curvature is above the ligand/W_SINK confound
   floor. **If the twin does NOT separate them, stop** — the confound dominates; fall back to reporting the
   combination (#4) + dust prior (#2). Near-zero-cost go/no-go before any real-data column build.
Layer #1 (aeolian weighting) + #2 (dust prior) underneath regardless — cheap, complementary, pin the alpfe leg.

## Honest ceiling (fine for an identifiability study)
Reparameterization recovers a COMBINATION, never the two physical parameters. Even clean orthogonal levers only
PARTIALLY separate (König 2021: remin and scavenging have opposing δ56Fe effects; Somes 2021: source and
scavenging are spatially coupled). The correct deliverable is the stiff combination + CI, with scav_rat flagged
rank-1-sloppy, and a precise statement of *which* observation breaks the wall (full-depth GEOTRACES sections in a
vertically-resolved model — the Somes 2021 recipe) and why surface DFe alone provably cannot. That is a stronger,
more defensible manuscript claim than a brittle 6/6 chase. See [[project_paramlearner_improvement_plan]],
[[finding_ironpair_structural_diagnostic]].
