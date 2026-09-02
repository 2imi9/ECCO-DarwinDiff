"""Safe ``torch.load`` for this repo's ``.pt`` caches, bundles, and checkpoints.

Why this module exists
----------------------
``torch.load(..., weights_only=False)`` runs the pickle machinery unrestricted, which
means loading a ``.pt`` file executes whatever that file asks for. Our ``.pt`` files come
from ``$DARWIN_DATA_ROOT`` -- a shared/scratch area on Explorer and AICR, and a plain
local directory on a workstation -- so "the checkpoint is trusted because we wrote it"
is an assumption about filesystem permissions, not something the code enforces.
Greptile flagged the unrestricted loads as a P1 on PR #195.

``weights_only=True`` restricts unpickling to tensors and a small builtin allowlist. That
alone is *not* enough here: none of our ``.pt`` files are plain tensor dicts. The AOI
target caches (``eqpac_targets_*.pt`` / ``native_targets_*.pt``) store **numpy** arrays
plus an ``aoi_name`` str and an ``aoi_bounds`` tuple; the emulator checkpoints store numpy
``mean``/``std`` alongside their state_dicts. So a bare ``weights_only=True`` raises
``UnpicklingError: Unsupported global: GLOBAL numpy._core.multiarray._reconstruct``.

The fix is to allowlist exactly the numpy array-reconstruction plumbing and nothing else.
Everything in ``_numpy_safe_globals()`` is a data constructor -- ``_reconstruct``/``scalar``
build an array or scalar from a dtype, a shape, and a raw buffer; the ``*DType`` classes
carry no payload beyond the dtype identity. None of them is a code-execution vector the
way ``__reduce__`` on an arbitrary class is.

Scoping and policy
------------------
We use the ``torch.serialization.safe_globals`` **context manager** rather than the
process-global ``add_safe_globals``, so the allowlist covers our own load and does not
silently widen the safe set for unrelated ``torch.load`` calls elsewhere in the process.

There is deliberately **no fallback to** ``weights_only=False``. If a file needs a global
outside this allowlist, that is either a corrupt/foreign file or a schema change, and both
should surface as a loud failure so the cache gets regenerated -- not be papered over by
silently re-enabling arbitrary-object unpickling.

Usage::

    from darwindiff.safe_load import safe_torch_load

    cache = safe_torch_load(cache_path)                      # AOI target cache
    ck = safe_torch_load(ckpt, map_location=device)          # emulator checkpoint
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np
import torch

__all__ = ["SafeLoadError", "safe_torch_load"]


class SafeLoadError(RuntimeError):
    """A ``.pt`` file could not be loaded under the restricted unpickler.

    Raised instead of falling back to ``weights_only=False``. The usual cause is a cache
    written by an older/newer schema; regenerate it rather than re-enabling the unsafe
    load path.
    """


# Numeric + bool dtype classes only. `ObjectDType` is deliberately excluded: an
# object-dtype array is a container for arbitrary pickled objects and has no legitimate
# use in these numeric caches. Datetime/void/string dtypes are excluded for the same
# "allowlist only what we actually store" reason -- if one is ever needed, the load fails
# loudly and this list gets a considered addition.
_DTYPE_CLASS_NAMES = (
    "BoolDType",
    "Float16DType",
    "Float32DType",
    "Float64DType",
    "Int8DType",
    "Int16DType",
    "Int32DType",
    "Int64DType",
    "LongDType",
    "LongLongDType",
    "UInt8DType",
    "UInt16DType",
    "UInt32DType",
    "UInt64DType",
    "ULongDType",
    "ULongLongDType",
    "Complex64DType",
    "Complex128DType",
)


def _numpy_safe_globals() -> list[Any]:
    """The minimal allowlist that lets numpy arrays through the restricted unpickler.

    Entries are either a bare callable (allowlisted under its runtime
    ``{__module__}.{__qualname__}``) or a ``(callable, "explicit.name")`` tuple. The
    tuples matter for cross-version portability: numpy 2.x pickles reference
    ``numpy._core.multiarray._reconstruct`` while numpy 1.x pickles -- e.g. a cache built
    on a cluster node with numpy 1.26 -- reference ``numpy.core.multiarray._reconstruct``.
    torch matches the allowlist on the *string in the pickle stream*, so a cache stays
    loadable regardless of which numpy wrote it. ``numpy.dtypes`` does not exist at all on
    numpy 1.x (dtypes pickle via ``numpy.dtype`` there), hence the ``getattr`` guards.
    """
    # `numpy._core` is the numpy>=2 home; `numpy.core` is a deprecated shim there and the
    # real home on numpy 1.x. Resolve whichever exists, then allowlist under *both* names.
    multiarray = getattr(getattr(np, "_core", None), "multiarray", None)
    if multiarray is None:  # numpy 1.x
        multiarray = np.core.multiarray  # type: ignore[attr-defined]

    allowed: list[Any] = [
        np.ndarray,
        np.dtype,
        # Both module spellings for the two array/scalar reconstruction functions.
        (multiarray._reconstruct, "numpy._core.multiarray._reconstruct"),
        (multiarray._reconstruct, "numpy.core.multiarray._reconstruct"),
        (multiarray.scalar, "numpy._core.multiarray.scalar"),
        (multiarray.scalar, "numpy.core.multiarray.scalar"),
    ]
    dtypes_mod = getattr(np, "dtypes", None)
    if dtypes_mod is not None:  # numpy >= 2.0
        for cls_name in _DTYPE_CLASS_NAMES:
            cls = getattr(dtypes_mod, cls_name, None)
            if cls is not None:
                allowed.append(cls)
    return allowed


# ---------------------------------------------------------------------------
# KNOWN LIMIT: cross-major-version numpy, UNVERIFIED
#
# Greptile flagged (PR #203) that a cache written under numpy 2.x might not load on a
# numpy 1.26 node, since `numpy.dtypes` does not exist there and the loop above then
# allowlists no dtype classes at all.
#
# What is verified: on a numpy 2.x runtime, removing the `*DType` classes DOES break the
# load ("but got <class 'numpy.dtypes.Float64DType'>"). That is why they are listed.
#
# What is NOT verified, either way: the actual numpy-1.26 runtime. torch's restricted
# unpickler type-checks the object it BUILDS, not the name in the stream, and under numpy
# 1.26 `numpy.dtype('float64')` builds a plain `numpy.dtype` -- which IS allowlisted above.
# By that mechanism the cross-version read should succeed, but reasoning is not a test and
# building a numpy-1.26 + torch environment to check it timed out. Treat this as an open
# question, not a cleared one.
#
# If it does fail on an older node, the symptom is a loud SafeLoadError naming the file
# (never a silent fallback), and the fix is to regenerate the cache on that node. The
# safest operational rule until someone tests it: generate caches with the same numpy
# major version that will consume them.
# ---------------------------------------------------------------------------


def safe_torch_load(
    path: str | os.PathLike[str],
    *,
    map_location: Any = None,
) -> Any:
    """``torch.load`` restricted to tensors, builtins, and numpy arrays.

    Drop-in replacement for ``torch.load(path, weights_only=False)`` on this repo's
    ``.pt`` files: AOI target caches, IC caches, scout input bundles, and emulator /
    diffusion checkpoints all load unchanged.

    Args:
        path: The ``.pt`` file to load.
        map_location: Passed straight through to ``torch.load``.

    Raises:
        SafeLoadError: The file needs a global outside the allowlist. Regenerate the
            cache; do not switch this call back to ``weights_only=False``.
    """
    path = Path(path)
    try:
        with torch.serialization.safe_globals(_numpy_safe_globals()):
            return torch.load(path, map_location=map_location, weights_only=True)
    except Exception as exc:  # re-raised below with actionable context; never fall back
        raise SafeLoadError(
            f"could not safely load {path}: {type(exc).__name__}: {exc}\n"
            "This file needs a pickle global outside darwindiff.safe_load's allowlist. "
            "Delete and regenerate the cache/checkpoint. Do NOT switch this call back to "
            "weights_only=False -- that re-enables arbitrary code execution from the file."
        ) from exc
