#!/usr/bin/env bash
# Fetch the GEOTRACES IDP2025 discrete-bottle dataset.
#
# IDP2025 is distributed via the BODC bulk-download DOI as ASCII, NetCDF (ODV
# format), and ODV collections. DarwinDiff uses the NetCDF variant. See Jon
# Lauderdale's 2026-05-11 email and `data/README.md` for context; the loader
# lives at `src/darwindiff/geotraces_loader.py` (added in PR #39).
#
# Usage:
#   GEOTRACES_DATA_ROOT=/path/to/local/cache ./scripts/fetch/geotraces.sh
#
# The DOI page may require accepting the GEOTRACES Fair Use Policy / data-use
# agreement before download; some files are served via redirect to the BODC
# catalogue. If the script fails mid-way, visit the URL in a browser, accept
# the policy, then re-run.

set -euo pipefail

: "${GEOTRACES_DATA_ROOT:=${HOME}/geotraces}"
mkdir -p "${GEOTRACES_DATA_ROOT}"

DOI_URL="https://doi.org/10.5285/42c92148-8d03-8be6-e063-7086abc09f0c"
LANDING_URL="https://www.geotraces.org/idp2025/"

echo "GEOTRACES IDP2025 fetch helper"
echo "  Target directory: ${GEOTRACES_DATA_ROOT}"
echo "  Landing page:     ${LANDING_URL}"
echo "  Bulk-download DOI: ${DOI_URL}"
echo ""
echo "Steps:"
echo "  1. Visit the landing page above and accept the GEOTRACES Fair Use Policy."
echo "  2. Download the NetCDF bundle (typically a single archive of"
echo "     ~hundreds of MB containing GEOTRACES_IDP2025_v1_Discrete_Sample_Data.nc"
echo "     and supporting metadata)."
echo "  3. Extract into \$GEOTRACES_DATA_ROOT so the loader finds"
echo "     \$GEOTRACES_DATA_ROOT/GEOTRACES_IDP2025*.nc"
echo ""
echo "Run this script once the policy is accepted to attempt a direct fetch:"
echo "  curl -L -o \"\${GEOTRACES_DATA_ROOT}/idp2025_netcdf.zip\" <direct-download-URL>"
echo "  unzip -d \"\${GEOTRACES_DATA_ROOT}\" \"\${GEOTRACES_DATA_ROOT}/idp2025_netcdf.zip\""
echo ""
echo "After download, validate with the opt-in test:"
echo "  DARWINDIFF_TEST_LLC270=1 GEOTRACES_DATA_ROOT=\"\${GEOTRACES_DATA_ROOT}\" \\"
echo "    pytest -q tests/test_geotraces_loader.py::test_real_idp2025_iron"
