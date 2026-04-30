# Data

Local data cache. Contents are gitignored — fetch with the project's data pipeline (TBD) before running anything.

## Sources

### ECCO-Darwin model output

- **Used for:** emulator training and parameter-learner ground truth.
- **Where:** https://data.nas.nasa.gov/ecco
- **Access:** registration required (NASA NAS account).
- **Volume:** large — full LLC270 history from 1992 is hundreds of GB. We will subset to the chosen 2D transect early.

### SOCATv5 (Surface Ocean CO2 Atlas)

- **Used for:** surface ocean fCO2 observations for parameter-learner loss.
- **Where:** https://socat.info
- **Access:** free download.
- **Note:** Carroll 2020 used SOCATv5 (also referenced as v6 update). We start with v5 to match the paper.

### GLODAPv2 (Global Ocean Data Analysis Project)

- **Used for:** DIC, alkalinity, NO3, PO4, SiO2, O2 ship-based profiles.
- **Where:** https://glodap.info
- **Access:** free download.

### BGC-Argo (Biogeochemical Argo)

- **Used for:** NO3, O2 float profiles for time-varying constraints.
- **Where:** https://biogeochemical-argo.org
- **Access:** via the `argopy` Python library.

## Layout

When the pipeline lands, expected layout:

```
data/
├── ecco_darwin/        ECCO-Darwin output subset (NetCDF/Zarr)
├── socat/              SOCATv5 fCO2
├── glodap/             GLODAPv2 ship profiles
└── argo_bgc/           BGC-Argo float profiles
```
