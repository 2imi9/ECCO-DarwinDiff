# References

PDFs are gitignored — drop your own copies into this directory if you want them locally.

## Core references

### Carroll et al. (2020) — *the ECCO-Darwin paper*

Carroll, D., Menemenlis, D., Adkins, J. F., Bowman, K. W., Brix, H., Dutkiewicz, S., Fenty, I., et al. (2020). The ECCO-Darwin data-assimilative global ocean biogeochemistry model: Estimates of seasonal to multidecadal surface ocean *p*CO2 and air-sea CO2 flux. *Journal of Advances in Modeling Earth Systems*, 12, e2019MS001888.
https://doi.org/10.1029/2019MS001888

Local: `references/carroll_2020_ecco_darwin.pdf` (gitignored).

### Carroll et al. (2022) — *the active calibration target*

Carroll, D., Menemenlis, D., Dutkiewicz, S., Lauderdale, J. M., Adkins, J. F., Bowman, K. W., Brix, H., et al. (2022). Attribution of space-time variability in global-ocean dissolved inorganic carbon. *Global Biogeochemical Cycles*, 36, e2021GB007162.
https://doi.org/10.1029/2021GB007162

The ECCO-Darwin v05 application paper. **Inherits Carroll 2020's 6-parameter calibration bit-for-bit** — verified by reading the namelists in `MITgcm-contrib/ecco_darwin/v04/llc270_JAMES_paper/` and `v05/llc270/`. The publicly-accessible ECCO-Darwin output is from this v05 run, so it's our active recovery target (notebooks 10–16 fit against v05 surface fields).

### Brix et al. (2015) — earlier ECCO-Darwin version, biogeochemistry equations

Brix, H., Menemenlis, D., Hill, C., Dutkiewicz, S., Jahn, O., Wang, D., Bowman, K., & Zhang, H. (2015). Using Green's functions to initialize and adjust a global, eddying ocean biogeochemistry general circulation model. *Ocean Modelling*, 95, 1–14.
https://doi.org/10.1016/j.ocemod.2015.07.008

### Dutkiewicz et al. (2009) — core Darwin biogeochemistry

Dutkiewicz, S., Follows, M. J., & Bragg, J. G. (2009). Modeling the coupling of ocean ecology and biogeochemistry. *Global Biogeochemical Cycles*, 23, GB4017.
https://doi.org/10.1029/2008GB003405

### Menemenlis et al. (2005) — Green's functions method

Menemenlis, D., Fukumori, I., & Lee, T. (2005). Using Green's functions to calibrate an ocean general circulation model. *Monthly Weather Review*, 133(5), 1224–1240.
https://doi.org/10.1175/MWR2912.1

### Savelli et al. (2026) — recent ECCO-Darwin update; flags fixed-parameter limits

Savelli, R., Carroll, D., Menemenlis, D., Lauderdale, J. M., Bertin, C., Dutkiewicz, S., Manizza, M., Bloom, A. A., Castro-Morales, K., Miller, C. E., Simard, M., Bowman, K. W., & Zhang, H. (2026). Implementing riverine biogeochemical inputs in ECCO-Darwin: a sensitivity analysis of terrestrial fluxes in a data-assimilative global ocean biogeochemistry model. *Geoscientific Model Development*, 19, 867.
https://doi.org/10.5194/gmd-19-867-2026

Same author team as Carroll 2020. Primarily about adding riverine BGC inputs to ED, but explicitly flags fixed parameters such as the 100-day DOC remineralization rate as a limitation — directly relevant to DarwinDiff's parameter-learning angle.

## Methodological references

### Xu et al. (2025) — BINN, the method template

Xu et al. (2025). BINN. arXiv:2502.00672.
https://arxiv.org/abs/2502.00672

Reference implementation: https://doi.org/10.5281/zenodo.19237379

### Kochkov et al. (2024) — Neural GCM, hybrid physics + ML

Kochkov, D., Yuval, J., Langmore, I., Norgaard, P., Smith, J., Mooers, G., Klöwer, M., et al. (2024). Neural general circulation models for weather and climate. *Nature*.
https://arxiv.org/abs/2311.07222

### Ouala & Lachkar (2026) — Neural-BGC, observation-driven ocean BGC emulator coupled to ROMS

Ouala, S., & Lachkar, Z. (2026). Neural-BGC: An Observation-Driven Emulator for Hybrid Physical–Biogeochemical Modeling. ESSOAr preprint, submitted to *Geophysical Research Letters*.
https://doi.org/10.22541/essoar.15002003/v1

Closest existing ocean BGC ML reference. Trains an NN on World Ocean Database in-situ profiles (1965–2024) to predict dissolved oxygen and nitrate from physical state (T, S, depth, latitude, longitude, month); cascaded architecture (DO predicted first, then NO3 conditioned on DO + physics). Coupled to ROMS by replacing the prognostic transport-reaction equation entirely; outperforms tuned ROMS-NPZD on mean state in the Arabian Sea and Canary Current Upwelling. Authors flag three limits: offline/diagnostic only (no BGC→physics feedback), generalization outside 1965–2024 training distribution untested, and DO + NO3 only. DarwinDiff differentiates by being mechanistic (emulates Darwin rather than bypassing the BGC model), parameter-aware (learns Darwin's scalars), and covering carbon-cycle variables (DIC, alkalinity, pCO2, POC export).

### Catão et al. (2025) — TUPANN, single-GPU differentiable physics + ML feasibility

Catão, A., Poveda, M., Voltarelli, L., & Orenstein, P. (2025). Precipitation nowcasting of satellite data using physically-aligned neural networks. arXiv:2511.05471.
https://arxiv.org/abs/2511.05471

Atmospheric precipitation nowcasting (not ocean), but uses a differentiable advection operator and a transformer trained on a single A100. Useful as a feasibility example for differentiable physics + machine learning at the single-GPU scale we are targeting. Currently a preprint; ICLR 2026 venue claim from the project brief is **not** stated on the arXiv page.

## Code

- ECCO-Darwin source: https://github.com/MITgcm-contrib/ecco_darwin
- ECCO-Darwin platform-independent run instructions (Zenodo): https://doi.org/10.5281/zenodo.3829965
- PhysicsNeMo: https://github.com/NVIDIA/physicsnemo
- neuraloperator: https://github.com/neuraloperator/neuraloperator
