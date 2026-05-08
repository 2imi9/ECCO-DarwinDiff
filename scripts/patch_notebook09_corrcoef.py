"""One-shot patcher: wire safe_pearson_r into notebook 09.

What this changes (cell IDs, not indices, so the script stays robust if cells
are reshuffled):

- ``cab00001`` (imports): add the diagnostics import.
- ``cab0000d`` (DINN final eval): assert no NaN after the integration loop and
  route the corrcoef through safe_pearson_r + format_pearson.
- ``ee2052c7`` (head-to-head global-scalar eval): same routing, plus inline
  formatting of the plot titles so the structural-ceiling case prints as
  "undefined" instead of a NaN with a numpy divide warning.

Outputs and execution_count are cleared on the cells we touched, since their
recorded outputs no longer match the source. Run the notebook to regenerate.
"""

from __future__ import annotations

import json
from pathlib import Path

NOTEBOOK = Path(__file__).resolve().parents[1] / "notebooks" / "09_real_data_glodap_pipeline.ipynb"


def replace_source(cell: dict, old: str, new: str) -> None:
    """Replace exact substring `old` with `new` in cell['source'], preserving
    the .ipynb list-of-lines convention."""
    src = "".join(cell["source"])
    if old not in src:
        cell_id = cell.get("id", "?")
        raise RuntimeError(
            f"old substring not found in cell {cell_id}\n"
            f"--- old ---\n{old}\n--- src ---\n{src}"
        )
    new_src = src.replace(old, new)
    # Re-split into the list-of-lines form, keeping the trailing-newline-on-all-but-last invariant.
    lines = new_src.splitlines(keepends=True)
    cell["source"] = lines


def clear_outputs(cell: dict) -> None:
    if cell.get("cell_type") == "code":
        cell["outputs"] = []
        cell["execution_count"] = None


def patch() -> None:
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    cells_by_id = {c.get("id"): c for c in nb["cells"]}

    # 1) imports cell — add diagnostics import.
    imports_cell = cells_by_id["cab00001"]
    replace_source(
        imports_cell,
        "from darwindiff.networks import DINN\n",
        "from darwindiff.networks import DINN\n"
        "from darwindiff.diagnostics import format_pearson, safe_pearson_r\n",
    )
    clear_outputs(imports_cell)

    # 2) DINN final eval cell — add NaN assert and route corrcoef through helper.
    dinn_eval_cell = cells_by_id["cab0000d"]
    replace_source(
        dinn_eval_cell,
        "    phyto_final = (state[1] + state[2]).cpu()                       # [H, W]\n",
        "    phyto_final = (state[1] + state[2]).cpu()                       # [H, W]\n"
        "\n"
        "# Sanity check: the box-model integration must not produce NaN at any ocean\n"
        "# cell. A single bad cell would silently poison the z-score (mean / std go\n"
        "# NaN, propagating to the entire field) and corrupt the headline correlation.\n"
        'assert torch.isfinite(phyto_final[mask]).all(), (\n'
        '    \"phyto_final has non-finite values at ocean cells — \"\n'
        '    \"the box-model integration blew up. Inspect params_final for outliers.\"\n'
        ")\n",
    )
    replace_source(
        dinn_eval_cell,
        "# Pearson correlation between target and prediction over ocean cells.\n"
        "pred_flat = phyto_plot[ocean_mask]\n"
        "target_flat = target_plot[ocean_mask]\n"
        "corr = np.corrcoef(pred_flat, target_flat)[0, 1]\n"
        'print(f"\\nPearson correlation (predicted phyto vs -NO3): r = {corr:.3f}")',
        "# Pearson correlation between target and prediction over ocean cells.\n"
        "# Uses safe_pearson_r so any non-finite values are filtered before corrcoef\n"
        "# and the structural-ceiling case (constant prediction) is reported as\n"
        '# "undefined" rather than firing a numpy divide warning.\n'
        "pred_flat = phyto_plot[ocean_mask]\n"
        "target_flat = target_plot[ocean_mask]\n"
        "result = safe_pearson_r(pred_flat, target_flat)\n"
        "corr = result.r\n"
        'print(f"\\nPearson correlation (predicted phyto vs -NO3): "\n'
        '      f"r = {format_pearson(result, n_total=int(ocean_mask.sum()))}")',
    )
    clear_outputs(dinn_eval_cell)

    # 3) Head-to-head global-scalar eval cell — same routing for both predictors,
    # and inline-formatted plot titles using is_constant.
    global_cell = cells_by_id["ee2052c7"]
    replace_source(
        global_cell,
        "# Pearson correlation for global-scalar fit.\n"
        "pred_g_flat = phyto_g_plot[ocean_mask]\n"
        "target_flat = target_plot[ocean_mask]\n"
        "corr_global = np.corrcoef(pred_g_flat, target_flat)[0, 1]\n"
        "\n"
        'print(f"Pearson correlation, predicted phyto vs -NO3 (ocean cells only):")\n'
        'print(f"  Global-scalar fit (Green\'s-functions class):  '
        'r = {corr_global:.3f}  (r^2 = {corr_global**2:.3f})")\n'
        'print(f"  DINN per-cell fit (DarwinDiff class):          '
        'r = {corr:.3f}  (r^2 = {corr**2:.3f})")',
        "# Pearson correlation for global-scalar fit. Use safe_pearson_r so the\n"
        "# structurally-zero-variance case (constant prediction → r mathematically\n"
        "# undefined) is reported as \"undefined (zero spatial variance)\" rather\n"
        "# than as a NaN with a numpy divide warning. That's the structural\n"
        "# ceiling we want to surface clearly.\n"
        "pred_g_flat = phyto_g_plot[ocean_mask]\n"
        "target_flat = target_plot[ocean_mask]\n"
        "result_global = safe_pearson_r(pred_g_flat, target_flat)\n"
        "corr_global = result_global.r  # NaN if is_constant; finite otherwise\n"
        "\n"
        'print(f"Pearson correlation, predicted phyto vs -NO3 (ocean cells only):")\n'
        'print(f"  Global-scalar fit (Green\'s-functions class):  '
        'r = {format_pearson(result_global, n_total=int(ocean_mask.sum()))}")\n'
        'print(f"  DINN per-cell fit (DarwinDiff class):          '
        'r = {format_pearson(result, n_total=int(ocean_mask.sum()))}")',
    )
    replace_source(
        global_cell,
        'axes[1, 0].set_title(f"Global-scalar prediction (r = {corr_global:.3f})")',
        'axes[1, 0].set_title(\n'
        '    "Global-scalar prediction (" + (\n'
        '        "undefined" if result_global.is_constant else f"r = {corr_global:.3f}"\n'
        '    ) + ")"\n'
        ")",
    )
    replace_source(
        global_cell,
        'axes[1, 1].set_title(f"DINN prediction (r = {corr:.3f})")',
        'axes[1, 1].set_title(\n'
        '    "DINN prediction (" + (\n'
        '        "undefined" if result.is_constant else f"r = {corr:.3f}"\n'
        '    ) + ")"\n'
        ")",
    )
    clear_outputs(global_cell)

    NOTEBOOK.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Patched {NOTEBOOK.name}: cleared outputs on cab00001, cab0000d, ee2052c7")


if __name__ == "__main__":
    patch()
