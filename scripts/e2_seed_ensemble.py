"""E2 seed-ensemble hardening: run the make-or-break real-data calcite E2
(``scripts/e2_real_calcite_eqpac.py``) across n>=10 random seeds, reusing that
script's EXACT machinery, to show the decisive negative is robust to closure init
(not a single lucky/unlucky seed).

This is a *seed* replication, not a power increase: n_val (~6, eqpac upper-quartile
Omega) is structurally fixed (the within-region Omega range is <=0.16 dex), so the
negative is hardened against random-init variance, not turned into a high-n rejection.

Faithfulness: every numeric primitive (velocity/dust/obs/IC loaders, EnvCalciteClosure,
SurfaceGatedClosure, TransportConfig, rollout_field, train_ude_closure, anomaly-R2
scoring) is imported from ``e2_real_calcite_eqpac.py`` and used verbatim. The only change
is that the ~100 GB velocity climatology + dust + obs + IC are loaded ONCE and reused
across seeds (the single-seed script re-loads them every invocation). Per-seed the RNG is
reset with ``torch.manual_seed(seed)`` exactly as the single-seed runner does, so
``--seeds 1`` reproduces the single-seed number bit-for-bit (regression-checkable).

Runs LOCALLY, CPU or GPU. The velocity dependency (uVel_C/vVel_C, ~103 GB) lives only on
the local native tree, so there is no cluster path without shipping it -- hence local.

Usage (regression check vs the known single-seed delta):
    python scripts/e2_seed_ensemble.py --cpu --seeds 1 --epochs 10 --hidden 16 --weight-decay 0.0
Usage (the hardening ensemble, regularized closure -- the clean diagnostic):
    python scripts/e2_seed_ensemble.py --cpu --seeds 10 --epochs 200 --hidden 4 --weight-decay 0.01 \
        --ladder-seeds 1 --out docs/findings/e2_seed_ensemble.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]

# Load the vetted single-seed runner as a module (its __main__ guard prevents main() running).
_spec = importlib.util.spec_from_file_location("_e2mod", ROOT / "scripts" / "e2_real_calcite_eqpac.py")
e2 = importlib.util.module_from_spec(_spec)
sys.modules["_e2mod"] = e2
_spec.loader.exec_module(e2)


def _resolve_device_dtype(args):
    """Device + dtype, with an explicit --dtype override (needed to build a float32
    CPU bundle that reproduces an H200 cuda/float32 run bit-for-bit)."""
    dt_map = {"float32": torch.float32, "float64": torch.float64}
    if not args.cpu and torch.cuda.is_available():
        return torch.device("cuda"), dt_map.get(args.dtype, torch.float32)
    return torch.device("cpu"), dt_map.get(args.dtype, torch.float64)


def _obs_to(obs, device, dtype):
    """Move the HeldOutObs tensor fields to device/dtype (NamedTuple is immutable)."""
    def _mv(t):
        return t.to(device=device, dtype=dtype) if t.is_floating_point() else t.to(device=device)
    return obs._replace(target=_mv(obs.target), train_mask=obs.train_mask.to(device),
                        val_mask=obs.val_mask.to(device), coverage_mask=obs.coverage_mask.to(device),
                        env=_mv(obs.env))


def _ctx_to(ctx, device, dtype):
    """Move a whole context (loaded from a portable CPU bundle) onto device/dtype."""
    out = dict(ctx)
    for k in ("u", "v", "w", "dust", "ic", "params", "env"):
        out[k] = ctx[k].to(device=device, dtype=dtype)
    out["obs"] = _obs_to(ctx["obs"], device, dtype)
    out["device"], out["dtype"] = device, dtype
    return out


def build_context(args) -> dict:
    """Load velocity / dust / held-out obs / IC ONCE (the expensive, seed-independent part)."""
    aoi = e2.AOI_BY_KEY[args.aoi]
    device, dtype = _resolve_device_dtype(args)
    p = e2._paths()
    n_z, dz = args.n_z, 10.0

    vel = e2.velocity_aoi_grid(p["monthly"], p["grid"], aoi, n_z=n_z, max_iters=args.max_iters)
    u2d, v2d = e2.depth_mean(vel["u"]), e2.depth_mean(vel["v"])
    u, v, w = e2.divfree_barotropic_velocity(u2d, v2d, e2.DX, e2.DY, dz, n_z, dtype=dtype, device=device)

    areal = e2.iron_flux_aoi_grid(p["iron"], p["grid"], aoi)
    cov = torch.as_tensor(e2.coverage_mask(areal), dtype=torch.bool, device=device)
    dust = e2.phi_dust_surface_field(areal, dz, n_z, dtype=dtype, device=device)

    cal_points = None
    if args.calcite_source == "marsh":
        from darwindiff.marsh_loader import load_marsh_points
        cal_points = load_marsh_points()
    obs = e2.held_out_calcite_obs(aoi, n_z=n_z, q=args.q, split_channel=args.split_channel,
                                  points=cal_points, forcing_coverage=cov, dtype=dtype, device=device)
    ic = e2._build_ic(p["cache"] / e2.CACHE_FILENAMES[aoi.name], n_z, dtype, device)
    params = torch.tensor([e2.CARROLL_VALUES[i] for i in range(6)], device=device, dtype=dtype)
    env = obs.env.to(device=device, dtype=dtype)

    print(f"[ens] device={device} dtype={dtype} aoi={args.aoi} calcite={args.calcite_source} "
          f"q={args.q} split={args.split_channel}")
    print(f"[ens] obs: coverage {int(obs.coverage_mask.sum())} cells train={obs.n_train} val={obs.n_val} "
          f"(band-edge={obs.band_edge:.2f}); basin log-ratio={obs.basin_mean:.3f}")
    if obs.n_val < 5:
        print("[ens] WARNING: n_val < 5 -> under-powered split")
    return dict(device=device, dtype=dtype, u=u, v=v, w=w, dust=dust, obs=obs, ic=ic,
                params=params, env=env, dz=dz)


def run_at_kh(ctx: dict, args, kh: float) -> tuple[float, float, float]:
    """Faithful copy of e2.main()'s inner run_at_kh, operating on the shared context."""
    obs = ctx["obs"]
    gate = (lambda c: c) if args.no_surface_gate else (lambda c: e2.SurfaceGatedClosure(c))
    tc = e2.TransportConfig(dx=e2.DX, dy=e2.DY, dz=ctx["dz"], dt=0.25, kz=args.kz, kh=kh,
                            u=ctx["u"], v=ctx["v"], w=ctx["w"], dust=ctx["dust"])
    null = gate(e2.EnvCalciteClosure(ctx["env"], A=1.0, hidden=args.hidden).to(
        device=ctx["device"], dtype=ctx["dtype"]))
    r2_null = e2._score(obs, e2.rollout_field(ctx["ic"], ctx["params"], tc, args.n_steps,
                                              calcite_closure=null))
    clo = gate(e2.EnvCalciteClosure(ctx["env"], A=1.0, hidden=args.hidden).to(
        device=ctx["device"], dtype=ctx["dtype"]))
    res = e2.train_ude_closure(
        clo, ctx["ic"], ctx["params"], tc, args.n_steps, observable=obs.observable, target=obs.target,
        train_mask=obs.train_mask, val_mask=obs.val_mask, hook=obs.hook,
        epochs=args.epochs, lr=5e-2, weight_decay=args.weight_decay,
        checkpoint_segment=min(15, args.n_steps), log_every=args.epochs,
    )
    aborted = any(h.get("aborted") for h in res.history)
    if aborted:
        print(f"[ens] kh={kh:.0f}: training ABORTED (non-finite guard)")
    r2_learned = e2._score(obs, res.final_field)
    return r2_learned, r2_null, r2_learned - r2_null


def run_seed(ctx: dict, args, seed: int, full_ladder: bool) -> dict:
    torch.manual_seed(seed)  # exactly as e2.main (governs null+closure init + training)
    t0 = time.perf_counter()
    r2_l, r2_n, delta = run_at_kh(ctx, args, args.kh)
    ladder = [(args.kh, delta)]
    if full_ladder:
        for kh in (4 * args.kh, 16 * args.kh):
            ladder.append((kh, run_at_kh(ctx, args, kh)[2]))
    shrinks = ladder[0][1] >= ladder[-1][1] if full_ladder else None
    wall = time.perf_counter() - t0
    is_pass = (delta > 0) and bool(shrinks) if full_ladder else None
    print(f"[ens] seed {seed}: learned={r2_l:+.3f} null={r2_n:+.3f} DELTA={delta:+.3f}"
          + (f"  ladder={[round(d,3) for _, d in ladder]} shrinks={shrinks} pass={is_pass}"
             if full_ladder else "") + f"  ({wall:.0f}s)")
    return {"seed": seed, "r2_learned": r2_l, "r2_null": r2_n, "delta": delta,
            "ladder": [[kh, d] for kh, d in ladder] if full_ladder else None,
            "knum_shrinks": shrinks, "is_pass": is_pass, "wall_s": wall}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=int, default=10, help="number of seeds in this shard")
    ap.add_argument("--seed-start", type=int, default=0, help="first seed index (shards: 0,2,4,...)")
    ap.add_argument("--ladder-for", type=str, default="0",
                    help="comma-separated seed indices that get the full K_num ladder (rest: physical-kh only)")
    ap.add_argument("--threads", type=int, default=0, help="torch CPU threads (0 = leave default)")
    ap.add_argument("--dtype", choices=("auto", "float32", "float64"), default="auto",
                    help="force compute dtype (auto: cuda->float32, cpu->float64)")
    ap.add_argument("--save-bundle", type=str, default=None,
                    help="build the AOI context, save a portable CPU bundle here, and exit "
                         "(ship this ~few-MB file to a cluster instead of the 103 GB velocity tree)")
    ap.add_argument("--load-bundle", type=str, default=None,
                    help="load the AOI context from a bundle instead of the raw D: tree")
    ap.add_argument("--cpu", action="store_true")
    ap.add_argument("--n-z", type=int, default=6)
    ap.add_argument("--epochs", type=int, default=200)
    ap.add_argument("--n-steps", type=int, default=120)
    ap.add_argument("--kh", type=float, default=50.0)
    ap.add_argument("--kz", type=float, default=50.0)
    ap.add_argument("--q", type=float, default=0.25)
    ap.add_argument("--aoi", choices=sorted(e2.AOI_BY_KEY), default="eqpac")
    ap.add_argument("--calcite-source", choices=("daniels", "marsh"), default="daniels")
    ap.add_argument("--split-channel", default="omega_c")
    ap.add_argument("--hidden", type=int, default=4)
    ap.add_argument("--weight-decay", type=float, default=0.01)
    ap.add_argument("--max-iters", type=int, default=None)
    ap.add_argument("--no-surface-gate", action="store_true")
    ap.add_argument("--out", type=str, default=None, help="write machine-readable JSON here")
    args = ap.parse_args()
    if args.threads:
        torch.set_num_threads(args.threads)
    ladder_set = {int(s) for s in args.ladder_for.split(",") if s.strip() != ""}
    seed_lo, seed_hi = args.seed_start, args.seed_start + args.seeds

    device, dtype = _resolve_device_dtype(args)

    if args.save_bundle:
        # Build on CPU (float32 by default so it reproduces an H200 cuda/float32 run) and
        # serialize a portable, device-agnostic bundle.
        cpu_args = argparse.Namespace(**{**vars(args), "cpu": True})
        ctx = build_context(cpu_args)
        Path(args.save_bundle).parent.mkdir(parents=True, exist_ok=True)
        torch.save(ctx, args.save_bundle)
        mb = Path(args.save_bundle).stat().st_size / 1e6
        print(f"[ens] saved portable bundle -> {args.save_bundle} ({mb:.1f} MB, dtype={ctx['dtype']}). "
              f"scp it to the cluster and run with --load-bundle.")
        return 0

    print(f"[ens] E2 SEED ENSEMBLE  seeds={seed_lo}..{seed_hi - 1}  ladder_for={sorted(ladder_set)}  "
          f"config: hidden={args.hidden} wd={args.weight_decay} epochs={args.epochs} "
          f"n_steps={args.n_steps} kh={args.kh} device={device} dtype={dtype} threads={torch.get_num_threads()}")
    if args.load_bundle:
        ctx = _ctx_to(torch.load(args.load_bundle, weights_only=False), device, dtype)
        obs = ctx["obs"]
        print(f"[ens] loaded bundle {args.load_bundle}: obs coverage {int(obs.coverage_mask.sum())} "
              f"cells train={obs.n_train} val={obs.n_val} band-edge={obs.band_edge:.2f} basin={obs.basin_mean:.3f}")
    else:
        ctx = build_context(args)

    def _write_partial(res_list, wall_s, done):
        if not args.out:
            return
        outp = Path(args.out)
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(json.dumps({
            "experiment": "e2_real_calcite_seed_ensemble",
            "status": "COMPLETE" if done else f"PARTIAL ({len(res_list)}/{args.seeds})",
            "config": {"aoi": args.aoi, "calcite_source": args.calcite_source,
                       "split_channel": args.split_channel, "q": args.q, "hidden": args.hidden,
                       "weight_decay": args.weight_decay, "epochs": args.epochs,
                       "n_steps": args.n_steps, "kh_physical": args.kh, "n_z": args.n_z,
                       "device": str(ctx["device"]), "dtype": str(ctx["dtype"])},
            "n_seeds_target": args.seeds, "n_seeds_done": len(res_list),
            "wall_s_so_far": wall_s, "seeds": res_list,
        }, indent=2), encoding="utf-8")

    results = []
    t0 = time.perf_counter()
    for seed in range(seed_lo, seed_hi):
        results.append(run_seed(ctx, args, seed, full_ladder=seed in ladder_set))
        _write_partial(results, time.perf_counter() - t0, done=False)  # crash-safe checkpoint
    wall = time.perf_counter() - t0

    deltas = np.array([r["delta"] for r in results], dtype=float)
    n_fail = int((deltas < 0).sum())   # delta<0 = closure loses to null = NOT A PASS
    n_pass_delta = int((deltas > 0).sum())
    ladder_seeds = [r for r in results if r["is_pass"] is not None]
    n_full_pass = sum(1 for r in ladder_seeds if r["is_pass"])  # delta>0 AND shrinks

    summary = {
        "experiment": "e2_real_calcite_seed_ensemble",
        "config": {"aoi": args.aoi, "calcite_source": args.calcite_source, "split_channel": args.split_channel,
                   "q": args.q, "hidden": args.hidden, "weight_decay": args.weight_decay,
                   "epochs": args.epochs, "n_steps": args.n_steps, "kh_physical": args.kh,
                   "n_z": args.n_z, "device": str(ctx["device"]), "dtype": str(ctx["dtype"])},
        "n_seeds": args.seeds,
        "n_val": ctx["obs"].n_val, "n_train": ctx["obs"].n_train,
        "delta_mean": float(deltas.mean()), "delta_std": float(deltas.std(ddof=0)),
        "delta_min": float(deltas.min()), "delta_max": float(deltas.max()),
        "n_delta_negative": n_fail, "n_delta_positive": n_pass_delta,
        "n_full_pass_delta_and_shrinks": n_full_pass, "n_ladder_seeds": len(ladder_seeds),
        "verdict": ("ROBUST NEGATIVE (no seed passes)" if n_full_pass == 0 and n_pass_delta == 0
                    else f"MIXED ({n_pass_delta} seeds delta>0, {n_full_pass} full-pass)"),
        "wall_s_total": wall,
        "seeds": results,
    }
    print(f"\n[ens] ==> delta mean={summary['delta_mean']:+.3f} +/- {summary['delta_std']:.3f} "
          f"[{summary['delta_min']:+.3f}, {summary['delta_max']:+.3f}]  "
          f"delta<0: {n_fail}/{args.seeds}  full-pass: {n_full_pass}/{len(ladder_seeds)}")
    print(f"[ens] VERDICT: {summary['verdict']}  ({wall:.0f}s total)")

    if args.out:
        outp = Path(args.out)
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"[ens] wrote {outp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
