#!/usr/bin/env python3
"""FIELD-version mass/carbon-budget check with REAL v05 advection (#7 / G11).

**The gap EXP-B left open.** ``scripts/ude_transport_stress_h200.py`` EXP-B
(``docs/findings/2026-07-21_ude_stress_result.md``) proved the transport conserves
mass to ~5e-6 out to 100,000 steps -- but that check used a *synthetic* batched-column
setup: ``column_tendency(..., w=1.0, bgc=False)`` on 2000 independent random columns,
a **scalar constant vertical velocity**, and **no horizontal advection at all**. It
never exercised the actual thing #7 is about: the real ECCO-Darwin v05 velocity field
(DB-2, ``velocity_loader``) advecting tracers **horizontally** across a real AOI grid,
where :func:`darwindiff.transport.horizontal_advection`'s centered-2nd scheme is
*dispersively unstable without adequate* ``kh`` (its own docstring), at real current
strengths the synthetic ``w=1.0`` sweep never touched.

**This script.** Rolls the real eqpac AOI grid forward via
:func:`darwindiff.transport.grid_tendency` + :func:`darwindiff.transport.imex_rollout`
with:
  - DB-2 real barotropic velocity (``velocity_loader.velocity_aoi_grid`` ->
    ``depth_mean`` -> ``velocity_loader.divfree_barotropic_velocity``, which calls
    ``transport.w_from_continuity`` so the 3-D flux is discretely divergence-free);
  - DB-1 real Mahowald dust forcing (``iron_forcing_loader.phi_dust_surface_field``);
  - the 7-tracer state ``[DFe, Ps, Pl, POC, PIC, DIC, ALK]`` so the A3 calcite/organic
    carbon stoichiometry (``bgc_tendency_field``) applies;
  - a real IC seeded from the AOI's own Darwin tracer climatology cache (the same
    ``eqpac_targets_equatorial_pacific.pt`` the flagship recovery driver uses).

**The budget-closure check** mirrors ``tests/test_transport.py::
test_carbon_budget_closes_over_rollout`` (co-integrate cumulative particulate export
alongside the state; ``carbon_total(state) + cumulative_export`` is conserved to
machine precision when only BGC sources/sinks act) -- extended from a single closed
cell to the full open FIELD: horizontal advection + vertical
advection/diffusion + real dust forcing are all flux-form / surface-only, so they
redistribute carbon but never create/destroy it, and dust/scavenging only touch DFe
(excluded from ``carbon_total``), so the carbon invariant is untouched by the open
iron forcing -- the only carbon exit is particulate export (``W_SINK*(POC+PIC)``),
which this script integrates explicitly. **This is a REAL, non-vacuous stress test**
because the invariant only holds if the discretization stays numerically well-behaved
at real current strength across the whole horizontal+vertical operator stack -- unlike
EXP-B's single-column vertical-only check.

**Pre-registered pass/fail** (see the module docstring in
``docs/research_notes/`` companion note / STATUS.md #7 entry):
  PASS  = at the DECADAL horizon (10 y, dt=0.25 d -> 14,600 steps), for BOTH rk4 and
          euler at the LARGEST ``--kh-list`` value: (a) the field stays finite at
          every checkpoint; (b) the domain-integrated carbon budget
          ``|closedN - closed0| / |closed0|`` < 1e-4; AND (c) the kh=0 control
          (diffusion removed, the known destabilizer for centered advection) shows
          a MATERIALLY WORSE outcome (non-finite, or >=100x larger drift) --
          confirming the pass is not vacuous (real currents at this AOI/resolution/
          dt actually exercise the horizontal operator, they don't just idle).
  FAIL  = non-finite state or drift >= 1e-4 at the largest kh by the decadal
          horizon, OR kh=0 behaves indistinguishably from it (the check would be
          uninformative and needs a stronger AOI/current or finer dt, not a clean
          "transport conserves" claim).

**RESULT (local, 2026-07-21 -- already run; this is not a hypothetical design).**
Bisecting the onset with the ``--years 0.1 0.25 0.5`` rungs found the field goes
NON-FINITE between 146 and 365 steps (0.1-0.25 y) at every ``kh`` up to and
including **1e6** -- this range INCLUDES kh=50, the "physical" default
``e2_real_calcite_eqpac.py`` / ``iron_scav_rat_profile.py`` currently pass to
``TransportConfig``/``divfree_barotropic_velocity``. So EXP-B's clean pass does
**not** trivially extend to the field: real horizontal advection breaks it almost
immediately at the kh value the rest of the E2 infra assumes is adequate (that
infra's own rollouts are short, n_steps~120 = 30 d, which sits BELOW the observed
onset -- they have not yet been long enough to hit this wall).
Bisecting upward, **kh=1e9** (native day-based units, matching this AOI's real
``|u|max`` against the ``horizontal_advection`` docstring's own stability
heuristic ``kh >~ 0.5|u|dx``) stabilizes the rollout: finite, and the carbon
budget conserves to **6e-14 (1 y) / 3e-13 (5 y) / 6e-13 (10 y)** relative drift,
for BOTH rk4 and euler, at the full decadal horizon. **So #7 CLOSES for the field
version -- but only once kh is raised ~7 orders of magnitude above the value the
rest of the E2/Track-2 real-advection scripts currently default to.** That kh
mismatch is a live, separate, and higher-priority finding this script surfaced as
a side effect (see the "dependencies" note this run should be filed against);
whether it also explains any E2 calcite-gate irregularities is untested here.

Nothing here is a science "recovery number" -- it is a numeric/infra property, like
EXP-A-D, and is NOT gated by scripts/verify_run.py.

Run (local, reuses the on-disk native LLC270 tree + AOI cache -- no new data):
    python scripts/ude_field_conservation_real_advection.py --out-dir runs/g11_field_conservation
Quick plumbing check (few steps, capped velocity climatology):
    python scripts/ude_field_conservation_real_advection.py --out-dir runs/g11_smoke --smoke
Cluster (CPU-only -- forward rollout, no gradient, no GPU needed):
    sbatch scripts/slurm/run_g11_field_conservation.sbatch
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import torch

from darwindiff.carroll6 import CARROLL_VALUES, W_SINK
from darwindiff.ecco_darwin_loader import (
    AOI,
    EQUATORIAL_PACIFIC_AOI,
    NORTH_ATLANTIC_SUBPOLAR_AOI,
    SOUTHERN_OCEAN_PACIFIC_AOI,
)
from darwindiff.held_out_obs import CACHE_FILENAMES
from darwindiff.iron_forcing_loader import IRONFILE_NAME, iron_flux_aoi_grid, phi_dust_surface_field
from darwindiff.safe_load import safe_torch_load
from darwindiff.transport import (
    carbon_total,
    grid_tendency,
    imex_rollout,
    interior_mask,
)
from darwindiff.velocity_loader import depth_mean, divfree_barotropic_velocity, velocity_aoi_grid

AOI_BY_KEY: dict[str, AOI] = {
    "eqpac": EQUATORIAL_PACIFIC_AOI,
    "natl": NORTH_ATLANTIC_SUBPOLAR_AOI,
    "southernoceanpac": SOUTHERN_OCEAN_PACIFIC_AOI,
}

# 1-deg cell ~ 111 km at the equator -- same constant-metric approximation
# e2_real_calcite_eqpac.py and iron_scav_rat_profile.py already use.
DX = DY = 1.11e5
DZ = 10.0  # matches the existing E2/iron-scav-rat convention (native DRF not used)


def _paths() -> dict:
    root = Path(os.environ.get("DARWIN_DATA_ROOT", r"D:\ecco_darwin_v5"))
    return {
        "root": root,
        "monthly": root / "output" / "monthly",
        "grid": root / "grid",
        "iron": root / "input" / IRONFILE_NAME,
        "cache": root / "cache",
    }


def _build_ic_7tracer(cache_path: Path, n_z: int, dtype, device) -> torch.Tensor:
    """Real 7-tracer IC ``[Y, X, Z, 7]`` = [DFe, Ps, Pl, POC, PIC, DIC, ALK] from the
    AOI's own Darwin climatology cache -- the SAME cache the flagship recovery driver
    (``run_v3.0_joint_multi_aoi.py``) builds and reads. Well-mixed over depth (matches
    ``e2_real_calcite_eqpac._build_ic``); non-finite/land -> a small/typical positive
    fallback so the rollout is finite from step 0."""
    c = safe_torch_load(cache_path)

    def _f(key, fallback):
        a = torch.as_tensor(np.asarray(c[key], dtype=np.float64), dtype=dtype, device=device)
        a = torch.nan_to_num(a, nan=fallback, posinf=fallback, neginf=fallback)
        return a.clamp_min(1e-6)

    dfe = _f("fet_binned", 1e-4)
    poc = _f("poc_binned", 0.1)
    pic = _f("pic_binned", 1e-3)
    dic = _f("dic_binned", 2000.0)
    alk = _f("alk_binned", 2300.0)
    ny, nx = dfe.shape
    small = torch.full((ny, nx), 0.1, dtype=dtype, device=device)
    surf = torch.stack([dfe, small, small, poc, pic, dic, alk], dim=-1)  # [Y, X, 7]
    return surf.unsqueeze(-2).expand(ny, nx, n_z, 7).contiguous()


def _make_tend_aug(params, u, v, kh, dust):
    """Build the 8-channel EXPLICIT tendency (state + cumulative-export bookkeeping),
    vertical diffusion EXCLUDED (``imex_rollout`` applies it implicitly). Channel 7 is
    a running per-cell integral of the local particulate-export rate
    ``W_SINK*(POC+PIC)`` -- it exactly cancels the sink term already inside
    ``bgc_tendency_field``'s ``dPOC``/``dPIC``, so ``carbon_total(core) +
    export`` is algebraically conserved by BGC alone (the
    ``test_carbon_budget_closes_over_rollout`` invariant); transport (horizontal
    advection/diffusion + vertical advection/diffusion) only *redistributes* carbon
    among cells (flux-form, no-flux domain edges), so it cannot change the
    DOMAIN-INTEGRATED total even though it acts on all 8 channels here (the export
    channel getting incidentally mixed/advected is harmless bookkeeping -- only the
    domain sum is checked, never a per-cell value).
    """
    from darwindiff.transport import bgc_tendency_field

    wsink = float(W_SINK)

    def tend(t: float, x_aug: torch.Tensor) -> torch.Tensor:
        core = x_aug[..., :7]
        d_transport = grid_tendency(
            core, params, u=u, v=v, dx=DX, dy=DY, kz=0.0, dz=DZ, w=0.0, kh=kh,
            bgc=False, include_vdiff=False,
        )
        d_bgc = bgc_tendency_field(core, params, dust=dust)
        d_export = (wsink * (core[..., 3] + core[..., 4])).unsqueeze(-1)
        return torch.cat([d_transport + d_bgc, d_export], dim=-1)

    return tend


def run_config(ic7, params, u, v, kz, kh, dust, method: str, n_steps: int, dt: float,
                device) -> dict:
    export0 = torch.zeros(*ic7.shape[:-1], 1, dtype=ic7.dtype, device=device)
    x0 = torch.cat([ic7, export0], dim=-1)  # [Y, X, Z, 8]
    tend = _make_tend_aug(params, u, v, kh, dust)

    t0 = time.perf_counter()
    with torch.no_grad():
        xN = imex_rollout(tend, x0, dt=dt, n_steps=n_steps, kz=kz, dz=DZ, method=method)
    wall = time.perf_counter() - t0

    finite = bool(torch.isfinite(xN).all())
    closed0 = float(carbon_total(x0[..., :7]).sum() + x0[..., 7].sum())
    if finite:
        closedN = float(carbon_total(xN[..., :7]).sum() + xN[..., 7].sum())
        drift = abs(closedN - closed0) / max(abs(closed0), 1e-30)
    else:
        closedN, drift = float("nan"), float("inf")

    # per-column (Y,X) budget, interior (A6, ring=1) vs full-domain (incl. the
    # closed-wall boundary ring, where a fake accumulation/depletion is EXPECTED --
    # see transport.interior_mask docstring).
    if finite:
        col0 = carbon_total(x0[..., :7]).sum(-1) + x0[..., 7].sum(-1)   # [Y, X]
        colN = carbon_total(xN[..., :7]).sum(-1) + xN[..., 7].sum(-1)
        rel = (colN - col0).abs() / col0.abs().clamp_min(1e-30)
        ny, nx = col0.shape
        m_int = interior_mask(ny, nx, ring=1, device=col0.device)
        max_interior = float(rel[m_int].max())
        max_full = float(rel.max())
    else:
        max_interior = max_full = float("inf")

    return {
        "method": method, "n_steps": n_steps, "years": n_steps * dt / 365.0,
        "kh": kh, "wall_s": round(wall, 3), "final_finite": finite,
        "global_carbon_drift": drift,
        "max_interior_percell_drift": max_interior,
        "max_full_percell_drift": max_full,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--aoi", choices=sorted(AOI_BY_KEY), default="eqpac")
    ap.add_argument("--n-z", type=int, default=6)
    ap.add_argument("--dt", type=float, default=0.25, help="days")
    ap.add_argument("--kz", type=float, default=50.0, help="physical vertical diffusivity")
    ap.add_argument("--kh-list", type=float, nargs="+", default=[0.0, 50.0, 1.0e9],
                    help="horizontal diffusivities to sweep, in the framework's native "
                         "day-based units (m^2/day, since dt is in days and u/v in m/day -- "
                         "NOT m^2/s). 0.0 = no-diffusion stress control; 50.0 = the value "
                         "e2_real_calcite_eqpac.py / iron_scav_rat_profile.py currently pass "
                         "as their '--kh physical' default (empirically this ALSO blows up "
                         "against real eqpac barotropic advection -- see the module "
                         "docstring); 1.0e9 is the empirically-stabilizing value found by "
                         "bisection here (matches the horizontal_advection docstring's own "
                         "``kh >~ 0.5|u|dx`` stability heuristic at this AOI's real |u|max)")
    ap.add_argument("--years", type=float, nargs="+",
                    default=[0.1, 0.25, 0.5, 1.0, 5.0, 10.0, 20.0],
                    help="rollout horizons in years (10.0 = the decadal #7 target; the short "
                         "0.1/0.25/0.5 rungs exist to LOCATE the blow-up onset cheaply -- it "
                         "was found empirically between 146 and 365 steps, i.e. 0.1-0.25 y, "
                         "at kh<=1e6, so do not drop these rungs when re-diagnosing)")
    ap.add_argument("--methods", nargs="+", default=["rk4", "euler"], choices=["rk4", "euler"])
    ap.add_argument("--max-iters", type=int, default=None, help="cap velocity climatology months")
    ap.add_argument("--cpu", action="store_true", default=True, help="CPU/fp64 (default; no grad needed)")
    ap.add_argument("--cuda", action="store_true", help="use CUDA/fp32 instead of the CPU/fp64 default")
    ap.add_argument("--smoke", action="store_true", help="tiny plumbing check (NOT the #7 result)")
    args = ap.parse_args()

    if args.smoke:
        args.years = [0.05]
        args.kh_list = [0.0, 50.0]
        args.methods = ["rk4"]
        if args.max_iters is None:
            args.max_iters = 2

    device = torch.device("cuda" if (args.cuda and torch.cuda.is_available()) else "cpu")
    dtype = torch.float32 if device.type == "cuda" else torch.float64
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    aoi = AOI_BY_KEY[args.aoi]
    p = _paths()
    n_z = args.n_z
    print(f"[g11] device={device} dtype={dtype} aoi={args.aoi} n_z={n_z} dt={args.dt}"
          f"{' SMOKE' if args.smoke else ''}")

    vel = velocity_aoi_grid(p["monthly"], p["grid"], aoi, n_z=n_z, max_iters=args.max_iters)
    u2d, v2d = depth_mean(vel["u"]), depth_mean(vel["v"])
    u, v, _w = divfree_barotropic_velocity(u2d, v2d, DX, DY, DZ, n_z, dtype=dtype, device=device)
    courant = float(u.abs().max()) * args.dt / DX
    print(f"[g11] DB-2 real velocity: |u|max={float(u.abs().max()):.1f} m/day "
          f"|v|max={float(v.abs().max()):.1f} m/day  Courant(u)~{courant:.4f}")

    areal = iron_flux_aoi_grid(p["iron"], p["grid"], aoi)
    dust = phi_dust_surface_field(areal, DZ, n_z, dtype=dtype, device=device)
    print(f"[g11] DB-1 real dust: mean areal={float(np.nanmean(areal)):.2e} mmol/m2/s")

    cache_path = p["cache"] / CACHE_FILENAMES[aoi.name]
    ic7 = _build_ic_7tracer(cache_path, n_z, dtype, device)
    params = torch.tensor([CARROLL_VALUES[i] for i in range(6)], device=device, dtype=dtype)

    results = []
    for kh in args.kh_list:
        for method in args.methods:
            for years in args.years:
                n_steps = max(1, round(years * 365.0 / args.dt))
                tag = f"kh{kh}_{method}_y{years}"
                done = out / f".done_{tag}"
                jpath = out / f"{tag}.json"
                if done.exists():
                    results.append(json.loads(jpath.read_text()))
                    continue
                rec = run_config(ic7, params, u, v, args.kz, kh, dust, method, n_steps,
                                 args.dt, device)
                rec["tag"] = tag
                jpath.write_text(json.dumps(rec, indent=1))
                done.touch()
                results.append(rec)
                print(f"[g11] {tag}: finite={rec['final_finite']} "
                      f"drift={rec['global_carbon_drift']:.3e} "
                      f"interior={rec['max_interior_percell_drift']:.3e} "
                      f"full={rec['max_full_percell_drift']:.3e} wall={rec['wall_s']}s")

    (out / "summary.json").write_text(json.dumps(results, indent=1))

    if not args.smoke:
        decadal = [r for r in results if abs(r["years"] - 10.0) < 1e-6]
        phys = [r for r in decadal if r["kh"] == max(args.kh_list)]
        zero = [r for r in decadal if r["kh"] == 0.0]
        pass_phys = all(r["final_finite"] and r["global_carbon_drift"] < 1e-4 for r in phys) if phys else False
        control_worse = False
        if phys and zero:
            control_worse = any(
                (not z["final_finite"]) or z["global_carbon_drift"] >= 100 * max(p["global_carbon_drift"], 1e-12)
                for p, z in zip(phys, zero)
            )
        verdict = "PASS (#7 CLOSES for the field version)" if (pass_phys and control_worse) \
            else ("PASS BUT UNINFORMATIVE (kh=0 control did not stress the check -- re-run at "
                  "stronger currents/AOI/dt before trusting the pass)" if pass_phys
                  else "FAIL (see per-config JSON for the failing horizon/method)")
        print(f"\n[g11] #7 VERDICT: {verdict}")

    print(f"[g11] wrote {out / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
