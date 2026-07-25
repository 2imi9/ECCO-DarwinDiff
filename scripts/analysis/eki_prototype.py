"""
EKI / Calibrate-Emulate-Sample prototype for the iron source<->scavenging degeneracy.

Demonstrates the #187 near-term bundle on the single-box iron model (the same model as
`iron_degeneracy_math.py`), so it also cross-checks the analytical rank-1 Fisher result
with a sampling-based estimator:

  Lever 2 (EKI): ensemble-Kalman-inversion returns a POSTERIOR ensemble, not a saddle-prone
                 point estimate — it never inverts a Hessian, so the theta* saddle problem
                 (issue #120) cannot bite it.
  Lever 1 (Fisher-basis + prior): the posterior collapses onto the STIFF ratio direction
                 and stays wide along the SLOPPY residence-time direction; an informative
                 prior on residence time (Black 2020) then bounds the sloppy direction.

Model (single-box steady state, V normalised to 1):
    Fe* = S / k          (mean concentration, the one observable)
    tau = 1 / k          (residence time, the sloppy coordinate)
Parameters u = (ln S, ln k). Observable G(u) = ln Fe* = ln S - ln k.
Stiff direction is (1,-1)/sqrt(2) (raise S, lower k -> Fe* up); sloppy is (1,1)/sqrt(2)
(raise S AND k together -> ratio fixed -> Fe* invariant, tau changes).

Pure numpy, CPU, seconds. Deterministic (fixed RNG seed) so verify_run can gate it.
"""
import numpy as np

from eki_core import eki  # shared, unit-tested EKI core (scripts/analysis/eki_core.py)

RNG = np.random.default_rng(0)

# ---- truth + observation (FeMIP mean concentration) ----
FE_OBS = 0.58                       # nM, Tagliabue 2016 ensemble-mean DFe
LOG_FE_OBS = np.log(FE_OBS)
SIGMA_OBS = 0.24                    # log-space obs noise (~24% CV, the FeMIP concentration spread)
J = 400                            # ensemble size
N_ITER = 30                        # EKI iterations (linear G -> converges fast)


def summarise(u, label):
    S, k = np.exp(u[0]), np.exp(u[1])
    ratio = S / k                                        # = Fe*, the stiff/observed combo
    tau = 1.0 / k                                        # residence time, the sloppy coord
    cv = lambda x: float(np.std(x) / np.abs(np.mean(x)))
    print(f"  [{label}]")
    print(f"    Fe* (ratio S/k): mean={np.mean(ratio):.3f}  CV={cv(ratio)*100:5.1f}%   <- STIFF (pinned by data)")
    print(f"    tau (1/k)      : mean={np.mean(tau):.3f}  CV={cv(tau)*100:5.1f}%   <- SLOPPY (free direction)")
    # posterior covariance principal axis in (lnS, lnk)
    C = np.cov(u)
    w, V = np.linalg.eigh(C)
    sloppy_vec = V[:, np.argmax(w)]
    align = abs(float(sloppy_vec @ (np.array([1, 1]) / np.sqrt(2))))
    print(f"    posterior principal axis = ({sloppy_vec[0]:+.2f},{sloppy_vec[1]:+.2f}); "
          f"|align with sloppy (1,1)/sqrt2| = {align:.3f}")
    return dict(ratio_cv=cv(ratio), tau_cv=cv(tau), tau_mean=float(np.mean(tau)), sloppy_align=align)


# ---- wide prior ensemble: ~140x span in both S and k (the FeMIP input range) ----
u0 = np.vstack([
    RNG.normal(LOG_FE_OBS, 2.0, J),    # ln S
    RNG.normal(0.0, 2.0, J),           # ln k
])

print("=" * 74)
print("EKI prototype: iron source<->scavenging degeneracy (single-box)")
print("=" * 74)
print("\nPART 1 - concentration only (Lever 2: EKI posterior, no Hessian inverted)")
G_conc = lambda u: (u[0] - u[1])[None, :]                # ln Fe* = lnS - lnk
post1 = eki(np.array([LOG_FE_OBS]), np.array([[SIGMA_OBS**2]]), G_conc, u0, n_iter=N_ITER, rng=RNG)
r1 = summarise(post1, "concentration only")
print("    => the observable pins the RATIO; residence time roams the sloppy ridge (the FeMIP degeneracy).")

print("\nPART 2 - Lever 1: add an informative prior on residence time (Black 2020 upper-ocean band)")
# Black 2020 surface Fe residence ~10-100 d; in the box's normalised time unit take a log-normal
# prior centred at tau0 with ~0.4 log-sd. Impose it as a SECOND (pseudo-)observation on ln tau=-lnk.
TAU0 = 1.0
LOG_TAU_PRIOR, SIGMA_TAU = np.log(TAU0), 0.4
G_aug = lambda u: np.vstack([u[0] - u[1], -u[1]])        # [ln Fe*, ln tau]
y_aug = np.array([LOG_FE_OBS, LOG_TAU_PRIOR])
gamma_aug = np.diag([SIGMA_OBS**2, SIGMA_TAU**2])
post2 = eki(y_aug, gamma_aug, G_aug, u0, n_iter=N_ITER, rng=RNG)
r2 = summarise(post2, "concentration + residence-time prior")
print("    => the ratio stays pinned AND the residence time is now bounded to the prior — the")
print("       identifiable direction is estimated, the sloppy one is prior-controlled, not pretended-known.")

# ---- verification block (verify_run-gateable assertions) ----
print("\n" + "=" * 74)
print("VERIFICATION")
print("=" * 74)
ok_ridge = r1["ratio_cv"] < 0.05 and r1["tau_cv"] > 5 * r1["ratio_cv"]
ok_align = r1["sloppy_align"] > 0.9
ok_prior = r2["tau_cv"] < r1["tau_cv"]
print(f"  ratio pinned & tau roams (degeneracy reproduced): {ok_ridge}  "
      f"(ratio CV {r1['ratio_cv']*100:.2f}% << tau CV {r1['tau_cv']*100:.1f}%)")
print(f"  posterior sloppy axis aligns with analytic (1,1)/sqrt2: {ok_align}  (align={r1['sloppy_align']:.3f})")
print(f"  residence-time prior tightens the sloppy direction: {ok_prior}  "
      f"(tau CV {r1['tau_cv']*100:.1f}% -> {r2['tau_cv']*100:.1f}%)")
all_ok = ok_ridge and ok_align and ok_prior
print(f"\n  ALL CHECKS PASS: {all_ok}")

# ---- figure ----
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    INK, MUTED = "#1F2328", "#6b7580"
    TEAL, AMBER = "#0B7A75", "#C77400"
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.2), dpi=200, sharex=True, sharey=True)
    xs = np.linspace(-4.5, 3.5, 50)
    for ax, post, col, title in [
        (axes[0], post1, TEAL, "Concentration only\nposterior rides the sloppy ridge"),
        (axes[1], post2, AMBER, "+ residence-time prior\nsloppy direction bounded"),
    ]:
        ax.plot(xs, xs - LOG_FE_OBS, color="#B23A48", lw=1.6, zorder=1,
                label=r"ridge  $\ln S-\ln k=\ln\,$Fe*")
        ax.scatter(post[0], post[1], s=8, color=col, alpha=0.5, zorder=3, edgecolors="none")
        ax.set_title(title, fontsize=11, color=INK, loc="left", pad=8)
        ax.set_xlabel(r"$\ln S$  (source)", fontsize=10, color=MUTED)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.spines["left"].set_color("#d0d4d8"); ax.spines["bottom"].set_color("#d0d4d8")
        ax.tick_params(length=0, labelsize=9); ax.grid(True, color="#eceef0", zorder=0)
        ax.legend(loc="upper left", frameon=False, fontsize=8.5)
    axes[0].set_ylabel(r"$\ln k$  (scavenging)   —   $\ln\tau=-\ln k$", fontsize=10, color=MUTED)
    fig.suptitle("EKI posterior for the iron degeneracy: the ratio is identified, residence time is not",
                 fontsize=12.5, color=INK, fontweight="bold", x=0.02, ha="left", y=0.99)
    fig.text(0.02, -0.01, "Ensemble-Kalman inversion of the single-box iron model. Left: concentration alone "
             "pins the source/scavenging ratio (points hug the ridge) but leaves residence time free along it. "
             "Right: an\nindependent residence-time prior localises the sloppy direction — the identifiable "
             "direction is estimated, the sloppy one is prior-controlled. No Hessian is inverted (saddle-robust).",
             fontsize=8.4, color=MUTED, va="top")
    plt.tight_layout(rect=[0, 0.05, 1, 0.96])
    out = "docs/figures/fig_eki_iron_degeneracy.png"
    plt.savefig(out, bbox_inches="tight", facecolor="white")
    print(f"\n  wrote {out}")
except Exception as e:
    print(f"\n  (figure skipped: {e})")
