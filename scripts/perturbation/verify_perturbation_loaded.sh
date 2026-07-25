#!/usr/bin/env bash
# verify_perturbation_loaded.sh -- confirm a v05 OAT perturbation run actually LOADED the
# perturbed value, from the model's own startup echo. This is the whole point of the recipe:
# do NOT trust the input file -- R_PICPOC and diatomgraz are trait-overridden, so an edit that
# "looks right" in data.traits can still be inert if the override path did not run. The model
# echoes the EFFECTIVE &DARWIN_* namelists to STDOUT.0000 after the override; that echo is proof.
#
# Usage:
#   verify_perturbation_loaded.sh <run_dir_or_STDOUT> <param> <expected_value>
#     <param>          alpfe | scav_rat | R_PICPOC | diatomgraz
#     <expected_value> the perturbed number you set (e.g. 0.843918, 4.607460000000000E-002)
#
# Exit 0 = the perturbed value is present in the effective namelist echo (and, for the
# trait-overridden pair, the frozen originals are NOT what loaded). Nonzero = the run tested
# nothing / could not be verified -- investigate before using it in the Jacobian.
set -u
shopt -s nocasematch   # tolerate E vs e in Fortran exponent echo

if [ $# -lt 3 ]; then
  echo "usage: $0 <run_dir_or_STDOUT> <alpfe|scav_rat|R_PICPOC|diatomgraz> <expected_value>" >&2
  exit 2
fi
target="$1"; param="$2"; expect="$3"
if [ -d "$target" ]; then LOG="$target/STDOUT.0000"; else LOG="$target"; fi
[ -f "$LOG" ] || { echo "FAIL: no STDOUT.0000 at $LOG" >&2; exit 3; }

fail() { echo "FAIL ($param): $1" >&2; exit 1; }
ok()   { echo "OK   ($param): $1"; }
has()  { [[ "$1" == *"$2"* ]]; }   # literal substring test (portable; no grep -F crash)

FROZEN_RPICPOC="4.188600000000000E-002"   # the frozen data.traits original
INERT_RPICPOC="0.04245"                    # the inert data.darwin generation scalar

case "$param" in
  alpfe|scav_rat)
    if [ "$param" = alpfe ]; then key=ALPFE; else key=SCAV_RAT; fi
    line=$(grep -iE "^[[:space:]]*${key}[[:space:]]*=" "$LOG" | tail -1)
    [ -n "$line" ] || fail "no '${key} =' echo line in $LOG"
    echo "  echo:$line"
    has "$line" "$expect" && ok "loaded ${key}=${expect}" || fail "expected ${expect} not in the ${key} echo"
    ;;
  R_PICPOC)
    has "$(cat "$LOG")" "opening data.traits" || fail "'opening data.traits' not in log -- override path may not have run"
    line=$(grep -iE "^[[:space:]]*R_PICPOC[[:space:]]*=" "$LOG" | grep -vi "val_R_PICPOC" | tail -1)
    [ -n "$line" ] || fail "no effective 'R_PICPOC =' echo found"
    echo "  echo:$line"
    has "$line" "$FROZEN_RPICPOC" && fail "STILL the frozen original 0.0418860 -- edit was inert"
    has "$line" "$INERT_RPICPOC"  && fail "shows the inert generation scalar 0.04245 -- wrong file edited"
    has "$line" "$expect" && ok "loaded R_PICPOC=${expect}" || fail "expected ${expect} not in the R_PICPOC echo"
    ;;
  diatomgraz)
    has "$(cat "$LOG")" "opening data.traits" || fail "'opening data.traits' not in log -- override path may not have run"
    line=$(grep -iE "^[[:space:]]*PALAT[[:space:]]*=" "$LOG" | tail -1)
    [ -n "$line" ] || fail "no effective 'PALAT =' echo found"
    echo "  echo:$line"
    has "$line" "$expect" && ok "loaded PALAT diatom-prey entry ${expect}" || fail "expected ${expect} not in the PALAT echo"
    ;;
  *) fail "unknown param '$param'";;
esac
