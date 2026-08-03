"""Guards on the canonical flagship config, `scripts/configs/flagship_geo1.sh`.

Why this exists. The reproducibility appendix gives the flagship as an override list that
delegates to `covar_env_common.sh`, a file that lives only on the AICR cluster and is not in
this repo. Following the row alone silently omits `POSI_W=1`, `USE_EPPLEY_T=1` and the per-AOI
weights {1,2,2}. That was found on 2026-07-29, fixed by committing `flagship_geo1.sh`, and a
warning banner was added to the appendix.

It happened again anyway. On 2026-08-01 the flagship window sweep (job 244487) hand-copied the
appendix row into an sbatch, omitted the same three values, and returned `scav_rat` 3/50 against
the published 25/50 -- firing the pre-registration's own falsifier and voiding a 30-task array.
A banner in a doc did not prevent a second occurrence, so the guard has to be executable.

The third test is the generic one. `flagship_geo1.sh` states that it sets values equal to the
runner's defaults explicitly, "so a future default change cannot silently move the flagship."
That guarantee is void for any variable whose *name* nothing reads. Until 2026-08-02 the file
exported `USE_MLD_CHANNEL` and `USE_AOI_ID_CHANNEL`, which are the runner's internal Python
identifiers, not its environment variables (it reads `MLD_CHANNEL` / `AOI_ID_CHANNEL`). Both
happened to equal the defaults, so the config was inert rather than wrong -- the failure mode it
promises to prevent was live in the file that promises it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_CFG = _ROOT / "scripts" / "configs" / "flagship_geo1.sh"
_SLURM = _ROOT / "scripts" / "slurm"

pytestmark = pytest.mark.skipif(not _CFG.is_file(), reason=f"{_CFG} not present")

# Read back out of a verified flagship artifact (verify_run exit 0; alpfe 49/50,
# scav_rat 25/50, R_PICPOC 50/50 per-AOI). The first five are what the appendix row omits.
_REQUIRED = {
    "POSI_W": "1",
    "USE_EPPLEY_T": "1",
    "AOI_W_EQPAC": "1",
    "AOI_W_NATLSUBPOLAR": "2",
    "AOI_W_SOUTHERNOCEANPAC": "2",
    "DANIELS_RPICPOC_W": "1",
    "RATIO_W": "0",
    "GLOBAL_SCALAR": "0",
}


@pytest.fixture(scope="module")
def exports() -> dict[str, str]:
    """`export NAME=VALUE` pairs from the config, comments and quotes stripped."""
    out: dict[str, str] = {}
    for line in _CFG.read_text(encoding="utf-8").splitlines():
        m = re.match(r'^\s*export\s+([A-Z][A-Z0-9_]*)=(.*)$', line)
        if not m:
            continue
        value = m.group(2).split("#")[0].strip().strip('"').strip("'")
        out[m.group(1)] = value
    return out


@pytest.fixture(scope="module")
def env_reads() -> tuple[set[str], set[str]]:
    """Environment names the codebase actually reads: (literal, dynamic-prefix).

    Some are built at runtime, e.g. ``os.environ.get(f"AOI_W_{k.upper()}")``, so a literal
    match alone would report the per-AOI weights as dead.
    """
    literal: set[str] = set()
    prefixes: set[str] = set()
    access = re.compile(r'(?:environ\.get\(|environ\[|getenv\()(f?)"([^"]+)"')
    for path in [*(_ROOT / "scripts").rglob("*.py"), *(_ROOT / "src").rglob("*.py")]:
        for is_f, name in access.findall(path.read_text(encoding="utf-8", errors="replace")):
            if is_f and "{" in name:
                prefixes.add(name.split("{")[0])
            elif "{" not in name:
                literal.add(name)
    return literal, prefixes


def test_flagship_config_pins_the_values_the_appendix_row_omits(exports: dict[str, str]) -> None:
    """The three omissions cost two sessions. They must be in the committed config."""
    for name, want in _REQUIRED.items():
        assert name in exports, (
            f"{_CFG.name} no longer exports {name}. The reproducibility appendix omits it, so "
            "dropping it here leaves no committed source for the flagship's actual value."
        )
        assert exports[name] == want, (
            f"{_CFG.name} sets {name}={exports[name]}, expected {want}. This value was read out "
            "of a verified flagship artifact; changing it silently redefines every headline count."
        )


def test_every_flagship_config_export_is_actually_read(
    exports: dict[str, str], env_reads: tuple[set[str], set[str]]
) -> None:
    """An exported name nothing reads is inert, and inert is indistinguishable from applied.

    This is the generic form of the `USE_MLD_CHANNEL` bug: the config looked like it pinned the
    channel setting and pinned nothing, so the protection it advertises against a future default
    change did not exist for that variable.
    """
    literal, prefixes = env_reads
    dead = sorted(
        name for name in exports
        if name not in literal and not any(name.startswith(p) for p in prefixes)
    )
    assert not dead, (
        f"{_CFG.name} exports {dead}, which nothing in scripts/ or src/ reads. Either the runner's "
        "variable was renamed, or the wrong spelling was used (the runner reads MLD_CHANNEL, not "
        "USE_MLD_CHANNEL). An export nothing reads pins nothing."
    )


def test_flagship_claiming_sbatch_sources_the_config() -> None:
    """A batch script that trains and says 'flagship' must source the config, not re-type it.

    Hand-transcribing the env list is how job 244487 came to omit three levers and fail its own
    pre-registered falsifier. Scoped to scripts that launch the runner: a grading script names
    the flagship too, but it reads finished artifacts and sets no training config.
    """
    if not _SLURM.is_dir():
        pytest.skip(f"{_SLURM} not present")
    offenders = []
    for path in sorted(_SLURM.glob("*.sbatch")):
        text = path.read_text(encoding="utf-8", errors="replace")
        trains = "run_v3.0_joint_multi_aoi.py" in text
        claims = "flagship" in path.name.lower() or "flagship" in text.lower()
        if trains and claims and "configs/flagship_geo1.sh" not in text:
            offenders.append(path.name)
    assert not offenders, (
        f"{offenders} mention the flagship but do not source scripts/configs/flagship_geo1.sh. "
        "Reproducing the flagship from a hand-copied env list omits POSI_W, USE_EPPLEY_T and the "
        "per-AOI weights, and the resulting run trains and grades without complaint."
    )
