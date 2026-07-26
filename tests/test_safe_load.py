"""Tests for darwindiff.safe_load — restricted unpickling of this repo's .pt files.

These lock in the two halves of the Greptile P1 fix (PR #195 follow-up): the repo's real
``.pt`` payload shapes must still load, and anything outside the numpy allowlist must fail
loudly rather than silently falling back to arbitrary-object unpickling.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from darwindiff.safe_load import SafeLoadError, _numpy_safe_globals, safe_torch_load


def _aoi_cache_payload() -> dict:
    """The AOI target-cache shape (``eqpac_targets_*.pt`` / ``native_targets_*.pt``).

    Numpy arrays plus a str and a tuple -- deliberately NOT a dict of tensors, which is
    why a bare ``weights_only=True`` is not sufficient for these files.
    """
    return {
        "aoi_name": "Equatorial Pacific",
        "aoi_bounds": (-5.0, 15.0, -160.0, -110.0),
        "resolution": "native",
        "native_flat_idx": np.arange(6, dtype=np.int64),
        "darwin_lats": np.linspace(-5, 15, 6),
        "sst": np.random.rand(2, 3).astype(np.float32),
        "chl_per_pft": {f"Chl{i}": np.random.rand(2, 3).astype(np.float32)
                        for i in range(1, 6)},
        "pic_binned": np.random.rand(2, 3),
        "poc_binned": np.random.rand(2, 3),
    }


def _checkpoint_payload() -> dict:
    """The emulator/diffusion checkpoint shape: state_dicts + numpy stats + config."""
    sd = {"w": torch.randn(3, 3), "b": torch.zeros(3)}
    return {
        "regression": sd,
        "diffusion": sd,
        "mean": np.random.rand(4).astype(np.float32),
        "std": np.random.rand(4).astype(np.float32),
        "channels": ["DIC_k0", "ALK_k0", "PIC_k0", "POC_k0"],
        "config": {"modes": 24, "reg_width": 64, "lr": 1e-3, "cpu": False, "out": None},
        "history": [{"epoch": 0, "train_mse_z": 0.5}, {"epoch": 1, "val_edm": 0.4}],
        "epoch": 2,
    }


def _assert_same(a, b, path="root") -> None:
    assert type(a) is type(b), f"{path}: {type(a)} vs {type(b)}"
    if isinstance(a, dict):
        assert a.keys() == b.keys(), f"{path}: keys differ"
        for k in a:
            _assert_same(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, np.ndarray):
        assert a.dtype == b.dtype and a.shape == b.shape, f"{path}: dtype/shape"
        assert np.array_equal(a, b), f"{path}: values"
    elif isinstance(a, torch.Tensor):
        assert torch.equal(a, b), f"{path}: tensor values"
    elif isinstance(a, list | tuple):
        assert len(a) == len(b), f"{path}: length"
        for i, (x, y) in enumerate(zip(a, b)):
            _assert_same(x, y, f"{path}[{i}]")
    else:
        assert a == b, f"{path}: {a!r} vs {b!r}"


class TestRoundTrip:
    def test_aoi_cache_shape_round_trips(self, tmp_path) -> None:
        payload = _aoi_cache_payload()
        p = tmp_path / "targets.pt"
        torch.save(payload, p)
        _assert_same(payload, safe_torch_load(p))

    def test_checkpoint_shape_round_trips(self, tmp_path) -> None:
        payload = _checkpoint_payload()
        p = tmp_path / "ckpt.pt"
        torch.save(payload, p)
        _assert_same(payload, safe_torch_load(p, map_location="cpu"))

    def test_bare_weights_only_true_is_insufficient(self, tmp_path) -> None:
        """Guards the assumption PR #195 got wrong: these are not plain tensor dicts."""
        p = tmp_path / "targets.pt"
        torch.save(_aoi_cache_payload(), p)
        with pytest.raises(Exception):  # torch raises UnpicklingError here
            torch.load(p, weights_only=True)
        safe_torch_load(p)  # ...but the allowlisted loader handles it

    def test_numpy_scalars_round_trip(self, tmp_path) -> None:
        payload = {"n": np.int64(7), "x": np.float64(0.25), "flag": np.bool_(True)}
        p = tmp_path / "scalars.pt"
        torch.save(payload, p)
        _assert_same(payload, safe_torch_load(p))

    def test_map_location_is_honoured(self, tmp_path) -> None:
        p = tmp_path / "t.pt"
        torch.save({"w": torch.randn(2, 2)}, p)
        assert safe_torch_load(p, map_location="cpu")["w"].device.type == "cpu"


class TestRejectsUnsafePayloads:
    def test_arbitrary_reduce_is_rejected(self, tmp_path) -> None:
        class Evil:
            def __reduce__(self):
                return (eval, ("1 + 1",))

        p = tmp_path / "evil.pt"
        torch.save({"ok": torch.zeros(2), "payload": Evil()}, p)
        with pytest.raises(SafeLoadError):
            safe_torch_load(p)

    def test_object_dtype_array_is_rejected(self, tmp_path) -> None:
        """Object arrays are a container for arbitrary pickles; not allowlisted."""
        p = tmp_path / "obj.pt"
        torch.save({"a": np.array([{"x": 1}], dtype=object)}, p)
        with pytest.raises(SafeLoadError):
            safe_torch_load(p)

    def test_error_says_to_regenerate_and_names_the_file(self, tmp_path) -> None:
        p = tmp_path / "bad.pt"
        torch.save({"a": np.array([object()], dtype=object)}, p)
        with pytest.raises(SafeLoadError) as ei:
            safe_torch_load(p)
        msg = str(ei.value)
        assert "bad.pt" in msg
        assert "regenerate" in msg.lower()
        assert "weights_only=False" in msg  # explicitly warns against re-disabling

    def test_missing_file_still_raises(self, tmp_path) -> None:
        with pytest.raises(SafeLoadError):
            safe_torch_load(tmp_path / "nope.pt")


class TestAllowlistScoping:
    def test_allowlist_is_not_leaked_globally(self, tmp_path) -> None:
        """The context manager must not permanently widen the process-wide safe set."""
        p = tmp_path / "targets.pt"
        torch.save(_aoi_cache_payload(), p)
        safe_torch_load(p)
        # A plain weights_only=True load must still reject numpy afterwards.
        with pytest.raises(Exception):
            torch.load(p, weights_only=True)

    def test_both_numpy_module_spellings_are_allowlisted(self) -> None:
        """numpy 1.x pickles say `numpy.core.*`; numpy 2.x say `numpy._core.*`.

        A cache built on a cluster node running numpy 1.x must stay loadable here.
        """
        names = {entry[1] for entry in _numpy_safe_globals() if isinstance(entry, tuple)}
        assert "numpy.core.multiarray._reconstruct" in names
        assert "numpy._core.multiarray._reconstruct" in names
        assert "numpy.core.multiarray.scalar" in names
        assert "numpy._core.multiarray.scalar" in names

    def test_object_dtype_is_not_in_the_allowlist(self) -> None:
        entries = [e for e in _numpy_safe_globals() if not isinstance(e, tuple)]
        assert not any(getattr(e, "__name__", "") == "ObjectDType" for e in entries)
