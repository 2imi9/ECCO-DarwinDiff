"""Keep generated.sha256: the hashes of the plotted figures and of the scripts that make them.

These PNGs need the ECCO-Darwin v05 bin-average file (1.9 GB) to regenerate, so CI cannot rebuild
them. Instead each generator records the hash of its own source and of every PNG it wrote, and
tests/test_generated_figures.py recomputes them: a generator edited without regenerating, or a
hand-edited PNG, fails CI. This mirrors docs/figures/readme/manifest.py for the TikZ figures.
Text sources are hashed with LF line endings, so a CRLF checkout hashes the same.

The generators call ``update(<their repo-relative path>)`` after writing their default outputs.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).resolve().parent / "generated.sha256"
FIGURES = {
    "scripts/make_chlorophyll_map.py": [
        "docs/figures/v05_surface_chlorophyll.png",
        "docs/figures/v05_surface_chlorophyll_dark.png",
    ],
    "scripts/make_param_field_figure.py": [
        "docs/figures/fig_param_fields.png",
        "docs/figures/fig_param_fields_dark.png",
    ],
}
TEXT_SUFFIXES = {".py"}


def tracked_files() -> list[str]:
    return [name for script, outputs in FIGURES.items() for name in (script, *outputs)]


def digest(name: str) -> str:
    data = (REPO / name).read_bytes()
    if Path(name).suffix in TEXT_SUFFIXES:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def read_manifest() -> dict[str, str]:
    if not MANIFEST.exists():
        return {}
    pairs = (line.split(maxsplit=1) for line in MANIFEST.read_text().splitlines() if line.strip())
    return {name: h for h, name in pairs}


def update(script: str) -> None:
    """Re-hash one generator and the outputs it just wrote; keep every other entry."""
    if script not in FIGURES:
        raise SystemExit(f"{script} is not a registered figure generator: {sorted(FIGURES)}")
    recorded = read_manifest()
    for name in (script, *FIGURES[script]):
        recorded[name] = digest(name)
    lines = [f"{recorded[name]}  {name}" for name in tracked_files() if name in recorded]
    with open(MANIFEST, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"updated {MANIFEST.name} for {script}")
