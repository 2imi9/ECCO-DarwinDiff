"""Self-twin artifacts may not retain an external or Darwin-derived loss target."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_v3.0_joint_multi_aoi.py"


def _literal_collection(function: ast.FunctionDef, variable: str) -> set[str]:
    for node in ast.walk(function):
        if not isinstance(node, ast.Assign):
            continue
        matches = any(
            isinstance(target, ast.Name) and target.id == variable
            for target in node.targets
        )
        if not matches:
            continue
        if isinstance(node.value, ast.Dict):
            return {
                key.value
                for key in node.value.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }
        if isinstance(node.value, ast.Set):
            return {
                item.value
                for item in node.value.elts
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            }
    raise AssertionError(f"{variable} is not a literal collection in apply_twin_targets")


def _function() -> ast.FunctionDef:
    tree = ast.parse(RUNNER.read_text(encoding="utf-8"), filename=str(RUNNER))
    return next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "apply_twin_targets"
    )


def test_every_non_twin_target_is_guarded() -> None:
    guarded = _literal_collection(_function(), "non_twin_target_terms")
    assert guarded == {
        "GEOTRACES_W",
        "GEOTRACES_SUB_W",
        "DANIELS_RPICPOC_W",
        "POSI_W",
        "GEOTRACES_POC_SUB_W",
        "BLACK_ALPFE_W",
        "ALK_ABS_W",
        "DUST_ANCHOR_W",
        "PIC_ABS_W",
        "POC_ABS_W",
        "RATIO_W",
        "POSI_DARWIN_W",
        "PRIMPROD_W",
        "F_CO2_ABS_W",
    }


def test_only_implemented_twin_anchors_are_regenerable() -> None:
    regenerated = _literal_collection(_function(), "regenerated")
    assert regenerated == {
        "GEOTRACES_W",
        "GEOTRACES_SUB_W",
        "DANIELS_RPICPOC_W",
        "POSI_W",
    }
