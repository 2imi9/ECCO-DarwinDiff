"""Symbolic-distillation go/no-go gate for a trained Track-2 closure (§2).

This is a **cheap, local (CPU) go/no-go gate that runs BEFORE any expensive
native-resolution H200 closure fit**. It distills a frozen closure NN into a
symbolic law and uses the *recovery quality* as a second, independent
identifiability oracle that must agree with the existing Fisher / profile-
likelihood diagnostics (``scripts/identifiability_sloppiness.py``): a
profile-flat parameter (the diatomgraz signature) must *also* fail bootstrap
inclusion here, and a genuinely identifiable Monod law must pass both.

The distillation is deliberately *algebraic*, not vanilla SINDy: the closure
already outputs a clean analytic flux ``f_fe(DFe) in [0,1]``, so there are no
numerical derivatives and no weak form -- it is a plain over-determined STLSQ on
a static ``(Theta(DFe), y_nn)`` table. The library is anchored on the physics
atom the closure is *supposed* to have learned (a Monod term ``DFe/(DFe+k)`` on
a fixed-k log bank) plus the polynomial confounders a network uses to *fake*
saturation. The Monod atom winning against those confounders IS the
identifiability signal.

The single most important idea here is **support-dependence**. A Monod curve and
a straight line are nearly indistinguishable when the visited DFe support sits
far below the half-saturation constant ``k`` (both look linear), and only
separate once the support spans the *knee*. So this gate does not merely ask
"does a Monod term fit"; it asks "is a Monod term *distinguishable from its
linear confounder on the support the closure actually visited*". That is exactly
the Night-1 finding operationalized: closure equifinality is a support problem;
excitation that spans the knee cures it. A narrow low-DFe support correctly
returns DISTILL-FAIL / non-identifiable even for a perfectly Monod closure --
which is the honest verdict, and the thing that saves H200 budget.

Verdict (per closure, mirroring the per-PFT/per-AOI 6/6 structure when looped):

    DISTILL-PASS  iff  inclusion(Monod) > 0.85
                       and k stable within 20% across bootstraps
                       and Monod is separable from its linear confounder on the
                           visited support (aliasing guard)
                       and held-out (spatial-split) R^2 is adequate
    DISTILL-FAIL  else -> do NOT spend native H200 budget; report why.

No pysindy dependency: STLSQ, the fixed-k bank, ensemble bootstrapping, and the
1-D k line-search are implemented directly on numpy + scipy (both already in the
env). Run ``python scripts/symbolic_distill_probe.py`` for the self-test panel
(analytic Monod / narrow-support Monod / flat / linear-confounder closures), or
``--npz path.npz`` to distill a real ``(dfe, y)`` dump from a cluster training
run, or ``--train-demo`` to distill a tiny CPU-trained MonodAnchored NN.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict, field
from pathlib import Path

import numpy as np
from scipy.optimize import minimize_scalar

# ----------------------------------------------------------------------------- #
# Library construction
# ----------------------------------------------------------------------------- #

def monod_bank_ks(k_lo: float = 1.0e-6, k_hi: float = 1.0e-2, n: int = 12) -> np.ndarray:
    """Fixed half-saturation constants on a log grid spanning the physical range
    (Carroll K_FE = 5e-5 sits comfortably inside)."""
    return np.logspace(np.log10(k_lo), np.log10(k_hi), n)


def build_library(dfe: np.ndarray, ks: np.ndarray, poly_degree: int = 2):
    """Static design matrix ``Theta`` with named columns.

    Columns: a Monod bank ``DFe/(DFe+k_j)`` (the physics atoms) followed by the
    polynomial confounders ``1, DFe, DFe^2, ...`` (what a NN uses to fake
    saturation). Returns ``(Theta[N,M], names[M], is_monod[M])``.
    """
    dfe = np.asarray(dfe, dtype=np.float64).reshape(-1)
    cols, names, is_monod = [], [], []
    for k in ks:
        cols.append(dfe / (dfe + k))
        names.append(f"monod(k={k:.2e})")
        is_monod.append(True)
    for d in range(poly_degree + 1):
        cols.append(dfe ** d)
        names.append("1" if d == 0 else ("DFe" if d == 1 else f"DFe^{d}"))
        is_monod.append(False)
    return np.column_stack(cols), names, np.asarray(is_monod)


# ----------------------------------------------------------------------------- #
# STLSQ (sequentially-thresholded least squares) on standardized columns
# ----------------------------------------------------------------------------- #

def stlsq(theta: np.ndarray, y: np.ndarray, threshold: float, max_iter: int = 12,
          sample_weight: np.ndarray | None = None) -> np.ndarray:
    """Sparse regression: standardize columns to unit std, iteratively drop
    coefficients below ``threshold`` (in standardized units), refit on the kept
    set, un-standardize. Returns coefficients in the *original* column units.
    """
    theta = np.asarray(theta, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64).reshape(-1)
    n, m = theta.shape
    scale = theta.std(axis=0)
    scale = np.where(scale < 1e-12, 1.0, scale)
    ts = theta / scale  # standardized columns

    if sample_weight is not None:
        w = np.sqrt(np.asarray(sample_weight, dtype=np.float64).reshape(-1))
        tw, yw = ts * w[:, None], y * w
    else:
        tw, yw = ts, y

    keep = np.ones(m, dtype=bool)
    coef_s = np.zeros(m)
    for _ in range(max_iter):
        coef_s[:] = 0.0
        if keep.any():
            sol, *_ = np.linalg.lstsq(tw[:, keep], yw, rcond=None)
            coef_s[keep] = sol
        new_keep = np.abs(coef_s) >= threshold
        if new_keep.sum() == 0:  # threshold too aggressive: keep the single best
            best = int(np.argmax(np.abs(coef_s)))
            new_keep = np.zeros(m, dtype=bool)
            new_keep[best] = True
        if np.array_equal(new_keep, keep):
            break
        keep = new_keep
    coef_s[~keep] = 0.0
    return coef_s / scale  # back to original units


def _r2(y: np.ndarray, yhat: np.ndarray) -> float:
    y = np.asarray(y, dtype=np.float64).reshape(-1)
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 1e-30 else float("nan")


# ----------------------------------------------------------------------------- #
# Support handling: mask + inverse-density (1/kde) reweighting
# ----------------------------------------------------------------------------- #

def support_mask(dfe: np.ndarray, q_lo: float = 0.01, q_hi: float = 0.99) -> np.ndarray:
    """Keep the central 1-99% of the visited DFe (drop off-support tails where a
    NN extrapolates garbage that STLSQ would happily fit)."""
    dfe = np.asarray(dfe).reshape(-1)
    lo, hi = np.quantile(dfe, q_lo), np.quantile(dfe, q_hi)
    return (dfe >= lo) & (dfe <= hi)


def inverse_density_weights(dfe: np.ndarray, n_bins: int = 40) -> np.ndarray:
    """~1/kde(DFe) on a log axis so rare-but-real regimes (high-DFe cells) are
    not drowned by abundant low-DFe points. Normalized to mean 1."""
    dfe = np.asarray(dfe, dtype=np.float64).reshape(-1)
    lg = np.log10(np.clip(dfe, 1e-12, None))
    hist, edges = np.histogram(lg, bins=n_bins)
    idx = np.clip(np.digitize(lg, edges[1:-1]), 0, n_bins - 1)
    dens = hist[idx].astype(np.float64)
    w = 1.0 / np.clip(dens, 1.0, None)
    return w / w.mean()


# ----------------------------------------------------------------------------- #
# Monod k refinement + aliasing (identifiability) guard
# ----------------------------------------------------------------------------- #

def refine_monod_k(dfe: np.ndarray, y: np.ndarray, k0: float,
                   sample_weight: np.ndarray | None = None) -> tuple[float, float]:
    """1-D line search: fit ``y ~= a * DFe/(DFe+k) + b`` and minimize weighted
    residual over log10(k). Returns ``(k_hat, r2)``."""
    dfe = np.asarray(dfe, dtype=np.float64).reshape(-1)
    y = np.asarray(y, dtype=np.float64).reshape(-1)
    w = (np.ones_like(y) if sample_weight is None
         else np.asarray(sample_weight, dtype=np.float64).reshape(-1))
    sw = np.sqrt(w)

    def resid(logk: float) -> float:
        k = 10.0 ** logk
        col = dfe / (dfe + k)
        A = np.column_stack([col, np.ones_like(col)]) * sw[:, None]
        sol, *_ = np.linalg.lstsq(A, y * sw, rcond=None)
        yhat = sol[0] * col + sol[1]
        return float(np.sum(w * (y - yhat) ** 2))

    res = minimize_scalar(resid, bounds=(np.log10(1e-7), np.log10(1e-1)),
                          method="bounded")
    k_hat = float(10.0 ** res.x)
    col = dfe / (dfe + k_hat)
    A = np.column_stack([col, np.ones_like(col)]) * sw[:, None]
    sol, *_ = np.linalg.lstsq(A, y * sw, rcond=None)
    yhat = sol[0] * col + sol[1]
    return k_hat, _r2(y, yhat)


def monod_linear_alias(dfe: np.ndarray, k: float) -> float:
    """|corr| between the fitted Monod column and a plain linear column on the
    visited support. Near 1 => the two are indistinguishable here, so a Monod
    'fit' is not identifiable *on this support* (the knee was not visited)."""
    dfe = np.asarray(dfe, dtype=np.float64).reshape(-1)
    col = dfe / (dfe + k)
    if col.std() < 1e-12 or dfe.std() < 1e-12:
        return 1.0
    return float(abs(np.corrcoef(col, dfe)[0, 1]))


# ----------------------------------------------------------------------------- #
# The gate
# ----------------------------------------------------------------------------- #

@dataclass
class DistillVerdict:
    passed: bool
    reason: str
    monod_inclusion: float
    k_hat: float
    k_rel_std: float
    monod_linear_alias: float
    r2_in: float
    r2_holdout: float
    n_points: int
    selected_terms: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


def distill(dfe: np.ndarray, y: np.ndarray, *, groups: np.ndarray | None = None,
            ks: np.ndarray | None = None, poly_degree: int = 2,
            threshold: float = 0.05, n_boot: int = 100,
            incl_tol: float = 0.85, k_tol: float = 0.20,
            alias_tol: float = 0.95, r2_tol: float = 0.90,
            flat_var_tol: float = 1e-6, seed: int = 0) -> DistillVerdict:
    """Distill a closure's ``(dfe -> y)`` law and return a go/no-go verdict.

    ``groups`` (optional) labels each point with a spatial group id; if given, a
    leave-one-group-out split scores transfer (train on all-but-last group, test
    on the held-out group). Without groups, a random 70/30 split is used.
    """
    rng = np.random.default_rng(seed)
    dfe = np.asarray(dfe, dtype=np.float64).reshape(-1)
    y = np.asarray(y, dtype=np.float64).reshape(-1)

    # 1. Flat / profile-flat guard (the diatomgraz analog): a closure with no
    #    variation carries no identifiable law -- FAIL before touching the bank.
    if y.std() < flat_var_tol:
        return DistillVerdict(False, "flat closure (no variance; profile-flat analog "
                              "-> non-identifiable)", 0.0, float("nan"), float("nan"),
                              1.0, float("nan"), float("nan"), int(dfe.size))

    # 2. Restrict to the visited support and reweight by inverse density.
    m = support_mask(dfe)
    dfe, y = dfe[m], y[m]
    if groups is not None:
        groups = np.asarray(groups).reshape(-1)[m]
    w = inverse_density_weights(dfe)

    if ks is None:
        ks = monod_bank_ks()
    theta, names, is_monod = build_library(dfe, ks, poly_degree)

    # 3. Point estimate on the full (masked, reweighted) table.
    coef = stlsq(theta, y, threshold, sample_weight=w)
    yhat = theta @ coef
    r2_in = _r2(y, yhat)
    selected = {names[i]: float(coef[i]) for i in np.nonzero(coef)[0]}

    # 4. Bootstrap inclusion probability per atom (ensemble-SINDy style).
    incl = np.zeros(theta.shape[1])
    n = dfe.size
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        cb = stlsq(theta[idx], y[idx], threshold, sample_weight=w[idx])
        incl += (np.abs(cb) > 0).astype(np.float64)
    incl /= n_boot
    monod_inclusion = float(incl[is_monod].max()) if is_monod.any() else 0.0

    # 5. Refine k on the winning Monod atom + measure its bootstrap stability.
    best_monod = int(np.argmax(np.where(is_monod, incl, -1)))
    k0 = ks[best_monod]
    k_hat, _ = refine_monod_k(dfe, y, k0, sample_weight=w)
    kboot = []
    for _ in range(min(n_boot, 60)):
        idx = rng.integers(0, n, n)
        kb, _ = refine_monod_k(dfe[idx], y[idx], k0, sample_weight=w[idx])
        kboot.append(kb)
    kboot = np.asarray(kboot)
    k_rel_std = float(kboot.std() / max(kboot.mean(), 1e-12))

    # 6. Aliasing / identifiability guard: is the Monod atom separable from a
    #    straight line on this support (was the knee visited)?
    alias = monod_linear_alias(dfe, k_hat)

    # 7. Held-out transfer R^2 (spatial split if groups supplied, else random).
    if groups is not None and len(np.unique(groups)) >= 2:
        held = np.unique(groups)[-1]
        tr, te = groups != held, groups == held
    else:
        perm = rng.permutation(n)
        te = np.zeros(n, dtype=bool)
        te[perm[: max(1, int(0.3 * n))]] = True
        tr = ~te
    th_tr, _, _ = build_library(dfe[tr], ks, poly_degree)
    coef_tr = stlsq(th_tr, y[tr], threshold, sample_weight=w[tr])
    th_te, _, _ = build_library(dfe[te], ks, poly_degree)
    r2_holdout = _r2(y[te], th_te @ coef_tr)

    # 8. Verdict.
    checks = {
        "inclusion": monod_inclusion >= incl_tol,
        "k_stable": np.isfinite(k_rel_std) and k_rel_std <= k_tol,
        "separable": alias <= alias_tol,
        "holdout": np.isfinite(r2_holdout) and r2_holdout >= r2_tol,
    }
    passed = all(checks.values())
    if passed:
        reason = "DISTILL-PASS: Monod law recovered, identifiable on visited support"
    else:
        fails = [k for k, ok in checks.items() if not ok]
        detail = {
            "inclusion": f"Monod inclusion {monod_inclusion:.2f} < {incl_tol}",
            "k_stable": f"k unstable (rel.std {k_rel_std:.2f} > {k_tol})",
            "separable": (f"Monod aliases linear on this support "
                          f"(|corr| {alias:.3f} > {alias_tol}); knee not visited "
                          f"-> add DFe excitation & retrain"),
            "holdout": f"held-out R^2 {r2_holdout:.2f} < {r2_tol}",
        }
        reason = "DISTILL-FAIL: " + "; ".join(detail[f] for f in fails)
    return DistillVerdict(passed, reason, monod_inclusion, k_hat, k_rel_std,
                          alias, r2_in, r2_holdout, int(dfe.size), selected)


# ----------------------------------------------------------------------------- #
# Closure sampling helpers
# ----------------------------------------------------------------------------- #

def sample_closure(closure_fn, dfe: np.ndarray) -> np.ndarray:
    """Evaluate a frozen closure (numpy callable or torch nn.Module) on the
    visited DFe samples, returning numpy ``y``."""
    try:
        import torch
        if isinstance(closure_fn, torch.nn.Module) or hasattr(closure_fn, "parameters"):
            with torch.no_grad():
                # match the module's parameter dtype (float32 nets vs float64 input)
                try:
                    dtype = next(closure_fn.parameters()).dtype
                except (StopIteration, AttributeError):
                    dtype = torch.float64
                t = torch.as_tensor(np.asarray(dfe), dtype=dtype)
                return closure_fn(t).detach().cpu().numpy().reshape(-1)
    except ImportError:
        pass
    return np.asarray(closure_fn(np.asarray(dfe, dtype=np.float64))).reshape(-1)


# ----------------------------------------------------------------------------- #
# Self-test panel + CLI
# ----------------------------------------------------------------------------- #

def _selftest_panel(seed: int = 0) -> dict:
    """Five analytic closures with known ground truth exercise the gate:
      * monod_wide     -- pure Monod, support spans the knee   -> PASS, recover k
      * monod_pow      -- Monod^0.7, support spans the knee     -> PASS (k biased low,
                          not asserted: a pure-Monod fit to a flattened curve)
      * monod_narrow   -- pure Monod, support far below k       -> FAIL (aliased)
      * flat           -- constant (diatomgraz analog)          -> FAIL (flat)
      * linear         -- rising line faking saturation         -> FAIL (not Monod)

    The Carroll closure the real experiment targets is a *pure* Monod
    (``f_fe = DFe/(DFe+K_FE)``), so k-recovery is asserted on ``monod_wide``.
    ``monod_pow`` is the harder synthetic twin (the ``_true_ffe`` used in the
    H200 arms): the gate still passes the verdict but the recovered k is the
    effective half-saturation of the best Monod approximation, so it is reported,
    not asserted.
    """
    rng = np.random.default_rng(seed)
    K_TRUE = 8.0e-5

    def monod(dfe, p=1.0):
        return (dfe / (dfe + K_TRUE)) ** p

    wide = np.logspace(-5, -3, 4000)            # 1e-5..1e-3, brackets K_TRUE
    narrow = np.logspace(-6.5, -5.2, 4000)      # all << K_TRUE (no knee)
    cases = {
        "monod_wide": (wide, monod(wide) + 0.002 * rng.standard_normal(wide.size)),
        "monod_pow": (wide, monod(wide, 0.7) + 0.002 * rng.standard_normal(wide.size)),
        "monod_narrow": (narrow, monod(narrow) + 0.002 * rng.standard_normal(narrow.size)),
        "flat": (wide, 0.5 + 1e-8 * rng.standard_normal(wide.size)),
        "linear": (wide, np.clip(0.2 + 300.0 * wide, 0, 1)
                   + 0.002 * rng.standard_normal(wide.size)),
    }
    out = {}
    for name, (dfe, y) in cases.items():
        v = distill(dfe, y, seed=seed)
        out[name] = v.as_dict()
        tag = "PASS" if v.passed else "FAIL"
        print(f"  [{tag}] {name:<13} incl={v.monod_inclusion:.2f} "
              f"k_hat={v.k_hat:.2e} k_relstd={v.k_rel_std:.2f} "
              f"alias={v.monod_linear_alias:.3f} r2_ho={v.r2_holdout:.3f}")
        print(f"         {v.reason}")
    # Expected: both Monod-wide cases pass; narrow/flat/linear fail; and the pure
    # Monod recovers K_TRUE within 20%.
    exp = {"monod_wide": True, "monod_pow": True, "monod_narrow": False,
           "flat": False, "linear": False}
    ok = all(out[n]["passed"] == exp[n] for n in exp)
    kok = abs(out["monod_wide"]["k_hat"] - K_TRUE) / K_TRUE < 0.20
    print(f"\n  panel self-consistency: verdicts={'OK' if ok else 'MISMATCH'}, "
          f"k-recovery={'OK' if kok else 'OFF'} (k_hat "
          f"{out['monod_wide']['k_hat']:.2e} vs true {K_TRUE:.2e})")
    out["_meta"] = {"verdicts_ok": bool(ok), "k_recovery_ok": bool(kok),
                    "k_true": K_TRUE}
    return out


def _train_demo(seed: int = 0) -> dict:
    """Train a tiny MonodAnchored closure on CPU (direct regression on the true
    ffe) and distill it -- an end-to-end demo on a real nn.Module. This is a
    gate self-test, not a science claim (no dynamics, no real data)."""
    import math
    import torch
    from torch import nn

    torch.manual_seed(seed)
    K_TRUE = 8.0e-5

    class MonodAnchored(nn.Module):
        def __init__(self, eps=0.25):
            super().__init__()
            self.log_k = nn.Parameter(torch.tensor(math.log(5.0e-5)))
            self.net = nn.Sequential(nn.Linear(1, 16), nn.Tanh(), nn.Linear(16, 1), nn.Tanh())
            self.eps = eps

        def forward(self, dfe):
            k = torch.exp(self.log_k)
            monod = dfe / (dfe + k)
            feat = torch.log10(dfe.clamp_min(1e-9)) + 4.0
            corr = 1.0 + self.eps * self.net(feat.unsqueeze(-1)).squeeze(-1)
            return (monod * corr).clamp(0.0, 1.0)

    dfe = torch.logspace(-5, -3, 3000, dtype=torch.float64)
    target = (dfe / (dfe + K_TRUE)) ** 0.7
    net = MonodAnchored().double()
    opt = torch.optim.Adam(net.parameters(), lr=5e-3)
    for _ in range(1500):
        opt.zero_grad()
        loss = ((net(dfe) - target) ** 2).mean()
        loss.backward()
        opt.step()
    y = sample_closure(net, dfe.numpy())
    v = distill(dfe.numpy(), y, seed=seed)
    tag = "PASS" if v.passed else "FAIL"
    print(f"  [{tag}] trained MonodAnchored  incl={v.monod_inclusion:.2f} "
          f"k_hat={v.k_hat:.2e} (learned log_k -> {math.exp(net.log_k.item()):.2e}) "
          f"r2_in={v.r2_in:.3f}")
    print(f"         {v.reason}")
    return {"verdict": v.as_dict(), "learned_k": math.exp(net.log_k.item()),
            "k_true": K_TRUE}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--npz", type=str, default=None,
                    help="distill a real (dfe, y) closure dump: keys 'dfe','y'[,'groups']")
    ap.add_argument("--train-demo", action="store_true",
                    help="train a tiny MonodAnchored on CPU and distill it")
    ap.add_argument("--out", type=str, default=None, help="write verdict JSON here")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    result: dict
    if args.npz:
        d = np.load(args.npz)
        groups = d["groups"] if "groups" in d else None
        v = distill(d["dfe"], d["y"], groups=groups, seed=args.seed)
        print(("PASS" if v.passed else "FAIL"), "-", v.reason)
        result = v.as_dict()
    elif args.train_demo:
        print("== symbolic-distillation gate: trained-closure demo ==")
        result = _train_demo(args.seed)
    else:
        print("== symbolic-distillation gate: analytic self-test panel ==")
        result = _selftest_panel(args.seed)

    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2))
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
