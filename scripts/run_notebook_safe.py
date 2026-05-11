"""Execute a notebook in-place with Windows-safe event-loop policy.

Wrapper for nbclient.NotebookClient that:
1. Sets WindowsSelectorEventLoopPolicy BEFORE any zmq imports — avoids the
   known jupyter-on-Windows deadlock pattern that hit our previous nb21 run.
2. Saves the notebook to disk AFTER EACH CELL (not just at the end), so
   progress is visible via mtime and we can recover partial results if the
   kernel hangs.
3. Prints cell start/end markers to stdout so a `tail -f` of the log shows
   live progress without needing to inspect the notebook.

Usage:
    uv run python scripts/run_notebook_safe.py notebooks/21_carbonate_block_cv.ipynb
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: run_notebook_safe.py <notebook.ipynb>", file=sys.stderr)
        return 2

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    import nbformat
    from nbclient import NotebookClient

    nb_path = Path(sys.argv[1])
    if not nb_path.is_file():
        print(f"Notebook not found: {nb_path}", file=sys.stderr)
        return 3

    print(f"[runner] loading {nb_path}", flush=True)
    nb = nbformat.read(nb_path, as_version=4)
    n_cells = len(nb.cells)
    n_code = sum(1 for c in nb.cells if c.cell_type == "code")
    print(f"[runner] {n_cells} cells total, {n_code} code cells", flush=True)

    client = NotebookClient(nb, timeout=14400, kernel_name="python3")

    t0 = time.time()
    with client.setup_kernel():
        print(f"[runner] kernel started ({time.time() - t0:.1f}s)", flush=True)
        for i, cell in enumerate(nb.cells):
            if cell.cell_type != "code":
                continue
            first_line = cell.source.split("\n", 1)[0][:60]
            cell_t0 = time.time()
            print(f"[runner] cell {i:2d} START  {first_line}", flush=True)
            client.execute_cell(cell, i)
            elapsed = time.time() - cell_t0
            print(
                f"[runner] cell {i:2d} DONE   in {elapsed:6.1f}s "
                f"({len(cell.outputs)} outputs)",
                flush=True,
            )
            # Save after each cell so progress is durable and visible via mtime.
            with nb_path.open("w", encoding="utf-8") as f:
                nbformat.write(nb, f)

    total = time.time() - t0
    print(f"[runner] all cells done in {total:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
