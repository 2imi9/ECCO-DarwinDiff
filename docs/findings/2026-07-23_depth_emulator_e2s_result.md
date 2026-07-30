# Depth-resolved (3D) BGC emulator + Earth2Studio adapter — built & result (2026-07-23)

> **⚠️ PARTIALLY SUPERSEDED (2026-07-23).** The per-depth 'beats persistence' rows below
> stand as measured, but persistence is a weak baseline on an autocorrelated monthly
> ocean. Against a per-cell **seasonal AR(1)** baseline the same model scores
> **−0.161 ± 0.015** across four seeds, CI entirely below zero. Read these numbers as
> 'clears a weak baseline', not as skill. See `2026-07-23_emulator_baselines_v2.md`.

**Bottom line: the depth-resolved ocean-BGC emulator is BUILT and the Earth2Studio wrapper is
built + verified against the real earth2studio source. Architecturally the depth-as-channel
approach works (trains fine, skill flat across depth). But the honest per-tracer skill is MIXED:
PIC and POC beat *persistence* at every depth (+0.35 to +0.51), but persistence is a weak baseline:
against a free per-cell seasonal AR(1) that edge vanishes
([`2026-07-23_emulator_baselines_v2.md`](2026-07-23_emulator_baselines_v2.md)). The slowly-varying
dissolved tracers (DIC, ALK, FeT) do NOT (persistence is near-unbeatable for them, exactly like the
surface gyres). The aggregate +0.21 "MAKE" is real *against persistence* but carried by PIC/POC — do
not report it alone.**

Two deliverables from the "3D emulator, Earth2Studio-adaptable" build (design:
`docs/research_notes/2026-07-23_3d_emulator_earth2studio_design.md`).

## 1. Earth2Studio wrapper — `src/darwindiff/e2s/` (built, verified, hardened)

The first ocean-BGC `PrognosticModel` for the Earth-2 / PhysicsNeMo stack (verified whitespace):
- `prognostic.py` — `DarwinBGCPrognostic`: canonical coord order `(batch, time, lead_time, variable,
  lat, lon)`, `timedelta64` lead-time that accumulates, unbounded iterator yielding the IC as step 0,
  nonnegativity + land-mask guards, log-Chl round-trip, residual mode, `@torch.inference_mode()` forward.
  Depth is folded into the `variable` name (`DIC_k0`…`FeT_k4`), matching E2S's `z500` convention.
- `datasource.py` — `EccoDarwinV05`: serves a dumped cube as E2S-shaped `xr.DataArray`s.
- `tests/test_e2s.py` — **7/7 contract tests pass** (import-guarded fallback, so it runs off-cluster/CI).

**Adversarial verification vs the real NVIDIA/earth2studio source** (workflow, read the actual `batch.py`
+ `models/px/base.py` + SFNO reference): **substantially conformant.** Import paths correct
(`utils.type.CoordSystem`, `utils.coords.handshake_*`, `models.batch.batch_*`), coord order + timedelta64
accumulation + iterator IC-first semantics + batch-decorator composition all verified. One genuine defect
found (missing `output_coords(None)` introspection branch) + one nit (`_forward` inference_mode) — **both
fixed and re-tested.** One cluster-only verify item remains: confirm `earth2studio.data.utils.prep_data_inputs`
resolves on the installed build (import-guarded, so worst case is a silent shim, not a crash).

## 2. Depth-resolved emulator — Stage 1 result (B200 job 184411)

5 tracers × 5 depth levels, global 1°, cube `[48, 25, 171, 360]`, channel names `{tracer}_k{level}`
(the exact naming the wrapper consumes). Trained via `--load-cube` (250 epochs, rollout-k4 +
mass-conserve + positivity guards). `verify_run`-style dump-fields.

**Aggregate:** verdict MAKE, skill vs persistence **+0.21**, beats=True. **But per-tracer × depth:**

| tracer | k0 (surf) | k1 | k2 | k3 | k4 (deep) | reading |
|---|---|---|---|---|---|---|
| **PIC** | +0.37 | +0.40 | +0.40 | +0.39 | +0.35 | **beats persistence at every depth** |
| **POC** | +0.50 | +0.51 | +0.51 | +0.50 | +0.45 | **beats persistence at every depth** |
| DIC | −2.04 | −1.58 | −2.27 | −3.48 | −4.90 | worse than persistence (near-conserved) |
| ALK | −3.39 | −2.97 | −4.05 | −5.20 | −7.77 | worse than persistence (near-conserved) |
| FeT | −2.27 | −2.35 | −2.48 | −2.83 | −3.51 | worse than persistence |

**10/25 channels beat persistence.** Two honest reads:
1. **Depth-as-channel is validated architecturally.** The emulator trains, is stable, and skill is *flat
   across depth* for the predictable tracers (PIC/POC hold +0.35–0.51 from surface to k4) — no depth
   degradation, no collapse. The design's choice (FNO2d-over-stacked-levels, not FNO3d) is vindicated.
2. **The mixed per-tracer skill is the real science, not a bug.** DIC/ALK are the near-conserved carbonate
   system: next month ≈ this month, so persistence is near-unbeatable and the emulator adds noise → negative
   skill. This is the *same* phenomenon as the persistence-dominated subtropical gyres in the surface globe.
   FeT (iron) is patchy/dynamic and also hard. **The aggregate +0.21 is carried by PIC/POC and must not be
   reported alone** — the per-tracer breakdown is the honest headline.

## Milestone + honest caveats

- **Milestone:** a global, multi-tracer, depth-resolved ocean-BGC operator that trains and is wrapped as the
  first ocean-BGC `PrognosticModel` in the Earth-2 stack. Genuinely first-of-kind (Samudra/SamudrACE/OceanNet
  all stop at T/S/U/V/SSH; the only depth-resolved BGC-ML art is two 1-D single-column emulators).
- **Chl deferred:** the design assumed a `--log-transform` flag in `emulator_poc.py` that does not exist
  (the surface globe's log was only in the plotter). Chl in linear z-score gives poor skill, so it was
  dropped from this run. Wiring log-space z-scoring into `emulator_poc.py` is the prerequisite to add Chl.
- **Next:** (a) log-Chl support; (b) the dissolved-tracer problem — DIC/ALK need either a tendency/anomaly
  target or a longer horizon where the carbonate system actually evolves (persistence wins at 1 month, but a
  correct operator should win at multi-month — the surface finding that the ceiling is structural applies);
  (c) Stage 4 global SFNO to kill polar artifacts.

Artifacts: `src/darwindiff/e2s/`, `tests/test_e2s.py`, `/scratch/qi_zim_neu/depth/` (B200).
