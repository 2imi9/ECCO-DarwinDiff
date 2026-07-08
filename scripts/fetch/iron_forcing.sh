#!/usr/bin/env bash
# Fetch the ECCO-Darwin v05 soluble-iron deposition forcing (DB-1).
#
# File: llc270_Mahowald_2009_soluble_iron_dust.bin  (~45.5 MB)
#   MITgcm LLC270 compact forcing: 12 monthly-climatology records, 13 faces,
#   270 x 270, big-endian float32. This is the spatial soluble-iron deposition
#   field that ECCO-Darwin v05 is forced by (v05 data.darwin: ironfile=...,
#   ironperiod=-12, darwin_inscal_iron=1000). Loader:
#   src/darwindiff/iron_forcing_loader.py. Context:
#   docs/findings/2026-07-07_jon_schultz_meeting_capture.md, data/README.md.
#
# IMPORTANT: this file lives in the ECCO-Darwin forcing/input tree, which is
# hosted on the Earthdata-authenticated ECCO JPL drive -- NOT on the public NAS
# output mirror (data.nas.nasa.gov/.../output/), which only carries the model
# OUTPUT (bin_average, monthly tracers) + the darwin_initial_conditions pickup.
# So you need an Earthdata login / bearer token to fetch it.
#
# Usage:
#   DARWIN_DATA_ROOT=/d/ecco_darwin_v5 EARTHDATA_TOKEN=xxxxx ./scripts/fetch/iron_forcing.sh
#
# The loader looks for the file at $DARWIN_DATA_ROOT/input/<name> by convention;
# this script writes it there.

set -euo pipefail

: "${DARWIN_DATA_ROOT:=/d/ecco_darwin_v5}"
IRON_NAME="llc270_Mahowald_2009_soluble_iron_dust.bin"
DEST_DIR="${DARWIN_DATA_ROOT}/input"
DEST="${DEST_DIR}/${IRON_NAME}"
EXPECTED_BYTES=45489600        # 12 * 13 * 270 * 270 * 4

# Canonical Earthdata-authenticated source (ECCO drive). If the exact input path
# has moved, browse: https://ecco.jpl.nasa.gov/drive/files/ECCO2/LLC270/
SRC_URL="https://ecco.jpl.nasa.gov/drive/files/ECCO2/LLC270/ECCO-Darwin_extension/input/${IRON_NAME}"

mkdir -p "${DEST_DIR}"

echo "ECCO-Darwin v05 soluble-iron forcing fetch helper"
echo "  File:     ${IRON_NAME}  (expected ${EXPECTED_BYTES} bytes)"
echo "  Dest:     ${DEST}"
echo "  Source:   ${SRC_URL}"
echo ""

if [[ -f "${DEST}" ]]; then
  actual=$(wc -c < "${DEST}")
  if [[ "${actual}" -eq "${EXPECTED_BYTES}" ]]; then
    echo "Already present and correct size (${actual} bytes). Nothing to do."
    exit 0
  fi
  echo "WARNING: ${DEST} exists but is ${actual} bytes (expected ${EXPECTED_BYTES}); re-fetching."
fi

if [[ -z "${EARTHDATA_TOKEN:-}" ]]; then
  echo "EARTHDATA_TOKEN is not set. Options:"
  echo "  1. Create an Earthdata bearer token at https://urs.earthdata.nasa.gov/ and export it:"
  echo "       export EARTHDATA_TOKEN=<token>"
  echo "  2. Or download in a browser (logged into Earthdata) and drop the file at:"
  echo "       ${DEST}"
  echo "  3. Or, if you have a machine with the MITgcm-contrib run inputs (e.g. Pleiades),"
  echo "       scp it: scp <host>:.../v05/llc270/input/${IRON_NAME} \"${DEST}\""
  exit 1
fi

echo "Fetching with Earthdata bearer token..."
curl -L -f --retry 3 -H "Authorization: Bearer ${EARTHDATA_TOKEN}" \
  -o "${DEST}.part" "${SRC_URL}"
mv "${DEST}.part" "${DEST}"

actual=$(wc -c < "${DEST}")
if [[ "${actual}" -ne "${EXPECTED_BYTES}" ]]; then
  echo "ERROR: downloaded ${actual} bytes, expected ${EXPECTED_BYTES}. Removing." >&2
  rm -f "${DEST}"
  exit 1
fi
echo "OK: ${DEST} (${actual} bytes)."
echo ""
echo "Validate against the real grid with the opt-in test:"
echo "  DARWINDIFF_TEST_IRON=1 DARWIN_DATA_ROOT=\"${DARWIN_DATA_ROOT}\" \\"
echo "    pytest -q tests/test_iron_forcing_loader.py -k real"
