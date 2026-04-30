# Data

Local data cache. Contents are gitignored — fetch separately before running anything.

## Sources

- **ECCO-Darwin model output** — emulator training and parameter-learner ground truth.
  https://data.nas.nasa.gov/ecco (NASA NAS account required)

- **SOCATv5** — surface ocean fCO2.
  https://socat.info

- **GLODAPv2** — DIC, alkalinity, NO3, PO4, SiO2, O2 ship profiles.
  https://glodap.info

- **BGC-Argo** — NO3, O2 float profiles.
  https://biogeochemical-argo.org (via the `argopy` library)
