# Track-2 questions for Jon — prep brief (2026-07-07)

Internal prep brief (drives the next Jon conversation; not a doc shown to Jon verbatim).
Grounded in the action-1 decision note
([2026-07-07_param_conditioned_emulator_decision.md](2026-07-07_param_conditioned_emulator_decision.md))
and the transport go/no-go probe (`scripts/transport_helps_probe.py`).

## Where Track 2 stands (context for the questions)

- **The route is decided (engineering call, not Jon's):** build **(B) the mechanistic UDE** — learn the
  uncertain closures inside differentiable Darwin BGC on *prescribed* v05 transport. **Shelve (A)** the
  parameter-conditioned black-box emulator and **SBI**: both need a perturbed-parameter Darwin *ensemble*
  (tens–hundreds of full GCM runs spanning Carroll-6) that we do not have and cannot cheaply produce. (B)
  needs **zero new GCM runs** because it prescribes v05's own velocities.
- **Cheap synthetic go/no-go passed:** in a 1-D column, holding out ~30% of layers, a transport-free *local*
  box gives **held-out R² ≈ −0.3** (the surrogate gap) while the **same fit with vertical mixing gives
  held-out R² ≈ +1.0** — transport supplies the spatial structure the box lacks, and gradients flow through
  it. This is a **synthetic vertical-1D capacity result, not the real E2 gate**; the real gate is held-out
  R² > 0 on real GEOTRACES/calcite cells with *horizontal* transport.

The questions below are ordered by how much they change what we build. Tier-1 gates the build; Tier-2 scopes
it; Tier-3 is the framing that decides whether clearing E2 counts as discovery.

---

## Tier 1 — decision-gating (answers change what we build)

**Q1. Is a v05 perturbed-parameter ensemble ever affordable?**
This is the single fact that could un-shelve routes (A)/SBI. Realistically, how many full ECCO-Darwin
integrations across the Carroll-6 space could we obtain on Explorer/AICR, and at what disk cost (v05 is
~5 TB/full run; we have one pickup on disk)? If the honest answer is ≈0, (A) and SBI stay shelved on
budget grounds, and (B) is confirmed the only route — which is our working assumption.

**Q2. Are v05's 3-D velocity + vertical-mixing (κz) fields archived on disk for the target AOI?**
This is the **one input (B) depends on**. The Phase-1 plan prescribes v05's own `(u, v)` (with `w`
recomputed from continuity) and vertical diffusivity, differentiated by plain autograd. We need to confirm
the standard Darwin3-offline transport archive is available at the resolution/period we want, for the AOI we
pick. If only time-mean fields exist, that constrains us to climatological (not seasonal) transport for
Phase 1.

**Q3. Which closure is Paper-2's primary learnable target — iron-limitation or calcification — and, if
calcite, what mechanistically drives it?**
This sets what the UDE's bounded NN replaces and which **absolute anchor** carries identifiability
(GEOTRACES dissolved iron vs Daniels/MODIS calcite rain ratio). Our default architecture: `PIC_prod =
R0 · g_θ(env, state) · mort_total`, with `g_θ ≡ 1` recovering the constant-`R_PICPOC` Darwin law exactly,
and `g_θ` fed SST, Ω_calcite (from v05 DIC/ALK/T/S), the Fe/nutrient-limitation factor, and PAR. Is that the
physically defensible driver set for the Darwin/v05 lineage, or should it differ?

---

## Tier 2 — scoping (refines the build, doesn't gate it)

**Q4. Is offline (prescribed-transport) scope acceptable for Phase 1?**
i.e. learn closures against v05's archived transport rather than an online-coupled run. This is what makes
(B) affordable and inherits MITgcm-offline conservation. We assume yes; confirming avoids a later rebuild.

**Q5. Forcing realism — how real must the excitation be for the E2 claim?**
Our closure identifiability currently comes from *synthetic* light-driven drawdown (offline-Fisher-designed).
Moving from a methods result to a **real-data** claim needs the real seasonal light/dust climatology for the
AOI. Is synthetic drawdown acceptable to demonstrate the method, with real forcing reserved for the E2 claim,
or should Phase 1 use real forcing from the start?

**Q6. Calcite anchor mechanics + the two R_PICPOC points.**
(a) When we build the calcite loss, does the Southern-Ocean ratio target still need the `RATIO_MAX=2`
sanitization (the contaminated-target fix from Track 1) so the loss doesn't chase the known-bad signal?
(b) Fold in the two load-bearing R_PICPOC points from the Track-1 write-up: that Carroll's `R_PICPOC` is
itself **under-constrained**, and that a single **global** constant is mis-specified against a
**regionally-variable** rain ratio (Daniels eqpac ~0.039 ≈ 1.6× the global mean). Does the calcite UDE
target the regional field rather than a global constant?

**Q7. Stoichiometry + boundary-flux conventions for the mass budget.**
Confirm DIC(−1)/ALK(−2) per mole PIC and the sign conventions for boundary fluxes (dust in, export/burial
out, air–sea CO₂) so a single `PIC_prod` feeds `dPIC`/`dDIC`/`dALK` and the per-element budget closes. Also:
is freezing PIC dissolution/sinking (learning **production only**) scientifically acceptable for Phase 1?
And what absolute mass-drift magnitude (Pg C/decade) counts as "<< the physical trend" — i.e. passing?

---

## Tier 3 — the framing question (decides discovery vs consistency-check)

**Q8. What counts as "independent validation = discovery" for you?**
Track 1 was honestly a **consistency check against Carroll's own (under-constrained) values**, not a
discovery against the GCM. Our internal bar for Paper #2 is **held-out real-data R² > 0 with transport
present** (the E2 gate) — an independent inversion the 0-D box structurally cannot pass. We need agreement
that clearing E2 constitutes independent validation, and on what the legitimate held-out target is (v05 vs
GLODAP; which region/period is genuinely held-out vs training data).

---

## What we decide ourselves (not Jon's time)

Route ranking (B > A > SBI); conditioning mechanism if (A) ever revives (FiLM/hypernetwork); the transport
numerics (centered flux-form advection, backward-Euler Thomas vertical diffusion, `w`-from-continuity);
discretise-then-optimise with windowed BPTT + checkpointing; net size/bounding/L2; structural conservation
(`dC = A·S`, softplus positivity); the symbolic-distillation go/no-go gate; and the Phase-1 build order. All
self-contained on the synthetic twin + merged infra, gated locally before any H200 spend.
