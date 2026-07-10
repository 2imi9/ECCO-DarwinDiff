# Overnight summary — 2026-07-08 (Track 2 build + FNO decision)

Morning readout of the autonomous overnight session. Everything below is committed on
`2imi9/status-handoff-2026-07-07` (not pushed) and gated (full suite / adversarial review / H200 / cited
sources). Three landed deliverables, one literature decision, a clear next step, and two items that want your
call.

---

## TL;DR

1. **DB-1 — spatial soluble-iron forcing loader** — done (`1098451`) + **real-data validated (2026-07-09)**.
   Replaces the constant `PHI_DUST` with the v05 Mahowald-2009 field. The `.bin` turned out to be **public on
   the NAS** (`input/darwin_forcing/`, no Earthdata login) — downloaded + real-file test passes. Finding: real
   local deposition ~200× below the tuned `PHI_DUST` (transport, not local dust, supplies dust-poor regions —
   a Track-2-thesis confirmation).
2. **Semi-implicit vertical-diffusion CFL fix** — done (`a0e7a50` + `862f319`). Removes the explicit
   silent-NaN wall that would have sunk an E2 rollout at realistic mixed-layer `kz`. **Validated ALL-PASS on a
   real H200.**
3. **FNO / neural-operator decision** — done (`f296246`). Cited, verified 9-topic pass: **keep the emulator
   shelved; the UDE is the right route** — and its literature hands the UDE reusable parts.
4. **Next step:** the **windowed-BPTT trainer** on the now-complete transport machinery → the E2 gate.
5. **Suite: 376 passed.** Track-2 machinery is numerically complete; no E2 *number* yet.

---

## Where both tracks stand

### Track 1 — parameter learner (per-cell DINN, 0-D box)
**Scientifically complete / manuscript-stage; unchanged this session.** The verified headline stands: the
per-cell DINN is load-bearing — it holds the observable trio {`alpfe`, `scav_rat`, `R_PICPOC`} 7/10 vs 0/10
for a global-scalar vector, from real absolute anchors. It is an honest **consistency check vs Carroll's
published values, not a discovery**; the surrogate gap (the 0-D box homogenizes → negative held-out real-data
R²) is what motivates Track 2. Nothing overnight touched Track 1.

### Track 2 — differentiable spatial model (UDE)
**Foundation + all deep-review fixes + the CFL fix are now in; the machinery is numerically E2-ready.** Status
by piece:

| Piece | State |
|---|---|
| Differentiable integrators (RK4 + checkpointing + time-aware forcing) | ✅ merged (#177) |
| Transport operators A1–A6 (div-free `w`, centered advection + explicit `kh`, DIC/ALK stoichiometry, surface dust, carbon budget, interior mask) | ✅ done + gated |
| **Semi-implicit Thomas vertical diffusion (no CFL wall)** | ✅ **done this session, H200-validated** |
| **DB-1 spatial soluble-iron forcing** | ✅ **done this session** (awaiting the `.bin`) |
| DB-2 real v05 velocity loader → `w_from_continuity` | ⬜ not built |
| DB-3 held-out GEOTRACES-section scoring | ⬜ not built |
| Windowed-BPTT trainer | ⬜ **next** |
| **E2 result** (held-out real-data R² with transport) | ⬜ **unbuilt — the make-or-break gate** |

**Emulator (FNO/operator surrogate): shelved, now with a cited justification** (see below). The forward-rollout
FNO scaffold (`emulator.py`) stays parked.

---

## 1. Semi-implicit vertical diffusion — the CFL fix (H200-validated)

**Problem it removes:** the explicit `vertical_diffusion` is stable only for `kz·dt/dz² < 0.5` and **silently
NaNs / blows up** above it. Realistic mixed-layer `kz ≈ 1e-2 m²/s` (≈ 864 m²/day) gives `r = 2.16` at
`dz=10 m, dt=0.25 d` — well past the wall — so an E2 rollout at realistic diffusivity would have silently
failed.

**What landed** (`src/darwindiff/transport.py`, `tests/test_transport_imex.py`,
`scripts/imex_h200_smoke.py` + sbatch):
- `thomas_solve` — batched, autograd-clean tridiagonal solve (matches dense `torch.linalg.solve` to **1e-16**).
- `vertical_diffusion_implicit` — backward-Euler `(I − dt·L)x = xⁿ`, same no-flux Laplacian `L`. **No CFL
  limit**, column-conservative (mass drift ~**1e-15**), gradcheck-clean.
- `imex_rollout` — first-order Lie split: explicit RK4/Euler on the (vdiff-free) tendency + implicit vdiff
  sub-step. Gradient-checkpointable (bit-identical recompute → windowed BPTT). `include_vdiff` flag + opt-in
  `dt` CFL guard.

**H200 validation** (node d4055, fp32; `sacct` COMPLETED): at `r=2.16` the explicit rollout blows up
**1.16e34×** while imex stays bounded (**0.88×**); checkpoint == plain **bit-identical on-GPU**; grads flow;
a **327k-cell** grid does fwd+bwd in **1.1 s**. Full suite **376**.

**Adversarial numerics review** (4 dims → verify): **numerics + autograd/checkpoint came back clean**. Applied
its fixes — `dt`-guard threading, an end-to-end operator-split regression test (catches double-count/drop of
vertical diffusion), and `rtol=0` to pin the backward-Euler boundary rows.
**Named follow-up (not blocking):** the `imex_rollout` explicit-tendency contract (`include_vdiff=False`) is
documented + test-guarded but not *structurally* enforced — a caller using the `include_vdiff=True` default
double-counts vertical diffusion. Consider having `imex_rollout` build the explicit part itself.

## 2. DB-1 — spatial soluble-iron forcing (recap)

Replaces constant `PHI_DUST` with the v05 **Mahowald-2009 spatial soluble-iron deposition field** (the
forcing fix from the Jon+Schultz meeting). Reads the LLC270 compact `.bin`, applies `darwin_inscal_iron=1000`,
AOI-bins onto the DFe target grid, converts areal flux → the box's volumetric rate via the transport `dz`.
Unit chain verified against the Darwin3 iron docs; compact reader / hFacC mask / DRF / binning **validated
against the real on-disk grid**. Adversarial review: physics/units + binary-IO clean; 1 docstring overclaim
fixed (+ `coverage_mask`), 3 test gaps hardened.

## 3. FNO / neural-operator decision (cited, verified)

Full doc: [`docs/research_notes/2026-07-08_fno_neural_operator_emulator_decision.md`]. **Unanimous verdict:
keep the parameter-conditioned emulator shelved; proceed with the UDE.** The two blockers are not removed by
any architecture:
- **Data scarcity is intrinsic to operator learning** — GINO trained on ~500 full solves, U-FNO on 4,500
  ECLIPSE sims, FourCastNet on ~37 yr hourly ERA5 (~1024 A100-hrs). DarwinDiff has **one** v05 point.
- **Dirty parameter gradients are measured** — SC-FNO: plain-FNO parameter-gradient R² **0.21–0.82** despite
  accurate forward solutions; the only fix needs **true Jacobian labels from a differentiable solver = the
  UDE**.
- **PINO** flips positive but argues *for* the UDE: a known-PDE residual loss drops data need to "few to no
  data" — but the physics you'd impose *is* the UDE.

**Reusable for the UDE (not the emulator):** PINO's physics-residual loss (data-free prior), **GINO's GNO
geometry encoder** for the irregular LLC270 grid + sparse-anchor ingest, SC-FNO/DINO sensitivity loss
(certified closure gradients + cheap UQ once differentiable), U-FNO's local U-Net path (closure architecture),
PhysicsNeMo blocks. **Earth2Studio** is a weather-only inference harness — not on the critical path.

---

## Next step (affordable with H200-only + 1 GCM point)

**Build the windowed-BPTT trainer** on the conservation-verified transport machinery (A1–A6 + IMEX vdiff),
toward the **E2 gate**. Fold in PINO's residual-loss idea (transport-residual term + test-time closure
fine-tuning). Optionally prototype a GINO-style geometry encoder as the LLC270 front-end — a modest accelerant,
not a dependency. **Reminder from the strategic review:** lead E2 with **calcite** (the information exists;
iron is the documented under-constrained counterexample), define the gate as a **delta vs a null/frozen
closure** under blocked CV — not raw held-out R² > 0.

## Needs your call

1. ~~**Stage the Mahowald ironfile.**~~ **RESOLVED (2026-07-09).** It was public on the NAS all along
   (`input/darwin_forcing/`, no Earthdata login — I'd had the path wrong); downloaded + real-file test passes.
2. **STATUS.md has concurrent-session WIP** (uncommitted `M STATUS.md`, `NEXT_SESSION.md`, `integrators.py`
   from a parallel session in the shared checkout). I deliberately did **not** edit them to avoid clobbering
   that work — so this summary + the E2-readiness note are the current "where we are" record for Track 2 until
   those are reconciled. If that parallel work is yours/settled, fold DB-1 + the IMEX fix + the FNO decision
   into STATUS.md's Track-2 section.
3. **E2 definition lock** (from the earlier strategic review) — still on hold pending your explicit go: I
   drafted the delta-based E2 gate (learned closure beats null/frozen closure + kriging under leave-region-out
   CV, skill peaking at physical K) for a #176 comment. Say the word and I'll post it.

*Session commits: `1098451` (DB-1) · `a0e7a50` + `862f319` (IMEX/CFL) · `f296246` (FNO decision). Issue #176
updated with DB-1 and the IMEX/H200 result.*
