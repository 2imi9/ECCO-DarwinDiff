#!/usr/bin/env bash
# Fetch the ECCO-Darwin v05 soluble-iron deposition forcing (DB-1).
#
# File: llc270_Mahowald_2009_soluble_iron_dust.bin  (45,489,600 bytes = ~45.5 MB)
#   MITgcm LLC270 compact forcing: 12 monthly-climatology records, 13 faces,
#   270 x 270, big-endian float32. The spatial soluble-iron deposition field
#   ECCO-Darwin v05 is forced by (v05 data.darwin: ironfile=..., ironperiod=-12,
#   darwin_inscal_iron=1000). Loader: src/darwindiff/iron_forcing_loader.py.
#   Context: docs/findings/2026-07-07_jon_schultz_meeting_capture.md, data/README.md.
#
# It is PUBLIC on the NAS ECCO data portal (no Earthdata login needed) -- in the
# input/darwin_forcing/ subdir alongside darwin_initial_conditions/. (Source
# confirmed from MITgcm-contrib/ecco_darwin v05/llc270/readme.txt.)
#
# Usage:
#   DARWIN_DATA_ROOT=/d/ecco_darwin_v5 ./scripts/fetch/iron_forcing.sh
#
# The loader/tests look for the file at $DARWIN_DATA_ROOT/input/<name>; this writes it there.

set -euo pipefail

: "${DARWIN_DATA_ROOT:=/d/ecco_darwin_v5}"
IRON_NAME="llc270_Mahowald_2009_soluble_iron_dust.bin"
DEST_DIR="${DARWIN_DATA_ROOT}/input"
DEST="${DEST_DIR}/${IRON_NAME}"
EXPECTED_BYTES=45489600        # 12 * 13 * 270 * 270 * 4
SRC_URL="https://data.nas.nasa.gov/ecco/llc_270/ecco_darwin_v5/input/darwin_forcing/${IRON_NAME}"

mkdir -p "${DEST_DIR}"

echo "ECCO-Darwin v05 soluble-iron forcing fetch"
echo "  File:   ${IRON_NAME}  (expected ${EXPECTED_BYTES} bytes)"
echo "  Dest:   ${DEST}"
echo "  Source: ${SRC_URL}"
echo ""

if [[ -f "${DEST}" ]] && [[ "$(wc -c < "${DEST}")" -eq "${EXPECTED_BYTES}" ]]; then
  echo "Already present and correct size. Nothing to do."
  exit 0
fi

echo "Downloading (public, no auth; ~45 MB)..."
curl -sSL --retry 3 -C - -o "${DEST}.part" "${SRC_URL}"
mv "${DEST}.part" "${DEST}"

actual=$(wc -c < "${DEST}")
if [[ "${actual}" -ne "${EXPECTED_BYTES}" ]]; then
  echo "ERROR: downloaded ${actual} bytes, expected ${EXPECTED_BYTES}. Removing." >&2
  rm -f "${DEST}"
  exit 1
fi
echo "OK: ${DEST} (${actual} bytes)."
echo ""
echo "Validate with the opt-in test:"
echo "  DARWINDIFF_TEST_IRON=1 DARWIN_DATA_ROOT=\"${DARWIN_DATA_ROOT}\" \\"
echo "    pytest -q tests/test_iron_forcing_loader.py -k real"
