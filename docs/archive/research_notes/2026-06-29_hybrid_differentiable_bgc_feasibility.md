# Making Darwin's biogeochemistry differentiable: what we face, what we change, what we plan

*2026-06-29. A plain-language feasibility note. Written for a reader who is not deep in machine learning; the few technical terms that matter are defined where they appear.*

---

## In one paragraph

The reason calibrating ECCO-Darwin is slow is that the model is **not differentiable**: you cannot ask it "if I nudge this parameter, which way does the error move?" and get an instant answer. Our first project worked *around* that by fitting a cheap stand-in model. This note is about a more direct option: **make Darwin's biogeochemistry itself differentiable**, by re-writing its equations in a framework that computes those "which way" answers automatically, and replacing the few uncertain pieces with small neural networks. We built a small test to check whether this is even executable before committing to it. **It is**: all four core capabilities work on the real equations at small scale. The one known risk — numerical drift over long runs — is real but has a standard fix.

---

## What we face (the problem)

ECCO-Darwin is calibrated through six biogeochemical parameters (the "Carroll-6"). Today they are tuned by **Green's functions**: you run the full model once for each parameter you want to nudge, compare to observations, and infer a direction. Each gradient (each "which way should I move?") costs roughly **seven full model runs**. That is expensive, and it is the symptom of a deeper fact:

- **The model is not differentiable.** *Differentiable* means you can compute a **gradient** — the exact slope of "error vs. each parameter" — in a single backward pass instead of by trial and error. Darwin's biogeochemistry, as written (large Fortran code, coupled to ocean circulation), does not expose that slope. So calibration is reduced to expensive guess-and-check.
- ECCO **does** have an efficient gradient tool for the ocean *physics* (the **adjoint** / 4D-Var). It does **not** have one for the *biogeochemistry*. That missing piece is the entire reason this project exists.

## What we change (the idea)

Instead of building a cheap substitute for Darwin (our first project — a 0-D "box" — which works but cannot represent spatial structure), we **make the real biogeochemistry differentiable**:

1. **Re-write the biogeochemical equations in an autograd framework** (PyTorch). *Autograd* = the computer tracks every arithmetic operation and can therefore hand back the exact gradient automatically. Once the equations live in this framework, "which way to move each parameter" is one cheap backward pass — no seven-runs-per-gradient.
2. **Replace only the *uncertain* pieces with small neural networks**, and keep all the *known* physics as real equations. A *neural network* here is just a small flexible function with adjustable weights; a *closure* is a sub-formula that stands in for a process we do not fully know (for example, how strongly iron limits growth). This mixed object — known equations + a learned piece, trained together — is called a **Universal Differential Equation (UDE)**. It keeps the physics honest and lets the data fill the gaps.

This is exactly what the BINN method (which our paper already cites) does for a land model — except we are doing it for Darwin's ocean biogeochemistry, which no one has made differentiable this way. The payoff: **calibration becomes gradient descent on the real dynamics**, and the genuine "recover the parameters" goal — which a 0-D box structurally cannot reach — moves to a model that can.

## Does it actually work? (the small-scale test)

Before committing, we built a probe (`scripts/hybrid_feasibility_probe.py`) that runs the **real Darwin box equations** and checks the four things this path depends on. All on a laptop CPU, in under two minutes. Each test reports a real measured number.

| # | What it checks | Plain-language question | Result |
|---|---|---|---|
| A | **Mass conservation** | Does the model lose or invent matter over a long run? | RK4 integrator: **<0.001% drift** over 2,000 simulated days. Plain forward-Euler: unstable. → *the fix is the integrator.* |
| B | **Neural closure (the UDE)** | Can a neural network stand in for an uncertain process *inside* the equations and be trained through time? | Yes — training loss fell by **more than four orders of magnitude (~78,000×)**, and the network re-learned the true iron-limitation curve to within **~0.5%** (mean absolute error ~0.005 on a 0–1 quantity). |
| C | **Gradient flow at depth** | Do the "which way" gradients stay stable through a long (2,000-step) run? | Yes — gradients are finite and well-defined end to end. |
| D | **Calibration by backprop** | Can we recover a known parameter by gradient descent through the real dynamics? | Yes — recovered the growth-rate parameter to **~0.00002%** of its true value. |

**What this means:** the four ingredients of the hybrid path — a differentiable forward model (C), parameter calibration by gradient (D), a trainable neural closure inside the physics (B), and stable long-run behavior with the right integrator (A) — all work on the real equations at small scale. There is no hidden show-stopper. The path is **executable**.

## Two things we learned the hard way

- **A GPU was the wrong lever.** We tried scaling the neural-closure training on an H200 cluster GPU to get a tighter result. It did **not** help: the simulation is a long chain of tiny sequential steps, so it is dominated by per-step overhead, not raw compute — the GPU sat mostly idle (~3 seconds per training step) and the job hit its time limit. This matches our earlier "single fits are launch-bound" finding. The lever for speed here is restructuring the computation (compiling the step, vectorizing), not more hardware.
- **The real win was a one-line formulation fix.** The neural closure was being fed raw dissolved-iron values (~0.00001) — too small for the network to resolve — so it stalled near 5% error. Feeding it the **logarithm** of iron instead took the recovered-curve error from ~5% to **~0.5%** and the fit error down ~78,000×. The gains on this path come from getting the formulation right, not from throwing compute at it.

## A related result Jon's feedback unlocked (the calcite "rain ratio")

Jon noted that only *some* Darwin plankton types calcify, so the bulk calcite-to-organic ratio (PIC:POC) should vary strongly in space rather than be one global number. We tested this (`scripts/per_pft_picpoc_experiment.py`): a single global ratio is mathematically forced to be constant and **cannot** reproduce the ~100× spread we see between basins, but moving the ratio onto the calcifier type alone makes the spread fall out of *how many calcifiers are present* — one constant per-calcifier ratio reproduces all three basins via calcifier fractions of ~3% / ~68% / ~0.7%, matching known biogeography. We had already built this mechanism (`USE_COCCOLITH_ONLY_CALCITE`) and shelved it, precisely because the 0-D box cannot carry the spatial calcifier field — which is another reason the next stage must be higher-dimensional.

## What we plan (the roadmap, and the honest risks)

**The honest risks, stated plainly:**

1. **Numerical drift over long runs (issue #7).** The simplest time-stepping method (*forward-Euler* — take a small step in the current direction) drifts and can go unstable, exactly as our test showed. The fix is a better **integrator** (*RK4* — a standard recipe that takes four sub-steps and is far more accurate); the test confirms RK4 holds matter to <0.001%. This is a solved problem in principle, but it must be watched at decadal scale.
2. **The hard part is the circulation, not the chemistry.** Making the *chemistry* differentiable is easy (the test proves it). Coupling it to the full 3-D ocean *transport* is the heavy lift — that is the part ECCO hand-builds an adjoint for. So the sensible first scope is **biogeochemistry on prescribed (offline) circulation**, not the fully coupled model.
3. **Engineering load.** This is building a differentiable forward model, not training a generic black box. It is real work, staged on the cluster.

**The plan, in stages:**

- **Stage 0 (done — this note):** small-scale feasibility probe on the real box equations. Verdict: executable.
- **Stage 1:** a differentiable biogeochemistry module for a handful of tracers on **offline** circulation; verify mass conservation over a decade with RK4 (closes #7).
- **Stage 2:** replace one or two genuinely-uncertain closures with neural networks (the UDE), and calibrate against ECCO-Darwin v05 output and real observations — the same anchors the first project used.
- **Stage 3:** scale up tracers/region on the cluster; this is where the "make Darwin's biogeochemistry differentiable" contribution becomes a result, and where the honest six-parameter recovery can finally be attempted on a model that can carry spatial structure.

**Why it is worth it:** this builds the *missing biogeochemistry adjoint* — the efficient gradient tool ECCO has for physics but not for biology — using automatic differentiation plus small neural networks instead of years of hand-coding. That is the strongest, most fundable version of the whole project (and the natural follow-on to the identifiability paper, which already names a "higher-dimensional surrogate" as the way forward).

---

*Reproduce the feasibility result: `python scripts/hybrid_feasibility_probe.py` (prints the four measured numbers; exits 0 only if all four pass).*
