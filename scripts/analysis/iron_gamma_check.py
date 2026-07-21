"""
gamma-check (UDE de-risk): does SPATIAL STRUCTURE raise the identifiability gamma = sigma_min of the
biological sensitivity G = d(H x)/d(theta) for the iron pair (source magnitude S, scavenging k)?

If the 0-D box (which sees only a homogenized ~mean) has gamma=0 along the sloppy direction, but a
transport-coupled SECTION has gamma>0, then a spatial UDE has a real identifiability payoff. If not,
even a perfect UDE cannot recover the source magnitude and the honest limit stands.

Minimal model: 1-D advective-scavenging iron, N cells. Flow enters cell 0 (upstream Fe=0), advects
0->1->...->N-1 at volume flux psi, source S into cell 0, scavenging k everywhere. Pure numpy, CPU.
"""
import numpy as np

N = 10
V = 1.0e15      # cell volume (m^3)
psi = 6.0e14    # advective volume flux between cells (m^3/yr)
S0 = 20e9       # source (mol/yr)
k0 = 1/50.      # scavenging (1/yr)

def steady_profile(S, k):
    # cell i: psi*Fe_{i-1} - (psi + k*V)*Fe_i + S*delta_{i0} = 0 ; Fe_{-1}=0
    a = psi/(psi + k*V)               # downstream attenuation factor
    Fe0 = S/(psi + k*V)
    return Fe0 * a**np.arange(N)      # exponentially decaying profile

def sensitivity(S, k, eps=1e-4):
    # d(log Fe_i)/d(log S), d(log Fe_i)/d(log k) by finite difference
    base = np.log(steady_profile(S, k))
    dS = (np.log(steady_profile(S*(1+eps), k)) - base)/eps
    dk = (np.log(steady_profile(S, k*(1+eps))) - base)/eps
    return np.stack([dS, dk], axis=1)   # [N, 2]

J = sensitivity(S0, k0)   # [N,2] per-cell log-sensitivity to (logS, logk)

def gamma(H):
    G = H @ J                          # [n_obs, 2]
    s = np.linalg.svd(G, compute_uv=False)
    smin = s[-1] if len(s) >= 2 else 0.0
    return float(smin), s

# Observation operators
H_mean    = np.ones((1, N))/N                                   # box sees a single ~mean value
H_section = np.eye(N)                                           # full spatial section (per-cell)
D = np.zeros((N-1, N))                                          # first-difference (gradient) operator
for i in range(N-1): D[i, i], D[i, i+1] = -1.0, 1.0
H_grad    = D

print("="*70)
print("gamma-check: sigma_min of biological sensitivity G for (S, k)")
print("="*70)
for name, H in [("mean-only (0-D box)", H_mean), ("full section (spatial)", H_section), ("gradient-only", H_grad)]:
    g, s = gamma(H)
    print(f"  {name:24s} sigma = {np.array2string(s, precision=3)}  -> gamma(sigma_min) = {g:.3e}")

print("-"*70)
gm,_ = gamma(H_mean); gs,_ = gamma(H_section); gg,_ = gamma(H_grad)
print(f"""  READ:
  - mean-only gamma = {gm:.2e}  (the 0-D box: rank-1 G -> the source/scav sloppy direction is UNIDENTIFIED)
  - full section gamma = {gs:.2e}  (spatial profile: the downstream decay pins k, the magnitude pins S/(psi+kV);
    together they identify BOTH -> gamma lifts OFF ZERO by {gs/max(gm,1e-30):.1e}x)
  - gradient-only gamma = {gg:.2e}  (the pure gradient is S-INVARIANT: d(logFe)/d(logS)=1 for all cells, so
    differencing kills the S column. The gradient pins k but NOT S alone.)

  CONCLUSION: it is the full SECTION (absolute concentrations at multiple advected points), not the
  gradient in isolation, that breaks the iron degeneracy. A spatial UDE that represents the section
  profile raises identifiability from gamma=0 to gamma>0 -> the UDE program has a real payoff, PROVIDED
  the model is spatial and the loss uses the per-cell section (not a basin mean). A 0-D box cannot; this
  is the surrogate gap, quantified.""")
