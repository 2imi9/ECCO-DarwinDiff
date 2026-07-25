"""Sign-flip / equifinality control at n>=50 seeds — robustifies the n=6 headline.

Extracts the exact synthetic mechanism already living (as notebook-cell strings) in
``scripts/build_demo_notebook.py`` (cells 6-8, "Lesson 2 -- fitting != identifying") into
a standalone, seed-scalable CLI so the n=6 (3/6, Wilson [0.19,0.81]) headline in
``docs/archive/research_notes/2026-06-27_synthetic_equifinality_demo.md`` and
``docs/research_notes/2026-07-21_manuscript_redteam.md`` ("REQUIRES A RERUN: sign-flip
control at n>=50") can be re-run at a referee-proof sample size. Same grid, same
TinyDINN, same forward box, same two loss conventions (pattern / absolute) -- only the
seed count changes.

Question this answers (verbatim from the gap): is a bigger n *decisive*, or does it just
tighten a Wilson CI on a known effect? At n=6 the CI [0.19,0.81] cannot distinguish a
genuine 50/50 coin flip from a 30/70 or 70/30 biased split -- it is uninformative. At
n=50 the CI half-width shrinks to roughly +/-0.14, which *can* separate those cases.
So n=50 is decisive for exactly one question: whether the sign-flip is a *symmetric*
degeneracy (Wilson CI straddles 0.5) or a *biased* one (CI excludes 0.5, i.e. one sign is
statistically preferred by the optimizer/init, which would nuance -- not overturn -- the
equifinality claim: the parameter's direction is still not determined by the data, but
the mechanism would be imperfect symmetry-breaking rather than a true double-well).

Pre-registered pass/fail (fixed BEFORE running, see docs/research_notes -- do not
re-target after seeing results):
  COIN-FLIP CONFIRMED   : Wilson 95% CI for P(sign(r_alpfe) > 0) contains 0.5
                          AND mean |r_alpfe| >= 0.8 (fits are genuinely strong, not noise)
  BIASED-BUT-STILL-EQUIFINAL : CI excludes 0.5 but both signs occur >= 3 times each
                          (direction still not data-determined, but not a fair coin)
  NOT EQUIFINAL AT n=50 : one sign occurs 0/50 or 50/50 with |r| high (i.e. the larger
                          sample reveals the effect does not replicate)

Run (CPU, no GPU, no real data -- pure synthetic, seconds per seed):
    python scripts/synthetic_signflip_control.py --n-seeds 50 --loss pattern \
        --output docs/findings/signflip_n50_pattern.json
    python scripts/synthetic_signflip_control.py --n-seeds 50 --loss absolute \
        --output docs/findings/signflip_n50_absolute.json

Recompute (anti-hallucination check, mirrors verify_run.py's policy of never trusting a
stored summary -- recomputes the Wilson CI and sign counts directly from the per-seed
array in the JSON):
    python scripts/synthetic_signflip_control.py --recheck docs/findings/signflip_n50_pattern.json
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import torch

from darwindiff.carroll6 import CARROLL_VALUES, PARAM_BOUNDS, bounded_params

H, W = 8, 16
N_STEPS = 150
DT = 0.25
LR = 5e-3


def _sst_grid(device: str) -> torch.Tensor:
    sst = (torch.linspace(-2.0, 2.0, H).unsqueeze(1) * torch.ones(1, W)).unsqueeze(0).unsqueeze(0)
    return ((sst - sst.mean()) / (sst.std() + 1e-8)).to(device)


def _make_truth(sst_norm_2d: torch.Tensor, device: str) -> torch.Tensor:
    carroll = CARROLL_VALUES.to(device)
    t = torch.zeros(6, H, W, device=device)
    t[0] = 0.30 + sst_norm_2d * (0.95 - 0.30)   # alpfe varies with SST
    t[1] = carroll[1]                            # scav_rat (constant)
    t[2] = 1.20 - sst_norm_2d * (1.20 - 0.30)   # Smallgrow varies with SST
    t[3] = carroll[3]
    t[4] = carroll[4]
    t[5] = carroll[5]
    return t


def _forward_box(params_field: torch.Tensor) -> torch.Tensor:
    device = params_field.device
    state = torch.stack([
        torch.full((H, W), 0.5e-3, device=device),  # DFe
        torch.full((H, W), 0.05, device=device),    # Ps
        torch.full((H, W), 0.05, device=device),    # Pl
        torch.full((H, W), 0.1, device=device),     # POC
        torch.full((H, W), 0.001, device=device),   # PIC
    ])
    for _ in range(N_STEPS):
        from darwindiff.carroll6 import carroll6_step
        state = carroll6_step(state, params_field, DT)
    return state[1] + state[2]  # Ps + Pl biomass


class TinyDINN(torch.nn.Module):
    """Identical architecture to the notebook demo (~438 weights, per-cell 1x1 convs)."""

    def __init__(self) -> None:
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Conv2d(1, 8, kernel_size=1), torch.nn.Tanh(),
            torch.nn.Conv2d(8, 8, kernel_size=1), torch.nn.Tanh(),
            torch.nn.Conv2d(8, 6, kernel_size=1),
        )

    def forward(self, env: torch.Tensor) -> torch.Tensor:
        return self.net(env)


def train_percell(
    seed: int, sst_z: torch.Tensor, target: torch.Tensor, bounds: torch.Tensor,
    loss_kind: str, n_epochs: int, device: str,
) -> torch.Tensor:
    torch.manual_seed(seed)
    net = TinyDINN().to(device)
    opt = torch.optim.Adam(net.parameters(), lr=LR)
    target_z = (target - target.mean()) / (target.std() + 1e-8)
    for _ in range(n_epochs):
        params = bounded_params(net(sst_z), bounds, param_axis=1).squeeze(0)
        pred = _forward_box(params)
        if loss_kind == "pattern":
            pred_z = (pred - pred.mean()) / (pred.std() + 1e-8)
            loss = ((pred_z - target_z) ** 2).mean()
        elif loss_kind == "absolute":
            loss = ((pred - target) ** 2).mean()
        else:
            raise ValueError(f"unknown loss_kind {loss_kind!r}")
        opt.zero_grad()
        loss.backward()
        opt.step()
    with torch.no_grad():
        params = bounded_params(net(sst_z), bounds, param_axis=1).squeeze(0)
    return params.detach()


def r_signed(field: torch.Tensor, true_flat: np.ndarray) -> float:
    a = field.flatten().cpu().numpy()
    if np.std(a) < 1e-9:
        return float("nan")
    return float(np.corrcoef(a, true_flat)[0, 1])


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion k/n (no continuity correction).

    Matches the convention already used for the project's recovery-rate headlines
    (e.g. STATUS.md's "33/50 ... Wilson [0.52,0.78]").
    """
    if n == 0:
        return (float("nan"), float("nan"))
    phat = k / n
    denom = 1 + z * z / n
    center = phat + z * z / (2 * n)
    half = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n))
    return ((center - half) / denom, (center + half) / denom)


def run(n_seeds: int, seed_start: int, n_epochs: int, loss_kind: str, device: str) -> dict:
    bounds = PARAM_BOUNDS.to(device)
    sst = torch.linspace(-2.0, 2.0, H).unsqueeze(1) * torch.ones(1, W)
    sst_z = ((sst - sst.mean()) / (sst.std() + 1e-8)).unsqueeze(0).unsqueeze(0).to(device)
    sst_norm = (sst_z.squeeze() - sst_z.min()) / (sst_z.max() - sst_z.min() + 1e-8)
    truth = _make_truth(sst_norm, device)
    alpfe_true = truth[0].flatten().cpu().numpy()
    smallgrow_true = truth[2].flatten().cpu().numpy()
    target = _forward_box(truth).detach()

    rows = []
    t0 = time.time()
    for i in range(n_seeds):
        seed = seed_start + i
        p = train_percell(seed, sst_z, target, bounds, loss_kind, n_epochs, device)
        pred = _forward_box(p).detach()
        target_z = (target - target.mean()) / (target.std() + 1e-8)
        pred_z = (pred - pred.mean()) / (pred.std() + 1e-8)
        final_loss = float(((pred_z - target_z) ** 2).mean()) if loss_kind == "pattern" \
            else float(((pred - target) ** 2).mean())
        ra = r_signed(p[0], alpfe_true)
        rs = r_signed(p[2], smallgrow_true)
        rows.append({"seed": seed, "final_loss": final_loss, "r_alpfe": ra, "r_smallgrow": rs})
    elapsed = time.time() - t0

    signs_alpfe = [1 if r["r_alpfe"] > 0 else 0 for r in rows if not math.isnan(r["r_alpfe"])]
    n_valid = len(signs_alpfe)
    k_pos = sum(signs_alpfe)
    lo, hi = wilson_ci(k_pos, n_valid)
    abs_r = [abs(r["r_alpfe"]) for r in rows if not math.isnan(r["r_alpfe"])]

    signs_sg = [1 if r["r_smallgrow"] > 0 else 0 for r in rows if not math.isnan(r["r_smallgrow"])]
    k_pos_sg = sum(signs_sg)
    lo_sg, hi_sg = wilson_ci(k_pos_sg, len(signs_sg))

    mean_abs = float(np.mean(abs_r)) if abs_r else 0.0
    coin_flip = (lo <= 0.5 <= hi) and (mean_abs >= 0.8)
    # Vet-refined verdict logic: (a) fits too weak to judge sign-determinism -> WEAK;
    # (b) near-unanimous (not just perfectly unanimous) sign -> effect does not replicate;
    # (c) CI brackets 0.5 with strong fits -> genuine coin-flip; else biased-but-equifinal.
    if mean_abs < 0.8:
        verdict = "WEAK_INCONCLUSIVE"
    elif k_pos <= 2 or k_pos >= n_valid - 2:
        verdict = "NOT_EQUIFINAL_AT_N50"
    elif coin_flip:
        verdict = "COIN_FLIP_CONFIRMED"
    else:
        verdict = "BIASED_BUT_STILL_EQUIFINAL"

    return {
        "config": {
            "n_seeds": n_seeds, "seed_start": seed_start, "n_epochs": n_epochs,
            "loss_kind": loss_kind, "device": device, "H": H, "W": W,
            "n_steps": N_STEPS, "dt": DT, "lr": LR,
        },
        "elapsed_sec": elapsed,
        "rows": rows,
        "alpfe": {
            "n_valid": n_valid, "n_sign_positive": k_pos,
            "wilson_ci_95": [lo, hi], "mean_abs_r": float(np.mean(abs_r)) if abs_r else float("nan"),
        },
        "smallgrow": {
            "n_valid": len(signs_sg), "n_sign_positive": k_pos_sg,
            "wilson_ci_95": [lo_sg, hi_sg],
        },
        "verdict": verdict,
    }


def recheck(path: Path) -> int:
    """Recompute the Wilson CI + verdict straight from the stored per-seed rows,
    never trusting the stored summary (verify_run.py's anti-hallucination policy)."""
    d = json.loads(path.read_text(encoding="utf-8"))
    rows = d["rows"]
    signs = [1 if r["r_alpfe"] > 0 else 0 for r in rows if not math.isnan(r["r_alpfe"])]
    n = len(signs)
    k = sum(signs)
    lo, hi = wilson_ci(k, n)
    stored = d["alpfe"]["wilson_ci_95"]
    ok = abs(lo - stored[0]) < 1e-9 and abs(hi - stored[1]) < 1e-9 and k == d["alpfe"]["n_sign_positive"]
    print(f"recomputed: k={k}/{n}  Wilson=[{lo:.3f},{hi:.3f}]  stored={stored}  match={ok}")
    return 0 if ok else 2


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n-seeds", type=int, default=50)
    ap.add_argument("--seed-start", type=int, default=0)
    ap.add_argument("--n-epochs", type=int, default=300)
    ap.add_argument("--loss", choices=["pattern", "absolute"], default="pattern")
    ap.add_argument("--output", type=str, default=None)
    ap.add_argument("--recheck", type=str, default=None, help="path to a prior JSON to recompute + verify")
    ap.add_argument("--device", choices=["auto", "cpu", "cuda"], default="cpu",
                    help="grid is 8x16 (128 cells) -- CPU is faster than GPU here (no kernel-launch "
                         "overhead on ops this small); default cpu. Use --device auto to prefer CUDA.")
    args = ap.parse_args()

    if args.recheck:
        return recheck(Path(args.recheck))

    if args.device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = args.device
    result = run(args.n_seeds, args.seed_start, args.n_epochs, args.loss, device)
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
