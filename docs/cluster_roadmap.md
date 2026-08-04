# Cluster compute roadmap — what to do with cluster compute now

Planning companion to [docs/cluster_setup.md](cluster_setup.md) (operational how-to). This doc covers WHAT to do with cluster compute now that Explorer and AICR access are both live (the MIT ORCD / Engaging path was an earlier exploratory option and was dropped — see the companion doc above). Track 1 (the surrogate-to-model identifiability study) is largely complete at 0-D box scale, with named open box-scale items (the `alpfe` bound-railing, an out-of-sample Southern-Ocean `scav_rat` replication, and the `ded77` structural-vs-practical test); the high-EV cluster work is now **Track 2** (the differentiable spatial UDE / emulator) plus optional **Track-1 closure** (native-res parameter maps, forward-Darwin validation). Ordered by expected value.

> **⚠ REFRAMED / SUPERSEDED (updated 2026-07-05).** Track 1 is scientifically **COMPLETE** — a surrogate-to-model identifiability study, not a 6/6 chase. Central verified result: the **per-cell architecture is load-bearing** — a per-cell DINN holds {`alpfe`, `scav_rat`, `R_PICPOC`}; a global-scalar vector holds ~0 (disjoint CIs). `alpfe` is method-independent / mass-balance-identified; `R_PICPOC` recovers via a real calcite anchor and a single global value is under-constrained (bulk PIC:POC should vary regionally); `scav_rat` needs per-cell (weakest leg); the growth pair is excluded — `Biggrow` unobservable by construction, `Smallgrow` non-identifiable from time-mean observables (a seasonal prototype recovers it natl 9/10, unconfirmed) — and `diatomgraz` recovers only from a model-internal observable (adding an MLD input channel takes it from chance to 10/10; 35/50 per-AOI with `POSI_W=0`), not from independent real data — so the 3-of-4 frontier is structural, with two operating points rather than one. **`R_PICPOC` is NOT cluster-gated** — native resolution was *tested and did not help*. The remaining high-EV cluster work is **Track 2** (the differentiable spatial UDE). Everything below that reads "5/6 ceiling" or "5/6 break" is **historical** framing.

## The identifiability map (settled finding)

The v3.0–v3.1 work (847 seeds across 85 configs, historically framed as a "5/6 ceiling") settled the identifiability map — which parameters are observable and why. The honest scope is **4 nominally-observable params** {`alpfe`, `scav_rat`, `diatomgraz`, `R_PICPOC`}. `alpfe`/`scav_rat`/`R_PICPOC` recover from real anchors (the flagship n=50 `geo1` ensemble `n50e2k_percell_trio` and a `POSI_W=0` (biogenic-silica-off) arm was run to test the bSi-tautology objection — but its per-AOI count is **RETRACTED** (it does not beat its architecture-matched untrained control), so that question is open; the n=10 `geo1` 7/10 is the superseded precursor; and a `POSI_W=0` (biogenic-silica-off) arm was run to test the bSi-tautology objection — but its per-AOI count is **RETRACTED** (it does not beat its architecture-matched untrained control), so that question is open). `diatomgraz` is **recoverable from a non-circular model-internal observable, but not from independent real data** — an SST-only DINN sits at chance (~4/10), while adding an MLD input channel takes it to 10/10, and a `POSI_W=0` (biogenic-silica-off) arm was run to test the bSi-tautology objection — but its per-AOI count is **RETRACTED** (it does not beat its architecture-matched untrained control), so that question is open. The catch is that the Chl target is Darwin's own output, so this is model-internal consistency, not independent real-data validation. This is also why the 3-of-4 frontier is **structural**: `scav_rat` needs the Darwin-pattern term and `diatomgraz` needs MLD, and the two conflict even at 4000 epochs, so there are two operating points — `geo1` holds {`alpfe`, `scav_rat`, `R_PICPOC`} and MLD-channel + heavy Daniels weight holds {`alpfe`, `diatomgraz`, `R_PICPOC`} — and no single config recovers all four. The growth pair is excluded: **`Biggrow` is unobservable by construction**, while **`Smallgrow` is non-identifiable from the time-mean observables this study fits** — a seasonal prototype recovers it in the North Atlantic 9/10 (unconfirmed, job 189324). A literal 6/6 was never attainable.

This map is a **finding, not a compute target**: no amount of box-scale compute changes which parameters are observable. Compute's value is elsewhere — **Track 2** (the differentiable spatial UDE, whose point is to close the surrogate gap) plus **Track-1 closure** (native-resolution parameter maps, forward-Darwin validation).

## What compute categorically enables

None of these change the settled Track-1 identifiability map at 0-D box scale — that map is a finding, not a compute target. The item they served was **Track 2's make-or-break gate E2** (does adding transport close the surrogate gap on real data, held-out real-data R² > 0); E2 has since been run and failed, so what they now serve is the Track-2 **identifiability-limits map**, not a discovery.

| Category | What compute changes | Attack on the Track-2 surrogate gap (E2) or scientific closure? |
|---|---|---|
| Resolution | 1° proxy → native LLC270 (~330× more cells per AOI) | Closure — per-cell parameter maps (Track-1 closure); does not change the box-scale identifiability map |
| Time | 23-yr time-mean → ~300 monthly snapshots | **Surrogate gap** — adds temporal structure toward transport; a Track-2 lever, not a box-scale param-recovery lever |
| Coverage | 3 AOIs → global ocean | **Surrogate gap** — more regimes add real independent channels for the transport UDE |
| Model | 5-PFT 2-layer box → toward full Darwin 3 (~25+ tracers + zooplankton + DOM) | **Surrogate gap** — narrows the box-vs-model gap that Track 2 must close; does not make the growth pair observable |
| Observations | Cluster lets you load + use POSi, PFT-Chl, BGC-Argo, SOCAT 2025 globally + time-resolved | **Surrogate gap** — adds independent real channels; an MLD input channel already lifts `diatomgraz` from chance to 10/10, but against a model-internal target, so the open question is whether *independent real* data holds it |
| Statistics | n=10 seeds → n=100 or n=500 | Negligible — better stats on a settled map, changes nothing |
| Architecture | Bigger DINNs, attention, transformers | Negligible — Wave 6 falsified architectural-composition; capacity is not the binding constraint |
| Validation | Forward Darwin runs with recovered parameters | Closure — Track-1 scientific closure (Green's-functions papers can't claim it) |
| Track 2 | Differentiable spatial UDE build (primary remaining direction) | **This is the direction** — gate E2 was the make-or-break test; it was run and failed, so the deliverable is an identifiability-limits map |

## Directions ranked by EV

The single highest-EV direction is **Track 2** (the differentiable spatial UDE) — see the Track-2 section below, promoted out of the old Tier-3 slot. The tiers below are re-anchored: Tier 1 = advance Track 2 / close the surrogate gap; Tier 2 = Track-1 scientific closure; Tier 3 = genuine nice-to-haves.

### Tier 1 — Advance Track 2 / close the surrogate gap

These box-scale and observation-channel levers do not change the settled Track-1 identifiability map — they add the temporal, spatial, and observational structure the **Track-2 transport UDE** needs to close the surrogate gap (gate E2).

#### A. Time-resolved fitting

**Hypothesis.** The 23-year time-mean target integrates away the temporal information the transport UDE needs; the box homogenizes over it. Switching to ~300 monthly snapshots gives ~300× more quasi-independent constraint sets, with different parameters driving different time scales:

- `scav_rat` — iron scavenging acts on days–weeks
- `Smallgrow`, `Biggrow`, `diatomgraz` — bloom timing, weeks–months
- `R_PICPOC` — coccolithophore phenology, seasonal
- `alpfe` — dust-deposition pulses, episodic

Effective constraint count could jump from ~5 to ~20–30.

**What it unlocks.** Temporal structure toward a transport-aware fit; a Track-2 prerequisite. Does not change the settled box-scale identifiability map.

**Compute cost.** ~300× current per-fit. Single fit on B200 ≈ 30–100 GPU-hours (vs ~10 min currently). Sweeps shrink from 80+ configs to 5–10 carefully designed configs per paper.

**Code lift.** ~1–2 weeks. Loader changes to stream monthly snapshots, loss function adjustments to handle temporal stacking, careful gradient accumulation across time. The box-model integrator stays per-snapshot.

**Risk.** Temporal modes may be more correlated than expected; effective constraint gain could be 2–3× rather than 10×. Even partial gain still feeds the transport UDE.

**Success criterion.** Time-resolved fitting is a Track-2 lever; its success is measured against **gate E2** — held-out real-data R² > 0 once temporal/transport structure is present. E2 has since been run on the calcite closure and failed, so a re-test here would be sharpening the identifiability-limits map, not converting the consistency-check into a discovery. At box scale it has no "/6" target; the Track-1 identifiability map is already settled.

---

#### B. Box-model state extension toward full Darwin 3

**Hypothesis.** The current 5-PFT 2-layer integrator (~10 tracers, `carroll6_5pft_2layer.py`) is a fraction of Darwin 3's state vector. The box-model proxy is a source of the **surrogate gap** — the box homogenizes structure that real Darwin resolves. Extending the box narrows that gap, a Track-2 prerequisite. Each new tracer also adds a corresponding new loss channel.

Candidate extensions in order of recovery payoff:

1. **Zooplankton** (Z_micro, Z_meso) — currently absorbed into grazing-rate parameters; explicit zooplankton improves grazing fidelity and narrows the surrogate gap (it does not make `Biggrow` observable — that is unobservable by construction).
2. **DOM** (DOC, DON, DOP, DOFe) — improves POC export and remineralization fidelity; constrains `R_PICPOC` indirectly via the C:N:P:Fe ratios.
3. **Full Darwin 3 carbonate** — currently `carbonate.py` has Follows 2006 + Wanninkhof 2014 but Darwin 3 has additional alkalinity sources/sinks; extending fixes the alkalinity drift seen under GLODAP hybrid targets.
4. **Multi-layer extension beyond 2 layers** — currently 0–50 m + 50–1000 m; full-depth multi-layer adds vertical structure information.

**What it unlocks.** Strongest long-term lever. Doesn't depend on new observation types — the existing tracer fields are already in Darwin output.

**Compute cost.** Each tracer added scales the box-model state vector ~linearly; per-fit cost increases ~1.5–3× depending on tracer count. Manageable on B200.

**Code lift.** Substantial. Each tracer family needs autograd-clean PyTorch dynamics + tests + integration with the loss function. ~2–4 weeks per major extension.

**Risk.** Higher than time-resolved because each extension requires careful physics fidelity. Some tracer dynamics (e.g. zooplankton density-dependent grazing) have multiple plausible formulations.

**Success criterion.** The box-extension narrows the surrogate gap (a Track-2 prerequisite for gate E2) — not that it recovers `Smallgrow`/`Biggrow`, which stay unobservable by construction. Success is a measurably smaller box-vs-Darwin discrepancy on held-out fields.

---

#### C. Observation channel additions

Each adds independent real information channels that feed the Track-2 transport UDE; whether any lifts `diatomgraz` (an open Track-1 question) is testable, but none makes the growth pair observable. Note: POSi (biogenic silica) is **already integrated** as an active constraint throughout v3.1 — the `POSI_W` env var in the production runner (`scripts/run_v3.0_with_modis_pic.py`) is the absolute-units MSE loss against GEOTRACES IDP2025 surface bSi, computed via the steady-state silica diagnostic in `src/darwindiff/silica.py` (no integrator extension required; bSi is diagnosed from existing diatom dynamics). Every Basin C config has `POSI_W=1.0`; `c_chl40_posi15` uses `POSI_W=1.5`. The settled identifiability map holds with bSi active.

##### C.1 Ocean color PFT-resolved Chl (OB.DAAC / OC-CCI) — leapfrog-phase per project directive

**Hypothesis.** Remote-sensing PFT decomposition gives Pro-HL-specific, Syn-specific, and diatom-specific Chl independently of Carroll's group-mean target — a real, independent channel for the Track-2 transport UDE. It bears on whether `diatomgraz` holds up against *independent real* data — an MLD input channel already takes it to 10/10, but against Darwin's own Chl; it does not make the growth pair {`Smallgrow`, `Biggrow`} observable.

**What it unlocks.** Replaces the Chl1–Chl5 z-scored loss with absolute-magnitude PFT-resolved targets — a real independent channel for the transport UDE.

**Compute cost.** Loader is non-trivial (regridding from satellite swath to LLC270 grid); compute per-fit unchanged.

**Code lift.** ~1 day for loader + integration. Currently partly built for the leapfrog phase.

**Risk.** Ocean color PFT decomposition has well-known limitations in cloud-covered + high-latitude regions. Coverage gaps need careful handling.

**Success criterion.** Adds a real, independent PFT-resolved channel for the Track-2 transport UDE. It can test whether `diatomgraz` survives a move to *independent real* data (an MLD channel already gets it to 10/10 against Darwin's own Chl) but cannot make the growth pair observable — the growth pair is unobservable by construction (`Biggrow`; `Smallgrow` is non-identifiable from time-mean observables only). No `Smallgrow` recovery target.

##### C.2 BGC-Argo depth-resolved profiles

**Hypothesis.** Currently we have surface + subsurface (50–1000 m) anchors via GEOTRACES; BGC-Argo gives much higher density of depth-resolved nitrate, oxygen, chl, particle backscatter, and DFe profiles. Time-resolved by construction.

**What it unlocks.** Combines naturally with time-resolved fitting (Tier 1 direction A). The strongest single observational addition for the time-resolved + global paper.

**Compute cost.** Loader uses `argopy` (already in deps); cluster-scale loading is the gating step.

**Code lift.** ~3–5 days. `argopy` handles the API; the integration with the box-model loss is the work.

**Risk.** Moderate. Float coverage is uneven; northern subtropical gyres have many fewer floats than Southern Ocean. Some regions have <10 floats over 23 years.

**Success criterion.** Depth-resolved DFe profiles tighten `alpfe` and `scav_rat` independently. Probably the strongest single addition for time-resolved fitting.

---

### Tier 2 — Track-1 scientific closure

These deliver scientific closure for the completed Track-1 study (parameter maps, forward-Darwin validation) — not changes to the settled identifiability map.

#### D. Native LLC270 resolution

**Hypothesis.** The current 1° proxy averages over ~10–30 native cells per 1° cell. Native resolution produces per-cell parameter maps at Darwin's own grid, the deliverable for Track-1 closure.

**What it unlocks.** Per-cell parameter maps (the "Carroll-can't-do-this" scientific story) and a basis for forward Darwin validation. Does not change the settled box-scale identifiability map.

**Compute cost.** ~100–1000× more cells per AOI (the proxy uses ~1k cells, native gives ~10k–1M per AOI depending on region). Per-fit compute scales near-linearly with cell count. Single global native fit ≈ 100–500 GPU-hours.

**Code lift.** Modest. The `llc270_loader.py` exists; integration with the differentiable box-model needs careful dask/torch tensor handling at scale.

**Risk.** More cells of the same regimes are highly correlated; the map is a closure deliverable, not a new-information source. The identifiability map is settled regardless of resolution.

**Success criterion.** Per-cell parameter maps that are spatially coherent and biologically interpretable (e.g. `alpfe` higher in dust-deposition regions, `scav_rat` higher near sediment sources). Visualization is the deliverable.

---

#### E. Global ocean coverage (full ocean, all regimes)

**Hypothesis.** Currently we use 3 specific regimes (HNLC, deep-mixed iron-replete, Southern Ocean). Adding subtropical gyres, coastal upwelling, marginal seas, polar shelves expands regime diversity — real independent channels for the Track-2 transport UDE and global parameter-map coverage for Track-1 closure.

**What it unlocks.** Global coverage for the parameter maps (Track-1 closure) and broader real-data regimes for the transport UDE (Track-2). Does not make the growth pair observable.

**Compute cost.** Scales with the AOI count × cells per AOI. Global at native ≈ several thousand GPU-hours for a single fit (n=10 batched).

**Code lift.** AOI registry expansion + loader work. ~1 week.

**Risk.** The PER_AOI_DINN architecture currently uses one DINN per AOI; scaling to 10+ AOIs needs an alternative (per-regime clustering, hierarchical DINN). Untested.

**Success criterion.** Reproducible per-AOI co-recovery of the observable set across multiple AOIs; per-regime parameter values that match published priors.

---

### Tier 3 — Lower EV; nice-to-haves and closure add-ons

(Direction H, forward-Darwin validation, is Track-1 closure — grouped here for cost but conceptually belongs with Tier 2.)

#### F. Multi-seed at scale (n=100–500)

Better statistics on an already-settled identifiability map. Easy to do on cluster (embarrassingly parallel array job); low EV — it does not change which parameters are observable. Shouldn't be the priority.

#### G. Architectural sophistication

Larger DINNDeep, attention layers across cells, transformer encoders for env-channel mixing. Wave 6 falsified architectural-composition explicitly; the binding constraint is observation information, not network capacity. Low priority unless a specific architecture has theoretical reason to add information (e.g. cross-cell attention as a soft spatial-coupling test).

#### H. Forward Darwin validation

Run actual Darwin with the recovered DarwinDiff parameter maps; compare global tracer fields. Scientific closure that Green's-functions papers cannot claim. Requires the Darwin source build + namelist injection of per-cell parameters. ~1–2 weeks for the integration; doesn't depend on AICR but uses cluster compute for the Darwin run itself. (This is Track-1 closure — moved conceptually alongside Tier 2 direction D.)

## Track 2 — the differentiable spatial UDE (primary remaining direction)

**Track 2 is now the primary remaining high-EV direction** (Track 1 is scientifically complete). Box-scale feasibility is **PROVEN on the 0-D box only** — self-twin, synthetic, transport-free, **NOT real Darwin**. Beyond the box the forward neural emulator **is** built, and it is a clean negative result: physically valid (0% negative concentrations in log space, mass ratio 1.000, valid carbonate chemistry) but with a useful horizon of **one step** and no significant skill over a per-cell seasonal AR(1) baseline. Deep ensembling is the only real skill lever; diffusion added nothing. Do not describe any of this as "made Darwin differentiable," "learned real biology," or "proved env-gated calcification."

**Gate E2 was run and returned a decisive negative** (`docs/findings/2026-07-10_e2_powered_result.md`, merged via #180): the learned closure cannot beat a constant-through-transport null out of sample, so transport does **not** close the surrogate gap on real data — not because the method fails but because the observations lack the signal. Held-out real-data R² stays negative, so Track-1 remains a consistency check against Carroll's own values, not a cross-validated discovery. Track 2's contribution is therefore an **identifiability-limits map**: across the iron, calcite and growth closures, real observations have not sharply constrained any of the three — with one anchor still untested where its data actually is: the GP15 ²¹⁰Po/²¹⁰Pb sink anchor has **0** points in `eqpac`, `natlsubpolar` and `southernoceanpac` but **92 points / 6 stations** in `npac`, so a single-AOI `npac` run is outstanding. The binding constraint is the observing system, not the method.

**Backbone survey.**

- **Samudra 2** (eddy-resolving physical ocean, arXiv 2606.02610) — best backbone, but its finer physics *worsens* the sparse-obs identifiability tension.
- **SamudrACE** (arXiv 2509.12490) — differentiable coupled atmosphere–ocean physics with an **explicit biogeochemistry hole** = our **Option-C carbon-BGC-UDE slot**.
- **ACE2** — atmosphere-only, no carbon.
- **OlmoEarth** — land / coastal EO, poor fit.

**Gated build plan (riskiest-assumption-first, multi-month, gated on Paper #1 shipping).**

1. **Phase 1 — minimal real-data transport UDE.** Regional 2-D (or 1-D column → minimal 2-D), driven by ECCO-Darwin's own velocities, fit to real GEOTRACES iron + calcite, held-out scored. **Gate E2 has already been run at closure level and returned a decisive negative** (see above) — the binding constraint was the observing system, not the method, so re-running the same gate against the same observations would return the same answer. Phase 1 is therefore gated on **new observations**, not on more building; the concrete candidate is a 1-D vertical column with real profile data, which is what breaks the alpfe↔scav_rat degeneracy the 0-D box cannot.
2. **Phase 2 — physical-backbone differentiability probe.** Samudra-coupling probe → gate 2 (gradients flow through a real physical backbone to a BGC UDE).
3. **Phase 3+ — full coupled build.**

See [docs/emulator_coupling_plan.md](emulator_coupling_plan.md) for the concrete gated path.

## Sequencing recommendations

### Phase 0 — laptop work, while waiting for cluster access

**Track-1 laptop work is COMPLETE.** Paper #1 (the surrogate-to-model identifiability study) has been hardened, 8-lens red-teamed, and an ensemble folded in. All major observation channels (bSi via POSI_W, GEOTRACES surface + subsurface DFe + POC, Darwin POC/PIC absolute anchors, per-AOI Chl1–5, carbonate via DIC/ALK/CO2_flux) are active; 85 single-lever configs / 847 seeds characterized the settled identifiability map. Box-scale is not closed: a widened-bound `alpfe` arm (the current recovery is a spike against the 1.0 ceiling), a genuinely out-of-sample Southern-Ocean `scav_rat` replication (`so_only2` is bitwise identical to `so_only`, so that result has none), and the symbolic structural-vs-practical test for `ded77` are all outstanding.

| Step | Direction | Cost | Notes |
|---|---|---|---|
| Optionally: small zooplankton extension to box model | B (start) | 1–2 weeks | Narrows the surrogate gap; a **Track-2 prerequisite**, not a Track-1 paper item |

Other potentially useful laptop work falls into **leapfrog territory** (different observation channels): ocean color PFT-Chl, MODIS-Aqua PIC, PACE carbon_phyto. These are real independent channels for the Track-2 transport UDE, not Track-1 recovery levers.

### Phase 1 — Explorer onboarding + first cluster jobs — **DONE**

| Step | Status |
|---|---|
| NU Research Computing access request (Schultz-sponsored) | Done |
| Key-auth `ssh explorer` automation | Live — Explorer is the unattended-automation cluster |
| Port the production runner to SLURM | Done — `scripts/slurm/run_explorer_gpu.sbatch` |
| First Explorer fit at 3-AOI Basin C base | Done; the n=50 ensembles run here |
| AICR account (B200) | Active (`qi_zim_neu`), interactive-only |

### Phase 2 — AICR onboarding + first B200 jobs (likely 2–8 weeks after Phase 1)

| Step | Notes |
|---|---|
| AICR access form + onboarding | After Explorer confirmation |
| First B200 fit replicating laptop Basin C | Baseline calibration |
| Native LLC270 1-AOI fit | Direction D — Track-1 closure (parameter maps) |
| Track-2 Phase-1 transport UDE scaffold | Built; gate E2 ran and returned a decisive negative |

### Phase 3 — Track-2 Phase 1: minimal real-data transport UDE (gated on Paper #1 shipping)

The next scientific step is **Track 2 Phase 1**, not more box-scale Track-1 recovery. Build the minimal real-data transport UDE (regional 2-D driven by ECCO-Darwin's own velocities), fit to real GEOTRACES iron + calcite, held-out scored → **gate E2** (held-out real-data R² > 0 once transport is present). This was run: E2 **failed** — the learned closure cannot beat a constant-through-transport null — so the consistency-check does not become a discovery, and the deliverable is an identifiability-limits map.

Supporting cluster-gated closure work that can run alongside:

1. **Native resolution** (Direction D) at 3 AOIs — 1–2 configs at ~500 GPU-hours → Track-1 parameter maps
2. **Forward-Darwin validation** (Direction H) → Track-1 scientific closure
3. **Box-model / observation extensions** (Directions B, C) — narrow the surrogate gap ahead of / feeding the transport UDE

The bSi (POSi) channel and per-AOI carbonate channels are already active and persist. The leapfrog observation channels (ocean color PFT-Chl, BGC-Argo, satellite PIC) feed the transport UDE, not a new box-recovery paper.

### Phase 4 — Track-2 full build + Track-1 closure paper(s)

Paper map (Track-1 being complete):

- **Paper #1** — the surrogate-to-model identifiability study (in hardening).
- **Next paper** — the Track-2 **identifiability-limits map**. E2 was run and failed, so this is a limits study plus an observing-system recommendation (wider within-region Ω, pure scavenged Fe, per-PFT production), not a discovery paper.
- Native-res parameter maps + forward-Darwin validation are Track-1 closure that can accompany Paper #1 or a methods companion.
- Samudra-coupling probe (Phase 2) and full coupled build (Phase 3+) are the follow-on Track-2 program.

## Decision tree based on AICR access timeline

Track 1 is complete, so the branch that matters is whether the **Track-2 Phase-1 transport UDE (gate E2)** fits on available laptop/local compute now or needs the cluster. Timelines are relative to Paper #1 shipping.

| AICR access timeline | Recommended priority |
|---|---|
| Fits on laptop/local now | Prototype the Track-2 Phase-1 transport UDE (gate E2) locally; onboard cluster in parallel for scale-up + native-res parameter maps |
| Cluster required, arrives soon | Onboarding in parallel with a minimal local UDE scaffold; first cluster jobs = Track-2 Phase-1 at scale + native-res closure maps |
| Cluster required, delayed | Paper #1 (the surrogate-to-model identifiability study) ships regardless; local work builds the Track-2 Phase-1 scaffold; cluster work (transport UDE at scale, native-res maps) follows once access lands |

## Risk-adjusted EV summary

| Direction | EV (Track-2 surrogate-gap close / scientific closure) | Cost (GPU-hr/fit) | Code lift | Risk | Priority |
|---|---|---|---|---|---|
| Track 2 — differentiable spatial UDE (gate E2) | **Tested** — E2 failed; delivers an identifiability-limits map, not a discovery | high | many wk | High | **Primary** |
| A. Time-resolved | High — Track-2 enabler (temporal → transport) | 30–100 | 1–2 wk | Low | **Tier 1 #1** |
| B. Box-model extension | High — narrows the surrogate gap | 1.5–3× current | 2–4 wk per | Medium | **Tier 1 #2** |
| C.1 Ocean color PFT-Chl | Medium-High — real independent channel | negligible | 1 d | Medium | Tier 1 |
| C.2 BGC-Argo | Medium-High — real independent channel | medium | 3–5 d | Medium | Tier 1 |
| POSi (bSi) — already integrated | — | — | done | — | Active in v3.1 sweep set |
| D. Native resolution | Medium — Track-1 closure (parameter maps) | 100–500 | 1 wk | Low | Tier 2 |
| E. Global coverage | Medium — global maps + channels | 500–5000 | 1 wk | Medium | Tier 2 |
| F. Multi-seed scale | Low — stats on a settled map | linear in n | negligible | Low | Tier 3 |
| G. Architectural | Low — capacity is not the constraint | 1–5× | 1–2 wk | High | Tier 3 |
| H. Forward Darwin | Medium — Track-1 closure (validation) | varies | 1–2 wk | Medium | Tier 2/3 |

## What to NOT do with cluster compute

- **Don't re-run box-scale Track-1 recovery to try to change the identifiability map.** It is a settled finding — which parameters are observable and why — not a compute-limited ceiling. No amount of seeds, cells, or iterations makes an unobservable parameter observable at 0-D box scale.
- **Don't describe any Track-2 output as a real-data discovery.** Results to date are a **synthetic self-twin on the 0-D box** — a differentiable *proxy*. Never say we made Darwin differentiable, learned real biology, or proved env-gated calcification. That claim is gated on **E2** (held-out real-data R² > 0 with transport present), and E2 was run and failed.
- **Don't run multi-thousand-seed confirmation runs on the settled map.** Better stats change nothing about which parameters are observable; cluster compute is better spent on Track 2.
- **Don't chase architectural exotica** (transformers, attention, mixture-of-experts) before extending observation channels. Architecture is not the binding constraint (Wave 6 falsified it).
- **Don't redo Wave 6 composition tests at cluster scale.** v3.1 already closed that hypothesis; cluster scale would not change the verdict. New compute is for Track 2 and Track-1 closure, not more of the same sweep.

## Cross-references

- [docs/emulator_coupling_plan.md](emulator_coupling_plan.md) — the concrete gated **Track-2** differentiable-spatial-UDE build path (Samudra Option-C coupling, gates E2 and gradient-flow)
- [docs/cluster_setup.md](cluster_setup.md) — operational guide for Explorer + AICR access
- [STATUS.md](../STATUS.md) — current results and verified numbers
- [docs/findings/v3.1_closeout.md](archive/findings/v3.1_closeout.md) — v3.1 closeout with Wave 6 composition test
- [docs/dinn_design.md](dinn_design.md) — architecture details
- [data/README.md](../data/README.md) — observation channel availability + planned integrations
