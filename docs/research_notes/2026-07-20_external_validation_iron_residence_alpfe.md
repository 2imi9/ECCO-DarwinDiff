# External-validation research — iron residence time, `alpfe`, and missing observables

**Date:** 2026-07-20 · **Scope:** the three external-validation questions in the overnight brief.
**Method:** a 7-finder + hostile-verify literature workflow (21 sonnet agents, 653 tool calls,
2.25 M tokens). Every load-bearing number was independently re-fetched and checked against primary
text by a separate agent. Numbers are tagged **[primary]** (a verifier read the source text stating
the number) or **[secondary]** (paywalled; corroborated by ≥2 independent citing sources but not the
source itself). Do not upgrade a **[secondary]** number to fact without an institutional-access read.

This note answers *whether our recovered parameters can be checked against the outside world*. Two of
the three questions land as **strong, citable results**; the third lands as a **well-documented
negative**. Net: the External-validation completion number is defensibly movable from 55% toward ~65%
— see the closing table.

---

## Q1 — Iron residence time is the sloppy coordinate of the iron pair. **STRONGLY SUPPORTED, and the framing is a genuine contribution.**

### The degeneracy is already in the ocean-iron literature — stated, but never named

**Tagliabue et al. 2016** (the first iron-model intercomparison, "FeMIP"), *Global Biogeochemical
Cycles* 30(2):149–174, [doi:10.1002/2015GB005289](https://doi.org/10.1002/2015GB005289):

- **13 models** compared against GEOTRACES dissolved-iron sections. **[primary]**
- Modelled dissolved-Fe **residence time spans 3.7 yr (COBALT) to 626.3 yr (BFM)**, mean 144.7 ±
  175.8 yr — a **~170× spread** (text: "~5 to >500 years"). This is a **whole-ocean bulk** value
  (total Fe inventory ÷ total input flux, integrated 0–5500 m), *not* depth-resolved. **[primary,
  Table 2 read directly]**
- **Yet the models agree on concentration:** mean ocean DFe **0.58 ± 0.14 nM (~24% spread)**, while
  total iron input flux roams at **66.9 ± 67.1 Gmol Fe/yr (~100% spread)** and dust flux alone spans
  ~1 to >30 Gmol/yr. **[primary]**
- The authors' own attribution, **verbatim**: *"this results in a wide range of residence times of
  dissolved iron in the models (~5 to >500 years) that reflects different assumptions regarding the
  strength of the sources of DFe to the ocean **compensated by variable scavenging rates in order to
  reproduce the observed DFe concentration**."* **[primary]**

That sentence *is* our degeneracy: the observable (concentration) is pinned; the input-magnitude ↔
scavenging-rate direction is free; residence time is the coordinate that roams along it.

**Somes et al. 2021**, *GBC* e2021GB006948, [doi:10.1029/2021GB006948](https://doi.org/10.1029/2021GB006948),
is an even cleaner, controlled demonstration **[primary, Table 2 read directly]**: five simulations
with atmospheric soluble-Fe deposition varying 1.4–3.4 Gmol/yr and reductive sedimentary release
varying 14.6–117 Gmol/yr (a ~5× source range) were each **manually tuned via the scavenging-rate
constants to hit the same global-mean DFe (0.68–0.73 nM, i.e. 0.70 ± 0.03)**, producing global iron
residence times of **7.49 to 35.9 yr**. Concentration data alone cannot distinguish the five. This is
our identifiability experiment, run inside a full ocean iron model, published.

Two more independent statements of the same compensation:
- **Frants et al. 2016** (JGR-Biogeosciences 121:28–51, [doi:10.1002/2015JG003111](https://doi.org/10.1002/2015JG003111)),
  via inverse modelling: "current dFe observations cannot constrain the iron sources because of local
  compensation between sources and sinks." **[secondary, as quoted in Pasquier & Holzer 2017]**
- **Pasquier & Holzer 2017** (Biogeosciences 14:4125–4159, [doi:10.5194/bg-14-4125-2017](https://doi.org/10.5194/bg-14-4125-2017)):
  iron source/sink parameters "cannot jointly be optimized because of local compensation" — they
  respond with an equifinality-aware *ensemble* of state estimates rather than one optimum. **[primary]**

### The contribution: the field measures this degeneracy but has not named it

Across a targeted search of the FeMIP / SCOR WG151 / Tagliabue–Frants–Holzer–Pasquier–Somes lineage —
including a direct read of the **SCOR WG151 (FeMIP) final report** and the Tagliabue 2017 *Nature*
review — **no paper uses the formal vocabulary "identifiability", "sloppiness", "equifinality", or
"parameter degeneracy"** for the inter-model iron divergence. They use functionally-equivalent domain
language ("compensation between sources and sinks", "essentially unconstrained scavenging rates",
"poorly constrained residence times"). The same formal framework **is** in active use in sibling
fields — soil biogeochemistry (**Marschmann et al. 2019**, *Env. Modelling & Software* 122:104518,
literally titled "Equifinality, sloppiness and emergent minimal structures of biogeochemical models")
and terrestrial ecosystem data assimilation (**Luo et al. 2009**, *Ecological Applications* 19:571–574).

**So naming the FeMIP divergence as a Fisher-information / sloppiness identifiability problem — and
measuring it with a profile-likelihood as we do — is a genuine methodological contribution *to their
field*, not merely a note about our own method.** (Caveat: this is a "not found despite a targeted
search", not a provable true negative.)

### Is there an observational number to check our recovered iron magnitude against?

**Upper ocean — YES, well constrained (sub-annual to a few years):**
- **Black et al. 2020**, *GBC* e2020GB006592, [doi:10.1029/2020GB006592](https://doi.org/10.1029/2020GB006592)
  (the current GEOTRACES synthesis, read in full): **total-Fe** residence time in the upper 250 m is
  **10–100 days for 67% of >100 estimates** (median 33 d, full range 1 d–2.2 yr); **dissolved-Fe**
  specifically is longer and more variable — **~20 days to 20 years, with most zonal means 1–4 yr**.
  **[primary]**
- **Croot et al. 2004** (GRL 31 L23S08, [doi:10.1029/2004GL020153](https://doi.org/10.1029/2004GL020153)):
  6–62 days for total Fe under active Saharan dust plumes (equatorial Atlantic). **[primary, abstract]**
- **Hayes et al. 2015** (GCA 169:1–16, [doi:10.1016/j.gca.2015.07.019](https://doi.org/10.1016/j.gca.2015.07.019)):
  Th-isotope-derived dissolved-Fe residence time ~6–12 months in the surface at Station ALOHA; the
  same study is cited (with Boyle 2005) for a Pacific dissolved-Fe range of **0.5–17 yr** (corrected
  during verify from a mis-stated ">10 yr"). **[secondary]**

**Deep / whole ocean — NO single settled observational number:**
- **Hayes et al. 2018** (GBC 32:1294–1311, [doi:10.1029/2017GB005839](https://doi.org/10.1029/2017GB005839)):
  a ²³²Th-supply "replacement time" of **6 ± 3 yr** for the GA03 North Atlantic section, integrated to
  4 km. **[primary]**
- **Bergquist & Boyle 2006** (GBC 20 GB1015, [doi:10.1029/2005GB002505](https://doi.org/10.1029/2005GB002505)):
  **270 ± 140 yr** for deepwater DFe along the aging NADW flow path (and 1–5 months at the surface).
  **[secondary]**

These deep estimates are **regional and disagree by more than an order of magnitude** (~6 yr GA03 vs
~270 yr NADW). There is **no whole-global-ocean observational residence-time number** to place our
recovered iron magnitude against — only the upper-ocean envelope (sub-annual to a few years) and the
model spread. **This bounds the claim:** our recovered iron *magnitude* can be sanity-checked against
the observed upper-ocean residence-time envelope, but it cannot be validated against a settled
deep/whole-ocean number, because that number does not observationally exist. Model-spread ranges
(Tagliabue 5–500 yr) are *plausibility*, not a constraint — exactly the distinction the brief demanded.

### The observable that would break the degeneracy (given concentration cannot)

- **The spatial GRADIENT of GEOTRACES sections**, not the global mean: reproducing a steep near-source
  gradient requires *both* a high local source *and* a compensating high local scavenging, which a
  low-source/low-scavenging tune cannot mimic (Somes et al. 2021). **[primary]** This is the single
  most actionable finding for Track-1: our 0-D box homogenizes and therefore *destroys* exactly this
  discriminating signal — the same surrogate-gap wall STATUS.md already documents.
- **²³⁰Th / ²³⁴Th** measure a *removal rate* by construction (²³⁰Th produced at a known constant rate
  from ²³⁴U; ²³⁴Th deficit gives days-to-weeks export), so they constrain the flux, not the standing
  stock (Francois et al. 2004; Savoye et al. 2006). **[primary / secondary]**
- **Dissolved δ⁵⁶Fe** apportions iron *fluxes* by source: Conway & John 2014 (*Nature* 511:212,
  [doi:10.1038/nature13482](https://doi.org/10.1038/nature13482)) attribute GA03 dissolved Fe to dust
  71–87%, non-reductive sediment 10–19%, reductive sediment 1–4%, hydrothermal 2–6%. **[primary]**
- **Dissolved Al inventory inversion** gives a dust-deposition flux *independent of any Fe data*
  (Al's scavenging residence time is externally calibrated; Han et al. 2008). **[secondary]** — a
  direct external check on the *input-magnitude* side of the degeneracy.

### Quantitative companion — our recovered τ (Job 2, `docs/findings/iron_residence/`)

Computed τ = DFe/(alpfe·PHI_DUST) per AOI along the alpfe profile under the real-GEOTRACES-iron
loss (Explorer job `8510828`; artifacts `tau_{eqpac,natlsubpolar,southernoceanpac}.json`). Result:

| AOI | alpfe\* | profile | τ (data-consistent band) | τ roam in band | τ roam full grid |
|---|---|---|---|---|---|
| eqpac | 0.826 (≈Carroll 0.928) | **valid, CURVED** | **~4–7 days** | 1.7× | 3.5× |
| natlsubpolar | 0.989 (rails to bound) | boundary-rail | ~5–8 days | 1.6× | 5.5× |
| southernoceanpac | 1.00 (rails to bound) | boundary-rail | ~0.7 day (HNLC) | 1.1× | 3.3× |

Two findings, both supporting Q1:

1. **The box's surface iron residence time is ~1–8 days** — the same order as the *observed
   upper-ocean* Fe residence-time envelope (Black 2020: 10–100 d; Croot 2004: 6–62 d), and nowhere
   near the whole-ocean 5–500 yr model range. Correct: the 0-D box is a surface mixed-layer object,
   PHI_DUST is a surface source, so τ is a surface residence time and it lands where surface
   observations do. A clean physical sanity check on the box's iron budget.
2. **Within the data-consistent band, τ barely roams (1.1–1.7×)** because the real GEOTRACES
   *section structure* constrains alpfe well per-AOI (recovers to 0.83–1.00, near Carroll). The 100×
   FeMIP residence-time spread is a **global, concentration-only** phenomenon; our per-cell fit to
   spatially-resolved section data **escapes it** — the concrete realization of Somes 2021's point
   that the section *gradient*, not the global mean, breaks the degeneracy. (natl/SO rail alpfe to
   its physical upper bound 1.0 — the box under-supplies iron there relative to the real data — the
   same boundary-solution pattern as diatomgraz, not a convergence failure.)

---

## Q2 — `alpfe` is a near-unity scalar on already-soluble iron, **not** a solubility. **DECISIVELY RESOLVED.**

The chain is now airtight and mostly **[primary]** from source code and namelists:

1. **Darwin3's own iron docs** define `alpfe` as "solubility of Fe dust", default **0.04**, and
   instruct: *"set it to 1 if the deposition rate in ironfile is already of soluble iron."*
   ([darwin_iron.rst](https://github.com/darwinproject/darwin3/blob/darwin/doc/phys_pkgs/darwin_iron.rst)) **[primary]**
2. In the source it is a **single scalar multiply** on the ironfile field, with no dust-to-Fe
   conversion anywhere in the routine (`darwin_forcing.F` line 483). **[primary]**
3. The production **ECCO-Darwin v05 llc270** config (the Carroll et al. 2022 solution) forces with
   `llc270_Mahowald_2009_soluble_iron_dust.bin` — the **already-soluble** product — and sets
   **`ALPFE = 0.92831`**, not the 0.04 code default. `darwin_inscal_iron = 1000` is a separate
   unit-conversion multiplier, ruling out unit-scaling as the reason. **[primary, namelist read]**
4. **Carroll et al. 2020** (JAMES, [doi:10.1029/2019MS001888](https://doi.org/10.1029/2019MS001888))
   Table 1 lists the Brix et al. 2015 baseline as **1** and the Green's-function optimum as **0.9283**.
   **[primary]** **0 of 20+** ecco_darwin configs use a total-dust product; all use the soluble one.

**Conclusion:** `alpfe ≈ 0.93` is a **near-unity dimensionless correction on an already-soluble iron
flux**, exactly as hypothesized — it is emphatically *not* a ~1% physical solubility. Our
`src/darwindiff/carroll6.py` docstring calling it "iron dust solubility (–)" is **materially wrong**
and should read something like *"scalar correction on the already-soluble Mahowald-2009 iron
deposition flux (≈1; Carroll GF optimum 0.928)."* (Small daytime fix — see next steps.)

### What `alpfe` would match *if* it were a solubility (it isn't)

Published aerosol/dust-iron **fractional solubility**: <1–2% for fresh mineral dust (Jickells et al.
2005, *Science* 308:67, [primary]); the classic offline chain is "dust × 3.5% Fe by weight × ~2%
soluble", with the 2% flagged as an underestimate in HNLC regions (Hamilton et al. 2019, GMD 12:3835,
[primary]); a transport-integrated global mean of **3.1%** dust-Fe dissolving (Scanza et al. 2018, ACP
18:14175, [primary]); and a full **0–90%** aerosol range depending on source/aging (Sholkovitz et al.
2012, [secondary — paywalled]). Darwin's own ancestor value is **α = 0.01 (1%)** in Parekh's model.
None of these is ~0.93. The number only makes sense as a scalar on already-soluble iron.

### Two contradictions with the brief, surfaced

- **Citation error in our notes.** The brief cites Darwin's iron basis as "Parekh, Follows & Boyle
  2006, [doi:10.1029/2005PA001258](https://doi.org/10.1029/2005PA001258)". That DOI actually resolves
  to **Parekh, Follows, Dutkiewicz & Ito 2006, "Physical and biological regulation of the soft tissue
  carbon pump," *Paleoceanography*** — four authors, a glacial-CO₂ paper, **not the iron model.** The
  real iron-model papers (confirmed against Carroll 2020's own reference list) are **Parekh, Follows &
  Boyle 2005** (GBC 19 GB2020, [doi:10.1029/2004GB002280](https://doi.org/10.1029/2004GB002280)) and
  **Parekh et al. 2004** (GBC). Fix this citation wherever it appears (memory + any draft).
- **The "cleanest route" to externally validating `alpfe` is more nuanced than the brief assumed.**
  Because Darwin applies **no** dust→Fe mass-fraction step (`alpfe` is the *only* multiplier),
  re-forcing with a **total-dust** product (Mahowald 2006) would make the recovered scalar a composite
  of (Fe-content 3.5% × solubility), **not solubility alone** — unless a 3.5% Fe conversion is applied
  upstream, or a **total-*iron*** (not total-*dust*) deposition product is sourced. So the route exists
  but needs one extra upstream step to make `alpfe` map onto a published solubility. **[primary]**

---

## Q3 — No observing-system product constrains `diatomgraz` or the growth pair. **Well-documented negative; confirms "unobservable by construction".**

- **diatomgraz (diatom grazing/palatability):** no diatom-specific — or even reliably size-fractionated
  — global grazing/mortality product exists. The only global synthesis is **Landry & Calbet 2004**
  (ICES JMS 61:501, [primary]): 788 bulk-chlorophyll dilution experiments (oceanic μ = 0.59 d⁻¹,
  grazing m = 0.39 d⁻¹, 69.6% of primary production grazed daily), which cannot be attributed to
  diatoms, and which states outright there are **"no established protocols for making such rate
  measurements from ships or satellites."** **Mouw et al. 2017** (Front. Mar. Sci. 4:41, [primary]):
  **0 of 14** satellite phytoplankton-functional-type algorithms retrieve any *rate* — all return
  biomass/abundance.
- **Smallgrow / Biggrow (size-class growth rates):** the one satellite growth-rate diagnostic
  (CAFE/CbPM μ = NPP/C_phyto) exists only at **bulk-community** resolution; the one size-class-resolved
  production product (**Uitz et al. 2010**, GBC 24 GB3016, [primary]) is by construction
  **biomass(Chl)-driven** and its authors report that microphytoplankton production **"mostly mimics"**
  total production — i.e. it carries no independent growth-rate signal. Kostadinov et al. 2023 gives
  size-partitioned *carbon* (biomass only). PACE (since 2024) adds hyperspectral community composition
  but still no rate. Dividing a size-partitioned production field by a size-partitioned biomass field
  would inherit shared ocean-color retrieval error, not a clean constraint.

**Conclusion:** `diatomgraz` and the growth pair remain **unobservable by any current observing-system
product** — this *confirms* the STATUS.md "unobservable by construction" framing rather than opening a
new avenue. A valid, thorough "we looked and it does not exist."

---

## What we could NOT establish (honest gaps)

- **No whole-global-ocean observational Fe residence time** exists (Q1). Deep estimates are regional
  and span ~6 yr to ~270 yr. Our recovered magnitude can be checked against the *upper-ocean* envelope
  only.
- **Several primary texts were paywalled** and are carried at **[secondary]** confidence with ≥2
  corroborating sources: Hayes 2015/2018 numbers beyond what a citing paper quotes, Bergquist & Boyle
  2006 (270 yr), Sholkovitz 2012 solubility range, Mahowald 2006/2009 methods sections, Baker & Croot
  2010. Do not cite their exact numbers as fact without an institutional read.
- **Mahowald 2009's own "~1–2%" solubility figure and its soluble-iron construction method** could not
  be read first-hand (Annual Reviews bot-wall). We rely on Darwin3's operational definition instead.
- **The Fe:Al box-inversion → alpfe-check link** (Q1 observable) is assembled from separately-confirmed
  pieces, not one paper that states it as a single argument.

---

## Ranked next experiments

1. **[cheap, tonight] Iron residence-time walk along the sloppy eigenvector** (Job 2, staged): compute
   τ = DFe/(alpfe·Φ_dust) along the alpfe profile and show τ roams while DFe stays pinned — the *local*
   analogue of Tagliabue's spread. Frame as analogy (0-D surface box vs whole-ocean), not a
   like-for-like τ. **This is the quantitative companion to Q1 and its interpretation is now settled by
   the literature above.**
2. **[high value, real contribution] Write the FeMIP-as-identifiability framing** into the manuscript:
   Tagliabue's own numbers (170× residence spread / 24% concentration / 100% flux) + Somes 2021's
   controlled 5-run demonstration, cast as a profile-likelihood/sloppiness result, is a contribution to
   the *ocean-iron* community, which has the phenomenon but not the vocabulary.
3. **[medium, unlocks external `alpfe` check] Re-force with a total-iron (or 3.5%-adjusted total-dust)
   product** so the recovered scalar becomes comparable to a published fractional solubility. Needs the
   upstream Fe-fraction step (Q2 nuance).
4. **[decisive but blocked] Add a GEOTRACES section-*gradient* objective** (not point concentrations)
   to Track-1 — the one observable Somes 2021 shows discriminates source from scavenging. Blocked by
   the surrogate gap: the 0-D box homogenizes and cannot represent a gradient. This is a Track-2 (spatial
   UDE) task, and it re-motivates Track-2 precisely.
5. **[fix] Correct `carroll6.py`'s `alpfe` docstring** and the Parekh-2006→2005 citation everywhere.

---

## Provenance

Workflow `wf_8e0d55dd-563`, 2026-07-20. 7 finders (67 claims) + 14 hostile verifications. Verify pass
confirmed all core-thesis claims against primary text and caught three finder errors (Somes ligand %
mis-attributed to the wrong experiment → corrected to 9.2%/3.9%; Hayes Pacific "0.5–17 yr" not
">10 yr"; a Black 2020 Fig-3 grouping detail refuted). Full agent transcripts in the workflow journal.
