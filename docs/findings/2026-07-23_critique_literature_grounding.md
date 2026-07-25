# Critique literature grounding — reviewer claims against the DarwinDiff manuscript

**Date:** 2026-07-23
**Scope:** READ-ONLY external literature verification. For each reviewer-cited work: confirm it
exists, extract exactly what it establishes, and state how it re-scopes our claim. Nothing
fabricated; items I could not confirm from source text are marked as such.

**Verification legend:** ✅ VERIFIED (paper found, citation + DOI confirmed, content read/extracted);
⚠️ FLAG (citation error or caveat the reviewer/author should know about).

---

## 1. Frants et al. — iron source–sink degeneracy ✅ VERIFIED (the key one)

- **Citation:** Frants, M., Holzer, M., DeVries, T., & Matear, R. (2016). "Constraints on the
  Global Marine Iron Cycle from a Simple Inverse Model." *Journal of Geophysical Research:
  Biogeosciences*, 121(1), 28–51.
- **DOI:** 10.1002/2015JG003111
- **What it establishes:** Using a data-constrained steady-state circulation with a simple iron
  model, biogeochemical parameters are fit by minimizing a weighted quadratic mismatch to
  dissolved-iron (dFe) observations including GEOTRACES transects. Central result: **because the
  effective iron sources and scavenging sinks spatially overlap (aeolian iron deposited at the
  surface is redistributed through the water column so the effective source and the scavenging
  sink co-locate), the dFe observations cannot constrain sources and sinks independently.** An
  increase in aeolian source strength is largely compensated by a proportional increase in
  scavenging amplitude without significantly changing dFe gradients where data exist. The data
  therefore constrain only **a *family* of compensating optimal solutions** — the paper spans an
  aeolian source strength of **0.3–6.1 Gmol yr⁻¹**, with the organic scavenging constant
  co-varying roughly in proportion.
- **Why it matters to us:** This is our `alpfe` (aeolian-iron source scalar) ↔ `scav_rat`
  (scavenging) degeneracy, already published as a general property of the marine iron cycle. Our
  compensating-parameter family is **not a novel discovery** — it is the expected behaviour when a
  source and a co-located sink are fit to the same concentration field.
- **Re-scope our claim:** Cite Frants et al. (2016) as prior art for the source–sink degeneracy
  itself; our novelty is the **ECCO-Darwin-specific quantitative characterization** (the Fisher /
  eigenmode / profile-likelihood geometry of *this* model's parameter space) and the
  **observation-design result** — which real absolute anchor (Daniels CP:PP / GEOTRACES iron)
  collapses the degenerate family — not the existence of the degeneracy.

---

## 2. FeMIP — iron model intercomparison ✅ VERIFIED

- **Citation:** Tagliabue, A., Aumont, O., DeAth, R., Dunne, J. P., Dutkiewicz, S., Galbraith, E.,
  Misumi, K., Moore, J. K., Ridgwell, A., Sherman, E., Stock, C., Vichi, M., Völker, C., & Yool, A.
  (2016). "How well do global ocean biogeochemistry models simulate dissolved iron distributions?"
  *Global Biogeochemical Cycles*, 30(2), 149–174.
- **DOI:** 10.1002/2015GB005289 (this is the canonical FeMIP reference; project name "Iron Model
  Intercomparison Project (FeMIP)", SCOR Working Group 151).
- **What it establishes:** First intercomparison of **13 global ocean iron models** against
  GEOTRACES IDP2014 (five basin-scale sections + a >20,000-point global dFe database). The
  documented intermodel spread is large and spans essentially every iron-cycle degree of freedom:
  **total iron input varies ~2 to ~200 Gmol yr⁻¹ (two orders of magnitude)**; even the "well-known"
  atmospheric-deposition source varies by ~an order of magnitude across models; iron **residence
  times** disagree strongly; and models differ in **sources, scavenging formulations, ligand /
  complexation treatment, and biological cycling**. Models that better capture emerging source and
  cycling pathways reproduce observations better, but no consensus parameterization exists.
- **Why it matters to us:** Establishes that iron-cycle parameterizations are **community-wide
  unconstrained**, not an ECCO-Darwin idiosyncrasy. The spread FeMIP documents is the ambient
  uncertainty our identifiability study operates inside.
- **Re-scope our claim:** Cite FeMIP to motivate *why* iron-parameter identifiability is worth
  studying at all (the whole field disagrees on sources/scavenging/ligands/bio-cycling); do **not**
  frame the iron degeneracy as unique to our model or our method.

---

## 3. Park et al. — seasonal-to-multiannual chlorophyll prediction beyond persistence ✅ VERIFIED, ⚠️ YEAR MIS-CITED

- **Reviewer wrote "Park et al., 2026" — no such paper exists.** The described study (seasonal-to-
  multiannual chlorophyll forecast skill exceeding persistence) is unambiguously the **2019 Science
  paper**:
- **Citation:** Park, J.-Y., Stock, C. A., Dunne, J. P., Yang, X., & Rosati, A. (2019). "Seasonal
  to multiannual marine ecosystem prediction with a global Earth system model." *Science*,
  365(6450), 284–288.
- **DOI:** 10.1126/science.aav6634
- **What it establishes:** An initialized global ESM forecast system skillfully predicts observed
  (satellite) chlorophyll fluctuations one season ahead in many regions, and **prediction skill
  *above a persistence forecast* extends beyond 1 year in some regions** — up to ~**24 months** in
  the subtropical/temperate North Atlantic during productive spring/summer/fall seasons, and ~15
  months in the south-central Pacific. Skill arises from simulating the chlorophyll response to
  ENSO and the extratropical winter re-emergence of subsurface nutrient anomalies. (Downstream:
  some fish catches forecastable 2–3 years ahead.)
- ⚠️ **The only genuine 2026 chlorophyll-forecast paper** is Martinez Balbontin, G., Jouanno, J.,
  Benshila, R., Lamouroux, J., Perruche, C., & Ciavatta, S. (2026), "Forecasting seasonal global
  sea surface chlorophyll a with a lightweight data-driven approach," *Biogeosciences* 23, 2601–…,
  **DOI 10.5194/bg-23-2601-2026** — a fast data-driven ~6-month global Chl forecast. It is a
  *different* paper and does **not** carry the "beyond persistence at multiannual leads" point; do
  not substitute it for Park.
- **Why it matters to us:** Park (2019) contradicts any blanket "chlorophyll is near-conserved /
  not predictable beyond persistence" framing. Chl carries real seasonal-to-multiannual
  predictability — but sourced from **dynamical drivers** (ENSO teleconnections, nutrient
  re-emergence), not from Chl persistence itself.
- **Re-scope our claim:** Narrow the emulator "1-step horizon / no rollout skill" statement to what
  it actually is — a property of *our monthly surrogate operator*, which does not carry the
  dynamical mechanisms (ENSO, nutrient re-emergence) that give Chl its multiannual predictability.
  Do **not** state or imply that Chl is intrinsically unpredictable / near-conserved; cite Park
  (2019) as the counter-existence proof and attribute our ceiling to the surrogate, not to the
  field.

---

## 4. Mogen et al. — absolute skill vs. value over persistence ✅ VERIFIED

- **Citation:** Mogen, S. C., Lovenduski, N. S., Yeager, S., Keppler, L., Sharp, J., Bograd, S. J.,
  Cordero Quiros, N., Di Lorenzo, E., Hazen, E. L., Jacox, M. G., & Pozo Buil, M. (2023). "Skillful
  Multi-Month Predictions of Ecosystem Stressors in the Surface and Subsurface Ocean." *Earth's
  Future*, 11, e2023EF003605.
- **DOI:** 10.1029/2023EF003605 (open access; read directly)
- **What it establishes:** CESM2 Seasonal-to-Multiyear Large Ensemble (SMYLE) forecasts DIC,
  dissolved oxygen, and temperature 1–13 months ahead with high skill in key regions and
  "frequently outperforms persistence forecasts." Crucially for the reviewer's point, the paper
  treats **persistence as a strong, mandatory baseline**, not a straw man: *"Persistence forecasts
  … provide regionally valuable predictions that can act as a useful baseline for other forecast
  methods"* and *"Dynamical forecasts … must outperform statistical [persistence] forecasts to
  justify their cost."* The study's explicit aim is to *"assess where and when our dynamic model
  forecasts outperform persistence"* — i.e., dynamic forecasts do **not** beat persistence
  everywhere. High absolute anomaly-correlation skill can therefore coexist with little or no gain
  over persistence in regions where autocorrelation is already high.
- **Why it matters to us:** Relative skill (skill *score* vs a baseline) is baseline-dependent. A
  high absolute correlation is not by itself evidence of a useful forecast/emulator if persistence
  already achieves it.
- **Re-scope our claim:** Whenever we report emulator or model skill, report **both** absolute skill
  **and** skill relative to persistence (and, ideally, damped persistence). Cite Mogen et al. (2023)
  (and the Jacox/Hervieux persistence-baseline lineage it draws on) so that our "beats/does-not-beat
  persistence" statements are framed as the baseline-dependent quantities they are — this directly
  answers the reviewer's "relative skill is baseline-dependent" objection.

---

## 5. Carroll et al. 2020 / 2022 — Green's-functions optimization, no formal parameter uncertainty ✅ VERIFIED (uncertainty point method-inferred)

- **Citations & DOIs (both confirmed):**
  - Carroll, D., Menemenlis, D., et al. (2020). "The ECCO-Darwin Data-Assimilative Global Ocean
    Biogeochemistry Model: Estimates of Seasonal to Multidecadal Surface Ocean pCO₂ and Air-Sea CO₂
    Flux." *JAMES*, 12, e2019MS001888. **DOI 10.1029/2019MS001888.**
  - Carroll, D., et al. (2022). "Attribution of Space-Time Variability in Global-Ocean Dissolved
    Inorganic Carbon." *Global Biogeochemical Cycles*, 36, e2021GB007162.
    **DOI 10.1029/2021GB007162.**
- **What it establishes (methodology):** ECCO-Darwin tunes the biogeochemistry with the **Green's
  Functions method of Menemenlis et al. (2005)** — a **linearized least-squares** minimization of a
  weighted quadratic (model−data) cost function. It adjusts biogeochemical **initial conditions plus
  six model parameters**. The Green's-functions approach is, by construction, **low-dimensional**:
  it "can in practice only be applied to a small number of control variables," each Green's function
  being one forward perturbation experiment. It returns **best-fit (optimized) parameter values**.
- ⚠️ **"No formal uncertainty" — method-inferred, not a quoted disclaimer.** The linearized
  least-squares Green's-functions procedure produces optimized point estimates; the papers report
  tuned parameter values, **not** posterior covariances / formal error bars on those six
  parameters. I could not fetch the full methods text (AGU paywalled the full HTML), so I confirmed
  the method (Menemenlis 2005 linearized least-squares, six parameters, small control space) from
  the abstract/summary and the ECCO-group Green's-functions documentation, and the absence of formal
  parameter uncertainties follows from the method rather than from an explicit sentence I could
  quote. Flagged as such — worth one direct check against the PDF methods section before we lean on
  it in print.
- **Why it matters to us:** Carroll's optima are a linearized, low-dimensional fit **without
  published parameter error bars**, and (per Frants/FeMIP above) they sit inside a degenerate family.
- **Re-scope our claim:** Recovering Carroll's Green's-functions optima is **model-conditional
  validation** — "does our differentiable learner land on the same point the established estimate
  chose" — **not** recovery of a ground-truth parameter set with known uncertainty. State explicitly
  that the target itself is an uncertainty-free point estimate within a degenerate family, so
  agreement is corroboration of method consistency, not proof of true-value recovery.

---

## One-line re-scoping summary per item

1. **Frants (2016, 10.1002/2015JG003111):** degeneracy is prior art → our novelty is the
   model-specific eigenmode quantification + observation-design fix.
2. **FeMIP / Tagliabue (2016, 10.1002/2015GB005289):** iron parameterizations are field-wide
   unconstrained → motivation, not a uniqueness claim.
3. **Park (2019, 10.1126/science.aav6634 — reviewer's "2026" is a mis-cite):** Chl *is* predictable
   at seasonal-to-multiannual leads via dynamics → drop any "Chl near-conserved/unpredictable"
   framing; scope the ceiling to our surrogate operator.
4. **Mogen (2023, 10.1029/2023EF003605):** persistence is a strong baseline → always report absolute
   **and** persistence-relative skill.
5. **Carroll (2020 10.1029/2019MS001888 / 2022 10.1029/2021GB007162):** Green's-functions optima are
   linearized point estimates without formal uncertainty → recovering them is model-conditional
   validation, not ground-truth recovery.

---

## Most important single re-scoping this forces

**Frants et al. (2016) removes any claim that the alpfe/scav_rat compensating family is a novel
finding.** The manuscript must reposition: the degeneracy is textbook iron-cycle behaviour (Frants;
corroborated by FeMIP's field-wide spread); the contribution is the *quantitative, ECCO-Darwin-
specific* identifiability geometry plus the *observation-design* result showing which real absolute
anchor breaks the family.
