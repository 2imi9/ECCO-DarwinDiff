# Preregistration: explicit-zooplankton source-conformance receipt

**Frozen before implementing the audit or measuring trajectory support:
2026-08-10.** This is a provenance and algebra audit of the explicit-grazer
projection used by the failed seasonal Stage-0 target. It runs no optimizer,
authorizes no B200 work, and cannot rehabilitate the target. The relational-map
query

```text
python scripts/research_map_db.py settled "explicit zooplankton source conformance palatability assimilation"
```

returned no settled answer over 543 untruncated `SETTLED` rows.

## Why this audit is required

The Stage-0 prototype is described as a **source-mirrored projection**, not a
full Darwin port. That phrase is load-bearing. Reading only
`darwin_plankton.F` is insufficient because the call site multiplies grazing
and mortality by temperature-function variables whose values are assigned in
the base Darwin package, outside the committed ECCO-Darwin configuration
overrides. This audit therefore distinguishes direct source evidence from
same-era corroboration and declared projection choices.

The audit must not reinterpret a source ambiguity as evidence for the target.
If a material mismatch is found, the existing explicit-grazer artifacts are
provisional until rerun or retracted.

## Frozen sources

### Direct official configuration evidence

Use the public `MITgcm-contrib/ecco_darwin` tree at commit
`75b8e4337c2fa0c0baa9fa9376590503229121af`. A local checkout is eligible only
when each audited file has the following Git blob identity:

| file | Git blob |
|---|---|
| `v04/llc270_JAMES_paper/code_darwin/DARWIN_OPTIONS.h` | `75705a67eaff7d77309f88da21d6f6abef07bb31` |
| `v04/llc270_JAMES_paper/code_darwin/darwin_init_fixed.F` | `20aa2864b97ddfafbde8245c43cfc34ee84607bf` |
| `v04/llc270_JAMES_paper/code_darwin/darwin_generate_phyto.F` | `2a112873650922030237df5430a7cae0341dcb87` |
| `v04/llc270_JAMES_paper/code_darwin/darwin_plankton.F` | `6af2b5fff7746bcd904a51af9390d92e2e764d30` |
| `v04/llc270_JAMES_paper/readme/readme_ecco_darwin.txt` | `84e3a53af19444d81308ffc24c840af56df97fc3` |
| `v02/cs510_Manizza_AO/darwin/darwin_generate_zoo.F` | `a3c811fa06544331b9b291ae54ae0b5b68eec0e0` |

The v04 readme is the lineage record: the build checks out
`MITgcm_contrib/darwin/pkg/darwin` dated 2018-03-22 and overlays the files in
`code_darwin`.

### Same-era base-package corroboration

The exact 2018-03-22 base-package checkout is not vendored in the
`ecco_darwin` repository. For the otherwise hidden temperature-function and
trait-generation assignments, use the independently archived matching-signature
Monod package in `SunderlandLab/MITgcm_PCB_pkg`, commit
`488cb795d7b933ea5a79b3bad84a182d7dbbe1ef`, first committed 2018-11-09:

| file | Git blob |
|---|---|
| `monod/monod_tempfunc.F` | `df89435be92cfa5544d0ba437f6abc44d0d12c18` |
| `monod/monod_generate_zoo.F` | `1bd7f20d8dc3397450c1a6ab7e1ddbad7bb40d1e` |
| `monod/monod_init_fixed.F` | `9711fd46b91c00a7b1ab29d08a61d203b59a8729` |

This source may corroborate but may not upgrade an inference to direct
bit-for-bit provenance. The receipt must label it `same-era-corroboration`.

## Frozen checks

1. **Source identity.** Recompute every direct-source Git blob and reject any
   mismatch. Record SHA-256 as a second transport checksum.
2. **Compile branch.** Confirm `OLD_GRAZE` is undefined, `TEMP_VERSION` is 2,
   and `NOTEMP` is undefined in the JAMES configuration.
3. **Scalar constants.** Parse active assignments and recover
   `GrazeFast=0.625 d-1`, `kgrazesat=0.085` phosphorus units,
   `val_R_PC=120`, `diatomgraz=0.83003`, `coccograz=0.85`,
   `olargegraz=0.90`, `palathi=1`, `palatlo=0.2`,
   `GrazeEfflow/mod/hi=(0.2,0.5,0.7)`, and both linear grazer mortalities
   `1/30 d-1`. The projected carbon half-saturation must be exactly
   `0.085 * 120 = 10.2`.
4. **Generated matrices.** Reconstruct the five-prey by two-predator
   palatability and assimilation matrices from the source size-class rules.
   They must equal the runtime matrices at Carroll truth. The audit must not
   compare against v05's later materialized `data.traits` value 0.845730.
5. **Grazing algebra.** Confirm the official v04 call site uses the shared
   prey pool, prey allocation, Holling-II response, predator biomass, and
   assimilation partition represented by the projection.
6. **Temperature semantics.** Confirm the v04 call signature alone does not
   establish a non-unit multiplier. The matching 2018 source must assign
   `zooTempFunction`, `mortZTempFunction`, and `mortZ2TempFunction` to 1 under
   `TEMP_VERSION == 2`, with Arrhenius alternatives commented. Record this as
   corroboration, not direct proof.
7. **Quadratic mortality.** Confirm the matching source assigns both
   `ZoomortSmall2` and `ZoomortBig2` to zero.
8. **Source prey floor.** The official configuration sets
   `phygrazmin=1e-10` in phosphorus units, or `1.2e-8` in the projection's
   carbon units. Rerun cycle 13 from the bound target artifact and compare the
   current numerical-guard response against a literal source-floor oracle at
   every verified cell and step. Record minimum prey-pool support, maximum
   absolute and relative rate discrepancy, and whether the source-floor
   oracle can change the large-predator exclusion classification.
9. **Declared non-conformances.** Preserve and enumerate the projection's
   missing DOC state, POC routing, two-layer truncation, approximate
   phytoplankton temperature factor, chemical restoring, and Euler/clamp
   numerics. None may be described as source-exact.
10. **Independent verification.** A separate verifier must recompute source
    identities, matrix/scalar comparisons, artifact hashes, support metrics,
    and the decision from the raw tensor bundle.

## Frozen tolerances and decision

- Scalar and matrix checks use absolute tolerance `1e-12` after parsing.
- Source-floor rate comparisons use both absolute tolerance `1e-12 d-1` and
  relative tolerance `1e-6` over nonzero projected rates.
- Existing energy-audit consistency uses absolute tolerance `5e-4` on annual
  log multipliers and `2e-5` relative L2 on the cycle endpoint.
- The large predator remains continuously excluded only if the source-floor
  oracle's maximum annual continuous margin is below `-0.10` in every AOI.

| Outcome | Decision |
|---|---|
| direct constants/algebra pass; corroborated hidden defaults pass; source floor is support-negligible; exclusion remains | `source-conformant-bounded-projection` |
| direct evidence passes but hidden defaults cannot be corroborated | `source-provenance-incomplete` |
| a material direct-source mismatch or classification change is found | `source-mismatch-rerun-required` |
| artifact reproduction or integrity fails | `audit-invalid` |

Even the strongest branch means only that the **bounded projection** faithfully
implements the audited grazing closure over the visited support. It does not
make the seasonal target valid, identify the omitted Darwin mechanism, or
authorize B200 work.
