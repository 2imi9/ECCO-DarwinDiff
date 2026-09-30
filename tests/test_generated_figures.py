"""The plotted figures must match the scripts that generate them.

CI has no ECCO-Darwin data, so it cannot regenerate these PNGs. Each generator records the hash of
its own source and of the PNGs it wrote in docs/figures/generated.sha256; this test recomputes
them, so a generator edited without regenerating (or a hand-edited PNG) fails here.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_MODULE = ROOT / "docs" / "figures" / "generated_manifest.py"


def _manifest():
    spec = importlib.util.spec_from_file_location("generated_figure_manifest", MANIFEST_MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_manifest_lists_every_generator_and_output():
    m = _manifest()
    assert set(m.read_manifest()) == set(m.tracked_files()), (
        "generated.sha256 lists the wrong files"
    )


def test_generated_figures_match_their_scripts():
    m = _manifest()
    recorded = m.read_manifest()
    stale = [name for name in m.tracked_files() if m.digest(name) != recorded.get(name)]
    assert not stale, (
        f"{stale} changed since the figures were last generated. Re-run the generator "
        "(uv run --group figures python <script> ...) and commit the PNGs with generated.sha256."
    )


def test_embedded_generated_figures_are_registered():
    registered = {out for outs in _manifest().FIGURES.values() for out in outs}
    for doc in ("README.md", "STATUS.md"):
        text = (ROOT / doc).read_text(encoding="utf-8")
        for src in re.findall(r"(docs/figures/[\w.-]+\.png)", text):
            assert src in registered, f"{doc} embeds {src}, which no registered generator produces"
