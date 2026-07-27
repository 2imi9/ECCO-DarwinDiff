"""Forward-model feasibility probe: can an environment-dependent rain ratio
reproduce Darwin's regional PIC:POC spread at a SINGLE set of params?

Context (2026-06-24 deep-research synthesis,
``docs/research_notes/2026-06-24_rpicpoc_observability_deep_research.md``):
R_PICPOC is box-scale unidentifiable because the box's calcite is a RIGID readout
(``PIC/POC = R_PICPOC`` everywhere) while Darwin's realized rain ratio varies ~100x
by region (corrected targets: eqpac 0.033 / natl 0.68 / SO 0.0067). The recommended
fix (option 3) is to make the rain ratio a smooth function of environment,
``R_PICPOC_eff = R_PICPOC * g(T, Omega_c)`` — standard in CESM/PISCES/CMIP
(Ridgwell 2007; Krumhardt CESM).

This probe tests the NECESSARY CONDITION *before* writing any model code or running a
fit: given each AOI's ACTUAL per-cell (T, Omega_c) fields from the Darwin caches, does
there exist a single (R_PICPOC, gating-shape) that reproduces the per-cell Darwin
PIC:POC across all three AOIs? It uses the exact steady-state identity (cocco OFF,
W_SINK_PIC = W_SINK):

    PIC_1 / POC_1  =  R_PICPOC * g(T, Omega_c)         (mort_total cancels)

so the surrogate is faithful for the rain ratio (the mort-independence is exactly why
the ratio observable identifies R_PICPOC orthogonally to the iron pair — see
docs/findings/rpicpoc_ratio_structural.md). Two gating forms are compared to isolate
whether the calcite saturation state is the load-bearing second driver:

    (A) T-window only:        g = exp(-0.5*((T - T_opt)/T_width)^2)
    (B) T-window x saturation: g = (A) * (Omega_c/(Omega_c + K_omega))^p_omega

A pure symmetric T-window CANNOT order eqpac(25C) above SO(2C) when the cocco optimum
sits near natl(~10C) — the analytic motivation for adding Omega_c (eqpac warm/high-Om,
SO cold/low-Om). The probe quantifies that.

GO  = form (B) drives every AOI's mean realized ratio within ~40% (Cal band) of target
      with physically-sane shape params -> implement option 3 and run the H200 fit.
NO-GO = even (B) cannot -> env-gating is insufficient at box scale (escalate to a
      cocco PFT / cluster), which would itself be the reportable result.

Run:  uv run python scripts/probe_env_rain_ratio.py
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import torch

from darwindiff.carbonate import calcite_saturation
from darwindiff.safe_load import safe_torch_load

CACHE_DIR = Path(os.environ.get("DARWIN_DATA_ROOT", r"D:\ecco_darwin_v5")) / "cache"
CACHES = {
    "eqpac": "eqpac_targets_equatorial_pacific.pt",
    "natlsubpolar": "eqpac_targets_north_atlantic_subpolar.pt",
    "southernoceanpac": "eqpac_targets_southern_ocean_pacific.pt",
}
# Corrected Darwin surface PIC:POC targets (HEAD.md / forward-model-fidelity-roadmap,
# 2026-06-24; the prior natl 0.9 / SO 1.4 were mislabeled recovered-degenerate values).
TARGETS = {"eqpac": 0.033, "natlsubpolar": 0.68, "southernoceanpac": 0.0067}
CAL_BAND = 0.40  # relative-error band that counts as "Cal-grade" recovery


def _load_aoi(key: str, fname: str) -> dict | None:
    path = CACHE_DIR / fname
    if not path.exists():
        return None
    cache = safe_torch_load(path)
    sst = np.asarray(cache["sst"], dtype=np.float32)
    sss = np.asarray(cache["sss"], dtype=np.float32)
    dic = np.asarray(cache["dic_binned"], dtype=np.float32)
    alk = np.asarray(cache["alk_binned"], dtype=np.float32)
    pic = np.asarray(cache["pic_binned"], dtype=np.float32)
    poc = np.asarray(cache["poc_binned"], dtype=np.float32)
    mask = (
        np.isfinite(sst) & np.isfinite(sss) & np.isfinite(dic) & np.isfinite(alk)
        & np.isfinite(pic) & np.isfinite(poc) & (poc > 0) & (pic > 0)
    )
    T = torch.tensor(sst[mask])
    S = torch.tensor(sss[mask])
    omega = calcite_saturation(
        torch.tensor(dic[mask]), torch.tensor(alk[mask]), T, S
    )["omega_c"]
    poc_t = torch.tensor(poc[mask])
    pic_t = torch.tensor(pic[mask])
    # Canonical AOI ratio = ratio-of-means mean(PIC)/mean(POC) (matches
    # box_vs_darwin_fidelity.py and the corrected TARGETS), NOT mean-of-per-cell-
    # ratios (which blows up where POC -> 0; the SO has such cells). POC also serves
    # as the cell weight for the realized rain ratio, since at steady state
    # POC_cell proportional to mort_cell and ratio-of-means = R_PICPOC*<g>_(w=mort).
    return {"key": key, "T": T, "omega": omega, "poc": poc_t,
            "darwin_rom": float(pic_t.sum() / poc_t.sum()),
            "target": TARGETS[key], "n": int(mask.sum())}


def _gate(T, omega, p, use_omega: bool):
    """g(T, Omega_c). ``p`` = unconstrained params; reparam to physical ranges."""
    t_opt = 30.0 * torch.sigmoid(p[0])          # 0..30 C
    t_width = 1.0 + torch.nn.functional.softplus(p[1])   # >1 C
    g = torch.exp(-0.5 * ((T - t_opt) / t_width) ** 2)
    if use_omega:
        k_omega = torch.nn.functional.softplus(p[2]) + 1e-3
        p_omega = 4.0 * torch.sigmoid(p[3])     # 0..4
        g = g * (omega / (omega + k_omega)) ** p_omega
    return g


# R_PICPOC learnable bound (carroll6.PARAM_BOUNDS row 5). The probe MUST honour it:
# an unconstrained base rate hides whether the spread is reproducible by a base rate
# the optimizer can actually reach. g peaks at 1 (T=T_opt, omega large), so the peak
# realized rain ratio is <= R_PICPOC <= RPP_MAX.
RPP_MIN, RPP_MAX = 0.005, 1.5


def _rpp(raw):
    return RPP_MIN + (RPP_MAX - RPP_MIN) * torch.sigmoid(raw)


def _g_norm(aois: list[dict], shape, use_omega: bool):
    """Model-faithful normalization G_NORM = POC-weighted arithmetic mean of g over
    the pooled field. With R_PICPOC_eff = R_PICPOC*g/G_NORM, the pooled-mean realized
    rain ratio equals R_PICPOC, so R_PICPOC is a physical, in-bound base rate (the
    field-mean PIC:POC) rather than a peak or geomean coefficient."""
    gs = torch.cat([_gate(a["T"], a["omega"], shape, use_omega) for a in aois])
    ws = torch.cat([a["poc"] for a in aois])
    return (gs * ws).sum() / ws.sum()


def _realized_rom(a: dict, rpp, shape, use_omega: bool, lng_mean):
    """AOI realized ratio-of-means = R_PICPOC * POC-weighted mean of (g / G_NORM).

    g is normalized by the pooled-field geometric mean G_NORM = exp(lng_mean) — a
    GLOBAL constant (not per-AOI, which would erase the cross-AOI spread). This lets
    g/G_NORM exceed 1, so R_PICPOC is the geomean-scale base rate (~Carroll 0.04) and
    stays inside the learnable bound while the gating carries the regional spread.
    This is exactly the model parametrization: R_PICPOC_eff = R_PICPOC * g / G_NORM.
    """
    gnorm = _gate(a["T"], a["omega"], shape, use_omega) / torch.exp(lng_mean)
    return rpp * (gnorm * a["poc"]).sum() / a["poc"].sum()


def _fit(aois: list[dict], use_omega: bool, steps: int = 8000) -> dict:
    """Fit (base, shape) to the per-AOI ratio-of-means targets, log-space.

    The cross-AOI RATIOS depend only on the shape (base is a pure scale), so the base
    is fit unbounded with a peak-1 gate; the in-bound R_PICPOC is then the geomean-
    convention base ``base * G_NORM`` (the model uses R_PICPOC_eff = R_PICPOC*g/G_NORM,
    so realized is invariant and R_PICPOC lands ~Carroll-scale). GO requires both the
    ratios matched (3/3 Cal) AND the geomean base inside the learnable bound.
    """
    log_base = torch.zeros((), requires_grad=True)   # peak-1 base = exp(log_base)
    shape = torch.zeros(4, requires_grad=True)
    opt = torch.optim.Adam([log_base, shape], lr=0.02)
    tgt = torch.tensor([a["target"] for a in aois])
    for _ in range(steps):
        opt.zero_grad()
        base = torch.exp(log_base)
        realized = torch.stack(
            [base * (_gate(a["T"], a["omega"], shape, use_omega) * a["poc"]).sum()
             / a["poc"].sum() for a in aois])
        loss = ((torch.log(realized + 1e-12) - torch.log(tgt)) ** 2).mean()
        loss.backward()
        opt.step()
    with torch.no_grad():
        base = torch.exp(log_base)
        g_norm = float(_g_norm(aois, shape, use_omega))
        per_aoi = []
        for a in aois:
            g = _gate(a["T"], a["omega"], shape, use_omega)
            mean_real = float(base * (g * a["poc"]).sum() / a["poc"].sum())
            rel = abs(mean_real - a["target"]) / a["target"]
            per_aoi.append({"key": a["key"], "mean_real": mean_real,
                            "target": a["target"], "rel": rel,
                            "cal": rel <= CAL_BAND})
        rpp_inbound = float(base) * g_norm   # geomean-convention base = model R_PICPOC
        t_opt = float(30.0 * torch.sigmoid(shape[0]))
        t_width = float(1.0 + torch.nn.functional.softplus(shape[1]))
        info = {"rpp": float(base), "rpp_inbound": rpp_inbound, "g_norm": g_norm,
                "in_bound": RPP_MIN <= rpp_inbound <= RPP_MAX,
                "t_opt": t_opt, "t_width": t_width,
                "loss": float(loss), "per_aoi": per_aoi}
        if use_omega:
            info["k_omega"] = float(torch.nn.functional.softplus(shape[2]) + 1e-3)
            info["p_omega"] = float(4.0 * torch.sigmoid(shape[3]))
        return info


def _report(name: str, info: dict) -> bool:
    print(f"\n=== {name} ===")
    shape_str = f"T_opt={info['t_opt']:.2f}C  T_width={info['t_width']:.2f}C"
    if "k_omega" in info:
        shape_str += f"  K_omega={info['k_omega']:.3f}  p_omega={info['p_omega']:.2f}"
    print(f"  {shape_str}  (log-MSE={info['loss']:.3f})")
    print(f"  G_NORM={info['g_norm']:.4g}  R_PICPOC(field-mean conv.)"
          f"={info['rpp_inbound']:.4f}  {'[in bound]' if info['in_bound'] else '[OUT OF BOUND]'}")
    print(f"  {'AOI':<18}{'realized':>10}{'target':>10}{'rel.err':>10}  band")
    n_cal = 0
    for r in info["per_aoi"]:
        n_cal += r["cal"]
        print(f"  {r['key']:<18}{r['mean_real']:>10.4f}{r['target']:>10.4f}"
              f"{r['rel']:>9.0%}   {'Cal' if r['cal'] else 'MISS'}")
    ratios_ok = n_cal == len(info["per_aoi"])
    go = ratios_ok and info["in_bound"]
    print(f"  -> {n_cal}/{len(info['per_aoi'])} AOIs within {CAL_BAND:.0%}; "
          f"base {'in' if info['in_bound'] else 'OUT OF'} bound "
          f"=> {'GO' if go else 'partial/NO-GO'}")
    return go


def main() -> int:
    aois = [a for k, f in CACHES.items() if (a := _load_aoi(k, f)) is not None]
    if not aois:
        print(f"No caches found under {CACHE_DIR}. Set DARWIN_DATA_ROOT.")
        return 1
    print("Env-dependent rain-ratio feasibility probe")
    print(f"cache dir: {CACHE_DIR}")
    print(f"\n{'AOI':<18}{'cells':>8}{'mean T':>9}{'mean Om_c':>11}"
          f"{'darwin_rom':>12}{'target':>9}")
    for a in aois:
        print(f"{a['key']:<18}{a['n']:>8}{float(a['T'].mean()):>9.2f}"
              f"{float(a['omega'].mean()):>11.2f}{a['darwin_rom']:>12.4f}"
              f"{a['target']:>9.4f}")

    info_a = _fit(aois, use_omega=False)
    info_b = _fit(aois, use_omega=True)
    go_a = _report("(A) T-window only", info_a)
    go_b = _report("(B) T-window x Omega_c saturation", info_b)

    print("\n" + "=" * 60)
    print("VERDICT")
    if go_b and not go_a:
        print("  Omega_c is the load-bearing second driver (as predicted): GO on")
        print("  form (B). Implement R_PICPOC_eff = R_PICPOC*g(T,Omega_c) and fit.")
    elif go_b and go_a:
        print("  Both forms reproduce the spread: GO. Prefer (A) (fewer knobs) unless")
        print("  the per-cell pattern needs Omega_c.")
    elif go_a and not go_b:
        print("  T-window alone suffices: GO on form (A).")
    else:
        print("  NO-GO: even (B) cannot reproduce the spread from (T, Omega_c).")
        print("  Env-gating is insufficient at box scale -> escalate (cocco PFT /")
        print("  cluster). That null is itself the reportable result.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
