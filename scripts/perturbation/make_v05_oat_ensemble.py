#!/usr/bin/env python3
r"""make_v05_oat_ensemble.py -- generate the 17-run ECCO-Darwin v05 OAT perturbation ensemble
input decks that validate the DarwinDiff surrogate parameter-Jacobian against the real GCM.

PREPARE ONLY. This writes 17 input decks (control + 4 params x 4 symmetric geometric steps).
It NEVER submits or runs anything. Launch is a NASA-side + Jon-coordinated step (see
docs/findings/2026-07-25_surrogate_to_gcm_validation.md and the perturbation recipe
docs/findings/2026-07-23_v05_perturbation_recipe.md).

Two of the four parameters are TRAIT-OVERRIDDEN and must be edited in the file the model
actually reads at runtime, or the run silently tests nothing:

    alpfe      -> data.darwin  &DARWIN_PARAMS  ALPFE            (read directly; safe)
    scav_rat   -> data.darwin  &DARWIN_PARAMS  SCAV_RAT         (read directly; safe)
    R_PICPOC   -> data.traits  &DARWIN_TRAITS  R_PICPOC array   (data.darwin val_R_PICPOC is INERT)
    diatomgraz -> data.traits  &DARWIN_TRAITS  PALAT entries 36 & 43 (diatom prey column; INERT in data.darwin)

Every edit is applied by LITERAL token replacement scoped to the correct namelist line, then
READ BACK and asserted. Any ambiguity (token not found, or found more than once in scope)
ABORTS -- we never write a deck we could not verify. After the runs exist, the model's own
STDOUT.0000 &DARWIN_* echo is the final proof the perturbed value loaded (see the grep protocol).

USAGE
  # dry run: print the manifest, write nothing
  python scripts/perturbation/make_v05_oat_ensemble.py --v05-input /path/to/v05/llc270/input --dry-run

  # write the 17 decks under out/ (each a full copy of the input dir with one knob changed)
  python scripts/perturbation/make_v05_oat_ensemble.py --v05-input /path/to/v05/llc270/input --out /path/to/oat_ensemble
"""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

# --- control (Carroll v05) values, verbatim from data.darwin / data.traits (recipe Sec.7) ---
ALPFE0 = 0.92831
SCAV_RAT0 = 6.02502315e-7
R_PICPOC0 = 0.0418860           # data.traits R_PICPOC(2:3); NOT val_R_PICPOC=0.04245
PALAT36_0 = 0.169146            # diatom -> small zooplankton
PALAT43_0 = 0.845730            # diatom -> large zooplankton (== documented diatomgraz optimum)

# symmetric geometric steps (label -> factor). Central-difference at two magnitudes for the
# finite-difference / nonlinearity convergence check. Same steps as the surrogate side.
STEPS = {"d1.2": 1.0 / 1.2, "d1.1": 1.0 / 1.1, "x1.1": 1.1, "x1.2": 1.2}


def fmt_darwin(x: float) -> str:
    """Match data.darwin scalar style (fixed for ALPFE, E-notation for SCAV_RAT)."""
    return f"{x:.6f}"


def fmt_sci(x: float) -> str:
    return f"{x:.6E}"  # e.g. 5.020853E-07


def fmt_trait(x: float) -> str:
    """Match data.traits echo style: 15-digit mantissa, 3-digit signed exponent,
    e.g. 4.607460000000000E-002 (Fortran namelist echo)."""
    mant, exp = f"{x:.15E}".split("E")
    return f"{mant}E{exp[0]}{int(exp[1:]):03d}"


def replace_scoped(text: str, line_key: str, old_token: str, new_token: str, path: str) -> str:
    """Replace old_token with new_token on the single namelist line beginning (after optional
    whitespace) with line_key. Abort unless exactly one line matches and the token appears
    exactly once on it."""
    lines = text.splitlines(keepends=True)
    hits = [i for i, ln in enumerate(lines) if re.match(rf"\s*{re.escape(line_key)}\b", ln)]
    if len(hits) != 1:
        raise SystemExit(f"[{path}] expected exactly 1 line starting '{line_key}', found {len(hits)}")
    i = hits[0]
    if lines[i].count(old_token) != 1:
        raise SystemExit(f"[{path}] token '{old_token}' appears {lines[i].count(old_token)} times "
                         f"on the '{line_key}' line (need exactly 1); refuse to edit ambiguously")
    lines[i] = lines[i].replace(old_token, new_token)
    return "".join(lines)


def edit_alpfe(input_dir: Path, factor: float) -> tuple[str, str, str]:
    p = input_dir / "data.darwin"
    txt = p.read_text()
    new = fmt_darwin(ALPFE0 * factor)
    # old token = the literal in data.darwin (recipe Sec.7: 'ALPFE = 0.92831'), not a reformat.
    txt2 = replace_scoped(txt, "ALPFE", "0.92831", new, "data.darwin:ALPFE")
    _verify(txt2, "ALPFE", new, "data.darwin")
    return "data.darwin", txt2, f"ALPFE = {new}"


def edit_scav(input_dir: Path, factor: float) -> tuple[str, str, str]:
    p = input_dir / "data.darwin"
    txt = p.read_text()
    # data.darwin holds SCAV_RAT = 6.02502315E-7 ; match the mantissa token literally
    new = fmt_sci(SCAV_RAT0 * factor)
    txt2 = replace_scoped(txt, "SCAV_RAT", "6.02502315E-7", new, "data.darwin:SCAV_RAT")
    _verify(txt2, "SCAV_RAT", new, "data.darwin")
    return "data.darwin", txt2, f"SCAV_RAT = {new}"


def edit_rpicpoc(input_dir: Path, factor: float) -> tuple[str, str, str]:
    p = input_dir / "data.traits"
    txt = p.read_text()
    new = fmt_trait(R_PICPOC0 * factor)
    # control line: R_PICPOC =  0.0, 2*4.188600000000000E-002, 4*0.0,
    # replace only the 2* shorthand mantissa (appears once on the line).
    old_val = "4.188600000000000E-002"
    txt2 = replace_scoped(txt, "R_PICPOC", old_val, new, "data.traits:R_PICPOC")
    _verify(txt2, "R_PICPOC", new, "data.traits")
    return "data.traits", txt2, f"R_PICPOC = 0.0, 2*{new}, 4*0.0"


def edit_diatomgraz(input_dir: Path, factor: float) -> tuple[str, str, str]:
    p = input_dir / "data.traits"
    txt = p.read_text()
    new36, new43 = f"{PALAT36_0*factor:.6f}", f"{PALAT43_0*factor:.6f}"
    # both tokens live on the single PALAT line; replace each exactly once, scoped to it
    txt2 = replace_scoped(txt, "PALAT", f"{PALAT36_0:.6f}", new36, "data.traits:PALAT(36)")
    txt2 = replace_scoped(txt2, "PALAT", f"{PALAT43_0:.6f}", new43, "data.traits:PALAT(43)")
    if factor == 1.2:
        print("    !! WARNING: diatomgraz x1.2 sends PALAT(43) to "
              f"{PALAT43_0*1.2:.6f} > 1.0 -- confirm Darwin does not clamp/renormalize palatability, "
              "or cap at 1.0, or lean on the +-10% slope (recipe Sec.3d caveat 2).")
    return "data.traits", txt2, f"PALAT(36)={new36} PALAT(43)={new43}"


def _verify(text: str, key: str, new_token: str, path: str) -> None:
    line = next((ln for ln in text.splitlines() if re.match(rf"\s*{re.escape(key)}\b", ln)), None)
    if line is None or new_token not in line:
        raise SystemExit(f"[{path}] post-edit verification FAILED: '{new_token}' not on the {key} line")


EDITORS = {"alpfe": edit_alpfe, "scav_rat": edit_scav,
           "R_PICPOC": edit_rpicpoc, "diatomgraz": edit_diatomgraz}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--v05-input", required=True,
                    help="path to the v05/llc270/input dir (must contain data.darwin + data.traits)")
    ap.add_argument("--out", help="output dir to write the 17 decks (omit with --dry-run)")
    ap.add_argument("--dry-run", action="store_true", help="print the manifest, write nothing")
    args = ap.parse_args()

    inp = Path(args.v05_input)
    for f in ("data.darwin", "data.traits"):
        if not (inp / f).exists():
            raise SystemExit(f"missing {inp / f} -- point --v05-input at the real v05 llc270 input dir")

    manifest = [("control", None, "(Carroll optimum; the run we already have)")]
    print(f"{'run':<22} {'file':<12} change")
    print(f"{'control':<22} {'-':<12} Carroll optimum (reuse existing baseline)")
    for param, editor in EDITORS.items():
        for label, factor in STEPS.items():
            run = f"{param}_{label}"
            _, txt, change = editor(inp, factor)  # also verifies; aborts on ambiguity
            file = "data.traits" if param in ("R_PICPOC", "diatomgraz") else "data.darwin"
            print(f"{run:<22} {file:<12} {change}")
            manifest.append((run, param, change))
            if not args.dry_run:
                if not args.out:
                    raise SystemExit("--out is required unless --dry-run")
                dst = Path(args.out) / run
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(inp, dst)
                (dst / file).write_text(txt)

    print(f"\n{len(manifest)} decks ({'DRY RUN -- nothing written' if args.dry_run else 'written to ' + str(args.out)}).")
    print("NEXT: benchmark control + 1 perturbation first; then confirm each STDOUT.0000 &DARWIN_* echo "
          "shows the perturbed value (see the grep protocol). Do NOT trust the input file alone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
