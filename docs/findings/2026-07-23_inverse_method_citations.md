# Inverse-method / identifiability baseline citations

Issue #117 — reproducibility appendix + inverse-method baseline citations.

Compiled 2026-07-23. Purpose: give the manuscript a defensible citation trail for
every inverse-method and identifiability technique it uses, and for the baseline it
grades against. Each DOI below was checked against the publisher's resolved article
page (or the DOI resolver directly). Verification status is stated per entry; nothing
here is a guessed DOI.

Paper context (for the "supports" column, not re-derived here): DarwinDiff recovers
the four observable Carroll-6 parameters {`alpfe`, `scav_rat`, `diatomgraz`,
`R_PICPOC`} with a per-cell neural network feeding a differentiable 0-D box, graded
against Carroll et al.'s published Green's-functions optima. The identifiability
section uses profile-likelihood (flat = structural / curved = practical
non-identifiability), Fisher/Hessian "sloppiness" eigenspectra, and an
Ensemble-Kalman-Inversion posterior. The iron pair (`alpfe`, `scav_rat`) is
degenerate: concentration constrains the source/sink *combination*, not the
individual rate.

## Citation table

| # | Topic | Full citation | DOI | Verified | What claim it supports |
|---|-------|---------------|-----|----------|------------------------|
| 1 | Profile-likelihood identifiability | Raue, A., Kreutz, C., Maiwald, T., Bachmann, J., Schilling, M., Klingmüller, U., & Timmer, J. (2009). Structural and practical identifiability analysis of partially observed dynamical models by exploiting the profile likelihood. *Bioinformatics*, 25(15), 1923–1929. | `10.1093/bioinformatics/btp358` | Yes | Grounds our profile-likelihood test and its interpretation: a profile that stays flat along a parameter direction indicates *structural* non-identifiability, while a bounded-but-shallow (curved) profile indicates *practical* non-identifiability. |
| 2 | Sloppiness eigenspectra (systems biology) | Gutenkunst, R. N., Waterfall, J. J., Casey, F. P., Brown, K. S., Myers, C. R., & Sethna, J. P. (2007). Universally sloppy parameter sensitivities in systems biology models. *PLoS Computational Biology*, 3(10), e189. | `10.1371/journal.pcbi.0030189` | Yes | Supports the Fisher/Hessian eigenspectrum analysis: multiparameter fits generically have eigenvalues spread evenly over many decades, so only a few "stiff" parameter combinations are constrained — the empirical precedent for our sloppy spectrum. |
| 3 | Sloppiness — information-geometry foundation | Transtrum, M. K., Machta, B. B., & Sethna, J. P. (2011). Geometry of nonlinear least squares with applications to sloppy models and optimization. *Physical Review E*, 83(3), 036701. | `10.1103/PhysRevE.83.036701` | Yes | Provides the model-manifold ("hyper-ribbon") theory behind stiff/sloppy directions, justifying our reading of the Fisher spectrum's sloppy eigenvectors as the degenerate parameter combinations. |
| 4 | Ensemble Kalman Inversion | Iglesias, M. A., Law, K. J. H., & Stuart, A. M. (2013). Ensemble Kalman methods for inverse problems. *Inverse Problems*, 29(4), 045001. | `10.1088/0266-5611/29/4/045001` | Yes | The derivative-free ensemble method underlying our EKI posterior for the parameter-estimation inverse problem. |
| 5 | Calibrate-Emulate-Sample | Cleary, E., Garbuno-Iñigo, A., Lan, S., Schneider, T., & Stuart, A. M. (2021). Calibrate, emulate, sample. *Journal of Computational Physics*, 424, 109716. | `10.1016/j.jcp.2020.109716` | Yes | Frames the EKI posterior as an approximate Bayesian inversion (calibrate → emulate → sample), supporting our use of the EKI ensemble to characterize posterior spread and the degenerate directions. |
| 6 | Iron inter-model degeneracy | Tagliabue, A., Aumont, O., DeAth, R., Dunne, J. P., Dutkiewicz, S., Galbraith, E., et al. (2016). How well do global ocean biogeochemistry models simulate dissolved iron distributions? *Global Biogeochemical Cycles*, 30(2), 149–174. | `10.1002/2015GB005289` | Yes | The published precedent that global BGC models agree on dissolved-iron *concentration* while disagreeing sharply on the source/sink processes and residence times — the field-level version of our (`alpfe`, `scav_rat`) degeneracy, where concentration fixes the combination, not the rate. |
| 7 | Green's-functions calibration (method origin) | Menemenlis, D., Fukumori, I., & Lee, T. (2005). Using Green's functions to calibrate an ocean general circulation model. *Monthly Weather Review*, 133(5), 1224–1240. | `10.1175/MWR2912.1` | Yes | The Green's-functions parameter-estimation methodology by which Carroll et al. produced the published optima we grade our recoveries against. |
| 8 | ECCO-Darwin + published optima (grading baseline) | Carroll, D., Menemenlis, D., Adkins, J. F., Bowman, K. W., Brix, H., Dutkiewicz, S., et al. (2020). The ECCO-Darwin data-assimilative global ocean biogeochemistry model: Estimates of seasonal to multidecadal surface ocean pCO₂ and air-sea CO₂ flux. *Journal of Advances in Modeling Earth Systems*, 12(10), e2019MS001888. | `10.1029/2019MS001888` | Yes | The source of the Green's-functions-optimized Carroll-6 parameter values (and the model itself) that define our recovery target and grading standard. |
| 9 | ECCO-Darwin v05 / Darwin-3 state estimate | Carroll, D., Menemenlis, D., Dutkiewicz, S., Lauderdale, J. M., Adkins, J. F., Bowman, K. W., et al. (2022). Attribution of space-time variability in global-ocean dissolved inorganic carbon. *Global Biogeochemical Cycles*, 36(7), e2021GB007162. | `10.1029/2021GB007162` | Yes | The active Darwin-3 / v05 ECCO-Darwin state estimate from which our AOI initial-condition and target fields are drawn. |
| 10 | Universal Differential Equations | Rackauckas, C., Ma, Y., Martensen, J., Warner, C., Zubov, K., Supekar, R., Skinner, D., Ramadhan, A., & Edelman, A. (2020). Universal differential equations for scientific machine learning. *arXiv preprint* arXiv:2001.04385. | `10.48550/arXiv.2001.04385` | Yes (arXiv preprint, not journal-published) | The methodological class our per-cell NN → differentiable 0-D box belongs to: neural components embedded inside a differential-equation model and trained by differentiable programming. |
| 11 | Differentiable physics for Earth systems | Shen, C., Appling, A. P., Gentine, P., Bandai, T., Gupta, H., Tartakovsky, A., et al. (2023). Differentiable modelling to unify machine learning and physical models for geosciences. *Nature Reviews Earth & Environment*, 4(8), 552–567. | `10.1038/s43017-023-00450-9` | Yes | Canonical geoscience-facing statement of differentiable modelling (learnable components inside process models via gradient-based training), situating our differentiable-box approach in the Earth-system-science literature. |

## Verification notes

- All eleven DOIs were confirmed against the publisher's resolved article page; each
  publisher URL embeds the DOI shown (e.g. Wiley `doi/full/10.1029/2019MS001888`,
  PLoS `10.1371/journal.pcbi.0030189`, APS `10.1103/PhysRevE.83.036701`, AMS
  `mwr2912.1`). The Iglesias et al. DOI additionally resolved through the DOI
  resolver (302 → IOPscience).
- Entry 10 (Rackauckas et al.) is an **arXiv preprint**, not a journal article. Cite
  it as such; the `10.48550/arXiv.2001.04385` DOI is arXiv's own registered DOI.
  (Some secondary sources incorrectly list it as a PNAS paper — that is wrong.)
- Entry 7 (Menemenlis et al. 2005) is the *methodological* origin of the
  Green's-functions calibration. The Carroll-6 optimized parameter values our study
  grades against are tabulated in the supplement of entry 8 (Carroll et al. 2020);
  internal notes referring to a "Menemenlis 2019 Table S1" point to that same
  Carroll-2020 supplementary material, not a separate 2019 publication.
- Entries 2 and 3 together cover the "sloppiness" topic: Gutenkunst et al. is the
  empirical spectrum result; Transtrum/Machta/Sethna is the information-geometry
  theory. Both are cited because the paper uses both the eigenspectrum and its
  geometric interpretation.

**Summary: 11 of 11 citations verified; none unconfirmed. One caveat flagged —
Rackauckas et al. (entry 10) is an arXiv preprint, cited with arXiv's DOI rather than
a journal DOI.**
