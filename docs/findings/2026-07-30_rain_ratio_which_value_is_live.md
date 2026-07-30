# The rain-ratio question, answered from source: 0.041886 on types 2 and 3, and 0.04245 is unreachable

**Date:** 2026-07-30 · **Method:** 4 source lenses over `darwinproject/darwin3` at the commit v05
pins (`24885b71`) plus `MITgcm-contrib/ecco_darwin`, each adversarially verified ·
**Run:** `wf_a92a1280-409` · **Answers the question put to Jon on 2026-07-30.**

> "The three rain ratio values in `data.darwin` and `data.traits` are the one thing I cannot
> resolve on my end. Which value is live changes what I can report."

**Short answer.** The live value is **0.041886**, applied to plankton types **2 and 3 only**, set in
`data.traits`. The published **0.04245** in `data.darwin` is not merely overridden, it is
**unreachable** under v05's compile flags. The anchor does constrain a product, but the multiplier
is **not** the large-phytoplankton fraction: it is the production share of types 2 and 3, which are
**one large type and one small type**.

## 1. Correction to the framing: two of the three are in `data.darwin`

Not one per file. `&DARWIN_RANDOM_PARAMS` and `&DARWIN_TRAIT_PARAMS` are both read from
`data.darwin`, because `pkg/darwin/darwin_readparms.F:52-55` opens that file and passes the same
unit number to `DARWIN_READ_TRAITPARAMS` at `:66`. Only `&DARWIN_TRAITS` comes from `data.traits`.

| variable | group | file | default | v05 status |
|---|---|---|---|---|
| `val_R_PICPOC` | `&DARWIN_RANDOM_PARAMS` | `data.darwin` | 0.8 | set to **0.04245** (`data.darwin:53`). **Dead**, read and discarded |
| `a_R_PICPOC(nGroup)` | `&DARWIN_TRAIT_PARAMS` | `data.darwin` | 0.8 | block present but empty. **Dead**, the allometric generator is never called |
| `R_PICPOC(nplank)` | `&DARWIN_TRAITS` | `data.traits` | none | `0.0, 2*4.1886E-2, 4*0.0` (`data.traits:36`). **LIVE** |

A fourth knob exists and is inert: `val_R_PICPOC_zoo` (`&DARWIN_RANDOM_PARAMS`, default 0.0), set
nowhere in the v05 tree, and `data.traits` zeroes types 6 and 7 regardless.

## 2. Why 0.04245 is unreachable, not just overwritten

This is stronger than "data.traits wins" and it is the part that changes what can be reported.

- `DARWIN_OPTIONS.h:149` defines `DARWIN_RANDOM_TRAITS`, so `darwin_init_fixed.F:356-360` calls
  `DARWIN_GENERATE_RANDOM` and never `DARWIN_GENERATE_ALLOMETRIC`. That kills `a_R_PICPOC`, whose
  only consumer is in the allometric routine.
- `DARWIN_OPTIONS.h:155` defines `DARWIN_NINE_SPECIES_SETUP`. Under it,
  `darwin_generate_random.F:204-213` sets the coccolithophore code `diacoc = 2` only at `np == 9`.
- The enclosing loop is `DO np = 1, nPhoto` and `DARWIN_SIZE.h:26` sets **`nPhoto = 5`**. `np`
  never reaches 9.
- So `diacoc == 2` never occurs, and `darwin_generate_random.F:582-586` takes its `ELSE` branch for
  every phytoplankton: `R_PICPOC(np) = 0.0`.

The generator therefore hands `DARWIN_READ_TRAITS` an array that is identically zero.
`val_R_PICPOC = 0.04245` is parsed from the namelist and then never touches a tendency term.

**Report 0.041886.** The gap to the published 0.04245 is **1.35%**, far inside the Excellent band,
so no recovery verdict changes. But the published optimum and the number the model integrated are
not the same number, and the manuscript should say which it grades against.

**Runtime handle, if Jon prefers not to read Fortran.** Every v05 run writes `darwin_traits.txt`
after both the namelist read and the `hasPIC` gate. That file is the post-precedence ground truth.

## 3. Who calcifies, and what this does to the anchor

`data.traits:36` gives `0.0, 2*4.1886E-2, 4*0.0`: types **2 and 3** carry the ratio, types 1, 4, 5
and the two predators are zero. A one-directional mask enforces it
(`darwin_read_traits.F:196-199`): `hasPIC = 0` zeroes the ratio, `hasPIC = 1` does not create one.

Our box's ordering (`carroll6_5pft_2layer.py:18-19`, indices `I_DIATOM=1, I_LGE=2, I_SYN=3,
I_PROLL=4, I_PROHL=5`) is diatom, large eukaryote, Synechococcus, Pro-LL, Pro-HL, matching
Chl1..Chl5. So Darwin's calcifying types 2 and 3 are **large eukaryotes and Synechococcus**.

**That is one large type and one small type**, which is the substantive correction. The hypothesis
put to Jon was that the anchor constrains `R_PICPOC * f_lge`. It constrains
`R_PICPOC * f_(Chl2 + Chl3)`, and `Chl3` is picoplankton.

Our box applies `R_PICPOC` to all 5 phytoplankton types, so the structural mismatch is real and the
product framing is right. Only the multiplier's identity was wrong.

## 4. This weakens a finding from earlier the same day

`2026-07-30_rpicpoc_bias_tracks_large_phyto_fraction.md` tested `1/f` against the measured per-AOI
bias using `f = Chl1 + Chl2`, diatoms plus large eukaryotes. With the correct calcifying set the
grouping is `Chl2 + Chl3`, and the fit is worse:

| AOI | Daniels cells | 1/f with **Chl1+Chl2** (assumed) | 1/f with **Chl2+Chl3** (correct) | measured bias |
|---|---|---|---|---|
| eqpac | 34 | 1.955 | **4.329** | 1.518 |
| natlsubpolar | 26 | 1.089 | **1.043** | 1.029 |
| southernoceanpac | 0 (unanchored) | 1.004 | 6.329 | 1.268 |

`natlsubpolar` still lands almost exactly (1.043 against 1.029). `eqpac` now **overshoots by about
2.9x**: the corrected law predicts 4.33x inflation and 1.52x is observed.

So the earlier note fit better with the wrong grouping, which is a warning about post-hoc curve
matching on two points and exactly why that note said "not established". The honest position now:

- **Survives:** the anchor constrains a product, the box applies the ratio too widely, and the
  offset is systematic rather than noise.
- **Does not survive:** that the offset's magnitude is predicted by `1/f`. It is not, for the one
  basin where the two groupings disagree.
- **Also relevant:** chlorophyll fraction is a proxy for production share, not equal to it, because
  Chl:C differs between types. The anchor is a production ratio. Closing that gap needs Darwin's
  own production partition, not chlorophyll.

## 5. What to tell Jon

The three values are resolved and he does not need to look them up. Two live in `data.darwin` and
one in `data.traits`; the live one is 0.041886 on types 2 and 3; the published 0.04245 is
unreachable because `nPhoto = 5` means the coccolithophore branch at `np == 9` never executes.

The product framing was right and the multiplier was wrong: it is large eukaryotes plus
Synechococcus, so one of the two calcifiers is picoplankton. That is worth flagging as a question
back to him, because a picoplankton calcifier is an unusual choice and may be a deliberate
stand-in rather than a literal claim about Synechococcus.
