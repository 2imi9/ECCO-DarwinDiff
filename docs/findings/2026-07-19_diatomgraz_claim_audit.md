# Audit of the `diatomgraz` non-identifiability claim (2026-07-19)

Sent an agent to fix a suspected **observable-set category error** in Paper #1's identifiability
claim. The premise was wrong, the agent's counter-claim was also wrong, and underneath both sits a
real methodological problem. All three are recorded because each is a different kind of mistake.

---

## What was checked, and what is actually true

| Claim | Source | Verdict |
|---|---|---|
| "Our profiles used total NPP, not ECCO-Darwin's observables — silicate would break the degeneracy" | my brief to the agent | **FALSE** |
| "The `diatomgraz` FLAT result was never measured" | the agent's scoping pass | **FALSE** |
| "FLAT is contradicted by the 10/10 POSi recovery" | the agent's scoping pass | **FALSE** |
| "The profile artifact is not in the repo" | the agent | **TRUE** |
| "The bSi observable is circular" | the agent | **TRUE, and it is the real issue** |

### 1. My premise was wrong — silicate was already in the loss

The config that produced the 2026-07-07 numbers exports `POSI_W=1.0` and `POSI_DARWIN_W=0.5`
(sparse GEOTRACES bSi **and** dense Darwin POSi). It never sets `PRIMPROD_W`, which defaults to
`0.0`. **Total NPP was switched off entirely.** The growth pair was constrained by Chl1–5 patterns,
POC/DIC/ALK, CO₂ flux, and biogenic silica. The category error as I described it does not exist.

### 2. The agent's counter-claim was also wrong — FLAT *was* measured

The agent examined the **07-07** run, which profiled only three parameters (`alpfe`, `scav_rat`,
`R_PICPOC`), found no `diatomgraz` entry, and concluded the FLAT verdict was invented from a legend
caption. But `diatomgraz` was profiled in a **different, earlier run** (2026-06-28, issues
#152/#120), which measured **span 0.039** in the full geo1 loss and **span 0.118** against bSi alone.

### 3. The claimed contradiction is not a contradiction

The agent paired FLAT against `posi_dense_diatomgraz.md`'s **0/10 → 10/10** recovery and called it a
refutation. It is the opposite. FLAT was measured on the loss **without** dense Darwin POSi; the
10/10 came **with** it (`POSI_DARWIN_W` 0.0 → 0.5, and 20/20 under Eppley). The profile's own
prescription was *"needs a NEW observable — dense Darwin POSi — not reweighting."*
**The prediction was confirmed, not contradicted.**

---

## The two things that ARE real

### A. Reproducibility gap — the artifact is not in the repo

`span 0.039` / `0.118` exist in project memory and nowhere under `docs/`. No file in the repo
contains a `profiled_param` key. The 07-07 profiles doc mentions `diatomgraz` exactly once, at
line 13, inside the **threshold legend**:

> **FLAT** `< 0.05` — structural non-identifiability (param invisible; new observable needed).
> *(the diatomgraz signature)*

That is an illustration of what the FLAT category means, not a measurement of this parameter. The
measurement exists; the evidence a referee could inspect does not. This is a **reproducibility gap,
not a fabrication** — but the claim must be re-run with `--out` and the JSON committed before
Paper #1 leans on it. Three downstream documents already cite it as established, one of them as a
go/no-go gate on H200 spend.

### B. The bSi observable is circular — this is the real methodological problem

`src/darwindiff/silica.py:78`, `diagnostic_bsi_steady`, algebraically back-solves biogenic silica
from diatom biomass. It is a **steady-state diagnostic, not a prognostic tracer**. The 2-layer box
carries 15 tracers (`N_TRACERS_2LAYER = 15`) — DFe, 5 PFTs, POC, PIC, DIC, ALK across two layers —
with **no dissolved SiO₂ state and no Si co-limitation on diatom growth**.

So "silicate constrains `diatomgraz`" is, in part, the model constraining itself against a rescaling
of terms it already contains. The 2026-06-19 reviewer panel flagged exactly this as **M11**.

And the sharper version of my original premise survives here: **ECCO-Darwin fits dissolved SiO₂
against GLODAP.** We fit biogenic silica derived from our own diatom biomass. Those are different
quantities, so we cannot claim to be testing identifiability against their observable set.

GLODAPv3 dissolved silicate *is* available (columns `silicate`/`silicatef`/`silicateqc`, µmol/kg;
822,326 QC-good values across Pacific + Atlantic, 39,676 at ≤10 m). Using it would require a
prognostic SiO₂ state — 15→17 tracers, invalidating every `darwin_ic_cache_*.npz`, plus an f_Si
co-limitation term and a GLODAPv3 bottle loader. **Multi-day, and a follow-on, not a precondition.**

---

## Consequence for Paper #1

**Do not write "diatomgraz carries no observational signal."** It is not supported and it is
attackable by any referee who knows the Darwin silicate cycle.

**Defensible framing, requiring no new simulation:** `diatomgraz` is constrained only through a
**steady-state biogenic-silica diagnostic**, not a prognostic silicate cycle; profile-likelihood is
FLAT (span 0.039) in the loss without dense POSi, and adding dense Darwin POSi recovers the
parameter 10/10 (20/20 under Eppley). That statement is honest, matches what was measured, and
names its own limitation.

**Required before submission:** re-run the profile with `--out` and commit the JSON. In flight as
Explorer array `8479481` (four parameters: `diatomgraz`, `Smallgrow`, `Biggrow`, plus a bSi-ablation
arm; ~52 min/param measured).

---

## The pattern worth noting

Three errors, three different failure modes, in one investigation:

- **Mine** — asserted a defect from memory without checking the config that produced the numbers.
- **The agent's** — found an absence in *one* artifact and concluded the measurement never existed,
  then read two results from different observable sets as contradictory.
- **The project's** — a legend caption hardened into cited fact across three documents, one gating
  compute spend, with no committed artifact behind it.

The third is the same shape as the `delta_t` bug found earlier today: a claim that was never wrong
*enough* to trip anything, propagating until something forced a check. The lesson is not "verify
more" in the abstract — it is that **claims which gate spending should carry a committed artifact.**
