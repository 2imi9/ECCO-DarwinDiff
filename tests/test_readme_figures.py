"""The README figures must be built from their committed sources.

CI has no TeX, so it cannot rebuild the SVGs. Instead docs/figures/readme/build.sh records the
hashes of every source and every SVG in build.sha256, and this test recomputes them: a .tex or
style edit committed without rebuilding, or a hand-edited SVG, fails here rather than leaving
the README showing a stale figure.
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "docs" / "figures" / "readme"


def _manifest_module():
    spec = importlib.util.spec_from_file_location("readme_figure_manifest", FIG_DIR / "manifest.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_svgs_match_their_sources():
    manifest = _manifest_module()
    recorded = {}
    for line in (FIG_DIR / "build.sha256").read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        recorded[name] = digest
    assert set(recorded) == set(manifest.tracked_files()), "build.sha256 lists the wrong files"
    stale = [name for name in manifest.tracked_files()
             if manifest.digest(FIG_DIR / name) != recorded[name]]
    assert not stale, (
        f"{stale} changed since the figures were last built. Rebuild them with "
        "`bash docs/figures/readme/build.sh` and commit the SVGs with build.sha256."
    )


def test_readme_embeds_only_built_figures():
    readme = (ROOT / "README.md").read_text()
    embedded = re.findall(r'src="(docs/figures/readme/[^"]+\.svg)"', readme)
    assert embedded, "README embeds no figure from docs/figures/readme"
    built = {f"docs/figures/readme/{name}" for name in _manifest_module().tracked_files()}
    assert set(embedded) <= built, f"README embeds figures the build does not produce: {embedded}"
