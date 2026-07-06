# Pre-registration — hold-together sweep (2026-06-26, before results)

Written **before** the 8 configs (`sweep_holdtogether_20260626_1119/` + job 7888644) complete, so the
analysis cannot be cherry-picked after the fact. Decisions, success criteria, and reward-hacking checks
are fixed here.

## Hypotheses

- **H1 (load-bearing test).** The real Daniels CP:PP anchor is what constrains `R_PICPOC`, not the
  Darwin-pattern loss. **Prediction:** the `dan0_control` config (no Daniels) reproduces the historical
  v3.2 behaviour — `R_PICPOC` does **not** co-recover — while the Daniels configs do. If `dan0_control`
  already recovers `R_PICPOC`, the anchor is not load-bearing and the headline must be downgraded.
- **H2 (hold-together).** A single config can hold ≥3 of {`alpfe`, `scav_rat`, `diatomgraz`, `R_PICPOC`}
  together with `R_PICPOC` real-anchored. **Prediction:** uncertain — this is the open question.
- **H3 (iron dose trade-off).** Increasing `GEOTRACES_W` (0.3 → 1 → 3) trades `alpfe` for `scav_rat`
  (the ironboost in B.3 dropped `alpfe` to 4/50). **Prediction:** `geo3*` drop `alpfe`; `geo0.3`
  hold the pair.

## What each config isolates (one-lever ablation from the base)

| config | lever changed | isolates |
|---|---|---|
| base (7888644) | — | the combined operating point |
| `dan0_control` | DANIELS_RPICPOC_W 1→0 | **H1** — is Daniels load-bearing for `R_PICPOC`? |
| `dan2` | DANIELS_RPICPOC_W 1→2 | does a stronger anchor help or distort? |
| `geo1_dan1` / `geo3_dan1` / `geo3sub10_dan1` | GEOTRACES_W 0.3→1→3 (+SUB) | **H3** — iron dose vs `alpfe`/`scav_rat` |
| `noeppley_dan1` | USE_EPPLEY_T 1→0 | Eppley's role in `diatomgraz` |
| `noposi_dan1` | POSI_W 1→0 | the bSi term's role in `diatomgraz` |

## Success criterion (fixed in advance)

Per-AOI **≥2-AOI co-recovery** (Cal-grade-or-better vs Carroll, re-derived via `band_of`), n=10 seeds,
**`verify_run.py --expect-seeds 10` exit 0**. The "winner" is the config holding the **most** of the
four params at ≥2-AOI co-recovery ≥7/10 — reported alongside every other config, including failures.

## Reward-hacking / failure-mode checks (must pass before any positive claim)

1. **Per-AOI, not joint.** Grade per-AOI co-recovery, not joint cell-weighted — the 2026-06-15 ALK-anchor
   result was a false positive (a cell-weighted average straddling Carroll while no single AOI recovered).
2. **The "we told it the answer" caveat (precision, not hacking).** The Daniels loss pins `R_PICPOC` to
   the real per-cell rain ratio (~0.05). Carroll = 0.0425. So a Cal grade means **"real CP:PP data is
   consistent with Carroll,"** *not* "the method discovered Carroll's value from Darwin output." The
   honest, non-circular claim is a **validation that independent data agrees with Carroll**, conditional
   on H1 (Daniels is load-bearing). State it that way; do not call it a from-scratch discovery.
3. **diatomgraz via sparse proxy.** Dense Darwin POSi is not staged on the cluster; `POSI_W` uses the
   sparser GEOTRACES bSi. If `diatomgraz` recovers, check it is not an artifact of a few bSi cells; if it
   fails, the cause may be the proxy, not the method — flag both.

## Decision rules

- Report **all 8 configs** (positive and negative), as a table with numbers — no narrative without the
  table.
- If H1 fails (`dan0_control` recovers `R_PICPOC`): downgrade the "real-data recovery" framing project-wide.
- If a winner holds ≥3 params with `R_PICPOC` real-anchored: robustify at **n=100** before any headline.
- If no config holds them together: that is a **publishable negative result** — the params trade off even
  with real anchoring — and is reported as such.
