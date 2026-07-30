# Track-2 forward emulator — build plan (2026-07-11)

> **⚠️ SUPERSEDED — the 'beats persistence' framing is RETRACTED (2026-07-23).** Persistence
> is a weak baseline on an autocorrelated monthly ocean. Against a per-cell *seasonal AR(1)*
> baseline with block-bootstrap CIs the emulator scores **−0.161 ± 0.015** across four seeds,
> with the interval entirely below zero on every seed. Read what follows as the record of what
> was believed at the time. See `docs/findings/2026-07-23_emulator_baselines_v2.md`.

**Decision (this session):** the **forward / OSSE neural-operator emulator** is the next Track-2
workstream, targeting **native LLC270 full resolution at B200 scale**. This note is the plan; no
code is written until it's reviewed. It supersedes nothing — it operationalizes ADR-0002 (which lives
in worktree `.claude/worktrees/competent-stonebraker-a9c3c0/docs/adr/0002-track2-emulator-scope.md`,
not yet on this branch) and the
[2026-07-09 emulator update](2026-07-09_parameter_conditioned_emulator_update.md). Cross-refs to
`docs/findings/emulator_poc_scored.md` and the `native_peraoi` results point to **local-only**
worktree artifacts (`dd_overnight_wt`), not files on this branch.

> Draft for review — not committed/pushed. Forward plan, not a result.

## 0. Which emulator this is (the load-bearing distinction)

There are two "emulators" in the Track-2 record; only one is being built:

- **Parameter-conditioned emulator for *calibration*** (`FNO(state, Carroll-6) → next`) — **stays
  shelved.** Blockers unchanged: no affordable perturbed-parameter Darwin ensemble, and the DIFNO
  theorem says a calibration-grade surrogate needs true Jacobian labels that only a differentiable
  solver (the UDE) provides. Not this build.
- **Forward / OSSE emulator** (this plan) — a neural operator that rolls ECCO-Darwin's ocean-carbon
  state forward in time for **long-timescale (multi-decadal) carbon runs and observing-system
  design**. This is the workstream Jon flagged as his deep interest, and the first genuine
  **B200-scale** job. It is a *forward instrument*, **not** an identifiability rescue — the
  identifiability limits (iron wall, calcite support-limit, growth degeneracy) stand regardless.

## 0b. UPDATE 2026-07-12 — the make-or-break gate PASSED (local, `docs/findings/emulator_poc_scored.md`) — that pass is RETRACTED 2026-07-23

Ran overnight on the Explorer cluster (job 8302950, T4; `scripts/emulator_poc.py`), eqpac, 6 carbon
tracers, 500 epochs, temporal hold-out, 3 prognostic seeds + 2 forcing seeds. **Result (RETRACTED
2026-07-23, see `2026-07-23_1hr_run_summary.md` §4 — no significant skill vs a per-cell seasonal AR(1)
baseline): an FNO appeared to beat persistence AND climatology on held-out v05 next-state** — skill
**+0.18 ± 0.01** (3/3 seeds),
anomaly-R² vs climatology **+0.36–0.41** (the load-bearing guard: it's learned dynamics, not the
seasonal cycle). Honestly bounded: the skill is concentrated in the dynamic biological tracers
(Chl1/PIC/POC/FeT); the slow carbonate fields **DIC (−0.25) / ALK (−0.05) are NOT beaten** (persistence
near-unbeatable there → a **residual/tendency formulation** is the obvious fix); and the 6-step rollout
is stable but degrades toward persistence (needs rollout-aware training). **Verdict: the emulator
direction is viable and worth the B200 scale-up.** Next experiments (for review before running):
residual formulation for DIC/ALK, rollout-aware loss, more AOIs. (GPU note: the `cu128` build has no
V100/CC-7.0 kernels — pin T4/A100/H200; the tiny grid is launch-bound so tier is immaterial.)

## 0c. UPDATE 2026-07-12 — the method-fix is CONFIRMED (local, `docs/findings/emulator_methodfix_scored.md`)

The §0b "next experiments" were run (Explorer T4), and both bounds are resolved:
- **Residual/tendency formulation** — the model predicts Δx and returns `x(t) + FNO(x(t))`, so it starts
  *at* persistence and learns only the correction. The slow carbonate tracers **DIC/ALK now beat
  persistence too** (the §0b failure is fixed).
- **Rollout-aware training** (K-step loss) — makes the multi-step autoregressive rollout robust.
- **Confirmed robust against the persistence yardstick only — RETRACTED 2026-07-23 (job 188087: no
  significant skill vs a per-cell seasonal AR(1) baseline):** all six tracers beat persistence across
  **n=6 seeds**, rollout beats persistence
  at the final step in **6/6**; and the method **generalizes to depth** (3 levels — overall skill holds,
  every tracer positive). Verified honest (fixed persistence yardstick; leak-free pipeline inherited from
  the audited PoC; residual is not a free lunch — a positive skill still requires the learned Δ to help
  out-of-sample). Full numbers are local-only in the scored doc.

**The cheap-Explorer de-risking is complete.** The residual + rollout-aware method is proven on the
eqpac subset at surface and depth, so the B200 scale-up (§2, §3) would now scale a *proven* method, not
a guess. Next is the scale-up itself (native LLC270 / global / full-depth), gated only on the practical
850 GB→AICR staging (+ Jon on the OSSE framing) — not on any remaining method risk.

## 1. The make-or-break gate (analogous to the UDE's E2) — PASSED, see §0b (that pass is RETRACTED 2026-07-23)

Before any scale-up, one question decides the whole thing: **can a neural operator learn v05
next-state on real data — i.e. beat persistence on held-out months?**

- **Baseline (the "null"):** persistence, `x̂(t+1) = x(t)`. The ocean is highly autocorrelated
  month-to-month, so persistence is a *strong* baseline — beating it is the real bar (this is the
  emulator's version of E2's constant-through-transport null).
- **PoC model:** the existing `src/darwindiff/emulator.py` FNO (`FNO2d` / PhysicsNeMo `FNO`),
  autoregressive one-month step, prognostic (input vars == output vars) + forcing channels
  (SST/wind/dust/MLD).
- **Split:** temporal hold-out (train early years, score later years), like NeuralOGCM/GLORYS.
- **PASS:** held-out anomaly-R² (or RMSE skill vs persistence) **> 0**, and stable multi-month
  autoregressive rollout with no non-physical drift (cf. the #7 mass-conservation research question).
- **Scoring must be honest:** report skill *over persistence*, not raw R² (raw R² is inflated by the
  autocorrelation persistence already captures — the same "transport did the work, not the closure"
  trap the E2 exposed).

**Where the PoC runs:** an Explorer cluster GPU, which I can automate. (It planned for H200 but
**actually ran on T4** — job 8302950 — after the `cu128` build hit `no kernel image` on V100; see
§0b. The tiny grid is launch-bound so tier is immaterial.) The PoC is a **tractable subset** — a
region (e.g. eqpac) and/or a handful of carbon tracers (DIC, ALK, PIC, POC, DFe, Chl), surface + a
few depth levels. The PoC de-risks the B200 spend; it is **not** the production model.

## 2. The H200 → B200 ladder

| stage | scope | platform | gated on |
|---|---|---|---|
| **PoC gate** | region/coarse subset, next-state, beat-persistence | **H200 (I automate)** | — (data staged) |
| Pipeline + adapters | data loader, Earth-2 coord/depth/DataSource adapters | **H200 (I automate)** | grid decision (§3) |
| **Production** | native LLC270 full-res, multi-decadal, all carbon tracers | **B200 (you launch)** | cert + Jon (§4) |
| OSSE runs | ensemble perturbation → observing-system design | **B200 (you launch)** | Jon's target |

Rationale for the ladder: a single *parameter fit* is launch-bound (same on H200/B200), but
**operator training is throughput/memory-bound** — many samples, large model, native full-res global
fields — which is exactly where B200's memory (192 GB) and throughput earn their keep. The PoC is
small enough for H200; production is not.

## 3. Earth-2 adaptability — what exists, what's missing (grid: native, per decision)

**Already wired (deliberate, in `emulator.py`):**
- `DarwinEmulator` subclasses **`physicsnemo.Module`** (fallback `nn.Module`) → slots into the
  PhysicsNeMo registry / checkpoint / distributed tooling unchanged. `build_emulator` swaps in
  `physicsnemo.models.fno.FNO` on-cluster.
- Implements the **Earth-2 Studio prognostic contract directly** (`input_coords`/`output_coords`/
  `step`/`create_iterator`), rolling its own rather than earth2studio's `create_prognostic` wrapper —
  which sidesteps the weather-coord coupling that wrapper carries (per the 2026-06-14 audit).

**The three adapters the production build needs (the "make it Earth-2 *runnable*" work):**
1. **Curvilinear-grid CoordSystem.** The scaffold hardcodes a regular lat/lon grid; native is
   **LLC270 curvilinear (13 faces)**. Earth-2 Studio's CoordSystem + IO assume rectilinear → write a
   curvilinear adapter. **Chosen: native** (per "utilize B200" — B200 is what makes native tractable;
   this session's identifiability map showed native resolution is where the science is).
2. **Depth coordinate.** Scaffold is surface-only (H,W); a carbon emulator needs Z (50 levels). Map
   ocean depth onto Earth-2's vertical-level machinery (built for atmospheric pressure levels).
3. **ECCO-Darwin `DataSource`.** Earth-2's data sources are all weather (ERA5/GFS); write a custom
   `DataSource` for the v05 monthly fields.

**Strategic upside of staying Earth-2 native:** free scale/checkpoint/distributed on B200; access to
Earth-2 Studio's ensemble-perturbation + diagnostics harness (directly useful for the OSSE mission);
and **first ocean-BGC model in the Earth-2 ecosystem** — a clean whitespace + NVIDIA-grant
(Simulation & Modeling) narrative.

## 4. Dependencies / blockers (honest) — B200 status verified 2026-07-11

- **B200 auth, tested with the freshly regenerated cert (aicr_keys.zip):** the new cert is installed
  (`~/.ssh/aicr2/`) and the server now **trusts the CA** (`ssh -vv` shows "Server accepts key") — a
  step forward from the prior outright CA rejection. **But the private key is passphrase-encrypted**
  (temporary passphrase in the zip), so unattended SSH cannot sign. Unlocking it requires either an
  interactive `ssh-add ~/.ssh/aicr2/id_ed25519_aicr` (**your step**) or stripping the passphrase
  (declined by the safety layer as an unattended credential-weakening — correctly). Per AICR docs,
  cert renewal is browser-portal-only (no non-interactive path). **Net: B200 is your interactive
  scale-up machine; I cannot drive it unattended tonight.**
- **This does not gate the PoC.** The make-or-break PoC is a tiny grid → launch-bound (same speed on
  H200/B200), and B200's value is the *scale-up* (native full-res, 850 GB staged to AICR — multi-day,
  not overnight). So the overnight PoC runs on **H200**, and B200 waits for the scale-up.
- **Data staging to B200:** ~850 GB (280 months × 16 native LLC270 fields) currently on Explorer; a
  B200 run needs it on AICR /scratch or /work (your Duo-gated transfer, or a shared mount if one
  exists — TBD).
- **Jon-gated:** the *OSSE target* (what observing system the scaled emulator optimizes). The
  emulator *infrastructure* (§1–§3) is **not** gated — it proceeds on H200 now.
- **Not gated / not blocking:** the papers. This emulator is a **parallel track**; it does not unblock
  Paper #1 or #2 (those still need Jon's review).

## 5. Data (verified on Explorer)

`/projects/schultz/qi.zim/ecco_darwin_v5/output/monthly`: **280 monthly timesteps**, 16 fields —
ALK, apCO2, Chl1-5, CO2_flux, DIC, FeT, mldDepth, PIC, POC, POSi, SST, wspeed. Native LLC270, ~50
levels, ~190 MB/field/step (~850 GB total). ~23 years — ample for temporal-split operator learning.
No velocity in this tree (the emulator learns dynamics implicitly from the tracer time series +
surface forcing; it does not need prescribed transport the way the UDE E2 did).

## 6. Open decisions for review

The **PoC gate is DONE and PASSED** (§0b — built, run on **T4** job 8302950, beat-persistence with a
climatology guard; single-AOI/low-seed caveats stand). The remaining open items are therefore:

1. ~~Go/no-go on the PoC~~ — **done**; the beat-persistence PoC passed (eqpac, surface, 6 tracers).
2. ~~Method-fix (residual + rollout-aware)~~ — **DONE + CONFIRMED** (§0c): both bounds resolved, robust
   at n=6 surface + generalizes to depth. **Next live rung — the pipeline (§3):** the Earth-2
   coord/depth/DataSource adapters (native-grid loader) + a modest scale-up on Explorer if wanted.
3. **Production target confirmation:** native LLC270 full-res on B200 (assumed per "utilize B200").
4. **B200 data path:** how the 850 GB reaches AICR (your Duo transfer vs a shared mount).
5. **Jon greenlight** on observing-system design (gates the OSSE ensembles, not the infra).

## 7. Recommendation

The PoC de-risked the direction: the FNO *can* learn v05 next-state (§0b). The single
highest-value **next** step is the cheap Explorer method-fix (residual formulation + rollout-aware
loss) — it's what turns the marginal rollout + the unbeaten carbonate tracers into a production-grade
emulator, and it's Jon- and B200-independent. Scale the *proven* method on B200 (not the current
architecture) once Jon greenlights and the cert + 850 GB staging are in place.
