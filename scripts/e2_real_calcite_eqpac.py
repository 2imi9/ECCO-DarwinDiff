"""The REAL-DATA E2 gate: held-out calcite (log PIC:POC) recovery through prescribed
ECCO-Darwin transport, eqpac. This is Track-2's make-or-break number.

Mirrors ``scripts/e2_synthetic_twin_h200.py`` but swaps the synthetic self-twin for
**real, out-of-class** obs and forcing:
  - target/masks/env  <- darwindiff.held_out_obs.held_out_calcite_obs (Daniels CP:PP,
                          env-regime hold-out on upper-quartile Omega_calcite, anomaly-R2)
  - dust forcing       <- DB-1 iron_forcing_loader (real Mahowald soluble-iron field)
  - velocity           <- DB-2 velocity_loader (real v05 uVel_C/vVel_C, div-free barotropic)
  - initial condition  <- the AOI's real Darwin tracer climatology (spin-up seed)

**What a pass would mean (and its limits).** PASS = the learned closure beats the
null (frozen ``g==1``) closure on **held-out** cells at physical ``kh``, i.e.
learned-minus-null anomaly-R2 > 0, AND that gap is **largest at physical K_num and
shrinks as K_num grows** (the load-bearing control: on REAL out-of-class data the
closure canNOT re-absorb transport smoothing, unlike the self-twin where the K_num
ablation was flat and non-discriminating). A positive dependence of R2 on ``kh`` would
mean the "pass" is numerical, not biological.

**Honesty (do not overstate — the last verification pass flagged motivating->confirming
overreach).** This does not "make Darwin differentiable" or "confirm the thesis". Daniels
is a LOW-POWERED anchor (eqpac geomean 0.039 ~= Darwin 0.042, ~1.6x global) — a pass
CORROBORATES a regionally-variable, environment-conditioned rain ratio; it does not
sharply validate a specific R_PICPOC. Calcite is environment-DOMINATED (Omega, SST) with
composition a minor modulation.

**Protocol decisions (the harness is already parameterized for them — this run does not
invent them). #2 and #3 are settled FROM OUR SIDE — no Jon question needed:**
  #2  log-space scoring of PIC:POC — our modeling choice for the log-normal rain ratio;
      BAKED IN (the log observable). Settled.
  #3  steady-state sinking identity W_SINK_PIC == W_SINK (+ cocco off) so the box's
      standing-stock PIC:POC == the PRODUCTION ratio Daniels measures. VERIFIED in our
      config: carroll6 uses a SINGLE ``W_SINK`` for both POC and PIC (carroll6.py:285-286,
      transport.bgc_tendency_field likewise) and the 5-tracer box has NO cocco PFT, so the
      sinking cancels (PIC/POC = R_PICPOC*g) and NO target correction is needed. (This is a
      property of our box, and Daniels is *observations* — not a Darwin-v05 config question.)
  #1  small n_val (~6 eqpac upper-quartile) — tune q / pool eqpac+natl (still our choice).
  #4  pre-register the split (Omega primary, SST robustness, q fixed) before the run.
  #5  report K_num as the load-bearing control + permuted-predictor / profile-curvature
      cross-checks at the claimed-pass kh.

**Where this runs: LOCALLY.** The inputs come from the native LLC270 tree on ``D:`` (DB-1
iron + DB-2 velocity, read via partial ``np.fromfile``), and the training itself is tiny
(a 21x51x6 grid — the synthetic twin did fwd+bwd in ~1 s on H200, ~16 s on CPU). So there
is no reason to ship the ~TB native tree to a cluster; run it on the box (CPU or the local
GPU when free). Only if the small AOI inputs were pre-bundled would a cluster run make
sense — not needed at this scale.

Run (real, local):    python scripts/e2_real_calcite_eqpac.py
Plumbing check (CPU): python scripts/e2_real_calcite_eqpac.py --smoke
The ``--smoke`` mode uses a tiny climatology (max_iters) + few epochs to verify the
harness wires end-to-end; its number is NOT the E2 result.
"""
from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import numpy as np
import torch

from darwindiff.carroll6 import CARROLL_VALUES
from darwindiff.closures import EnvCalciteClosure
from darwindiff.ecco_darwin_loader import (
    EQUATORIAL_PACIFIC_AOI,
    NORTH_ATLANTIC_SUBPOLAR_AOI,
)
from darwindiff.held_out_obs import (
    CACHE_FILENAMES,
    SurfaceGatedClosure,
    anomaly_masked_r2,
    held_out_calcite_obs,
)

AOI_BY_KEY = {"eqpac": EQUATORIAL_PACIFIC_AOI, "natl": NORTH_ATLANTIC_SUBPOLAR_AOI}
from darwindiff.iron_forcing_loader import (
    IRONFILE_NAME,
    coverage_mask,
    iron_flux_aoi_grid,
    phi_dust_surface_field,
)
from darwindiff.safe_load import safe_torch_load
from darwindiff.trainer import TransportConfig, rollout_field, train_ude_closure
from darwindiff.velocity_loader import (
    depth_mean,
    divfree_barotropic_velocity,
    velocity_aoi_grid,
)

# 1-deg cell ~ 111 km at the equator; a constant metric spacing is fine for Phase-1
# (a latitude-varying dx is a later refinement, negligible over the eqpac band).
DX = DY = 1.11e5


def _device_dtype(force_cpu: bool):
    if not force_cpu and torch.cuda.is_available():
        return torch.device("cuda"), torch.float32
    return torch.device("cpu"), torch.float64


def _paths() -> dict:
    root = Path(os.environ.get("DARWIN_DATA_ROOT", r"D:\ecco_darwin_v5"))
    return {
        "root": root,
        "monthly": root / "output" / "monthly",
        "grid": root / "grid",
        "iron": root / "input" / IRONFILE_NAME,
        "cache": root / "cache",
    }


def _build_ic(cache_path: Path, n_z: int, dtype, device) -> torch.Tensor:
    """Spin-up seed IC ``[Y, X, Z, 5]`` = [DFe, Ps, Pl, POC, PIC] from the AOI's real
    Darwin tracer climatology (well-mixed over depth). Non-finite/land -> small positive
    so the rollout is finite; the steady-state target washes out IC detail."""
    c = safe_torch_load(cache_path)

    def _f(key, fallback):
        a = torch.as_tensor(np.asarray(c[key], dtype=np.float64), dtype=dtype, device=device)
        a = torch.nan_to_num(a, nan=fallback, posinf=fallback, neginf=fallback)
        return a.clamp_min(1e-6)

    dfe = _f("fet_binned", 1e-4)
    poc = _f("poc_binned", 0.1)
    pic = _f("pic_binned", 1e-3)
    ny, nx = dfe.shape
    small = torch.full((ny, nx), 0.1, dtype=dtype, device=device)
    surf = torch.stack([dfe, small, small, poc, pic], dim=-1)     # [Y, X, 5]
    return surf.unsqueeze(-2).expand(ny, nx, n_z, 5).contiguous()  # well-mixed over Z


def _score(obs, field) -> float:
    with torch.no_grad():
        return float(anomaly_masked_r2(obs.observable(field), obs.target, obs.val_mask, obs.basin_mean))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--smoke", action="store_true", help="tiny plumbing check (NOT the E2 number)")
    ap.add_argument("--cpu", action="store_true", help="force CPU/fp64")
    ap.add_argument("--n-z", type=int, default=6)
    ap.add_argument("--epochs", type=int, default=200)
    ap.add_argument("--n-steps", type=int, default=120)
    ap.add_argument("--kh", type=float, default=50.0, help="physical horizontal diffusivity")
    ap.add_argument("--kz", type=float, default=50.0)
    ap.add_argument("--q", type=float, default=0.25, help="env-regime hold-out fraction")
    ap.add_argument("--aoi", choices=sorted(AOI_BY_KEY), default="eqpac")
    ap.add_argument("--calcite-source", choices=("daniels", "marsh"), default="daniels",
                    help="calcite target compilation: daniels (2018) or marsh (2025, +400 pts)")
    ap.add_argument("--split-channel", default="omega_c", help="env-regime split axis (omega_c/sst/...)")
    ap.add_argument("--hidden", type=int, default=16, help="closure MLP width (lower = less overfit capacity)")
    ap.add_argument("--weight-decay", type=float, default=0.0, help="L2 on the closure MLP (anti-overfit)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-iters", type=int, default=None, help="cap velocity climatology months")
    ap.add_argument("--no-surface-gate", action="store_true",
                    help="diagnostic control: let the closure act at ALL depths (measures the "
                         "subsurface-through-transport contamination the gate removes)")
    args = ap.parse_args()
    aoi = AOI_BY_KEY[args.aoi]
    if args.smoke:
        args.epochs = min(args.epochs, 3)
        args.n_steps = min(args.n_steps, 8)
        if args.max_iters is None:
            args.max_iters = 2

    device, dtype = _device_dtype(args.cpu)
    p = _paths()
    n_z = args.n_z
    dz = 10.0
    print(f"[e2-real] device={device} dtype={dtype} torch={torch.__version__}"
          f"{' SMOKE (plumbing, not the E2 number)' if args.smoke else ''}")
    print(f"[e2-real] config: aoi={args.aoi} calcite={args.calcite_source} "
          f"split={args.split_channel} q={args.q} hidden={args.hidden} wd={args.weight_decay} "
          f"epochs={args.epochs} n_steps={args.n_steps} seed={args.seed}")
    if device.type == "cuda":
        print(f"[e2-real] gpu={torch.cuda.get_device_name(0)}")

    # --- DB-2 velocity: real v05 uVel_C/vVel_C -> div-free barotropic (u, v, w) ---
    vel = velocity_aoi_grid(p["monthly"], p["grid"], aoi, n_z=n_z, max_iters=args.max_iters)
    u2d, v2d = depth_mean(vel["u"]), depth_mean(vel["v"])
    u, v, w = divfree_barotropic_velocity(u2d, v2d, DX, DY, dz, n_z, dtype=dtype, device=device)
    # NOTE: sign-correctness of uVel_C (eastward, do-not-negate) is owned by the DB-2
    # loader's CI test; the area-mean below is just a magnitude sanity print (and is not
    # the SEC sign check when --max-iters caps the climatology).
    print(f"[e2-real] DB-2 velocity: surface u area-mean={float(np.nanmean(vel['u'][...,0])):+.1f} "
          f"m/day; |u|max={float(u.abs().max()):.1f} m/day (Courant~{float(u.abs().max())*0.25/DX:.3f})")

    # --- DB-1 forcing: real Mahowald soluble-iron surface dust + coverage mask ---
    areal = iron_flux_aoi_grid(p["iron"], p["grid"], aoi)
    cov = torch.as_tensor(coverage_mask(areal), dtype=torch.bool, device=device)
    dust = phi_dust_surface_field(areal, dz, n_z, dtype=dtype, device=device)
    print(f"[e2-real] DB-1 dust: mean areal={float(np.nanmean(areal)):.2e} mmol/m2/s, "
          f"coverage {int(cov.sum())}/{cov.numel()} bins")

    # --- DB-3 held-out obs: real calcite, env-regime hold-out, DB-1 coverage AND-ed ---
    cal_points = None
    if args.calcite_source == "marsh":
        from darwindiff.marsh_loader import load_marsh_points
        cal_points = load_marsh_points()
    obs = held_out_calcite_obs(aoi, n_z=n_z, q=args.q, split_channel=args.split_channel,
                               points=cal_points, forcing_coverage=cov, dtype=dtype, device=device)
    print(f"[e2-real] DB-3 obs: coverage {int(obs.coverage_mask.sum())} cells, "
          f"train={obs.n_train} val={obs.n_val} ({args.split_channel} band-edge={obs.band_edge:.2f}); "
          f"basin log-ratio={obs.basin_mean:.3f} (ratio {float(np.exp(obs.basin_mean)):.4f})")
    if obs.n_val < 5:
        print("[e2-real] WARNING: n_val < 5 -> under-powered split (decision #1: raise q or pool eqpac+natl)")

    ic = _build_ic(p["cache"] / CACHE_FILENAMES[aoi.name], n_z, dtype, device)
    params = torch.tensor([CARROLL_VALUES[i] for i in range(6)], device=device, dtype=dtype)
    env = obs.env.to(device=device, dtype=dtype)

    gate = (lambda c: c) if args.no_surface_gate else (lambda c: SurfaceGatedClosure(c))
    print(f"[e2-real] closure depth-gating: {'OFF (diagnostic control)' if args.no_surface_gate else 'ON (surface-only; clean attribution)'}")

    def run_at_kh(kh: float) -> tuple[float, float, float]:
        tc = TransportConfig(dx=DX, dy=DY, dz=dz, dt=0.25, kz=args.kz, kh=kh,
                             u=u, v=v, w=w, dust=dust)
        null = gate(EnvCalciteClosure(env, A=1.0, hidden=args.hidden).to(device=device, dtype=dtype))
        r2_null = _score(obs, rollout_field(ic, params, tc, args.n_steps, calcite_closure=null))
        clo = gate(EnvCalciteClosure(env, A=1.0, hidden=args.hidden).to(device=device, dtype=dtype))
        res = train_ude_closure(
            clo, ic, params, tc, args.n_steps, observable=obs.observable, target=obs.target,
            train_mask=obs.train_mask, val_mask=obs.val_mask, hook=obs.hook,
            epochs=args.epochs, lr=5e-2, weight_decay=args.weight_decay,
            checkpoint_segment=min(15, args.n_steps), log_every=args.epochs,
        )
        if any(h.get("aborted") for h in res.history):
            print(f"[e2-real] kh={kh:.0f}: training ABORTED (non-finite guard) -- see history")
        r2_learned = _score(obs, res.final_field)
        return r2_learned, r2_null, r2_learned - r2_null

    torch.manual_seed(args.seed)
    t0 = time.perf_counter()

    print("\n[e2-real] E2 GATE (held-out anomaly-R2, learned vs null, physical kh):")
    r2_l, r2_n, delta = run_at_kh(args.kh)
    print(f"  learned={r2_l:+.3f}  null={r2_n:+.3f}  DELTA(learned-null)={delta:+.3f}")

    print("\n[e2-real] K_num control (LOAD-BEARING on real out-of-class data --")
    print("          delta should be LARGEST at physical kh and SHRINK as kh grows;")
    print("          a positive R2-vs-kh dependence means the pass is numerical):")
    ladder = [(args.kh, delta)]
    for kh in (4 * args.kh, 16 * args.kh):
        ladder.append((kh, run_at_kh(kh)[2]))
    for kh, d in ladder:
        print(f"  kh={kh:8.0f}  delta={d:+.3f}")
    shrinks = ladder[0][1] >= ladder[-1][1]

    wall = time.perf_counter() - t0
    print(f"\n[e2-real] {wall:.1f}s. delta@physical={delta:+.3f}  K_num-shrinks={shrinks}")
    if args.smoke:
        print("[e2-real] SMOKE: plumbing OK -- this number is NOT the E2 result. "
              "Run the full config locally (no --smoke); #2/#3 are settled (see docstring).")
    else:
        verdict = "PASS (corroborates env-conditioned rain ratio)" if (delta > 0 and shrinks) \
            else "NOT A PASS"
        print(f"[e2-real] E2 VERDICT: {verdict}. Reminder: Daniels is low-powered; this "
              f"corroborates, it does not sharply validate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
