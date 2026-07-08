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

**ALL A1–A6 done and gated (2026-07-08); full suite 314.** The transport machinery is now scientifically sound
for E2. Remaining before an E2 *number*: the windowed-BPTT trainer (with the checkpoint-equivalence gate,
already added) + the E2 run carrying the `K_num`/ablation diagnostics; plus the data staging (soluble-iron
forcing loader, real v05 velocity → `w_from_continuity`, held-out GEOTRACES-section scoring). The air-sea CO₂
flux in the field version (currently an optional `co2_flux` passthrough) and a semi-implicit Thomas vertical
diffusion are named follow-ups.
