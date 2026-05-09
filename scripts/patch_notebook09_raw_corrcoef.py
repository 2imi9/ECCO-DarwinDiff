"""One-shot patcher: switch notebook 09 corrcoef calls to RAW fields.

Follow-up to ``patch_notebook09_corrcoef.py``. Reviewer caught that passing
the z-scored field (``phyto_g_z`` after ``.std().clamp(min=1e-6)``) to
``safe_pearson_r`` defeats the relative-tolerance constant detection: the
clamp magnifies float-level noise from ~1e-15 to ~1e-9, moving
``std/|mean|`` from ~1e-16 to ~O(1) and making a constant prediction
indistinguishable from a real signal. Pearson r is scale-and-shift
invariant for non-degenerate inputs so the value is identical when the
prediction has real spread; for the constant case, the raw scale is the
only place where detection works.

This script swaps ``phyto_plot[ocean_mask]`` / ``phyto_g_plot[ocean_mask]``
for raw ``phyto_final.numpy()[ocean_mask]`` / ``phyto_global.numpy()[ocean_mask]``
in cells ``cab0000d`` and ``ee2052c7``, with the matching raw target.
"""

from __future__ import annotations

import json
from pathlib import Path

NOTEBOOK = Path(__file__).resolve().parents[1] / "notebooks" / "09_real_data_glodap_pipeline.ipynb"


def replace_source(cell: dict, old: str, new: str) -> None:
    src = "".join(cell["source"])
    if old not in src:
        cell_id = cell.get("id", "?")
        raise RuntimeError(
            f"old substring not found in cell {cell_id}\n"
            f"--- old ---\n{old}\n--- src ---\n{src}"
        )
    new_src = src.replace(old, new)
    cell["source"] = new_src.splitlines(keepends=True)


def clear_outputs(cell: dict) -> None:
    if cell.get("cell_type") == "code":
        cell["outputs"] = []
        cell["execution_count"] = None


def patch() -> None:
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    cells_by_id = {c.get("id"): c for c in nb["cells"]}

    # Cell cab0000d (DINN final eval): raw phyto_final + raw -no3_target.
    dinn_eval_cell = cells_by_id["cab0000d"]
    replace_source(
        dinn_eval_cell,
        "# Pearson correlation between target and prediction over ocean cells.\n"
        "# Uses safe_pearson_r so any non-finite values are filtered before corrcoef\n"
        "# and the structural-ceiling case (constant prediction) is reported as\n"
        '# "undefined" rather than firing a numpy divide warning.\n'
        "pred_flat = phyto_plot[ocean_mask]\n"
        "target_flat = target_plot[ocean_mask]\n"
        "result = safe_pearson_r(pred_flat, target_flat)\n",
        "# Pearson correlation between target and prediction over ocean cells.\n"
        "# Pass RAW fields (not z-scored) so safe_pearson_r's constant-detection\n"
        "# fires correctly. Pearson r is scale-and-shift invariant, so the value\n"
        "# is identical when the prediction has real spread; but z-scoring with\n"
        "# .std().clamp(min=1e-6) magnifies float-level noise from ~1e-15 to ~1e-9,\n"
        "# moving the spread/|mean| ratio from ~1e-16 to O(1) and defeating the\n"
        "# relative-tolerance check. Compare raw to raw.\n"
        "pred_flat = phyto_final.numpy()[ocean_mask]\n"
        "target_flat = (-no3_target.numpy())[ocean_mask]\n"
        "result = safe_pearson_r(pred_flat, target_flat)\n",
    )
    clear_outputs(dinn_eval_cell)

    # Cell ee2052c7 (head-to-head global eval): raw phyto_global + raw -no3_target.
    global_cell = cells_by_id["ee2052c7"]
    replace_source(
        global_cell,
        "# Pearson correlation for global-scalar fit. Use safe_pearson_r so the\n"
        "# structurally-zero-variance case (constant prediction → r mathematically\n"
        "# undefined) is reported as \"undefined (zero spatial variance)\" rather\n"
        "# than as a NaN with a numpy divide warning. That's the structural\n"
        "# ceiling we want to surface clearly.\n"
        "pred_g_flat = phyto_g_plot[ocean_mask]\n"
        "target_flat = target_plot[ocean_mask]\n"
        "result_global = safe_pearson_r(pred_g_flat, target_flat)\n",
        "# Pearson correlation for global-scalar fit. Pass RAW fields (not the\n"
        "# z-scored phyto_g_plot / target_plot) so safe_pearson_r can detect the\n"
        "# structurally-zero-variance case: z-scoring with .std().clamp(min=1e-6)\n"
        "# magnifies float-level noise from ~1e-15 to ~1e-9, defeating the\n"
        "# relative-tolerance constant check. Pearson r is scale-and-shift\n"
        "# invariant for non-degenerate inputs, so the value is identical when\n"
        "# the prediction has real spread.\n"
        "pred_g_flat = phyto_global.numpy()[ocean_mask]\n"
        "target_flat_raw = (-no3_target.numpy())[ocean_mask]\n"
        "result_global = safe_pearson_r(pred_g_flat, target_flat_raw)\n",
    )
    clear_outputs(global_cell)

    NOTEBOOK.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Patched {NOTEBOOK.name}: cleared outputs on cab0000d, ee2052c7")


if __name__ == "__main__":
    patch()
