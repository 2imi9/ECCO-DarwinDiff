# References

DOIs verified via OpenAlex. If your work depends on the underlying model, cite Carroll et al.
[2020](https://doi.org/10.1029/2019MS001888) (*JAMES*) and
[2022](https://doi.org/10.1029/2021GB007162) (*GBC*).

## The model we differentiate against

| Reference | Why it matters |
|---|---|
| [Carroll et al. 2020](https://doi.org/10.1029/2019MS001888) (*JAMES*) | Original ECCO-Darwin; the 6-parameter Green's-functions calibration we differentiate against. |
| [Carroll et al. 2022](https://doi.org/10.1029/2021GB007162) (*GBC*) | ECCO-Darwin v05; the publicly-accessible output is our active recovery target. |
| [Menemenlis et al. 2005](https://doi.org/10.1175/MWR2912.1) (*MWR*) | The Green's-functions calibration method DarwinDiff replaces. |

## Biogeochemistry implemented in `src/darwindiff/`

| Reference | Used by |
|---|---|
| [Dutkiewicz et al. 2009](https://doi.org/10.1029/2008GB003405) (*GBC*) | Core Darwin equations — `carroll6.py` |
| [Follows et al. 2006](https://doi.org/10.1016/j.ocemod.2005.05.004) | Carbonate-system solver — `carbonate.py` |
| [Wanninkhof 2014](https://doi.org/10.4319/lom.2014.12.351) | Air-sea CO₂ flux — `carbonate.py` |

## Observational products

| Reference | Used by |
|---|---|
| [Olsen et al. 2016](https://doi.org/10.5194/essd-8-297-2016) | GLODAP DIC/ALK — `glodap_loader.py` |
| [Schlitzer et al. 2018](https://doi.org/10.1016/j.chemgeo.2018.05.040) | GEOTRACES iron — `geotraces_loader.py` |

## Method templates

| Reference | Relevance |
|---|---|
| [Xu et al. 2025 (BINN)](https://arxiv.org/abs/2502.00672) | Differentiable physics + per-location parameter network — closest template. |
| [Kochkov et al. 2024 (NeuralGCM)](https://arxiv.org/abs/2311.07222) | Hybrid-physics reference. |
| [Ouala & Lachkar 2026 (Neural-BGC)](https://doi.org/10.22541/essoar.15002003/v1) | ROMS+NN ocean BGC emulator (DO/NO₃ only). |

## Ocean / climate emulators (Track 2)

Architecture, resolution-scaling, and coupling templates. SamudrACE names an explicit biogeochemistry
hole as future work — the carbon-BGC slot Track 2 targets. **None emulate ocean carbon**, which is the
whitespace. See [ADR-0002](adr/0002-track2-emulator-scope.md).

| Reference |
|---|
| [Dheeshjith et al. 2024 (Samudra)](https://arxiv.org/abs/2412.03795) |
| [Yuan et al. 2026 (Samudra 2)](https://arxiv.org/abs/2606.02610) |
| [Ai2 2025 (SamudrACE)](https://arxiv.org/abs/2509.12490) |
| [Clark et al. 2026 (ACE2S)](https://arxiv.org/abs/2606.07928) |
