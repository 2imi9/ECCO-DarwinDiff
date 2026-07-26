"""Physics-equation verification — a THIRD, independent validator for the emulator.

Motivation: our only two yardsticks are (1) self-consistency vs the v05 MODEL and (2) real
observations (the untouched #163 gap). Both are *data* comparisons, and an MSE-style skill score is
blind to physics: a model can score well while emitting chemically impossible seawater. This adds a
third axis that needs NO reference data at all — only laws we already trust.

Checks (each run on BOTH v05 truth and the emulator prediction — the truth column is the CONTROL;
v05 itself violates some of these, e.g. it contains negative chlorophyll, so a violation the emulator
merely INHERITS is not the emulator's fault):

  A. POSITIVITY          concentrations >= 0. MSE barely penalises a small negative; physics forbids it.
  B. ALK:DIC RATIO       seawater sits at ALK/DIC ~1.0-1.25 (0.997 of QC-good GLODAP falls in that band).
  C. CARBONATE CLOSURE   feed (DIC, ALK) at nominal T/S into carbonate.py (validated r=1.000 vs GLODAP
                         CO2SYS) and require a physical pCO2. A pair can be near-truth in MSE yet fail
                         to solve. NB: nominal T/S tests the PAIR's validity, not the actual pCO2.
  D. STOICHIOMETRY       the emulator predicts 6 tracers as INDEPENDENT channels; chemistry couples them.
                         CaCO3 formation: dALK ~ -2*dPIC. We regress the predicted increments and compare
                         the slope to v05's own slope. Deviation = learned chemistry violation.

Run:
  python scripts/physics_verify.py --cube global3d_L10_cube.npz --model de3d_seed0.pt --out phys.json
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import numpy as np
import torch

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
_SRC = _HERE.parent / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
from darwindiff.safe_load import safe_torch_load  # noqa: E402
from diffusion_emulator import FNO2d, _batch, load_cube, time_split, zscore  # noqa: E402


def _chan_idx(names, tracer):
    """Indices of a tracer's levels, e.g. DIC -> [DIC_k0..DIC_k9]."""
    return [i for i, n in enumerate(names) if n.split("_k")[0] == tracer]


def _slope(x, y):
    """Least-squares slope of y on x (both 1-D), robust to tiny variance."""
    x = x - x.mean(); y = y - y.mean()
    d = float((x * x).sum())
    return float((x * y).sum() / d) if d > 1e-12 else float("nan")


def physics_report(state, mask, names, tag, sample=200_000, rng=None):
    """state: [B,C,H,W] PHYSICAL units. Returns dict of physics diagnostics."""
    rng = rng or np.random.default_rng(0)
    out = {"tag": tag}
    oc = state[:, :, mask]                                   # [B,C,ocean]
    # ---- A. positivity, per tracer ----
    pos = {}
    for t in sorted({n.split("_k")[0] for n in names}):
        idx = _chan_idx(names, t)
        v = oc[:, idx, :]
        pos[t] = {"neg_fraction": float((v < 0).mean()),
                  "min": float(v.min())}
    out["A_positivity"] = pos
    # ---- B. ALK:DIC ratio ----
    di, ai = _chan_idx(names, "DIC"), _chan_idx(names, "ALK")
    if di and ai:
        dic = oc[:, di, :].ravel(); alk = oc[:, ai, :].ravel()
        ok = np.isfinite(dic) & np.isfinite(alk) & (dic > 1e-6)
        r = alk[ok] / dic[ok]
        if len(r) > sample:
            r = rng.choice(r, sample, replace=False)
        out["B_alk_dic_ratio"] = {
            "median": float(np.median(r)),
            "frac_in_physical_band_1.0_1.25": float(((r >= 1.0) & (r <= 1.25)).mean()),
            "p1": float(np.percentile(r, 1)), "p99": float(np.percentile(r, 99)),
        }
        # ---- C. carbonate closure at nominal T/S ----
        try:
            from darwindiff.carbonate import solve_carbonate
            n = min(20000, ok.sum())
            sel = rng.choice(np.flatnonzero(ok), n, replace=False)
            D = torch.tensor(dic[sel], dtype=torch.float32)
            A = torch.tensor(alk[sel], dtype=torch.float32)
            T = torch.full((n,), 15.0); S = torch.full((n,), 35.0)
            pco2 = solve_carbonate(D, A, T, S)["pCO2"].numpy()
            fin = np.isfinite(pco2)
            out["C_carbonate_closure"] = {
                "n": int(n),
                "frac_finite": float(fin.mean()),
                "frac_physical_50_2000uatm": float(((pco2 > 50) & (pco2 < 2000) & fin).mean()),
                "median_pco2_uatm": float(np.median(pco2[fin])) if fin.any() else None,
                "note": "nominal T=15C S=35 — tests the (DIC,ALK) PAIR's validity, not actual pCO2",
            }
        except Exception as e:  # pragma: no cover
            out["C_carbonate_closure"] = {"error": str(e)}
    return out


def stoichiometry(prev, nxt, mask, names, tag, rng=None):
    """D. CaCO3 coupling: dALK ~ -2*dPIC. Regress increments; compare emulator slope to v05's."""
    rng = rng or np.random.default_rng(0)
    pi, ai = _chan_idx(names, "PIC"), _chan_idx(names, "ALK")
    if not (pi and ai):
        return {"tag": tag, "error": "PIC/ALK channels absent"}
    dP = (nxt[:, pi, :, :] - prev[:, pi, :, :])[:, :, mask].ravel()
    dA = (nxt[:, ai, :, :] - prev[:, ai, :, :])[:, :, mask].ravel()
    ok = np.isfinite(dP) & np.isfinite(dA)
    dP, dA = dP[ok], dA[ok]
    if len(dP) > 400_000:
        s = rng.choice(len(dP), 400_000, replace=False); dP, dA = dP[s], dA[s]
    r = float(np.corrcoef(dP, dA)[0, 1]) if dP.std() > 1e-12 else float("nan")
    return {"tag": tag, "slope_dALK_vs_dPIC": _slope(dP, dA), "corr": r,
            "expected_slope_CaCO3": -2.0,
            "note": "v05 is the CONTROL — compare emulator slope to v05's, not to -2 in the abstract"}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cube", required=True)
    p.add_argument("--model", nargs="+", required=True, help="regression checkpoint(s)/globs; >1 = ensemble mean")
    p.add_argument("--eval-batch", type=int, default=2)
    p.add_argument("--max-batches", type=int, default=8)
    p.add_argument("--log-transform", action="store_true",
                   help="MUST match the model's training transform. Physical-unit checks then use "
                        "exp() as the inverse — so positivity is GUARANTEED by construction (that IS the fix).")
    p.add_argument("--log-floor", type=float, default=1e-4)
    p.add_argument("--cpu", action="store_true")
    p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    device = "cpu" if (args.cpu or not torch.cuda.is_available()) else "cuda"

    paths = sorted({q for m in args.model for q in glob.glob(m)})
    state, mask, names = load_cube(args.cube)
    if args.log_transform:
        state = np.log(np.clip(state, args.log_floor, None)).astype(np.float32)
    T, C, H, W = state.shape
    z, mean, std = zscore(state, mask)
    Z = torch.from_numpy(z)
    tr_t, va_t = time_split(T)
    print(f"[phys] cube {(T,C,H,W)} | {len(paths)} model(s) | device={device}", flush=True)

    models = []
    for pth in paths:
        ck = safe_torch_load(pth, map_location=device)
        cfg = ck["config"]
        m = FNO2d(C, C, modes1=cfg["modes"], modes2=cfg["modes"], width=cfg["reg_width"]).to(device)
        m.load_state_dict(ck["regression"]); m.eval(); models.append(m)

    mean_t = torch.tensor(mean, device=device).view(1, -1, 1, 1)
    std_t = torch.tensor(std, device=device).view(1, -1, 1, 1)
    va = torch.tensor(va_t)[: args.eval_batch * args.max_batches]
    P_prev, P_true, P_pred = [], [], []
    with torch.no_grad():
        for k in range(0, len(va), args.eval_batch):
            bt = va[k : k + args.eval_batch]
            xt, yt = _batch(Z, bt, device)
            mu = torch.stack([xt + m(xt) for m in models]).mean(0)
            # back to PHYSICAL units. z-score inverse, then exp() if trained in log space
            # (⇒ physical values are exp(...) > 0 by construction: log-space GUARANTEES positivity).
            def to_phys(arr):
                v = arr * std_t + mean_t
                return (torch.exp(v) if args.log_transform else v).cpu().numpy()
            for buf, arr in ((P_prev, xt), (P_true, yt), (P_pred, mu)):
                buf.append(to_phys(arr))
    prev = np.concatenate(P_prev); true = np.concatenate(P_true); pred = np.concatenate(P_pred)
    print(f"[phys] evaluated {prev.shape[0]} val fields in physical units", flush=True)

    rep = {
        "v05_truth": physics_report(true, mask, names, "v05_truth"),
        "emulator": physics_report(pred, mask, names, "emulator"),
        "stoichiometry_v05": stoichiometry(prev, true, mask, names, "v05_truth"),
        "stoichiometry_emulator": stoichiometry(prev, pred, mask, names, "emulator"),
        "n_members": len(paths),
    }

    print("\n=== A. POSITIVITY (neg fraction) — truth is the CONTROL ===")
    for t in rep["v05_truth"]["A_positivity"]:
        a = rep["v05_truth"]["A_positivity"][t]["neg_fraction"]
        b = rep["emulator"]["A_positivity"][t]["neg_fraction"]
        flag = "  <-- EMULATOR WORSE" if b > a + 1e-4 else ""
        print(f"  {t:6s} v05={a:.4f}  emulator={b:.4f}{flag}")
    for key in ("B_alk_dic_ratio", "C_carbonate_closure"):
        print(f"\n=== {key} ===")
        print(f"  v05     : {rep['v05_truth'].get(key)}")
        print(f"  emulator: {rep['emulator'].get(key)}")
    print("\n=== D. STOICHIOMETRY  dALK ~ -2*dPIC (CaCO3) ===")
    print(f"  v05     : {rep['stoichiometry_v05']}")
    print(f"  emulator: {rep['stoichiometry_emulator']}")
    if args.out:
        Path(args.out).write_text(json.dumps(rep, indent=2))
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
