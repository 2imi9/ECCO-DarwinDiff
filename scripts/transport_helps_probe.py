"""Go/no-go probe: does prescribed transport let a differentiable fit predict
held-out iron that a transport-free local box structurally cannot?

This is the cheapest decisive experiment from
``docs/research_notes/2026-07-07_param_conditioned_emulator_decision.md`` (Section 4),
run on the merged Track-2 code (``transport.py`` + ``integrators.py``), CPU-only,
with **zero new GCM runs**. It isolates the ONE variable that separates route (B)
(the mechanistic UDE) from the failed Track-1 0-D box: spatial transport.

WHAT IT TESTS (a faithful miniature of the STATUS.md #163 surrogate gap)
-----------------------------------------------------------------------
The Track-1 held-out test (hold out 30% of iron cells, predict DFe there) returns
NEGATIVE R^2 because the 0-D box homogenizes -- a cell's iron is set purely by its
local forcing, so the box has no way to produce the spatial structure that real
iron gets from *transport* (mixing/advection redistributing iron from where it
enters). Here, in a single water column:

  * A surface dust source injects iron into the top layer only.
  * TRUTH is generated WITH vertical mixing (``kz_true > 0``), so iron is carried
    downward -- the deep-layer iron is a TRANSPORT product, coupling the layers.
  * We hold out a random ~30% of layers, fit the one identifiable iron parameter
    (``alpfe``) to the observed layers by gradient descent THROUGH the forward
    model, and score held-out-layer R^2.

  - Model A "local box" (transport OFF, ``kz=0``): each layer is independent, so
    deep layers get no iron -> it cannot reproduce the mixing-fed profile ->
    held-out R^2 <= 0. This is the surrogate gap.
  - Model B "transport"  (transport ON,  ``kz=kz_true``): the coupled profile is
    representable -> held-out R^2 > 0.

DECISION RULE (from the note):
  R^2_B > 0 (where R^2_A <= 0)  ->  transport is the fix; route (B) green-lit.
  R^2_B <= 0                    ->  spatial coupling alone is insufficient here.

HONESTY GUARDRAIL (memory: track2-feasibility-not-realdata): this is a SYNTHETIC
self-twin *capacity* demonstration on a vertical 1-D column, NOT the real E2 gate
(which needs real held-out GEOTRACES cells + horizontal transport). It shows
transport supplies structure the box lacks -- a necessary precondition for E2, not
E2 itself.
"""
from __future__ import annotations

import argparse

import torch

from darwindiff import carroll6
from darwindiff.carroll6 import P, PHI_DUST
from darwindiff.integrators import integrate
from darwindiff.transport import column_tendency


def _r2(pred: torch.Tensor, truth: torch.Tensor) -> float:
    """Coefficient of determination R^2 = 1 - SS_res/SS_tot (mean baseline)."""
    ss_res = ((pred - truth) ** 2).sum()
    ss_tot = ((truth - truth.mean()) ** 2).sum()
    return (1.0 - ss_res / ss_tot).item()


def _steady_dfe(alpfe, *, kz, dust, params0, z, dz, dt, n_steps):
    """Integrate a single column to a fixed horizon and return the DFe profile.

    ``alpfe`` is the (possibly grad-requiring) iron parameter; everything else is
    fixed at Carroll values. Returns DFe over the Z layers.
    """
    params = params0.clone()
    params = params.index_copy(0, torch.tensor([P.alpfe]), alpfe.reshape(1))
    # state: [Z, 5] tracers [DFe, Ps, Pl, POC, PIC]; small positive IC
    state0 = torch.full((z, 5), 0.05)

    def f(t, x):
        return column_tendency(x, params, kz=kz, dz=dz, w=0.0, dust=dust)

    xN = integrate(f, state0, dt=dt, n_steps=n_steps, method="rk4")
    return xN[..., 0]  # DFe over layers


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--z", type=int, default=16, help="number of layers")
    ap.add_argument("--dz", type=float, default=25.0)
    ap.add_argument("--dt", type=float, default=0.5)
    ap.add_argument("--nsteps", type=int, default=250)
    ap.add_argument("--kz-true", type=float, default=50.0,
                    help="true vertical diffusivity (m^2/day); must mix several "
                         "layers over the horizon: sqrt(kz*T) >~ a few*dz")
    ap.add_argument("--holdout", type=float, default=0.30)
    ap.add_argument("--noise", type=float, default=0.02, help="rel. obs noise on DFe")
    ap.add_argument("--iters", type=int, default=80)
    ap.add_argument("--lr", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    torch.set_default_dtype(torch.float64)

    params0 = carroll6.CARROLL_VALUES.clone().double()
    alpfe_true = params0[P.alpfe].clone()

    # Surface-only dust source: iron enters the top layer, nothing below.
    # Shape [Z] so it aligns elementwise with the per-layer DFe.
    dust = torch.zeros(args.z).double()
    dust[0] = float(PHI_DUST) * args.z  # concentrate the column's dust at the surface

    # --- Generate TRUTH with transport ON (deep iron is a mixing product) ------
    with torch.no_grad():
        dfe_truth = _steady_dfe(
            alpfe_true, kz=args.kz_true, dust=dust, params0=params0,
            z=args.z, dz=args.dz, dt=args.dt, n_steps=args.nsteps,
        )
        obs = dfe_truth * (1.0 + args.noise * torch.randn(args.z).double())

    # --- Random held-out layer mask (analog of held-out GEOTRACES cells) -------
    perm = torch.randperm(args.z)
    n_test = max(1, int(round(args.holdout * args.z)))
    test_idx = perm[:n_test].sort().values
    train_idx = perm[n_test:].sort().values

    truth_cv = (dfe_truth.std() / dfe_truth.mean().abs()).item()
    print(f"# truth DFe: mean={dfe_truth.mean():.4g}  CV={truth_cv:.3g}  "
          f"(depth-structured by mixing; box target CV in STATUS.md ~4e-5)")
    print(f"# layers Z={args.z}  held-out={n_test} {test_idx.tolist()}  "
          f"kz_true={args.kz_true}  noise={args.noise}")
    print(f"# alpfe_true (Carroll) = {alpfe_true.item():.4g}\n")

    def fit_and_score(kz, label):
        """Fit alpfe on TRAIN layers by autograd through the forward model with
        the given kz, then score held-out-layer R^2."""
        alpfe = torch.tensor(0.02, requires_grad=True)  # deliberately off Carroll
        opt = torch.optim.Adam([alpfe], lr=args.lr)
        for it in range(args.iters):
            opt.zero_grad()
            pred = _steady_dfe(alpfe, kz=kz, dust=dust, params0=params0,
                               z=args.z, dz=args.dz, dt=args.dt, n_steps=args.nsteps)
            loss = ((pred[train_idx] - obs[train_idx]) ** 2).mean()
            loss.backward()
            opt.step()
            with torch.no_grad():
                alpfe.clamp_(1e-4, 5.0)
            if it % 20 == 0 or it == args.iters - 1:
                print(f"  [{label:10s}] iter {it:3d}  loss={loss.item():.3e}  "
                      f"alpfe={alpfe.item():.4g}", flush=True)
        with torch.no_grad():
            pred = _steady_dfe(alpfe, kz=kz, dust=dust, params0=params0,
                               z=args.z, dz=args.dz, dt=args.dt, n_steps=args.nsteps)
        r2_test = _r2(pred[test_idx], dfe_truth[test_idx])
        r2_train = _r2(pred[train_idx], obs[train_idx])
        grad_flows = alpfe.grad is not None
        print(f"[{label:10s}] fit alpfe={alpfe.item():.4g}  "
              f"train R^2={r2_train:+.3f}  HELD-OUT R^2={r2_test:+.3f}  "
              f"(grad flowed: {grad_flows})")
        return r2_test

    r2_a = fit_and_score(kz=0.0, label="A local")      # transport OFF
    r2_b = fit_and_score(kz=args.kz_true, label="B transport")  # transport ON

    print()
    verdict = "PASS" if (r2_b > 0.0 and r2_a <= r2_b) else "FAIL"
    print(f"=== VERDICT: {verdict} ===")
    print(f"    local-box held-out R^2 = {r2_a:+.3f}   (the surrogate gap: <= 0 expected)")
    print(f"    transport  held-out R^2 = {r2_b:+.3f}   (route B: > 0 green-lights Phase 1)")
    if verdict == "PASS":
        print("    -> transport supplies the spatial structure the local box lacks.")
        print("       SYNTHETIC vertical-1D capacity result, NOT the real E2 gate.")
    else:
        print("    -> transport alone did not help in this setup; inspect / redesign.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
