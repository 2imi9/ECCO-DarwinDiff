# Per-parameter identifiability map: 1-deg vs native LLC270 (empirical Fisher / CRLB)

_Local overnight result (Explorer H200, jobs 8266733 / 8266734; laptop-only, not on GitHub). CRLB =
variance bound at Carroll (lower = better constrained). Sloppiest direction = the unidentifiable
parameter combination per basin._

**Readout for Jon (per-parameter uncertainty):**
- `R_PICPOC` is the dominant **null** direction in the Southern Ocean at both resolutions (CRLB
  5,818 -> 77,372) -- calcite is unconstrained there (no Daniels coverage).
- `diatomgraz` has the *lowest* CRLB everywhere, but that is the residual-weighting artifact noted
  in the profile-likelihood diagnostic (Fisher-constrained yet structurally flat) -- not a real
  constraint.
- **Native inflates every CRLB** (the sparse real GEOTRACES/Daniels obs diluted across ~10x more
  cells: eqpac 1071 -> 9750), so per-parameter constraint gets *worse* at native -- quantifies the
  'native dilutes sparse obs' finding.
- The sloppiest direction shifts `scav_rat` (1-deg) -> `R_PICPOC` (native) in eqpac/natl; the iron
  pair is best-constrained in the Southern Ocean (alpfe/scav_rat CRLB 46-103).

## eqpac  (1-deg: 1071 cells, 3.9 dec | native: 9750 cells, 4.1 dec)
| param | CRLB 1-deg | CRLB native | verdict (native) |
|---|---|---|---|
| `alpfe` | 154 | 511 | unconstrained |
| `scav_rat` | 179 | 357 | unconstrained |
| `Smallgrow` | 39 | 331 | unconstrained |
| `Biggrow` | 148 | 657 | unconstrained |
| `diatomgraz` | 4 | 22 | sloppy |
| `R_PICPOC` | 45 | 8373 | unconstrained |
- sloppiest direction (1-deg): **scav_rat** (-0.71)
- sloppiest direction (native): **R_PICPOC** (+0.99)

## natlsubpolar  (1-deg: 484 cells, 3.5 dec | native: 7939 cells, 3.5 dec)
| param | CRLB 1-deg | CRLB native | verdict (native) |
|---|---|---|---|
| `alpfe` | 79 | 335 | unconstrained |
| `scav_rat` | 88 | 232 | unconstrained |
| `Smallgrow` | 44 | 403 | unconstrained |
| `Biggrow` | 69 | 1809 | unconstrained |
| `diatomgraz` | 5 | 18 | constrained |
| `R_PICPOC` | 37 | 5483 | unconstrained |
- sloppiest direction (1-deg): **scav_rat** (+0.68)
- sloppiest direction (native): **R_PICPOC** (-1.00)

## southernoceanpac  (1-deg: 1296 cells, 4.3 dec | native: 21120 cells, 4.6 dec)
| param | CRLB 1-deg | CRLB native | verdict (native) |
|---|---|---|---|
| `alpfe` | 46 | 72 | sloppy |
| `scav_rat` | 50 | 103 | sloppy |
| `Smallgrow` | 156 | 899 | unconstrained |
| `Biggrow` | 634 | 4035 | unconstrained |
| `diatomgraz` | 6 | 11 | constrained |
| `R_PICPOC` | 5818 | 77372 | unconstrained |
- sloppiest direction (1-deg): **R_PICPOC** (-0.99)
- sloppiest direction (native): **R_PICPOC** (+1.00)
