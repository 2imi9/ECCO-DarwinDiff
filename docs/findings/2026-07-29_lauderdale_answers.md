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

### 4. The growth pair — softer than "unobservable by construction"

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

Our E2 calcite experiment tested an **Ω-driven** rain-ratio closure and returned NULL. If a large
share of real dissolution occurs **above** the saturation horizon via grazing, an Ω-only closure is
misspecified by construction — a candidate explanation for that null we had not considered.

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

### Two consequences worth raising with him

**1. The `np = 8` assignment is dead code, and possibly an out-of-bounds write.**
`npmax = 5` in this build, so only `np = 2, 3` are valid. The `np = 8` element of that assignment
targets an index outside the array. It is at best a no-op left from a larger-`npmax` configuration;
at worst it writes past the end. **Worth flagging to the Darwin team** — it is their code, and it is
a one-line check for someone with the build in front of them.

**2. `R_PICPOC` is per-phytoplankton-type, and only two of five types calcify.**
The override applies to `np = 2, 3` only. Our 0-D box treats `R_PICPOC` as a **single global scalar**
— see `carroll6_5pft_2layer.py`, whose own comments already note the model "finds a degenerate
(R_PICPOC, mort_lge) pair" and that a single scalar struggles across AOIs.

This connects directly to his remark that the next ECCO-Darwin version "explicitly determines which
plankton groups calcify." The structural mismatch is already present: **Darwin gives calcification to
a subset of PFTs; our surrogate gives it to the bulk.** That is a cleaner statement of the
`R_PICPOC` limitation than "the global value should be regional", and it is checkable rather than
speculative.

### Status of the R_PICPOC ground truth

**Unchanged and safe.** `0.04245` is the value the override writes, so our recovery target matches
what the model runs on. The uncertainty Jon raised is about *where the value lives*, not *what it is*.
Our **50/50** recovery stands.
