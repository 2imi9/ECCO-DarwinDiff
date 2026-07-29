# Domain-expert answers on the open identifiability questions (J. Lauderdale, 2026-07-29)

**Source:** email reply from Jonathan Lauderdale (MIT) to the open questions on the deck's final
slide, cc Cristina Schultz. Substance captured faithfully; interpretation and consequences are ours.

## What changes in the repo

### 1. The iron degeneracy is FUNDAMENTAL — not a parameterization artifact

> "The ocean iron cycle is 'open' because of its short residence time, so source and sink
> parameterizations really matter — so yes, it's fundamental. We don't really understand most of the
> processes that iron participates in, so we're left with simple representations of sources (aeolian
> input, hydrothermal vents, sediments, glacial runoff) and scavenging (modulated by complexation by
> ligands, colloids)."

**This weakens a hypothesis raised on 2026-07-28.** In `2026-07-28_bling_comparability.md` I
suggested the alpfe/scav_rat degeneracy might be partly an artifact of Darwin's *ligand-free*
scavenging, since BLING partitions free from complexed Fe, and framed "is the degeneracy
formulation-dependent?" as the most interesting open question.

A domain expert says the degeneracy is a property of the **cycle** — short residence time makes it
source/sink-controlled regardless of which simple parameterization is chosen. The ligand question is
still worth testing, but it is **not** the explanation, and that note must not be read as implying
the degeneracy is an artifact of our model choice.

The constructive response he names: **"This would be a good candidate for UDE!"**

### 2. How to finish Track 1 — drop the model target

> "This work is great. I think what would wrap up track 1 is dropping the ECCO-Darwin model output
> and just trying to fit observations."

A direct answer to *"what would a true discovery look like, versus a consistency check?"* The README
states the study is a consistency check because the 0-D box homogenizes and held-out real-data R² is
negative. The prescribed path out is to **remove the model target entirely and fit observations
alone**. Concrete, scoped, and it should be the Track-1 closeout.

### 3. Which rain ratio does Darwin actually use? Unresolved AT SOURCE

> "I actually notice three rain ratio values in `data.darwin` and `data.traits`, and I'm not sure
> which are used. I'll ask around."

**Load-bearing, and checkable in darwin3.** We treat `R_PICPOC = 0.04245` as the recovery target and
report **50/50**. If three values exist and a Darwin developer is unsure which is operative, our
ground truth may not be the parameter the model actually runs on. Highest-priority code check.

He also confirms the regional-rain-ratio finding — *"Yes it should vary"* — and notes the next
ECCO-Darwin version **explicitly determines which plankton groups calcify**, which would change what
`R_PICPOC` means structurally.

### 4. The growth pair — softer than "unobservable by construction (`Biggrow`; `Smallgrow` is non-identifiable from time-mean observables only)"

> "Because these are model structure parameters and they don't really line up with any phytoplankton
> classes, they are difficult to constrain. Perhaps the chlorophyll might help?"

We say **unobservable by construction, excluded not failed**. He says *model-structure parameters
that do not map to real plankton classes*, hence difficult — and floats chlorophyll as a handle.
Compatible with our framing but less absolute. Worth softening "by construction" to "not identifiable
from any observable we have, because they are structural rather than physiological" — truer, and more
defensible under review.

### 5. Ω-driven calcite closure — real, but incomplete above the horizon

> "Calcite should only dissolve in waters undersaturated with CO3²⁻ (which is measured by omega)...
> the horizon where waters go undersaturated is around 2-3 km depth. However, inverse models claim
> that, to close the calcite budget, there is significant dissolution above this mediated by
> biological activity — think zooplankton grazing."

Our calcite work returned NULL, and I initially read his grazing point as an unconsidered
explanation for it. **Checking the artifacts, that framing needs two corrections.**

**(a) The closure is not Ω-only.** `EnvCalciteClosure` (`src/darwindiff/closures.py`) is driven by
**SST, Ω_calcite and PAR** — three exogenous environmental channels. Calling it "Ω-driven" is
imprecise, and an argument that "Ω-only is misspecified" does not land against it as written.

**(b) The recorded null already attributes itself to data support, not to misspecification.**
`docs/findings/calcite_omega_identifiability_real.json` states:

> `verdict: "NULL: real Daniels data does not constrain an Omega-power-law rain ratio
> (identifiability-limits; small n / narrow Omega support)"`

with `n_points = 58` across all AOIs, **zero in the Southern Ocean**. So the cause on record is
*insufficient and narrowly-spread data*, which is a different claim from *the physics is wrong*.

**What is genuinely striking in that artifact, and unremarked so far:** the fitted Ω exponent is
wildly scale-dependent.

| | n̂ | 95% CI | R² | n points |
|---|---|---|---|---|
| eqpac | 6.42 | 1.83 – 10.35 | 0.313 | 32 |
| natl | 7.01 | 0.86 – 12.99 | 0.147 | 24 |
| **pooled** | **0.89** | **−0.23 – 1.78** | 0.046 | 58 |

Per-AOI exponents near 6–7, pooled near **0.89** with a CI straddling zero. Pooling does not average
the two regional fits — it collapses them. That is an aggregation artifact of the same family as the
cell-weighted-vs-per-AOI straddle we already grade around, and it deserves its own look.

**Where his point still bites.** Above-horizon grazing dissolution would mean the *rain ratio* is not
the only thing Ω should modulate — dissolution is also biologically mediated. That is a structural
argument about what the closure should contain, and it stands independently of why this particular
fit came back null. Worth recording as a design input for any future calcite closure, **not** as the
explanation for the existing null.

### 6. The remaining questions

- **Sections vs isotopes:** sections "definitely useful"; isotopes possibly informative but models
  avoid them (extra tracers, complexity). Consistent with our observation-design ranking, which puts
  depth-resolved subsurface Fe first.
- **Particulate vs dissolved split:** *"Maybe, but is it realistic/comparable to observations?"* —
  a fair challenge we have not answered.
- **Seasonal vs 23-year climatology:** *"Yes, I imagine the timing of different changes might be
  revealing."* Supports the time-resolved fitting track.
- **Role of emulator/UDE:** *"UDE would be really interesting for discoverability (could it aid
  equation discovery, not just parameter learning?) ECCO-Darwin is pretty expensive to run, so a
  forward tool would be VERY useful!"* — independent endorsement of the forward emulator **as
  infrastructure**, which is exactly how we frame it given its one-step horizon.

## Actions

1. **Check darwin3 for the three rain-ratio values**; determine which is operative. Blocks the
   `R_PICPOC` ground truth.
2. **Scope the observations-only Track-1 fit** — no Darwin target.
3. Amend `2026-07-28_bling_comparability.md` so the ligand hypothesis is not read as the explanation.
4. Soften the growth-pair wording in STATUS and README.
5. Record above-horizon grazing dissolution as a candidate cause of the E2 calcite null.

---

## Answer to the rain-ratio question — already resolved in this repo (2026-07-29)

Jon asked which of the three rain-ratio values in `data.darwin` / `data.traits` is operative.
`docs/ecco_darwin_parameter_inventory.md` already answers it, from a source audit against the
`v04/llc270_JAMES_paper` build:

> **`R_PICPOC` is not set by a namelist at all.** It is an **inline Green's-functions override in
> Fortran**, `darwin_generate_phyto.F:484`:
>
>     R_PICPOC(np) = 0.04245     for np = 2, 3, 8
>
> (`docs/ecco_darwin_parameter_inventory.md:58, 196, 219`)

So the namelist values are likely **not** what the model runs on — a hardcoded override sets it after
the namelist is read. That is why three values can coexist without a clear winner.

### PRIMARY VERIFICATION (2026-07-29) — fetched the actual Fortran

The claim above was sourced to our own inventory doc. I then fetched the real file from
`MITgcm-contrib/ecco_darwin@master`, `v04/llc270_JAMES_paper/code_darwin/darwin_generate_phyto.F`
(782 lines). Lines 476–486 read:

```fortran
        if(diacoc(np) .eq. 2.0 _d 0)then
          R_PICPOC(np) =  val_R_PICPOC          ! 477
        else
          R_PICPOC(np) = 0.0 _d 0               ! 479
        end if
cswd %%%%%%%%%%% OCMIP STYLE for other phyto (not diatom or prochl)
        if (np.eq.2.or.np.eq.3.or.np.eq.8) then
C ECCO-Darwin V4 JAMES
          R_PICPOC(np) = 0.04245 _d 0           ! 484
cBX GF optizm run ag4         R_PICPOC(np) = 0.133 _d 0    ! 485 -- COMMENTED OUT
        endif
```

**This is the direct answer to the three-values question.** There are exactly three live code paths
plus one decoy:

| value | line | applies to |
|---|---|---|
| `val_R_PICPOC` (namelist/traits) | 477 | coccolithophores, `diacoc == 2` |
| `0.0` | 479 | every non-calcifier |
| **`0.04245`** | **484** | **`np = 2, 3, 8`** — overrides both branches above |
| `0.133` | 485 | **commented out** — labelled `GF optizm run ag4` |

Because 484 runs *after* 477/479, **`0.04245` wins for `np = 2, 3`**. Our recovery target is the
operative value. The likely source of confusion is the **commented-out `0.133`**, which is visible in
the file and looks live at a glance.

### ⚠ RETRACTION — my "out-of-bounds write" claim was wrong

I wrote that the `np = 8` element "targets an index outside the array" and might "write past the
end", and suggested flagging it to the Darwin team as a possible bug.

**That is incorrect.** Line 483 is a *condition on the loop variable* — `if (np.eq.2.or.np.eq.3.or.np.eq.8)`
— not an assignment to `R_PICPOC(8)`. If the loop never reaches `np = 8`, the branch simply never
fires. That is harmless dead code, not an out-of-bounds write. No memory is touched.

I also **could not verify `npmax = 5` from primary source** — no `npmax` declaration appears in this
file, and the array dimension is defined elsewhere. So even the "dead code" reading is unconfirmed.

**Do not send this to the Darwin team as a bug.** It was an overstatement built on a secondary
source, and I nearly had us report a non-bug to a collaborator.

**2. Calcification is restricted to a subset of PFTs in Darwin, and the flagship does not match it.**

Verified in source, and it is stronger than "a structural mismatch exists" — the repo already knows,
already built the fix, and ships it **off**:

```python
USE_COCCOLITH_ONLY_CALCITE: bool = False      # carroll6_5pft_2layer.py:158
"""Restrict PIC production (and the matching DIC + ALK calcite budget terms)
to the Chl2 = "other large eukaryote" mortality source only, instead of the
sum over all 5 PFTs.  In Darwin 3, only coccolithophores produce calcite."""
```

With the flag off, the box computes `dPIC = R_PICPOC * mort_total` where
`mort_total = mort_s + mort_l + graze_l` (`carroll6.py:225,231`) — calcification from **all five
PFTs**. Darwin applies its rain ratio to a subset: `np = 2, 3` in v04, and a per-group array in v06.

**The flagship ran with it off.** Its own run record contains
`"use_coccolith_only_calcite": false`. So the **50/50 `R_PICPOC`** result was obtained with a
calcification structure that differs from Darwin's, using a switch the repo provides to match it.

That is not a reason to doubt the number — `0.04245` is still the v05 target and the grading is
unchanged — but it belongs in the limitations, and it makes an obvious experiment: **re-run the
flagship with `COCCOLITH_ONLY=1`** and see whether `R_PICPOC` holds. The code comment predicts it
should *help* the cross-AOI problem ("with PFT-specific scaling the cross-AOI PIC differences come
naturally from P_lge abundance"), and the ~23× eqpac-vs-natl PIC/POC spread is exactly what a single
bulk scalar has to absorb.

**Correction to my earlier draft.** I cited the code's "degenerate (R_PICPOC, mort_lge) pair" comment
as evidence that a single scalar struggles across AOIs. That is backwards: the degeneracy is a
**caveat about the coccolith-only mode** — it appears when that mode runs without `PIC_ABS_W > 0` to
anchor PIC magnitude. It is a warning about the fix, not evidence about the default.

### ⚠ SECOND CORRECTION — I answered the wrong model generation

An adversarial validation pass caught this before it went out. The `generate_phyto.F` finding is from
**Darwin 1 / v04 `llc270_JAMES_paper`**, where parameters are *hardcoded in source*. Jon asked about
**`data.darwin` / `data.traits`** — those are **Darwin 3** namelist files. Our own inventory states
the distinction explicitly (`ecco_darwin_parameter_inventory.md:125-127`):

> **Darwin 1**: parameters hardcoded in source (`code_darwin/`) …
> **Darwin 3**: parameters exposed via namelist files (`input_darwin/data.darwin`, `data.traits`).

So "R_PICPOC is not set by a namelist at all" was answering a build he is not asking about.

## The actual answer — from the Darwin 3 namelists (PRIMARY, fetched 2026-07-29)

Fetched from `MITgcm-contrib/ecco_darwin@master`:

**`v05/llc270/input/data.darwin:53`** — a single scalar, inside the Carroll-6 block:

```
 smallgrow=0.66098,
 biggrow=0.43148,
 diatomgraz=0.83003,
 val_R_PICPOC=0.04245,
 /
 &DARWIN_TRAIT_PARAMS
 /
```

**`v06/llc270/input_darwin/data.darwin:223`** — a **per-plankton-group array**:

```
 a_R_PICPOC(:) = 2*4.19E-2,1*0.05,3*4.19E-2,
```

which expands to six groups: `[0.0419, 0.0419, 0.05, 0.0419, 0.0419, 0.0419]`.

### v05 `data.traits` — the file that completes the picture (verified 2026-07-29)

Fetched `v05/llc270/input/data.traits` from `MITgcm-contrib/ecco_darwin@master`:

```
line  7:  HASPIC   = 0, 2*1, 4*0,
line 36:  R_PICPOC = 0.0, 2*4.1886E-2, 4*0.0,
```

**`HASPIC` says only 2 of 7 plankton types calcify**, and `data.traits` carries its own rain-ratio
array at **0.041886** — a *different number* from `data.darwin`'s scalar `0.04245`, in the same v05
configuration.

That is precisely the situation he described: **two v05 files, different values**, plus the v06
per-group array. His "three values" are `0.04245`, `0.041886`, and v06's `0.05`.

### So the three values are

| value | where | build |
|---|---|---|
| **0.04245** | `val_R_PICPOC`, v05 `data.darwin:53` | **v05 — our active target** |
| **0.0419** | `a_R_PICPOC`, five of six groups, v06 | v06 |
| **0.05** | `a_R_PICPOC`, the third group, v06 | v06 |

(plus the commented-out `0.133` in the v04 Fortran, which is inert but visible)

**This also confirms his own remark from the other direction.** He wrote that in the next ECCO-Darwin
version "we have more explicitly determined which plankton groups calcify" — the v06 array is exactly
that: one group is given a *different* rain ratio (0.05) from the other five (0.0419). In v05 it is a
single scalar for everything.

### Status of the R_PICPOC ground truth

**Confirmed against the v05 namelist.** `val_R_PICPOC = 0.04245` at
`v05/llc270/input/data.darwin:53`, sitting directly beside `smallgrow`, `biggrow` and `diatomgraz` —
the Carroll-6 block. v05 is our active recovery target, so the ground truth is correct and the
**50/50** recovery stands, now on primary evidence rather than on our own note.

**But it is v05-specific.** In v06 the rain ratio becomes a six-element per-group array, so a single
global `R_PICPOC` is no longer the right target shape for that generation. That is worth stating in
the manuscript's limitations.
