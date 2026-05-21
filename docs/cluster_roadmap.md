# Cluster compute roadmap — directions ranked by EV against the 5/6 bottleneck

Planning companion to [docs/cluster_setup.md](cluster_setup.md) (operational how-to). This doc covers WHAT to do with cluster compute once Engaging + AICR access is online. Ordered by expected value against the v3.1 structural 5/6 ceiling.

## The bottleneck recap

After 847 seeds across 85 configs of single-lever variation, two unreproduced single-seed 5/6 events, and a failed composition test (Wave 6) of the two complementary 5/6 lever families, the 5/6 ceiling is **structural**, not a hyperparameter-tuning artifact. The diagnosis from v3.0–v3.1: **~5 effective constraints on 6 parameters** under the current observational set; the 6th parameter is always the residual sink, and loss weighting decides which.

Compute alone does NOT solve this. The bottleneck is observation-information content, not cell count or training iterations. Compute is necessary but not sufficient: it enables observation-type extensions (POSi, PFT-Chl, BGC-Argo), temporal extensions (time-resolved fitting), and structural model extensions (full Darwin-3 box) that would not otherwise fit in memory or wall-clock.

## What compute categorically enables

| Category | What compute changes | Direct attack on 5/6 ceiling? |
|---|---|---|
| Resolution | 1° proxy → native LLC270 (~330× more cells per AOI) | Weak — more cells of same regimes are highly correlated |
| Time | 23-yr time-mean → ~300 monthly snapshots | **Strong** — different params drive different time scales, partially decorrelating the binding set |
| Coverage | 3 AOIs → global ocean | Moderate — new regimes add constraint diversity, but information per-regime is bounded |
| Model | 5-PFT 2-layer box → toward full Darwin 3 (~25+ tracers + zooplankton + DOM) | **Strong** — each added tracer adds ~1 effective constraint; box-model proxy is a co-binding limit |
| Observations | Cluster lets you load + use POSi, PFT-Chl, BGC-Argo, SOCAT 2025 globally + time-resolved | **Strong** — adds independent information channels directly |
| Statistics | n=10 seeds → n=100 or n=500 | Negligible — better stats on the ceiling, doesn't break it |
| Architecture | Bigger DINNs, attention, transformers | Negligible — Wave 6 falsified architectural-composition; capacity is not the binding constraint |
| Validation | Forward Darwin runs with recovered parameters | Doesn't break ceiling but provides scientific closure |
| Track 2 | Emulator training (different problem class) | N/A — second project goal |

## Directions ranked by EV

### Tier 1 — Direct attack on the structural ceiling

#### A. Time-resolved fitting

**Hypothesis.** The 23-year time-mean target integrates away the temporal information that decorrelates the binding parameter set. Switching to ~300 monthly snapshots gives ~300× more quasi-independent constraint sets, with different parameters driving different time scales:
- `scav_rat` — iron scavenging acts on days–weeks
- `Smallgrow`, `Biggrow`, `diatomgraz` — bloom timing, weeks–months
- `R_PICPOC` — coccolithophore phenology, seasonal
- `alpfe` — dust-deposition pulses, episodic

Effective constraint count could jump from ~5 to ~20–30.

**What it unlocks.** Potentially breaks 5/6 outright; minimum delivers stronger statistical confidence on each parameter's identifiability.

**Compute cost.** ~300× current per-fit. Single fit on B200 ≈ 30–100 GPU-hours (vs ~10 min currently). Sweeps shrink from 80+ configs to 5–10 carefully designed configs per paper.

**Code lift.** ~1–2 weeks. Loader changes to stream monthly snapshots, loss function adjustments to handle temporal stacking, careful gradient accumulation across time. The box-model integrator stays per-snapshot.

**Risk.** Temporal modes may be more correlated than expected; effective constraint gain could be 2–3× rather than 10×. Even partial gain still attacks the ceiling.

**Success criterion.** First time-resolved fit at 3-AOI with Basin C base + POSi (see Tier 1 direction C) targets ≥ 5.5/6 mean_cal at n=10, or breaks 5/6 reproducibly (≥3/10 seeds at 5/6).

---

#### B. Box-model state extension toward full Darwin 3

**Hypothesis.** The current 5-PFT 2-layer integrator (~10 tracers, `carroll6_5pft_2layer.py`) is a fraction of Darwin 3's state vector. Each new tracer adds ~1 effective constraint AND a corresponding new loss channel. The box-model proxy is a co-binding constraint on the 5/6 ceiling alongside parameter conservation; extending the box dissolves part of the ceiling structurally.

Candidate extensions in order of recovery payoff:
1. **Zooplankton** (Z_micro, Z_meso) — currently absorbed into grazing-rate parameters; explicit zooplankton would decouple `Biggrow` from `diatomgraz` at the structural level.
2. **DOM** (DOC, DON, DOP, DOFe) — improves POC export and remineralization fidelity; constrains `R_PICPOC` indirectly via the C:N:P:Fe ratios.
3. **Full Darwin 3 carbonate** — currently `carbonate.py` has Follows 2006 + Wanninkhof 2014 but Darwin 3 has additional alkalinity sources/sinks; extending fixes the alkalinity drift seen under GLODAP hybrid targets.
4. **Multi-layer extension beyond 2 layers** — currently 0–50 m + 50–1000 m; full-depth multi-layer adds vertical structure information.

**What it unlocks.** Strongest long-term lever. Doesn't depend on new observation types — the existing tracer fields are already in Darwin output.

**Compute cost.** Each tracer added scales the box-model state vector ~linearly; per-fit cost increases ~1.5–3× depending on tracer count. Manageable on B200.

**Code lift.** Substantial. Each tracer family needs autograd-clean PyTorch dynamics + tests + integration with the loss function. ~2–4 weeks per major extension.

**Risk.** Higher than time-resolved because each extension requires careful physics fidelity. Some tracer dynamics (e.g. zooplankton density-dependent grazing) have multiple plausible formulations.

**Success criterion.** With zooplankton + DOM extensions, the 5/6 ceiling either dissolves or shifts the binding parameter to a previously-recoverable one. Either outcome is publishable.

---

#### C. Observation channel additions

Each adds independent information channels that directly attack the structural ceiling. Note: POSi (biogenic silica) is **already integrated** as an active constraint throughout v3.1 — the `POSI_W` env var in the production runner (`scripts/run_v3.0_with_modis_pic.py`) is the absolute-units MSE loss against GEOTRACES IDP2025 surface bSi, computed via the steady-state silica diagnostic in `src/darwindiff/silica.py` (no integrator extension required; bSi is diagnosed from existing diatom dynamics). Every Basin C config has `POSI_W=1.0`; `c_chl40_posi15` uses `POSI_W=1.5`. The structural 5/6 ceiling holds with bSi active.

##### C.1 Ocean color PFT-resolved Chl (OB.DAAC / OC-CCI) — leapfrog-phase per Jon's directive

**Hypothesis.** Remote-sensing PFT decomposition gives Pro-HL-specific, Syn-specific, and diatom-specific Chl independently of Carroll's group-mean target. Constrains `Smallgrow` (Pro-HL specific), `Biggrow` (Syn / large-euk), and `diatomgraz` simultaneously.

**What it unlocks.** Replaces the Chl1–Chl5 z-scored loss with absolute-magnitude PFT-resolved targets. Decouples the multi-PFT identifiability.

**Compute cost.** Loader is non-trivial (regridding from satellite swath to LLC270 grid); compute per-fit unchanged.

**Code lift.** ~1 day for loader + integration. Currently partly built for the leapfrog phase.

**Risk.** Ocean color PFT decomposition has well-known limitations in cloud-covered + high-latitude regions. Coverage gaps need careful handling.

**Success criterion.** Independent PFT-Chl constraints unlock `Smallgrow` Cal+ rate from current ~70% to ≥ 90% at Basin C base.

##### C.2 BGC-Argo depth-resolved profiles

**Hypothesis.** Currently we have surface + subsurface (50–1000 m) anchors via GEOTRACES; BGC-Argo gives much higher density of depth-resolved nitrate, oxygen, chl, particle backscatter, and DFe profiles. Time-resolved by construction.

**What it unlocks.** Combines naturally with time-resolved fitting (Tier 1 direction A). The strongest single observational addition for the time-resolved + global paper.

**Compute cost.** Loader uses `argopy` (already in deps); cluster-scale loading is the gating step.

**Code lift.** ~3–5 days. `argopy` handles the API; the integration with the box-model loss is the work.

**Risk.** Moderate. Float coverage is uneven; northern subtropical gyres have many fewer floats than Southern Ocean. Some regions have <10 floats over 23 years.

**Success criterion.** Depth-resolved DFe profiles tighten `alpfe` and `scav_rat` independently. Probably the strongest single addition for time-resolved fitting.

---

### Tier 2 — Indirect benefit on the structural ceiling

#### D. Native LLC270 resolution

**Hypothesis.** The current 1° proxy averages over ~10–30 native cells per 1° cell. If sub-1° spatial structure carries independent constraint information, native resolution captures it.

**What it unlocks.** Modest improvement on the 5/6 ceiling; substantial improvement on per-cell parameter maps (the "Carroll-can't-do-this" scientific story) and forward Darwin validation.

**Compute cost.** ~100–1000× more cells per AOI (the proxy uses ~1k cells, native gives ~10k–1M per AOI depending on region). Per-fit compute scales near-linearly with cell count. Single global native fit ≈ 100–500 GPU-hours.

**Code lift.** Modest. The `llc270_loader.py` exists; integration with the differentiable box-model needs careful dask/torch tensor handling at scale.

**Risk.** More cells of the same regimes are highly correlated; effective constraint gain may be small. The 5/6 ceiling may persist even at native resolution.

**Success criterion.** Per-cell parameter maps that are spatially coherent and biologically interpretable (e.g. `alpfe` higher in dust-deposition regions, `scav_rat` higher near sediment sources). Visualization is the deliverable, not the 5/6 break.

---

#### E. Global ocean coverage (full ocean, all regimes)

**Hypothesis.** Currently we use 3 specific regimes (HNLC, deep-mixed iron-replete, Southern Ocean). Adding subtropical gyres, coastal upwelling, marginal seas, polar shelves expands regime diversity. Different regimes constrain different parameters: subtropical gyres → `Smallgrow` (Pro-HL dominated), coastal upwelling → `R_PICPOC` (high PIC export), polar shelf → `diatomgraz`.

**What it unlocks.** Probably 0.5–1 additional Cal-grade parameter on average. Best combined with time-resolved + box extension; alone, the gain is modest.

**Compute cost.** Scales with the AOI count × cells per AOI. Global at native ≈ several thousand GPU-hours for a single fit (n=10 batched).

**Code lift.** AOI registry expansion + loader work. ~1 week.

**Risk.** The PER_AOI_DINN architecture currently uses one DINN per AOI; scaling to 10+ AOIs needs an alternative (per-regime clustering, hierarchical DINN). Untested.

**Success criterion.** Reproducible 5/6 across multiple AOIs; per-regime parameter values that match published priors.

---

### Tier 3 — Lower EV; nice-to-haves

#### F. Multi-seed at scale (n=100–500)

Better statistics on the structural ceiling claim. Confirms whether single-seed 5/6 events become reproducible at much larger n (they probably don't, per v3.0/v3.1 evidence). Easy to do on cluster (embarrassingly parallel array job); shouldn't be the priority.

#### G. Architectural sophistication

Larger DINNDeep, attention layers across cells, transformer encoders for env-channel mixing. Wave 6 falsified architectural-composition explicitly; the binding constraint is observation information, not network capacity. Low priority unless a specific architecture has theoretical reason to add information (e.g. cross-cell attention as a soft spatial-coupling test).

#### H. Forward Darwin validation

Run actual Darwin with the recovered DarwinDiff parameter maps; compare global tracer fields. Scientific closure that Green's-functions papers cannot claim. Requires the Darwin source build + namelist injection of per-cell parameters. ~1–2 weeks for the integration; doesn't depend on AICR but uses cluster compute for the Darwin run itself.

#### I. Track 2 emulator (separate project goal)

Train a neural-network stand-in for Darwin for long climate runs. Different problem class (likely transformer/FNO/graph net with spatial coupling); different network architecture. Cluster-required for training; the second project deliverable, distinct from Track 1 parameter recovery.

## Sequencing recommendations

### Phase 0 — laptop work, while waiting for cluster access

The proof-of-concept Carroll-6 v05 laptop work is **substantially done**: 85 single-lever configs, 847 seeds, all major observation channels (bSi via POSI_W, GEOTRACES surface + subsurface DFe + POC, Darwin POC/PIC absolute anchors, per-AOI Chl1–5, carbonate via DIC/ALK/CO2_flux) already active. Strict Phase-0 work that fits the proof-of-concept paper framing is essentially complete.

| Step | Direction | Cost | Notes |
|---|---|---|---|
| Reproduce `c_chl40_posi15` at n=20 (seeds 10-19) | — | ~7 min | Closes the only open reproducibility check from Wave 5 |
| Optionally: small zooplankton extension to box model | B (start) | 1–2 weeks | Decouples grazing-rate identifiability; useful for paper-2 but Carroll-6 v05 proof-of-concept doesn't need it |

Other potentially useful laptop work falls into **leapfrog territory** (different observation channels) per Jon's strategic directive: ocean color PFT-Chl, MODIS-Aqua PIC, PACE carbon_phyto. Shelved for paper-2.

### Phase 1 — Engaging onboarding + first cluster jobs (1–4 weeks)

| Step | Notes |
|---|---|
| MIT Sponsored Account via Jon | Critical-path step |
| Kerberos + Duo + OnDemand login | Auto-activates Engaging |
| Port one Basin C config to SLURM | `scripts/slurm/run_notebook.sbatch` template |
| First Engaging fit at 3-AOI Basin C base | "Code ran on Engaging" proof for AICR application |
| Reply to Lauren confirming Engaging usage | Per the AICR onboarding email |

### Phase 2 — AICR onboarding + first B200 jobs (likely 2–8 weeks after Phase 1)

| Step | Notes |
|---|---|
| AICR access form + onboarding | After Engaging confirmation |
| First B200 fit replicating laptop Basin C | Baseline calibration |
| Native LLC270 1-AOI fit | Direction D, baseline |
| Time-resolved 3-AOI fit | Direction A — the highest-EV experiment |

### Phase 3 — Paper #2 experiments (8–20 weeks total)

The paper-#2 experiments combine three cluster-gated directions:
1. **Time-resolved fitting** (Direction A) — 5–10 configs at ~50–100 GPU-hours each
2. **Native resolution** (Direction D) at 3 AOIs — 1–2 configs at ~500 GPU-hours
3. **Box-model extension toward Darwin 3** (Direction B) — incremental tracer additions (zooplankton, DOM) ship between configs

Total: ~1000–5000 GPU-hours on AICR. Substantial but fits comfortably in a beta-period allocation. The bSi (POSi) channel and per-AOI carbonate channels are already active and persist into paper #2; the leapfrog observation channels (ocean color PFT-Chl, BGC-Argo, satellite PIC) come in paper #3.

### Phase 4 — Global, full Darwin-3 box extension, Track 2

After Paper #2 ships. Each is a follow-on paper:
- Global recovery → paper #3 (parameter maps + forward Darwin validation)
- Track 2 emulator → paper #4 (long-timescale climate emulator)
- Full Darwin-3 box → paper #5 or method-paper companion

## Decision tree based on AICR access timeline

| AICR access timeline | Recommended priority |
|---|---|
| < 4 weeks (best case) | Phase 0 POSi + Phase 1 onboarding in parallel; aim for Phase 2 first jobs by end of June |
| 4–8 weeks | Phase 0 POSi extends to small zooplankton extension; Phase 1 + Phase 2 telescope to late summer |
| 8–16 weeks | Phase 0 expands: POSi + zooplankton + ocean color PFT-Chl loader; Phase 1 starts mid-summer |
| > 16 weeks (worst case) | Paper #1 ships as the proof-of-concept; Phase 0 work becomes the laptop-feasible POSi-augmented continuation; cluster work moves to the leapfrog paper independent of the proof-of-concept timeline |

## Risk-adjusted EV summary

| Direction | EV (5/6 break) | Cost (GPU-hr/fit) | Code lift | Risk | Priority |
|---|---|---|---|---|---|
| A. Time-resolved | High | 30–100 | 1–2 wk | Low | **Tier 1 #1** |
| B. Box-model extension | High | 1.5–3× current | 2–4 wk per | Medium | **Tier 1 #2** |
| C.1 Ocean color PFT-Chl (leapfrog) | Medium-High | negligible | 1 d | Medium | Tier 1, paper-3 |
| C.2 BGC-Argo (leapfrog) | Medium-High | medium | 3–5 d | Medium | Tier 1, paper-3 |
| POSi (bSi) — already integrated | — | — | done | — | Active in v3.1 sweep set |
| D. Native resolution | Medium | 100–500 | 1 wk | Low | Tier 2 |
| E. Global coverage | Medium | 500–5000 | 1 wk | Medium | Tier 2 |
| F. Multi-seed scale | Low | linear in n | negligible | Low | Tier 3 |
| G. Architectural | Low | 1–5× | 1–2 wk | High | Tier 3 |
| H. Forward Darwin | Medium (closure) | varies | 1–2 wk | Medium | Tier 3 |
| I. Track 2 emulator | N/A (separate) | high | many wk | High | Separate project |

## What to NOT do with cluster compute

- **Don't redo Wave 6 composition tests at cluster scale.** v3.1 already closed that hypothesis; cluster scale would not change the verdict.
- **Don't run multi-thousand-seed ceiling-confirmation runs.** The structural ceiling is well-characterized at n=10; cluster compute is better spent on Tier 1 directions.
- **Don't chase architectural exotica** (transformers, attention, mixture-of-experts) before extending observation channels. Architecture is not the binding constraint.
- **Don't try to brute-force more lever combinations.** The 84-config sweep set is comprehensive at single-lever scale; Wave 6 showed compositional levers don't help. New compute is for new directions, not more of the same sweep.

## Cross-references

- [docs/cluster_setup.md](cluster_setup.md) — operational guide for Engaging + AICR access
- [STATUS.md](../STATUS.md) — current v3.1 results and verified numbers
- [docs/findings/v3.1_closeout.md](findings/v3.1_closeout.md) — v3.1 closeout with Wave 6 composition test
- [docs/dinn_design.md](dinn_design.md) — architecture details
- [data/README.md](../data/README.md) — observation channel availability + planned integrations
