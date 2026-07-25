# Earth2Studio conformance — VERIFIED against the real package, and one real bug found (2026-07-25)

**Bottom line: `DarwinBGCPrognostic` now satisfies NVIDIA's actual `PrognosticModel`
protocol (`isinstance` → `True`), but getting there exposed a genuine conformance bug that
the test suite could not have caught, because the fallback shims validate nothing.**

Verified against **earth2studio 0.18.0a0**, commit `3400b69` ("Add model load configuration
checks", #1013), cloned from `github.com/NVIDIA/earth2studio`.

## What the protocol actually requires

`earth2studio/models/px/base.py` defines `PrognosticModel` as a `@runtime_checkable`
Protocol with exactly five members:

```
__call__ · create_iterator · input_coords · output_coords · to
```

Because it is runtime-checkable, conformance is directly assertable rather than a matter
of opinion:

```python
>>> isinstance(DarwinBGCPrognostic(...), PrognosticModel)
True
```

## The bug: `_forward` assumed rank 4 and would have indexed the wrong axis

`batch_func` computes `i = len(coords) - len(input_coords) + 1` and flattens only the dims
*beyond* the model's own declared `input_coords`. We declare six —
`batch, time, lead_time, variable, lat, lon` — following the **FCN3** convention
(`models/px/fcn3.py`), so a workflow calling us with exactly those six passes a **6-D
tensor straight through the decorator uncompressed**.

Our `_forward` indexed `x[:, i]` for the channel axis. At rank 6 that is **`time`, not
`variable`**. The log-transform and the land mask were being applied to the wrong axis.

It went unnoticed because the fallback `batch_func` shim is a **no-op**: with earth2studio
absent, the decorator does nothing, tensors keep whatever rank the test happened to use
(rank 4), and everything passes. The tests proved the code *runs*; they never proved it
*conforms*.

Fixed by collapsing all leading dims into one batch axis and restoring them on the way
out, which is rank-agnostic. FCN3 solves the same problem with an explicit
`squeeze(2)`/`unsqueeze(2)`; collapsing generalises it.

## Second gap: `__call__` was missing `@batch_func()`

Both the official custom-prognostic example (`examples/08_extend/01_custom_prognostic.py`)
and the built-in `Persistence` model decorate `__call__` with it. We had it on
`_default_generator` but not on `__call__`, so single-step calls bypassed batch handling
entirely. Added.

## What was already correct

Worth recording, because these are the parts that are easy to get wrong:

- **Coordinate order** matches the canonical `batch, time, lead_time, variable, lat, lon`.
  Earth2Studio validates positionally via `handshake_dim`, so order is load-bearing.
- **`lead_time` is `np.timedelta64` and accumulates** — `output_coords` returns
  `input_coords["lead_time"] + dt`. A rollout that fails to accumulate silently labels
  every step after the first with the same valid time.
- **`create_iterator` yields the initial condition first** (0th step), per the protocol
  docstring, then runs unbounded so the caller decides `nsteps`.
- **`output_coords` validates its input** via `handshake_size` / `handshake_dim` /
  `handshake_coords`. The protocol explicitly makes this the model's responsibility.

## How to re-run the check

```bash
uv sync --extra earth2studio
uv run pytest tests/test_e2s_conformance.py -v
```

Without the extra those tests **skip**, which is the correct CI behaviour but means a
green CI run is not evidence of conformance. `tests/test_e2s.py` now uses correctly-ranked
6-D tensors so it exercises the same code path either way.

## Caveat

The conformance check covers the *interface*. It does not run our model inside a full
`earth2studio.run.deterministic` workflow, which would need the complete dependency set
(`pygrib` and friends). Interface conformance is necessary, not sufficient — an
end-to-end workflow run on the cluster is still the honest final check.
