# Deep review — the transport machinery is NOT yet E2-ready (2026-07-07)

A deep review (workflow: 4 dimensions → verify → synth + completeness critic; verify partly rate-limited so
the load-bearing claims were re-confirmed by hand) of the Track-2 transport/closure machinery. **Verdict: the
primitives are correct and well-tested for what they claim (closed-domain conservation, fp64 gradcheck, finite
long rollouts), but the *scientific scaffolding* around them is missing or wrong, and every conservation test
is structurally blind to its absence. An E2 held-out-R² computed on the machinery as-is would be an artifact.**
This corrects the earlier "Phase-1 machinery complete" framing.

Self-confirmed against the code (torch probes):
- **A1 divergence artifact:** a perfectly uniform tracer under a divergent velocity spreads to **[0.0, 9.6]**
  over a short rollout, total exactly conserved.
- **CFL silent NaN:** explicit `vertical_diffusion` at `kz·dt/dz²=1.25` → **NaN** (no guard).
- **A4 dust every layer:** `dDFe += alpfe·PHI_DUST` is identical across all 8 layers → **column gets 8× the
  surface iron flux.**

## Must-fix before any E2 number (ordered — each corrupts the held-out R²)

**A1 — make the velocity field discretely non-divergent (the single most important fix).**
Flux-form advection is `dC/dt = -u·∇C - C·div(u)`; for `div(u)≠0` the `C·div(u)` term is a spurious reaction
that manufactures per-cell structure the closures absorb as fake biology. Real ECCO-Darwin time-mean
velocities are **not** discretely div-free, so this fires on the E2 field. **Fix:** recompute `w(z)` from
column continuity (integrate horizontal divergence) so the 3-D flux is div-free. **API change required:**
`vertical_advection` takes a scalar `w: float` and `grid_tendency` hardcodes `w=0`, so horizontal `div(u)` is
structurally uncompensable today — give `vertical_advection` a per-layer `w(z)` vector. Gate: uniform tracer
under the *continuity-completed* field stays uniform to machine precision.

**A2 — replace first-order upwind with a physical, tunable scheme (decisive).**
Upwind's numerical diffusion `K_num ≈ 0.5·|u|·dx` is **3× (native) to 25–50× (1° eqpac, ~25,000 m²/s) the
physical eddy diffusivity** (~500–2,000). It smears gradients >1,000 km (≥ the AOI) over a year. E2 fails
**both ways**: (a) *false pass* — everything homogenises to a smooth basin shape, so held-out cells are
"predicted" by smeared neighbours; (b) *destroyed signal* — the per-cell gradient the recovery needs is erased
and equifinality returns. The design brief explicitly forbade upwind ("re-opens the surrogate gap"). The prior
review's centered→upwind swap fixed a ~1e10 instability but re-introduced this defect. **Fix:** flux-form
centered-2nd (or the brief's smooth tanh-blended TVD limiter) **+ a small explicit Laplacian/biharmonic
horizontal diffusion set to the physical eddy value**, so total diffusion is physical and controllable. The
instability that motivated the upwind swap was largely the **A1 divergence source** — fix A1 first and
centered+explicit-diffusion is far more stable. **The decadal-stability test is under-certified:** it runs to
t=200 at Courant ~0.0125 (real is ~0.1–0.3); extended to a true decade the field grows 20.16× and *fails* its
own <20× bound.

**A3 — wire calcite stoichiometry into the state, or explicitly scope it out.**
`bgc_tendency_field` returns 5 tracers `[DFe,Ps,Pl,POC,PIC]`; `pic_prod` feeds **only** `dPIC`. The
`pic_prod→dPIC(+1)/dDIC(−1)/dALK(−2)` coupling ("the property that protects the mass gate") lives only in the
separate 7-tracer `carroll6_carbonate_step`, which the transport path never calls. So `EnvCalciteClosure`'s
carbon/alkalinity effect is silently dropped and calcite conservation is untestable on the E2 path. **Fix:**
carry DIC+ALK in the field state and route the single `pic_prod` into (+1/−1/−2), **or** scope Phase-1 E2 to
PIC-only and drop the mass-gate claim for this state vector.

**A4 — iron dust is a surface flux, not a per-layer injection.** Apply dust only at Z=0 (÷ dz), or pass a
surface-only dust field; gate that column-integrated dust equals the surface flux independent of Z. (The
`dust=` kwarg already accepts a field, so this is a forcing-staging fix + a guard, not an operator rewrite.)

**A5 — build (and test) the per-element open-system budget.** It does not exist: every conservation test is
`bgc=False`; the two `bgc=True` tests assert only `isfinite`. Accumulate integrated dust in / export+scav out
in fp64 and assert `|ΔN − (in−out)| < tol` **per element in its own units** (Fe in Fe, C in C). Extend
`relative_mass_drift` to receive the source/sink terms.

**A6 — open boundary conditions for the regional AOI window.** No-flux zero-pad = solid walls (uniform outflow
`u=+1` gives edge tendencies `[−1,0,0,+1]` — a fake boundary layer exactly where the closures read the signal).
The E2 AOI is open. **Fix:** prescribed-halo inflow / zero-gradient outflow, or mask an edge ring from the loss.

## Completeness-critic (compounding, and a silent-failure)

- **Vertical structure is currently off or wrong:** `w=0` everywhere (A1), dust in every layer (A4), and POC/PIC
  sinking is an *in-place point sink* (`dPOC = mort − W_SINK·POC` at every depth, never *moved* to depth). So
  "prescribed transport supplies the spatial structure" — Phase-1's whole premise over the 0-D box — is **not
  yet realised by the code**, independent of the upwind problem.
- **Explicit vertical diffusion has no CFL guard → silent NaN** at realistic mixed-layer `kz` (confirmed). The
  brief mandates semi-implicit backward-Euler (batched Thomas); interim, at least a loud `kz·dt/dz²<0.5` assert.
- **Checkpoint-vs-dense gradient equivalence is only tested on the trivial `_decay` tendency**, never on
  `grid_tendency`+a live closure with the upwind `where` branch under recompute. Add that gate.

## Ordered build sequence (revised Phase-1)

1. **A1** per-layer `w(z)` + `w_from_continuity` + div-free gate. 2. **A2** centered + explicit physical
diffusion (stable once A1 lands) + `K_num` diagnostic. 3. **A4** surface dust. 4. **A3** DIC/ALK in the state
(or scope PIC-only). 5. **A5** per-element budget accumulator. 6. **A6** open BCs. 7. CFL guard / semi-implicit
Thomas. 8. Windowed-BPTT trainer **with a checkpoint-equivalence gate**. **Only then** an E2 number — carrying
`K_num` and a dt/dx ablation showing R² does *not* track numerical diffusion (a positive dependence proves the
pass is numerical).

## Progress (2026-07-08)

**Landed + gated:**
- Interim hardening: precondition docstrings (div-free velocity, closed-domain BCs, surface dust, explicit-CFL
  limit) + non-square directional grid gate + checkpoint-vs-dense equivalence gate.
- **A1 — divergence-free `w(z)` from continuity** (`w_from_continuity` + per-interface `vertical_advection`).
  Verified: uniform-field spurious tendency **0.60 → <1e-12** (fp64); stays uniform over a 400-step rollout.
- **A2 — centered-2nd advection + explicit tunable `horizontal_diffusion(kh)`** (drops upwind's 3–50×
  numerical diffusion; diffusion now explicit/diagnosable for the `K_num` ablation). Verified: centered exact
  on linear fields; unstable at `kh=0` (→1e7), bounded at `kh≥0.05` with A1's `w`.
- **A4 — `surface_dust_field`** (dust at the surface layer only; column no longer gets Z× iron).
- **A3 — DIC/ALK stoichiometry** in `bgc_tendency_field` (7-tracer): the single `pic_prod` feeds
  `dPIC(+1)/dDIC(-1)/dALK(-2)`, so the calcite closure's carbon effect is real and carbon conserves through
  calcification. Verified: total-C tendency `== -W_SINK*(POC+PIC)`; `dALK == -2*pic_prod`.
- **A5 — `carbon_total` + rollout budget-closure gate**: co-integrating cumulative export, carbon conserves to
  fp64 machine precision over a rollout (the per-element mass gate, #7).
- **A6 — `interior_mask`**: no-flux walls are closed-domain-only; the open-AOI E2 loss excludes the wall ring.

## E2 design guardrails (independent second-opinion, 2026-07-08)

- **Lead with CALCITE, not iron.** The wall is at the *observable*, not the cell count: iron *concentration* is a
  low-information projection of the scavenging *rate* (Tagliabue decoupling), so a held-out iron R²>0 can come from
  an *equifinal, meaningless* `scav_rat`. Calcite's PIC:POC observable ≈ the parameter → a pass is meaningful.
  Report iron as the documented *information-wall counterexample* in the same paper, not a second attempt.
- **Primary E2 control = a NULL-CLOSURE baseline** (`g_θ≡1` constant, through the *identical* transport + K_num).
  If the constant closure also clears held-out R², transport smoothing did the work → the pass is spurious. This
  is stronger than the K_num ablation alone (which stays: learned-minus-null gap must be largest at physical K_num
  and shrink as K_num grows).
- **Metric = anomaly-R² (field minus basin-mean) on a BLOCKED/regime split** (e.g. train eqpac+natl / test SO),
  never level-R² on random cells whose neighbours are in-training (trivial interpolation). Add a permuted-predictor
  control and a profile-curvature cross-check at the claimed-pass K_num.
- **Guard calcite circularity:** do NOT fit to MODIS PIC and test on held-out MODIS PIC (that's satellite-field
  interpolation). Anchor on Daniels CP:PP + a blocked split; the claim is *environment-conditioning of PIC:POC
  reproduced on held-out data*, corroborating (not discovering) a ratio closure Darwin already parameterises.
- **Fallback = the paper spine, not a consolation prize:** an *identifiability map* of Darwin's BGC closures through
  a conservation-verified differentiable transport model — which real obs CAN constrain (calcite, curved) vs CANNOT
  (iron scavenging, shallow/DPI-limited) + the observing-system density (GEOTRACES/PACE) that would close the gap.
  Novel and honest even if a binary E2 "pass" never lands.

**ALL A1–A6 done and gated (2026-07-08); full suite 314.** The transport machinery is now scientifically sound
for E2. Remaining before an E2 *number*: the windowed-BPTT trainer (with the checkpoint-equivalence gate,
already added) + the E2 run carrying the `K_num`/ablation diagnostics; plus the data staging (soluble-iron
forcing loader, real v05 velocity → `w_from_continuity`, held-out GEOTRACES-section scoring). The air-sea CO₂
flux in the field version (currently an optional `co2_flux` passthrough) and a semi-implicit Thomas vertical
diffusion are named follow-ups.

## Data staging toward E2 — DB-1 (2026-07-08)

**DB-1 — soluble-iron forcing loader (`src/darwindiff/iron_forcing_loader.py`, + `scripts/fetch/iron_forcing.sh`,
`tests/test_iron_forcing_loader.py`).** Replaces the constant scalar `PHI_DUST` with the v05 **Mahowald-2009
spatial soluble-iron deposition field** — the forcing fix from the Jon+Schultz meeting (spatial iron
variability belongs in the *forcing*; `alpfe` stays a global scalar). Independent of the calcite-first E2
guardrail above: this forcing field drives the DFe part of the coupled rollout regardless of which observable
leads, so it is shared infrastructure, not an iron-first commitment.

- **Format** (from v05 `data.darwin` + Darwin3 iron docs): `ironfile=llc270_Mahowald_2009_soluble_iron_dust.bin`,
  `ironperiod=-12` → LLC270 **compact** binary, 12 monthly-climatology records × 13 faces × 270², big-endian f4
  (45.5 MB); `darwin_inscal_iron=1000` (raw `mol Fe/m²/s` → `mmol/m²/s`); `iron_interpMethod=0` (step).
- **Unit chain** (the crux): Darwin's surface source is `S_Fe = alpfe/(dr_F·hFacC)·F_Fe`, so `PHI_DUST ≡ F_Fe/dz`
  with `alpfe` separate. The loader returns the **grid-independent areal flux**; `flux_to_phi_dust(areal, dz)`
  divides by the transport model's *own* `dz` (not Darwin's 10 m), and `phi_dust_surface_field` places it at
  Z=0 only (composes **A4**). `hFacC` dropped — verified **exactly 1** at the LLC270 open-ocean surface.
- **Ocean masking** uses grid `hFacC>0` (correct land/sea), *not* the tracer loader's `field!=0` (which would
  drop genuine low-deposition ocean and bias bin-means high). Bins onto the **same 1° grid as the DFe targets**.
- **Validation — now against the REAL `.bin` (2026-07-09).** The file is **public on the NAS** ECCO portal
  (no Earthdata login) in `input/darwin_forcing/` (my earlier "Earthdata-gated" claim was wrong — I'd missed
  that subdir); downloaded (exact 45,489,600 B) and the real-file test passes. Real areal flux is physically
  ordered — **natl (Saharan) 1.9e-10 > eqpac 1.4e-10 > SO 5.1e-11 mmol/m²/s**, spatial CV 0.13–0.66.
  **FINDING:** the real local deposition runs **~200× BELOW the box's tuned `PHI_DUST=5e-5`** (eqpac vol@50m
  ~2.4e-7) — because dust-poor regions get their iron from lateral/vertical **transport** (the Equatorial
  Undercurrent), which the 0-D box faked with an inflated scalar. **This is a clean confirmation of the
  Track-2 thesis** (transport supplies the iron the box couldn't), not a load error. `phi_dust_sanity` was
  therefore corrected from a ratio-vs-`PHI_DUST` gate to a **physical-range** check on the areal flux.
- **Adversarial review** (workflow: 4 dims → per-finding verify): **physics/units and binary-IO came back
  clean** (empty, with concrete reproduction attempts); fixed 1 docstring overclaim (`interior_mask` excludes
  only the outer ring, *not* interior no-coverage bins → added `coverage_mask` for the E2 loss) + hardened 3
  test-adequacy gaps (independent-literal unit pin; non-opt-in monkeypatched `hFacC>0`-mask test; synthetic
  `hFacC` surface-slice test) — mutation-checked to fail on their target regressions. **Full suite 352.**
- **Caveat for the E2 loss:** the `fill=0` at no-coverage bins is a *fabricated* zero source; the loss must
  AND-in `coverage_mask(areal_flux_grid)` (computed before the fill) alongside `interior_mask`. eqpac has 0
  no-coverage bins so it is harmless there, but coastal/island AOIs need it.

Next in the DB chain: **DB-2** (real v05 velocity loader → `w_from_continuity`), **DB-3** (held-out
GEOTRACES-section scoring), then the windowed-BPTT trainer → the E2 run.

## Semi-implicit vertical diffusion — CFL silent-NaN fix (2026-07-08)

The named follow-up "semi-implicit Thomas vertical diffusion" is now **done** (commit `a0e7a50`,
`src/darwindiff/transport.py`, `tests/test_transport_imex.py`, `scripts/imex_h200_smoke.py` +
`scripts/slurm/run_imex_h200_smoke.sbatch`). The explicit `vertical_diffusion` is stable only for
`kz·dt/dz² < 0.5` and **silently NaNs / blows up** above it; realistic mixed-layer `kz ≈ 1e-2 m²/s`
(≈ 864 m²/day) gives `r = 2.16` at `dz=10 m`, `dt=0.25 d` — well past the wall — so an E2 rollout at
realistic diffusivity would have silently failed.

- **`thomas_solve`** — batched, autograd-clean tridiagonal solve (matches a dense `torch.linalg.solve`
  to 1e-16); **`vertical_diffusion_implicit`** — one backward-Euler `(I − dt·L)x = xⁿ` sub-step, `L` the
  *same* no-flux Laplacian the explicit operator applies. **No CFL limit**, column-conservative (mass
  drift ~1e-15), gradcheck-clean.
- **`imex_rollout`** — first-order Lie split: explicit RK4/Euler on the (vdiff-free) tendency, then one
  implicit vertical-diffusion sub-step. Gradient-checkpointable (bit-identical recompute) for the
  windowed-BPTT trainer; `include_vdiff` flag + opt-in `dt` CFL guard on the explicit path.
- **Validated on a real NVIDIA H200** (node d4055): at `r=2.16` the explicit rollout blows up `1.16e34×`
  while imex stays bounded (`0.88×`); checkpoint==plain bit-identical on-GPU; grads flow; a 327k-cell grid
  does fwd+bwd in **1.1 s**. **Full suite 376.**
- **Adversarial review** (4 dims → verify): **numerics + autograd/checkpoint came back clean**; fixed
  the `dt`-guard threading, added an end-to-end operator-split regression test (catches double-count/drop
  of vdiff), and `rtol=0` to pin the backward-Euler boundary rows. **Named follow-up:** the imex
  explicit-tendency contract (`include_vdiff=False`) is documented + test-guarded but not *structurally*
  enforced — a caller using the `include_vdiff=True` default double-counts vertical diffusion (silent at
  small `r`, NaN above CFL). Consider making `imex_rollout` build the explicit part itself.

This removes the last numerical blocker the deep review named; the windowed-BPTT trainer can now roll out
at realistic `kz`. The trainer + DB-2/DB-3 data staging remain before an E2 *number*.

## Windowed-BPTT trainer + synthetic-twin dry run (2026-07-08)

The windowed-BPTT trainer is **built** (`src/darwindiff/trainer.py`, `tests/test_trainer.py`,
`scripts/e2_synthetic_twin_h200.py` + sbatch). It fits a learned closure by rolling the spatial field
through `imex_rollout` (prescribed transport, mass-conserving, no CFL wall) and backpropagating a masked
observation loss to the closure's parameters. Two modes: **checkpointed full BPTT** (climatology
steady-state, exact gradient) and **truncated BPTT** (`detach_window` — score only the final converged
window). Built-in E2 controls: a **frozen-closure null baseline** (`rollout_field`) and **held-out** cell
scoring (`masked_r2`).

**Machinery validated on a synthetic self-twin (H200-runnable).** Recover a known env-driven calcite
closure through genuine **divergence-free advective** transport (`w_from_continuity`) at eqpac scale, blocked
49% hold-out: **learned held-out R² = +1.00, null = −0.31, DELTA = +1.31** — the trainer recovers the closure
and beats the null baseline. Full suite **387**.

**But the dry run surfaced E2-protocol findings that would have bitten the real run (the valuable part):**
- **A synthetic self-twin cannot test the E2 *thesis*.** The closure is **per-cell in env** `g(env)`, so
  held-out recovery comes from **env-interpolation**, not "transport closes the surrogate gap." A flexible
  closure can **absorb** transport differences. So the twin validates the *machinery*, not the science.
- **The K_num ablation is non-discriminating on a self-twin.** Sweeping `kh` (50→800) leaves the
  learned-minus-null delta **flat** (1.306→1.307) — the closure re-fits to whatever transport it is given.
  K_num only bites on **real, out-of-class** data (Darwin's field is not a per-cell env function). The
  script reports K_num as a **non-gating diagnostic**, not a pass.
- **`u=v=0` leaves the columns nearly decoupled** — the first script version had no advection, so `kh` did
  almost nothing (correctly flagged by the review). Fixed: a prescribed **div-free** velocity so the rollout
  genuinely transports.
- **For a per-cell env closure, spatial blocking ≠ env-regime hold-out** — env interpolates across spatial
  blocks. The real E2 needs an **env-regime** hold-out (hold out an env band), not just spatial blocks.

**Adversarial review of the trainer** (4 dims → verify): training-correctness + autograd came back with
hardening findings, all fixed — a **finite-guard** that aborts (preserving last-good params, records
`aborted`) instead of a NaN gradient silently poisoning every parameter via `clip_grad_norm_` (**P2**, real
hazard for autonomous sweeps); `weight_decay` restricted to the flexible MLP (not `ScavClosure`'s
nonzero-anchored `log_r0`/`raw_p`, which would fabricate a rate/`p` signal); a **structural-coupling guard**
(rejects a hook/observable pair the closure can't influence — e.g. `calcite_closure` vs `dfe_observable`);
and the **TBPTT bias fix** (score only the final converged window — recovery jumped 0.04→0.999). Plus test
hardening: a leakage tripwire, all-params-moved, TBPTT-recovers-and-beats-null, and a `ScavClosure` trainer test.

**Net:** the trainer machinery is complete and gated. The real E2 *number* now needs three inputs, not more
machinery: **DB-2** (real v05 velocity → `w_from_continuity`), **DB-3** (real held-out obs — calcite first,
per the E2 guardrails), and an **env-regime hold-out** with the K_num control on that out-of-class data.
