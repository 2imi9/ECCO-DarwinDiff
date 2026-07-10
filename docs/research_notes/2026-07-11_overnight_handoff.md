# Overnight run 2026-07-10 → morning 2026-07-11 — handoff

**Constraints honored:** everything ran on the cluster; the local RTX 5090 was **never used**
(you were asleep). B200 was attempted first (per your request) but is **blocked** — see below.

## TL;DR
- **B200 could not be driven unattended:** the AICR certificate has **expired**
  (`Permission denied (publickey)`), and renewing it needs *your* browser SSO through
  `ood.aicr.ai` — a human step I can't do. So the big jobs ran on **Explorer H200** (key-auth,
  no 2FA, automatable), which is the correct automation cluster per our setup notes.
- **1 deliverable finished + committed** (observing-system power analysis), **3 GPU jobs launched**
  on Explorer H200, results landing overnight.

## GPU jobs launched (Explorer H200, `/projects/schultz/qi.zim/`)

| job | id | what it is | output |
|---|---|---|---|
| `fim_peraoi` | 8266733 | per-AOI **Fisher / CRLB** identifiability map, **1°** — your per-parameter-uncertainty ask | `runs/fim_peraoi.json` |
| `fim_native` | 8266734 | per-AOI Fisher / CRLB at **native LLC270** — the #152 spatial identifiability map (new) | `runs/fim_native.json` |
| `native_peraoi` | 8266735 | native per-AOI **recovery ensemble** (5 seeds, 1500 ep) | `runs/native_peraoi/*.json` |

**Check them:**
```bash
ssh explorer 'squeue -u $USER; sacct -j 8266733,8266734,8266735 --format=JobName,State,Elapsed,ExitCode -n'
ssh explorer 'cat /projects/schultz/qi.zim/runs/fim_peraoi.json 2>/dev/null | head'
```

## Finished + committed (branch `overnight/2026-07-10-experiments`)

**Observing-system power analysis** — `scripts/observing_system_power_analysis.py` →
`docs/findings/observing_system_power.json`. This is the **quantified Paper #2 forward
contribution**: it converts "get wider Ω" from a heuristic into a spec. Analytic OLS-power
frontier `n·S·√N/(σ·√12) = 1.96 + Φ⁻¹(p)`, Monte-Carlo-validated (analytic vs MC power match to
~0.02). **Headline** (detect Ω-exponent `n=0.5`, log-residual `σ=0.2`, 80 % power):

| within-region Ω span | co-located samples needed |
|---|---|
| **0.16 dex** (current) | **~589** — impractical |
| 0.5 dex | ~60 |
| 1.0 dex | ~15 |

→ **Ω *span* is the binding lever, not sample count.** The observing-system spec is "widen Ω first,
then count samples." This is also the **emulator/OSSE precursor** — it defines the observing system
an emulator would be built to optimize.

## B200 — how to use it (needs you, in the morning)

1. **Renew the AICR certificate** (the blocker): open `https://ood.aicr.ai` in a browser, sign in with
   NU SSO, and use the **SSH Certificate** app (or Files → download the `aicr_keys` folder) to refresh
   `~/.ssh/id_ed25519_aicr-cert.pub`.
2. Then B200 batch is: `ssh aicr` → stage code/data (scp triggers a **Duo push** — approve it) →
   `sbatch --partition=b200-batch --account=p2026_0089_neu <job>.sbatch`. B200 = **throughput** (many/large
   runs); a single fit is launch-bound (same speed as H200/5090). Full procedure in
   `docs/cluster_setup.md`. Interactive B200 notebooks: `ood.aicr.ai` → JupyterLab on `b200-devel`.
3. **AICR = the multi-institutional Massachusetts AI Compute Resource** (accessed via NU); it is *not*
   automatable unattended (Duo on data transfer), so keep autonomous runs on Explorer and use the B200
   for user-launched throughput.

## When do we touch the emulator?

The emulator / spatial UDE is a **forward / OSSE** tool — *not* an identifiability rescue (the Track-2
map already showed transport doesn't close the gap because the observations lack the signal). The
**trigger** to build it: a pivot to **observing-system design**, which tonight's power analysis is the
precursor to (it quantifies the observing system the emulator would optimize). It's gated on Jon's
direction, and it is the **first genuine B200-scale workload** once greenlit. So: not now, but the
groundwork (the power analysis) is laid, and the emulator is the natural next B200 job if Jon says go.

## Morning next steps
1. Aggregate the Fisher/CRLB results (`fim_peraoi.json`, `fim_native.json`) → the per-parameter
   uncertainty table for Jon; check the native recovery ensemble stats.
2. The binding step remains: **get both papers to Jon** (the collaboration gate).
