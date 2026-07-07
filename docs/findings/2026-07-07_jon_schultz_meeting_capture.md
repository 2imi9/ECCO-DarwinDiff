# Meeting capture — Jon Lauderdale + Cristina Schultz, 2026-07-07

**Source:** fragment notes taken live during the meeting (terse). Captured, organized, and each item
**marked by research-decision value** and cross-checked against the repo (a 4-agent grounding pass,
`verify`-level, high confidence). This is authoritative PI feedback — the physics is Jon's; the repo
cross-checks are ours.

Legend: **[DECISION]** = changes what we build/claim · **[CONFIRM]** = validates a current direction ·
**[ACTION]** = something they asked us to produce · **[OPEN]** = question left for us / next meeting.

---

## 1. IRON — the load-bearing correction  **[DECISION]**

**What Jon/Cristina said (verbatim, stitched):** *"The ECCO-Darwin model is fed by a **soluble** iron
product, not a dust-iron product, so the [solubility] value is **one**. It should be **spatially
homogeneous** — that value should be 1 and homogeneous because ECCO-Darwin already contains the spatial
variability [in the forcing field]. The iron dust product gives soluble iron because the model computes
it. Iron is presumed, not actually observable."*

**Repo cross-check — this is a real MISMATCH in our box (high confidence):**
- Our DFe source term everywhere is `dDFe = alpfe * PHI_DUST - scav_rat·DFe·POC - fe_uptake`
  (`carroll6.py:221/282/405`, `transport.py:85`, `carroll6_5pft_2layer.py:452`). `alpfe` **multiplies a
  fixed scalar** `PHI_DUST = 5e-5` (`carroll6.py:68`) that carries **no** spatial variability.
- `alpfe` is a **learnable, per-cell-capable** parameter (bounds 0.05–1.0, Carroll 0.928,
  `carroll6.py:119-123`), literally documented as "iron dust solubility."
- GEOTRACES soluble iron (`Fe_S_CONC`) enters **only as an observational loss constraint**
  (`geotraces_loader.py:14-18,97`), never as the DFe forcing — the exact inversion of Jon's picture.

So our box does the opposite of Jon's model on **both** counts: it puts a tunable knob where solubility
should be a fixed 1, and it omits the spatial iron field that supplies the real variability.

**External-literature confirmation (VERIFIED against primary sources — Darwin3 docs + the actual v05/v06
config files, adversarially checked, CONFIRMED):**
- Darwin3 iron doc, verbatim: *"alpfe is the solubility of iron dust; **set it to 1 if the deposition rate
  in [ironfile] is already of soluble iron.**"* `alpfe` is a **single global scalar** (`DARWIN_PARAMS`),
  not a spatial field; spatial iron variability lives in the `ironfile` deposition field + internal
  ligand/scavenging chemistry.
- **v05 (our recovery target) IS fed soluble iron:** `ironfile = 'llc270_Mahowald_2009_soluble_iron_dust.bin'`.
  Yet Carroll's GF calibration **retained `ALPFE = 0.92831`** — a ~7% residual *scale* on the soluble
  product (deck: 1.0 → 0.927), **not** "93% of dust dissolves." **v06 sets `alpfe = 1.0`** with a soluble
  product (Hamilton 2020) — exactly Jon's prescription.
- So `alpfe` is a **dimensionless scale on the already-soluble iron forcing**, physical prior **1.0**; the
  bare gloss "iron dust solubility" is misleading (invites a false ~1–2% comparison). Our box's
  `alpfe·PHI_DUST` is a **faithful** 0-D reduction of Darwin3's surface source — the real gap is that
  **`PHI_DUST` is a constant scalar** while Darwin's `ironfile` is a **spatial** soluble-iron field.

**Research decision (refined by the literature — do NOT bluntly fix alpfe=1):**
- **Keep `alpfe` as a global scalar** (it already is one, in Darwin and in our box). For **v05 recovery**,
  do **not** fix it =1 — v05's ground truth is 0.928; report it as recovering a *near-unity global scale
  residual*, and state the *physical prior is 1.0* (v06 adopts it). Re-gloss the registry:
  "dimensionless scale on the (already-soluble) iron-deposition forcing," not "iron dust solubility."
- **The real Track-2 forcing fix:** replace the constant `PHI_DUST` with the **spatial soluble-iron
  deposition field** (the Mahowald/Hamilton product), passed through the existing `dust=` kwarg
  (`transport.py:42-68` already broadcasts a field). This is what "ECCO-Darwin already contains the spatial
  variability" means — put it in the forcing, keep `alpfe` a scalar.
- **The learned iron closure should target SCAVENGING, not solubility.** Solubility is already in the
  forcing; the genuine spatial iron physics is scavenging (free-Fe′ + ligand partition, particle-weighted).
- **Honesty caveat:** `alpfe`'s recovery profile is flat/one-sided (initialization-anchored) — the
  *expected* signature of a well-specified homogeneous forcing property. Claim "consistent with a
  homogeneous forcing scalar," not "sharply data-identified."
- **Iron observability (Jon: "presumed, not observable"):** dFe is sparse (~16k points IDP2021, ~70% in the
  upper 500 m, Southern-Ocean austral winter essentially unsampled). A GEOTRACES held-out test can
  constrain a **homogeneous scalar** but **cannot verify a spatial field** — the honest figure is
  model-vs-obs along GEOTRACES **sections/profiles** (Tagliabue-2016 style), NOT a dense global map;
  caption any held-out-iron result as station-level, upper-ocean, non-winter-biased.

---

## 2. CALCITE / PIC:POC — the spatial-variation framing is confirmed  **[CONFIRM]**

**What they said:** *"Different region, different degree — yes, different ratio in different regions makes
sense, and the model does simulate it. The PIC:POC ratio is first-order; it depends on environmental
conditions and carbonate chemistry, and on phytoplankton composition. In the bulk sense the value varies
if you look at the whole community. Having a spatially-varying ratio makes sense."*

**Repo cross-check:** the code already encodes exactly this — composition (via the `Chl2` coccolithophore-
proxy pool) and a spatial thermal-window ratio (`USE_ENV_RAIN_RATIO`, `carroll6_5pft_2layer.py:231`,
which reproduced the 3-basin spread in a probe). The single-scalar bulk `R_PICPOC` is
**mathematically incapable** of the ~100× basin spread (`per_pft_picpoc_experiment.py`), and per-cell
recovers it 9/10 vs global-scalar 0/10.

**NEW validation this session — composition alone is REFUTED against Darwin's real Chl field**
(`scripts/per_pft_real_chl2_validation.py`, native caches, CPU): the earlier `per_pft_picpoc_experiment.py`
showed composition *could* explain the ~100× spread *if* the calcifier fraction were 3.3/67.6/0.7% — but it
**assumed** those fractions. Reading Darwin's **actual** Chl2 (coccolithophore-proxy) field:
- calcifier fraction is **nearly flat — 1.4×** (eqpac 0.153 / natl 0.134 / SO 0.109),
- while bulk PIC:POC spans **113×** (0.034 / 0.729 / 0.006),
- so the implied per-calcifier R is **NOT constant — 92× spread** (0.22 / 5.4 / 0.06).

Chl2 *is* the best PIC-correlate in eqpac (r=0.50) and SO (r=0.73), so it's a fair calcifier proxy. The
conclusion: **composition (which PFTs are present) does NOT carry the basin spread** — the spread is
carried by the **per-calcifier calcification *efficiency*, which varies with environment / carbonate
chemistry.** This **adjudicates Jon's two statements** ("depends on composition" vs "depends on
environmental condition and carbonate chemistry") — the data says **environment dominates**; and it
explains why the code's thermal-window ratio (`USE_ENV_RAIN_RATIO`) reproduced the spread while cocco-only
composition gating didn't (§6).

**Research decision:** the **Track-2 `calcite_closure`** is the go-forward learnable, and it should be
**environment-driven** — feed it SST, Ω_calcite, PAR, Fe-limitation (composition/`Chl2` at most a minor
modulation), targeting a **regional PIC:POC field**. Keep the coccolith-only per-PFT gating **shelved**
(refuted here and in §6).

---

## 3. The convergence — identifiability tracks physics (source vs sink)  **[DECISION — framing]**

The single most valuable synthesis: **Jon's physics and our identifiability map are the same result**,
and the one apparent wrinkle resolves cleanly.

| Parameter | Term in the equations | Physics (Jon) | Identifiability (ours) |
|---|---|---|---|
| `alpfe` (iron solubility) | `alpfe · PHI_DUST` — scalar × **constant** flux | homogeneous, ≈1 | **global-scalar recovers 10/10**, method-independent (DINN = global = Nelder-Mead ≈ Carroll) |
| `scav_rat` (iron scavenging) | `scav_rat · DFe · POC` — × **local fields** | (spatial by mechanism) | **requires per-cell** (8/10 vs 0/10) |
| `R_PICPOC` (calcite ratio) | `R · mortality`, region-dependent | spatially varying | **requires per-cell** (9/10 vs 0/10) |

**The rule:** *source-magnitude* parameters that multiply a constant (`alpfe`) are homogeneous and
globally recoverable; *sink/ratio* parameters whose terms multiply **local, spatially-varying tracer
fields** (`scav_rat`, `R_PICPOC`) are genuinely spatial and require per-cell. So `scav_rat` being "an iron
param that needs per-cell" **confirms** rather than contradicts "iron solubility is homogeneous" — once
you separate source from sink.

**Why it matters:** this reframes Paper 1's "per-cell is load-bearing" from a fitting fact into a
**physics fact** — the per-cell requirement is the empirical fingerprint of the surrogate gap (the 0-D box
has no transport, so terms depending on local fields can only be fit by giving each cell its own
parameter). **Track-2 thesis, sharpened:** does adding ECCO-Darwin transport let `scav_rat` and `R_PICPOC`
recover as (near-)homogeneous parameters the way `alpfe` already does on the 0-D box? That is the E2 gate,
now with a physics story behind it.

**The literature confirms and sharpens the axis (verified):** the correct split is **not** "iron vs
calcite" but **"homogeneous forcing-property *scalar* (`alpfe` solubility) vs spatial process-*rate* acting
on a spatial field."** In Darwin `alpfe` is literally a single `DARWIN_PARAMS` scalar, while `scav_rat`
multiplies the particle field (Honeyman/Parekh scavenging on `POC`) and `R_PICPOC` is a per-PFT/regional
array — so both are genuinely spatial. `scav_rat` "straddling" (iron *and* per-cell) is therefore not a
wrinkle: it's an iron **rate on a spatial field**, distinct from the homogeneous solubility **scalar**.
The identifiability split is **predicted by Darwin's parameter algebra**, not an artifact.

---

## 4. What they asked to SEE — spatial-distribution maps  **[ACTION]**

Repeated asks: *"what is the spatial distribution," "assume there is some spatial distribution to
visualize," "spatial variability on GEOTRACES."* They want **maps, not numbers.**

**All the data is on disk (D:), CPU-plottable now** (loaders verified live in the grounding pass):
- **GEOTRACES surface dissolved iron** — `geotraces_loader.bin_to_grid("Fe_D", aoi, depth_max=50)`.
  Surface cells: **eqpac 25, N.Atlantic 13, S.Ocean 14** (confirms Jon's "~14"); globally ~2% coverage.
  The map *will* look sparse — that is the honest, on-message point (the identifiability ceiling).
- **Modeled DFe field** — native caches `native_targets_{eqpac,natl,SO}.pt` → `fet_binned` per cell w/ lat/lon.
- **Per-AOI PIC:POC ratio** — same caches, `pic_binned/poc_binned` → eqpac 0.034 / natl 0.73 / SO 0.006
  (reproduces the ~100× spread; real in the cached fields).
- **Chl2 calcifier fraction** — global from `bin_average` (Chl1–5, 44,730 ocean cells); per-AOI from caches.
  **The strongest figure** — directly the per-PFT mechanism (bulk PIC:POC = R × calcifier fraction).

**Action — DONE this session:** `scripts/spatial_distribution_figures.py` →
`docs/findings/figures/2026-07-07_spatial/`:
- `per_aoi_fields.png` — per-AOI PIC:POC / DFe / calcifier-fraction maps (real spatial structure).
- `global_calcifier.png` — global Chl2 fraction (the composition field — visibly flat ~0.1–0.15).
- `geotraces_iron.png` — GEOTRACES surface dFe coverage (~4.7k samples; sparse by design, the honest point).
- `composition_refuted.png` — bulk PIC:POC (113×) vs calcifier fraction (flat 1.4×) vs implied R (92×).

---

## 5. SILICATE — reframe, don't drop  **[CONFIRM + rename]**

Jon: *"silicate we don't include."* Correct — the box has **no dissolved-silicate tracer and no
Si-limitation on growth** (5-tracer state `[DFe, Ps, Pl, POC, PIC]`). **But** plan item 2's "dense-silica
targets" refers to **biogenic silica (POSi / bSi)** — a *diatom output diagnostic* (`silica.py`, a
diagnostic not a tracer) used to constrain `diatomgraz`, **not** a silicate nutrient. **Decision:** rename
"dense-silica targets" → **"dense biogenic-silica (POSi/bSi) diagnostic targets for diatomgraz"** in all
comms to avoid conflation. It's currently unstaged, so nothing live is misaligned.

---

## 6. SOUTHERN OCEAN — a distinct regime  **[CONFIRM]**

Jon: *"Southern Ocean is a particularly different ocean."* Matches the code strongly: SO is a first-class
AOI with the **lowest PIC:POC (0.0067)**, **no Daniels calcite coverage**, a **contaminated ratio target**
(needs `RATIO_MAX=2`), and it recovers the **full iron pair 5/5 alone at native resolution**. **Decision:**
keep SO distinct; secure a real SO calcite anchor before using it in any calcite gate; it's the strongest
single-AOI iron testbed.

---

## 7. Open questions left for us  **[OPEN]**

- **Per-PFT vs per-time parameterization** — Jon asked whether the ratio parameter should be set
  per-functional-type or per-time, constant or time-varying. (Feeds the `calcite_closure` design.)
- **Which Darwin version's coccolithophore treatment to anchor** — *"Darwin simulates where
  coccolithophores are, confused by versions."* Darwin 3 has a dedicated Cocco group; the box proxies it
  with `Chl2`. Ask Jon which version to target.
- **"Definition of ocean weathering, considering ocean dynamics"** — a concept Jon raised; not reflected
  in the code. Flag for clarification (likely about iron/alkalinity sources).
- **"Parameter recovery detailed"** — they want more detail on the recovery method (a presentation ask).

---

## Research-decision summary (ranked by impact)

1. **[IRON — VERIFIED]** `alpfe` is a global scalar on an already-soluble forcing (Darwin3 doc; v05 Mahowald
   soluble file, `ALPFE=0.928`; v06 `alpfe=1.0`). **Don't fix =1 for v05 recovery** (truth 0.928); re-gloss
   as "scale on the soluble-iron forcing," physical prior 1.0. Real Track-2 fix = spatial soluble-iron
   **forcing field** replacing constant `PHI_DUST`; the **learned iron closure targets scavenging**, not
   solubility. **← biggest**
2. **[FRAMING — VERIFIED]** Headline axis = **homogeneous forcing *scalar* (alpfe) vs spatial process-*rate*
   on a spatial field (scav_rat·POC, R_PICPOC)** — the identifiability split is *predicted by Darwin's
   parameter algebra*. Per-cell requirement = surrogate-gap fingerprint; E2 = does transport homogenize
   `scav_rat`/`R_PICPOC`? (Caveat: alpfe profile is flat/initialization-anchored — claim "consistent with
   homogeneous," not "sharply identified.")
3. **[CALCITE — VALIDATED]** Composition alone is **refuted** against real Chl2 (fraction flat 1.4× vs bulk
   113×). `calcite_closure` = **environment-driven** (SST, Ω, PAR, Fe-lim), regional field; coccolith-only
   gating stays shelved.
4. **[ACTION]** Ship spatial-distribution figures — but per the iron-lit, GEOTRACES iron as a **sparse
   section/coverage** map (Tagliabue-style), NOT a dense global field; annotate the ~13/14/25-cell sparsity.
5. **[SILICATE]** Rename plan item 2 to "biogenic-silica (POSi/bSi) diagnostic."
6. **[SO / OPEN]** SO distinct + secure a real SO calcite anchor; resolve per-PFT-vs-per-time and the
   Darwin-version question with Jon.

*Iron-literature research pass: COMPLETE and folded in above (verified against Darwin3 docs + v05/v06
config). Calcite composition validation: COMPLETE (`per_pft_real_chl2_validation.py`).*
