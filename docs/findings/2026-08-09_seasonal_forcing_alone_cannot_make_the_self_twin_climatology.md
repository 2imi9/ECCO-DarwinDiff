# Seasonal forcing alone cannot make the self-twin climatology

**As of 2026-08-09. Stage-0 target result only; no optimizer, recovery
submission, or B200 job was launched.**

## Verdict

The existing two-layer Carroll box with monthly SST, SSS, and wind cannot
produce the stable whole-cycle self-twin target preregistered for issue #239.
All three AOIs fail the target gate before recovery. The first cycle retains
DFe2 contrast and has sane Chl1 structure, but it is an initial-condition
transient, not a stable climatology. Repeating the seasonal cycle erases the
DFe2 structure, drives Chl1 outside the frozen sanity interval, and eventually
makes surface DIC non-finite.

This blocks the proposed seasonal self-twin construction. It **does not choose
endpoint versus time mean for Darwin**, and it says nothing about parameter
recovery because no fit was run.

## Frozen construction and gate

The preregistration is
[`2026-08-09_prereg_seasonal_loss_self_twin.md`](2026-08-09_prereg_seasonal_loss_self_twin.md).
The corrected production run used:

- Carroll truth and each AOI's existing Darwin initial-condition cache;
- monthly ECCO-Darwin SST, SSS, and wind climatologies;
- the canonical flagship Eppley temperature gate, explicitly on with
  `A_E_EPPLEY=0.0633`, `T_REF_EPPLEY=15.0`;
- `dt=0.25 d`, 122 steps/month, 1,464 steps/cycle, up to eight cycles;
- the all-post-step mean of each recorded cycle, never the 12-month-end mean;
- no monthly light input, because the current box exposes none;
- no Daniels or POSi term in the Southern Ocean.

The first attempted harness had Eppley temperature growth off because the
model module defaults it off; that output is invalid for inference. The
omission was found by canonical-config inspection before the corrected result,
recorded as a harness amendment in the preregistration, and no threshold was
changed.

## Target result

Relative spatial SD is `spatial SD / |spatial mean|` over complete-forcing ocean
cells. The DFe2 gate minima were 0.0423 / 0.0662 / 0.1195 for EqPac / North
Atlantic / Southern Ocean, and the Chl1 sanity interval was [0.1, 1.0].

| AOI | cells | cycle 1 DFe2 rel-SD | cycle 1 Chl1 rel-SD | cycle 2 DFe2 rel-SD | cycle 2 Chl1 rel-SD | first non-finite DIC1 cycle |
|---|---:|---:|---:|---:|---:|---:|
| EqPac | 1,071 | 0.0834 | 0.1315 | 0.0101 | 1.6046 | 5 |
| North Atlantic | 489 | 0.1818 | 0.2732 | 0.1593 | 4.1462 | 5 |
| Southern Ocean | 1,296 | 0.2599 | 0.4049 | 0.0636 | 4.6515 | 4 |

Cycle 1 clears the contrast and Chl1-magnitude gates in all three basins, but
there is no preceding cycle against which to establish periodic stability.
Cycle 2 fails field stability and Chl1 sanity everywhere; EqPac and the
Southern Ocean also fail DFe2 contrast immediately. The North Atlantic retains
DFe2 contrast in cycle 2 but loses it by cycle 3 (`0.00714`). By cycle 8 the
DFe2 rel-SD is `0.000144 / 0.000528 / 0.000463`, effectively homogeneous in all
three basins.

The failure is not a GPU-memory or optimizer failure. The compiled no-gradient
gate completed in 18.2 s on the local RTX 5090 and peaked at 4.50 MB allocated.
The science gate exited 2 by design. Its separate artifact verifier recomputed
all summaries and all 21 comparable-cycle decisions from the 24 saved cycle
tensors and exited 0:

```text
VERIFIED target gate: science_status=FAIL aois=eqpac,natlsubpolar,southernoceanpac cycles=24
```

The committed metrics are in
[`2026-08-09_seasonal_twin_target_gate.json`](2026-08-09_seasonal_twin_target_gate.json),
and the hash-bound verification receipt is
[`2026-08-09_seasonal_twin_target_gate_verification.json`](2026-08-09_seasonal_twin_target_gate_verification.json).
The 4.15 MB tensor bundle remains under gitignored `runs/`; its exact byte size
and SHA-256 are recorded in both artifacts, and the production command
regenerates it deterministically.

## Mechanistic boundary

The observed trajectory is consistent with a missing replenishment/transport
closure, not with a merely insufficient optimizer:

1. The box carries sinking/export, mortality, scavenging, gas exchange, and
   vertical exchange, but no advective tracer tendency or monthly restoring
   field. Monthly T/SSS/wind modulate local rates; they do not restore exported
   carbon, biomass, or the AOI-specific iron structure.
2. At Carroll truth the all-step DIC1 mean falls sharply before becoming
   non-finite: EqPac `1733 -> 1336 -> 973 -> 613 -> non-finite`; North Atlantic
   `1880 -> 1465 -> 1101 -> 745 -> non-finite`; Southern Ocean
   `1884 -> 1455 -> 1088 -> non-finite`.
3. DFe2 approaches a common mean near `9.61e-6` while its spatial contrast
   collapses. That is the same observable that must anchor `scav_rat`.

The direct result is only that the current forcing-only target construction
fails. “Missing transport/replenishment causes the failure” is the next
abductive hypothesis, not yet a settled mechanism. Monthly light remains
untested and cannot be blamed or cleared by this result.

## Consequence for #239

The preregistered stop rule worked: do not run `end_end`, `mean_mean`,
`mean_end`, or an untrained recovery arm against this target, and do not replace
the whole-cycle target with the attractive first cycle after seeing the result.
A B200 would add no information once Stage 0 fails, so none was reserved.

The next discriminating target-only test must add a **frozen,
parameter-independent periodic transport/replenishment closure** and audit its
annual budgets before any optimizer runs. It must retain the existing stability,
DFe2-contrast, and Chl1 gates; it must also compare closure magnitude with the
unclosed annual residual so a direct target-restoring shortcut cannot masquerade
as transport. Light seasonality is a separate arm, not an unregistered patch to
the failed target.

## Reproduction

```bash
python scripts/analysis/seasonal_twin_target_gate.py \
  --aois eqpac,natlsubpolar,southernoceanpac \
  --steps-per-month 122 --min-cycles 2 --max-cycles 8 \
  --device cuda --compile \
  --output docs/findings/2026-08-09_seasonal_twin_target_gate.json \
  --bundle-out runs/seasonal_twin/target_bundle_spm122_eppley_v2.pt

python scripts/analysis/verify_seasonal_twin_target_gate.py \
  docs/findings/2026-08-09_seasonal_twin_target_gate.json \
  runs/seasonal_twin/target_bundle_spm122_eppley_v2.pt \
  --receipt docs/findings/2026-08-09_seasonal_twin_target_gate_verification.json
```

One deterministic construction, no out-of-sample replication, no recovery
claim, and no GitHub issue closed.
