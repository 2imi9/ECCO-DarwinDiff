"""Tests for the ``--load-model`` path in scripts/emulator_poc.py.

``save_checkpoint`` existed for a year with no reader, so the only way to re-score a
trained emulator was to retrain it. These tests pin the inverse: weights survive the
safetensors complex-packing round trip bitwise, and the standardization guard fires
when a run fails to reconstruct the z-space the model was trained in.

That guard is the science-critical half. Scoring a model against a z-space it was not
trained in produces numbers that look fine and mean nothing, so a mismatch must abort
rather than warn. CPU-only, tiny synthetic model; no data files, no GPU.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
import emulator_poc as ep  # noqa: E402

CHANS = ["Chl1_k0", "Chl2_k0"]


def _tiny_model():
    """A 2-channel forcing-free FNO2d on a small grid: real weights + complex spectral."""
    op = ep.FNO2d(in_ch=2, out_ch=2, modes1=4, modes2=4, width=8, n_layers=2)
    model = ep.DarwinEmulator(
        variables=CHANS,
        grid_shape=(12, 16),
        modes=4,
        width=8,
        n_layers=2,
        dt_hours=24.0,
        lats=np.linspace(0.0, 1.0, 12),
        lons=np.linspace(0.0, 1.0, 16),
        operator=op,
    )
    return ep._cast_model(model, torch.float32)


def _save(tmp_path, model, means, stds, name="ck.safetensors"):
    return ep.save_checkpoint(
        tmp_path / name, model, {"channel_names": CHANS, "modes": 4, "width": 8, "layers": 2},
        means, stds,
    )


def test_roundtrip_restores_every_weight_bitwise(tmp_path):
    src = _tiny_model()
    means = np.array([1.5, -0.25]); stds = np.array([2.0, 0.5])
    path = _save(tmp_path, src, means, stds)

    dst = _tiny_model()
    # perturb the destination so a no-op load would be caught
    with torch.no_grad():
        for p in dst.parameters():
            p.add_(torch.ones_like(p))

    ep.load_checkpoint(path, dst, means, stds, CHANS)

    s_sd, d_sd = src.state_dict(), dst.state_dict()
    assert set(s_sd) == set(d_sd)
    for k in s_sd:
        assert torch.equal(s_sd[k].cpu(), d_sd[k].cpu()), f"{k} did not round-trip bitwise"


def test_complex_spectral_weights_survive_the_real_view_packing(tmp_path):
    """safetensors has no complex dtype; w1/w2 are stored as a real view and rebuilt."""
    src = _tiny_model()
    means, stds = np.zeros(2), np.ones(2)
    path = _save(tmp_path, src, means, stds)

    sd, _, _, _ = ep.read_checkpoint(path)
    complex_keys = [k for k, v in src.state_dict().items() if v.is_complex()]
    assert complex_keys, "fixture must exercise the complex path"
    for k in complex_keys:
        assert sd[k].is_complex(), f"{k} came back real; view_as_complex was not applied"
        assert torch.equal(sd[k], src.state_dict()[k].cpu())


def test_stats_are_restored_alongside_the_weights(tmp_path):
    means = np.array([3.25, -7.5]); stds = np.array([1.25, 4.0])
    path = _save(tmp_path, _tiny_model(), means, stds)
    _, ck_means, ck_stds, cfg = ep.read_checkpoint(path)
    assert np.allclose(ck_means, means)
    assert np.allclose(ck_stds, stds)
    assert cfg["channel_names"] == CHANS


@pytest.mark.parametrize(
    "bad_means, bad_stds",
    [
        (np.array([1.5, -0.25 + 0.1]), np.array([2.0, 0.5])),  # mean drifted 0.2 sigma
        (np.array([1.5, -0.25]), np.array([2.0, 0.6])),        # std drifted 20%
    ],
)
def test_a_run_that_does_not_reproduce_the_standardization_aborts(tmp_path, bad_means, bad_stds):
    """The whole point of the guard: wrong z-space must stop the run, not warn."""
    means = np.array([1.5, -0.25]); stds = np.array([2.0, 0.5])
    path = _save(tmp_path, _tiny_model(), means, stds)
    with pytest.raises(SystemExit, match="does not reproduce the checkpoint's standardization"):
        ep.load_checkpoint(path, _tiny_model(), bad_means, bad_stds, CHANS)


def test_matching_standardization_passes(tmp_path):
    means = np.array([1.5, -0.25]); stds = np.array([2.0, 0.5])
    path = _save(tmp_path, _tiny_model(), means, stds)
    # a deviation well inside tolerance must NOT abort (float round-trip is not bitwise)
    ep.load_checkpoint(path, _tiny_model(), means + 1e-9, stds, CHANS)


def test_channel_mismatch_aborts(tmp_path):
    means, stds = np.zeros(2), np.ones(2)
    path = _save(tmp_path, _tiny_model(), means, stds)
    with pytest.raises(SystemExit, match="channel mismatch"):
        ep.load_checkpoint(path, _tiny_model(), means, stds, ["surfChl1", "surfChl2"])


def test_architecture_mismatch_aborts(tmp_path):
    """Loading a width-8 checkpoint into a width-16 model must not silently partially load."""
    means, stds = np.zeros(2), np.ones(2)
    path = _save(tmp_path, _tiny_model(), means, stds)
    op = ep.FNO2d(in_ch=2, out_ch=2, modes1=4, modes2=4, width=16, n_layers=2)
    wide = ep._cast_model(
        ep.DarwinEmulator(
            variables=CHANS, grid_shape=(12, 16), modes=4, width=16, n_layers=2,
            dt_hours=24.0, lats=np.linspace(0, 1, 12), lons=np.linspace(0, 1, 16), operator=op,
        ),
        torch.float32,
    )
    with pytest.raises(SystemExit, match="state_dict does not match|size mismatch"):
        ep.load_checkpoint(path, wide, means, stds, CHANS)


def test_missing_checkpoint_aborts(tmp_path):
    with pytest.raises(SystemExit, match="no such checkpoint"):
        ep.read_checkpoint(tmp_path / "nope.safetensors")


def test_torch_pt_fallback_round_trips(tmp_path):
    """The .pt branch must carry the same payload as the safetensors branch."""
    src = _tiny_model()
    means = np.array([0.5, 2.5]); stds = np.array([1.5, 3.5])
    path = _save(tmp_path, src, means, stds, name="ck.pt")
    sd, ck_means, ck_stds, cfg = ep.read_checkpoint(path)
    assert np.allclose(ck_means, means) and np.allclose(ck_stds, stds)
    assert cfg["channel_names"] == CHANS
    for k, v in src.state_dict().items():
        assert torch.equal(sd[k].cpu(), v.cpu())
