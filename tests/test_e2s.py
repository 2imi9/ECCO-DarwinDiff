"""Contract tests for the Earth2Studio adapters (src/darwindiff/e2s).

Run off-cluster: earth2studio is import-guarded, so these exercise the fallback
shims exactly like CI. They check the PrognosticModel contract (coord order,
lead_time accumulation, unbounded iterator yielding the IC first), the physics
guards (nonnegativity, land mask), and the log-Chl round-trip.
"""
import numpy as np
import pytest
import torch

from darwindiff.e2s import E2S_AVAILABLE, DarwinBGCPrognostic, EccoDarwinV05


def _zero_residual_model(v):
    """A core model whose residual is zero -> the wrapper is identity in z-space."""
    m = torch.nn.Conv2d(v, v, 1)
    torch.nn.init.zeros_(m.weight)
    torch.nn.init.zeros_(m.bias)
    return m


def _make_model(variables=("DIC_k0", "DIC_k1", "Chl1_k0", "Chl1_k1"), h=8, w=12,
                log_vars=("Chl1", "Chl2", "Chl3", "Chl4", "Chl5")):
    lat = np.linspace(-80.0, 80.0, h)
    lon = np.linspace(0.0, 360.0, w, endpoint=False)
    v = len(variables)
    means = np.zeros(v)
    stds = np.ones(v)
    mask = np.ones((h, w), dtype=bool)  # all-ocean; land-mask checked separately
    # log_vars is passed EXPLICITLY: the wrapper defaults to no transform, because the
    # transform is a property of the checkpoint rather than of the caller. Relying on a
    # non-empty default is what silently corrupts linear-space checkpoints.
    model = DarwinBGCPrognostic(
        _zero_residual_model(v), variables, lat, lon, means, stds,
        ocean_mask=mask, residual=True, log_vars=log_vars,
    )
    return model, lat, lon, v, h, w, mask


def test_input_coords_canonical_order():
    model, *_ = _make_model()
    ic = model.input_coords()
    assert list(ic.keys()) == ["batch", "time", "lead_time", "variable", "lat", "lon"]
    assert ic["batch"].size == 0  # batch is empty + FIRST (required by _compress_batch)
    assert list(ic["variable"]) == ["DIC_k0", "DIC_k1", "Chl1_k0", "Chl1_k1"]


def test_forward_shape_and_lead_time_accumulates():
    model, _lat, _lon, v, h, w, _ = _make_model()
    ic = model.input_coords()
    coords = ic.copy()
    coords["batch"] = np.array([0])
    coords["time"] = np.array([np.datetime64("2016-01-01")])
    x = torch.rand(1, 1, 1, v, h, w) + 0.1  # positive physical units; 6-D per coords
    x_next, oc = model(x, coords)
    assert x_next.shape == (1, 1, 1, v, h, w)   # rank preserved through batch_func
    # lead_time advanced by exactly one dt (from 0)
    assert oc["lead_time"][0] == model.dt
    assert next(iter(oc.keys())) == "batch"


def test_zero_residual_is_identity_and_guards():
    model, _lat, _lon, v, h, w, _mask = _make_model()
    ic = model.input_coords()
    coords = ic.copy()
    coords["batch"] = np.array([0])
    coords["time"] = np.array([np.datetime64("2016-01-01")])
    x = torch.rand(1, 1, 1, v, h, w) + 0.1
    x_next, _ = model(x, coords)
    # non-Chl channels (linear, zero residual) should round-trip to the input
    assert torch.allclose(x_next[..., :2, :, :], x[..., :2, :, :], atol=1e-4)
    # nonnegativity guard: no negatives anywhere
    assert (x_next >= 0).all()


def test_land_mask_zeroed():
    v_vars = ["DIC_k0", "DIC_k1", "Chl1_k0", "Chl1_k1"]
    h, w = 8, 12
    lat = np.linspace(-80.0, 80.0, h)
    lon = np.linspace(0.0, 360.0, w, endpoint=False)
    mask = np.ones((h, w), dtype=bool)
    mask[0, 0] = False  # one land cell
    model = DarwinBGCPrognostic(
        _zero_residual_model(len(v_vars)), v_vars, lat, lon,
        np.zeros(len(v_vars)), np.ones(len(v_vars)), ocean_mask=mask, residual=True,
    )
    ic = model.input_coords()
    coords = ic.copy()
    coords["batch"] = np.array([0])
    coords["time"] = np.array([np.datetime64("2016-01-01")])
    x = torch.rand(1, 1, 1, len(v_vars), h, w) + 0.1
    x_next, _ = model(x, coords)
    assert (x_next[0, 0, 0, :, 0, 0] == 0.0).all()   # land cell zeroed on every channel
    assert (x_next[0, 0, 0, :, 1, 1] > 0).all()      # an ocean cell is not


def test_log_chl_roundtrip():
    # Chl channels go through log->exp; zero residual must still round-trip positives
    model, _lat, _lon, v, h, w, _ = _make_model()
    assert model.log_idx == [2, 3]  # the two Chl1_k* channels
    ic = model.input_coords()
    coords = ic.copy()
    coords["batch"] = np.array([0])
    coords["time"] = np.array([np.datetime64("2016-01-01")])
    x = torch.rand(1, 1, 1, v, h, w) + 0.5
    x_next, _ = model(x, coords)
    assert torch.allclose(x_next[..., 2:, :, :], x[..., 2:, :, :], atol=1e-3, rtol=1e-3)


def test_iterator_yields_ic_first_and_is_unbounded():
    model, _lat, _lon, v, h, w, _ = _make_model()
    ic = model.input_coords()
    coords = ic.copy()
    coords["batch"] = np.array([0])
    coords["time"] = np.array([np.datetime64("2016-01-01")])
    x = torch.rand(1, 1, 1, v, h, w) + 0.1
    it = model.create_iterator(x, coords)
    x0, c0 = next(it)
    assert torch.allclose(x0, x)              # step 0 IS the initial condition
    assert c0["lead_time"][0] == np.timedelta64(0, "h")
    _x1, c1 = next(it)
    assert c1["lead_time"][0] == model.dt     # step 1 advanced one dt
    _x2, c2 = next(it)
    assert c2["lead_time"][0] == 2 * model.dt  # unbounded, keeps accumulating


def test_datasource_roundtrip(tmp_path):
    # build a tiny dumped-cube npz and serve it as an E2S DataSource
    import xarray as xr  # noqa: F401 - skip cleanly if xarray missing
    h, w, m = 6, 9, 3
    chan = np.array(["DIC_k0", "DIC_k1", "Chl1_k0"])
    state = np.random.rand(m, len(chan), h, w).astype(np.float32)
    lats = np.linspace(-80, 80, h)
    lons = np.linspace(0, 360, w, endpoint=False)
    p = tmp_path / "cube.npz"
    # times_days is required for positional access: without a calendar the loader can
    # no longer invent a timestamp for an index, since doing so labelled month 0 as
    # 1970-01-01 and silently misaligned every downstream diagnostic.
    np.savez_compressed(p, state=state, chan_names=chan, lats=lats, lons=lons,
                        times_days=np.array([0.0, 31.0, 61.0]))
    ds = EccoDarwinV05(str(p))
    da = ds(0, ["DIC_k0", "Chl1_k0"])  # positional month 0
    assert da.dims == ("time", "variable", "lat", "lon")
    assert list(da.coords["variable"].values) == ["DIC_k0", "Chl1_k0"]
    assert np.allclose(da.values[0, 0], state[0, 0])
    # the label comes from the cube's own calendar, not from casting the index
    assert da.coords["time"].values[0] == np.datetime64("1992-01-01", "ns")


if __name__ == "__main__":
    # allow a plain `python tests/test_e2s.py` smoke run without pytest
    import pathlib
    import tempfile
    test_input_coords_canonical_order()
    test_forward_shape_and_lead_time_accumulates()
    test_zero_residual_is_identity_and_guards()
    test_land_mask_zeroed()
    test_log_chl_roundtrip()
    test_iterator_yields_ic_first_and_is_unbounded()
    with tempfile.TemporaryDirectory() as d:
        test_datasource_roundtrip(pathlib.Path(d))
    print(f"e2s contract tests PASSED (E2S_AVAILABLE={E2S_AVAILABLE})")


# --------------------------------------------------------------------------------
# Regressions for the review findings on PR #193 (Codex + Greptile, both P1).
# --------------------------------------------------------------------------------
def _tiny_cube(tmp_path, *, with_coords=True, with_times=True):
    import numpy as _np

    p = tmp_path / "cube.npz"
    kw = dict(
        state=_np.ones((4, 2, 3, 5), dtype=_np.float32),
        chan_names=_np.array(["Chl1", "PIC"]),
        valid_mask=_np.ones((3, 5), dtype=bool),
    )
    if with_coords:
        kw["lats"] = _np.linspace(-5, 5, 3)
        kw["lons"] = _np.linspace(-160, -110, 5)
    if with_times:
        kw["times_days"] = _np.array([0.0, 30.0, 60.0, 90.0])
    _np.savez(p, **kw)
    return str(p)


def test_datasource_refuses_to_fabricate_coordinates(tmp_path):
    """A cube without lats/lons must raise, not label an ocean grid 0..H-1.

    Index coordinates survive Earth2Studio regridding and verification silently, so
    the failure would surface as a plausible but geospatially wrong map.
    """
    import pytest as _pytest

    from darwindiff.e2s.datasource import EccoDarwinV05

    with _pytest.raises(KeyError, match="fabricate index coordinates"):
        EccoDarwinV05(_tiny_cube(tmp_path, with_coords=False))


def test_datasource_rejects_datetime_on_a_positional_cube(tmp_path):
    """Without a calendar every datetime used to resolve to month 0 and still be
    labelled with the requested timestamp -- a 40-month rollout reusing one month."""
    import numpy as _np
    import pytest as _pytest

    from darwindiff.e2s.datasource import EccoDarwinV05

    ds = EccoDarwinV05(_tiny_cube(tmp_path, with_times=False))
    assert ds.times is None
    with _pytest.raises(ValueError, match="cannot be resolved to a month"):
        ds._month_index(_np.datetime64("2005-06-01"))
    # positional addressing still works
    assert ds._read_field(2, "Chl1").shape == (3, 5)


def test_datasource_resolves_distinct_months_when_calendar_present(tmp_path):
    import numpy as _np

    from darwindiff.e2s.datasource import EccoDarwinV05

    ds = EccoDarwinV05(_tiny_cube(tmp_path))
    base = _np.datetime64("1992-01-01")
    idx = [ds._month_index(base + _np.timedelta64(d, "D")) for d in (0, 30, 60, 90)]
    assert idx == [0, 1, 2, 3], "each month must resolve to its own index"


def test_prognostic_defaults_to_no_log_transform():
    """A linear-space checkpoint served through a log wrapper is silently corrupted,
    so the default must be no transform; the transform belongs to the checkpoint."""
    import numpy as _np
    import torch as _torch

    from darwindiff.e2s.prognostic import DarwinBGCPrognostic

    m = DarwinBGCPrognostic(
        _torch.nn.Identity(), ["Chl1", "PIC", "POC", "FeT"],
        _np.array([0.0]), _np.array([0.0]),
        means=_np.zeros(4), stds=_np.ones(4),
    )
    assert m.log_idx == [], "default must apply no log transform"


def test_prognostic_from_config_round_trips_the_training_transform():
    import numpy as _np
    import torch as _torch

    from darwindiff.e2s.prognostic import DarwinBGCPrognostic

    args = (_torch.nn.Identity(), ["Chl1", "PIC", "POC", "FeT"],
            _np.array([0.0]), _np.array([0.0]), _np.zeros(4), _np.ones(4))

    off = DarwinBGCPrognostic.from_config(*args, config={"log_transform": False,
                                                        "log_tracers": []})
    assert off.log_idx == []

    on = DarwinBGCPrognostic.from_config(
        *args,
        config={"log_transform": True, "log_tracers": ["Chl1", "PIC"],
                "log_floors": {"Chl1": 1e-6}},
    )
    assert on.log_idx == [0, 1]
    assert float(on.log_floors[0]) == pytest.approx(1e-6)
    # untouched channels keep the legacy floor
    assert float(on.log_floors[2]) == pytest.approx(1e-12)


def test_from_config_syncs_residual_and_dt(monkeypatch):
    """residual and dt are checkpoint properties. A direct-prediction checkpoint served
    with residual=True adds the prediction to the input; a wrong dt mislabels every
    rollout step's valid time and the error accumulates linearly."""
    import numpy as _np
    import torch as _torch

    from darwindiff.e2s.prognostic import DarwinBGCPrognostic

    args = (_torch.nn.Identity(), ["Chl1", "PIC"], _np.array([0.0]), _np.array([0.0]),
            _np.zeros(2), _np.ones(2))

    m = DarwinBGCPrognostic.from_config(
        *args, config={"residual": False, "dt_hours": 168.0, "log_transform": False}
    )
    assert m.residual is False
    assert m.dt == _np.timedelta64(168, "h")

    # an explicit keyword still wins over the config
    m2 = DarwinBGCPrognostic.from_config(
        *args, config={"residual": False, "dt_hours": 168.0}, residual=True
    )
    assert m2.residual is True


def test_positional_index_never_becomes_a_false_timestamp(tmp_path):
    """Casting a positional index to datetime64 labelled month 0 as 1970-01-01."""
    import numpy as _np
    import pytest as _pytest

    _pytest.importorskip("xarray")
    from darwindiff.e2s.datasource import EccoDarwinV05

    p = tmp_path / "c.npz"
    _np.savez(
        p,
        state=_np.ones((3, 1, 2, 2), dtype=_np.float32),
        chan_names=_np.array(["Chl1"]),
        lats=_np.array([0.0, 1.0]),
        lons=_np.array([0.0, 1.0]),
    )
    ds = EccoDarwinV05(str(p))
    assert ds.times is None
    with _pytest.raises(ValueError, match="cannot be given a timestamp"):
        ds(0, "Chl1")


def test_positional_index_uses_the_real_calendar_when_present(tmp_path):
    import numpy as _np
    import pytest as _pytest

    _pytest.importorskip("xarray")
    from darwindiff.e2s.datasource import EccoDarwinV05

    p = tmp_path / "c.npz"
    _np.savez(
        p,
        state=_np.ones((3, 1, 2, 2), dtype=_np.float32),
        chan_names=_np.array(["Chl1"]),
        lats=_np.array([0.0, 1.0]),
        lons=_np.array([0.0, 1.0]),
        times_days=_np.array([0.0, 31.0, 61.0]),
    )
    ds = EccoDarwinV05(str(p))
    da = ds(1, "Chl1")
    assert da.coords["time"].values[0] == _np.datetime64("1992-02-01", "ns")


def test_out_of_range_datetime_is_rejected_not_clamped(tmp_path):
    """argmin silently clamped to the nearest edge month while __call__ kept the
    requested timestamp, so a 2050 request returned the last month labelled 2050."""
    import numpy as _np
    import pytest as _pytest

    from darwindiff.e2s.datasource import EccoDarwinV05

    p = tmp_path / "c.npz"
    _np.savez(
        p,
        state=_np.ones((3, 1, 2, 2), dtype=_np.float32),
        chan_names=_np.array(["Chl1"]),
        lats=_np.array([0.0, 1.0]),
        lons=_np.array([0.0, 1.0]),
        times_days=_np.array([0.0, 31.0, 61.0]),  # 1992-01 .. 1992-03
    )
    ds = EccoDarwinV05(str(p))
    with _pytest.raises(ValueError, match="outside this cube's calendar"):
        ds._month_index(_np.datetime64("2050-01-01"))
    # in-range requests still resolve, including a mid-month one
    assert ds._month_index(_np.datetime64("1992-02-03")) == 1
