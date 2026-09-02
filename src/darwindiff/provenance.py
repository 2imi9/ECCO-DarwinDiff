"""What code produced this number.

WHY THIS EXISTS
---------------
On 2026-08-03 the published flagship was found to be **bound to a code build**. The same
configuration and the same seeds give `scav_rat` 60% on the 2026-07-26 tree and 2% on HEAD; the
North Atlantic leg went 50% -> 0%. Nothing detected it. `verify_run` exited 0, the recorded config
matched on every key, and the test suite was green — because every one of those checks inspects the
*artifact*, and no artifact recorded the code that wrote it.

That failure is not recoverable after the fact. A config you forgot to record can be reconstructed
from a sibling run; a code version you never recorded cannot be reconstructed at all, and every
number produced in the gap becomes unattributable.

So: stamp it at write time, always, and never let stamping fail a run.

TWO IDENTIFIERS, BECAUSE ONE IS NOT AVAILABLE WHERE IT MATTERS
--------------------------------------------------------------
The cluster checkout (`~/emulator_poc` on AICR) is **not a git repository** — issue #218 — which is
precisely where every production number is produced. So a git SHA alone would be `None` exactly
when it is needed. Content hashes are always computable and are the fallback that actually works:

* ``git`` — SHA + dirty flag when a repo is present. Authoritative when available.
* ``code_digest`` — a hash over the runner and the ``darwindiff`` package. Always available, and
  it compares two checkouts that have no git in common. A digest match is a strong statement:
  the executable content was identical.

Stdlib only, so ``verify_run.py`` (which deliberately avoids torch/numpy) can import it.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path


def _git(repo: Path, *args: str) -> str | None:
    """Run a read-only git command, or return None if git/the repo is unavailable."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip() or None


def code_digest(paths: list[Path]) -> str:
    """A stable content hash over the given files and ``.py`` trees.

    Sorted by relative path so it does not depend on filesystem order, and hashing the relative
    path alongside the bytes so a rename is a change. Newlines are normalised, because the same
    commit checked out on Windows and on Linux differs only by CRLF and must not read as different
    code.
    """
    h = hashlib.sha256()
    files: list[tuple[str, Path]] = []
    for p in paths:
        if p.is_dir():
            for f in sorted(p.rglob("*.py")):
                files.append((f.relative_to(p.parent).as_posix(), f))
        elif p.is_file():
            files.append((p.name, p))
    for rel, f in sorted(files):
        try:
            data = f.read_bytes()
        except OSError:
            continue
        h.update(rel.encode("utf-8"))
        h.update(data.replace(b"\r\n", b"\n"))
    return h.hexdigest()[:16]


def config_files_from_env(var: str = "DD_PROVENANCE_FILES") -> list[Path]:
    """Paths listed in an env var, ``os.pathsep``-separated. Missing entries are dropped."""
    raw = os.environ.get(var, "")
    return [p for p in (Path(x).expanduser() for x in raw.split(os.pathsep) if x.strip())
            if p.is_file()]


def stamp(runner_file: str | os.PathLike | None = None) -> dict:
    """Provenance block for a run artifact. Never raises.

    Returns ``git_sha``, ``git_dirty``, ``git_describe``, ``code_digest``, ``runner_md5``,
    ``runner_file``, and ``config_digest`` / ``config_files``. Any field may be ``None``; a
    ``None`` git SHA on the cluster is expected and is exactly why ``code_digest`` exists.

    WHY CONFIGS ARE HASHED TOO
    --------------------------
    Three separate runs were lost on 2026-08-03, and none of them to the science: the
    reproducibility appendix omitted three levers, `flagship_geo1.sh` did not pin the learning
    rate, and a config copied from Windows arrived with CRLF so every value carried a trailing
    carriage return. **The transmission path from repo to run is where this project loses runs**,
    and it had the least machinery around it -- `code_digest` recorded what code ran while
    nothing recorded which config bytes it ran with.

    Point ``DD_PROVENANCE_FILES`` at the sourced config(s) and every artifact carries their
    digest, so two runs can be compared on configuration without either one being a git
    checkout, and a silently-mangled config is visible after the fact instead of inferred.
    Line endings are normalised, so the same config on Windows and Linux hashes equal.
    """
    out: dict = {
        "git_sha": None, "git_dirty": None, "git_describe": None,
        "code_digest": None, "runner_md5": None, "runner_file": None,
        "config_digest": None, "config_files": None,
    }
    try:
        here = Path(__file__).resolve()
        pkg = here.parent                      # src/darwindiff
        repo = pkg.parent.parent               # repo root, when there is one

        runner = Path(runner_file).resolve() if runner_file else None
        if runner and runner.is_file():
            out["runner_file"] = runner.name
            out["runner_md5"] = hashlib.md5(
                runner.read_bytes().replace(b"\r\n", b"\n")).hexdigest()

        targets = [pkg] + ([runner] if runner and runner.is_file() else [])
        out["code_digest"] = code_digest(targets)

        cfgs = config_files_from_env()
        if cfgs:
            out["config_files"] = {
                c.name: hashlib.md5(
                    c.read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:12]
                for c in cfgs
            }
            out["config_digest"] = code_digest(cfgs)

        sha = _git(repo, "rev-parse", "HEAD")
        if sha:
            out["git_sha"] = sha[:12]
            status = _git(repo, "status", "--porcelain")
            out["git_dirty"] = bool(status)
            out["git_describe"] = _git(repo, "describe", "--always", "--dirty", "--tags")
    except Exception:  # never fail a run over provenance
        pass
    return out
