from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_evidence_navigator.py"
SOURCE = ROOT / "docs/research_map.json"
OUTPUT = ROOT / "docs/tools/darwindiff_evidence_navigator.html"


def _builder():
    spec = importlib.util.spec_from_file_location("evidence_navigator_builder", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _payload(html: str) -> dict:
    match = re.search(
        r'<script id="map-data" type="application/json">(.*?)</script>',
        html,
        flags=re.DOTALL,
    )
    assert match is not None
    return json.loads(match.group(1))


def _application_shell(html: str) -> str:
    return re.sub(
        r'(<script id="map-data" type="application/json">).*?(</script>)',
        r"\1{}\2",
        html,
        flags=re.DOTALL,
    )


def test_generated_navigator_is_current(tmp_path: Path) -> None:
    builder = _builder()
    candidate = tmp_path / "navigator.html"
    builder.build(SOURCE, candidate)
    assert candidate.read_bytes() == OUTPUT.read_bytes()


def test_navigator_binds_the_map_counts_and_hash() -> None:
    builder = _builder()
    html = OUTPUT.read_text(encoding="utf-8")
    payload = _payload(html)
    map_data = json.loads(SOURCE.read_text(encoding="utf-8"))
    assert payload["meta"]["sha256"] == builder._sha256(SOURCE)
    assert payload["meta"]["counts"] == map_data["counts"]
    assert payload["meta"]["failing_constraints"] == 0


def test_navigator_contains_only_live_claim_rows() -> None:
    payload = _payload(OUTPUT.read_text(encoding="utf-8"))
    claims = [row for row in payload["entries"] if row["relation"] == "claim"]
    assert claims
    assert all(row["status"].startswith("live") for row in claims)


def test_navigator_preserves_scientific_boundaries() -> None:
    html = OUTPUT.read_text(encoding="utf-8")
    assert "The emulator is not" in html
    assert "emulator_globe_chl1.png" not in html
    assert "beats persistence at every scale tested" not in html.lower()
    assert "not validation of Carroll's numerical value" in html
    assert "excluded, not failed" in html
    assert "conditioning did not guarantee recovery across basins" in html


def test_navigator_quick_queries_return_citable_relations() -> None:
    payload = _payload(OUTPUT.read_text(encoding="utf-8"))
    queries = (
        "seasonally forced self-twin",
        "emulator seasonal AR1 persistence",
        "diatomgraz equatorial Pacific",
        "scav_rat vertical iron",
        "R_PICPOC Daniels anchor",
        "continuity constrained relocation path",
    )
    for query in queries:
        wanted = query.lower().split()
        matches = [
            entry
            for entry in payload["entries"]
            if entry["citable"]
            and all(
                term
                in " ".join(
                    str(entry.get(key, ""))
                    for key in ("title", "body", "doc", "parameter", "id")
                ).lower()
                for term in wanted
            )
        ]
        assert matches, query


def test_navigator_has_no_external_runtime_dependency() -> None:
    shell = _application_shell(OUTPUT.read_text(encoding="utf-8"))
    assert '<script src=' not in shell
    assert '<link rel="stylesheet"' not in shell
    assert "https://" not in shell
