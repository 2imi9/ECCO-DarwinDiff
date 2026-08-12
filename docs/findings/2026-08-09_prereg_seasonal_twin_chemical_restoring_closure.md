# Preregistration: chemical restoring closure for the seasonal twin

**Frozen 2026-08-09 before any closure-enabled target cycle was run.**

## Relational state

The forcing-only construction is settled negative: the current box loses DFe2
contrast, drives Chl1 pathological, and makes DIC1 non-finite before reaching a
stable annual cycle. The recovery hypothesis `hy_szn_loss` remains open but blocked.
The live abductive explanation is `hy_szn_chem`: a climatological twin needs the
parameter-independent tracer replenishment/transport omitted by the 0-D box.

The pre-work queries were:

```text
python scripts/research_map_db.py settled "periodic transport replenishment closure"
python scripts/research_map_db.py sql \
  "SELECT hy_id, statement, predicts, falsifier FROM hypothesis \
   WHERE lower(statement) LIKE '%transport/replenishment closure%'"
```

The first query returned the settled no-closure failure; the second returned
`hy_szn_chem`. This test evaluates that hypothesis without reopening the settled arm.

## Frozen intervention

The no-closure production configuration remains unchanged: Carroll truth,
AOI-specific Darwin IC caches, monthly SST/SSS/wind, flagship Eppley temperature
growth, `dt=0.25 d`, 122 steps/month, and the all-post-step cycle mean.

After each ordinary forward-Euler step, apply this fixed closure:

```text
x_next[j] = clamp(x_model_next[j] + dt * (x_ref[j] - x[j]) / tau, min=0)
tau       = 365.25 days
```

`x_ref` is the AOI's cached Darwin pickup field used for the initial condition.
The closure acts on exactly ten chemical/particle tracers:

```text
DFe1 POC1 PIC1 DIC1 ALK1 DFe2 POC2 PIC2 DIC2 ALK2
```

It acts on none of the five phytoplankton fields. Its tensor is fixed before
optimization and independent of all six learned parameters. This is a scoping
approximation to missing transport/restoring, not a claim that Darwin transport
is linear relaxation or has a one-year timescale.

Only `tau=365.25 d` is registered. There is no post-result timescale ladder,
per-basin timescale, monthly target restoring, or direct phytoplankton source in
this experiment.

## Unchanged target gates

The intervention must pass every original Stage-0 gate in every AOI:

1. masked relative-L2 change <=1% for all 11 fitted/raw gate fields between the
   last two all-step cycle means;
2. DFe2 relative-spatial-SD change <=5%;
3. DFe2 relative-spatial SD >=0.0423 / 0.0662 / 0.1195 for EqPac / North
   Atlantic / Southern Ocean;
4. Chl1-mapped diatom relative-spatial SD in [0.1, 1.0];
5. all decision quantities finite.

The first passing cycle at or after cycle 2 is selected, up to a hard maximum
of eight cycles. Thresholds are not changed from the no-closure preregistration.

## Closure-dominance gate

For each restored tracer, accumulate over the selected cycle and ocean cells:

```text
A_closure = sum |dt * (x_ref - x) / tau|
A_model   = sum |x_model_next - x|
share     = A_closure / (A_closure + A_model)
turnover  = A_closure / sum_over_steps(mean |x|)
```

The closure is admissible only if:

- no phytoplankton index receives a closure increment (exact structural check);
- `share <= 0.50` for every restored tracer; and
- `turnover <= 1.0` per recorded cycle for every restored tracer.

These are gross-increment checks, not a net-budget cancellation test. A closure
that passes only by contributing more absolute motion than the endogenous box,
or by replacing more than one mean inventory per year, is direct restoration
for this scoping purpose and fails even if the state target looks attractive.

## Decision rule

- **Supports `hy_szn_chem` at target level:** all three AOIs pass the unchanged target
  gates and closure-dominance gate, while the already-verified no-closure arm is
  the negative control.
- **Refutes this one-year chemical closure:** any AOI misses a target or
  dominance gate. This does not refute transport in general.
- **Non-diagnostic:** a coding/integrity verifier fails, any closure touches a
  phytoplankton state, or a gate is changed after output inspection.

Passing Stage 0b would authorize only a one-seed/one-epoch B200 autograd cost
gate. It would not itself choose endpoint versus time mean, establish parameter
recovery, or authorize an n=50 array.

No GitHub issue will be closed. Monthly light remains a separate rival and is
not added to this arm.
