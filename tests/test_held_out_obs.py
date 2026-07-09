"""Tests for the DB-3 held-out real-obs E2 harness (darwindiff.held_out_obs).

Hermetic tests (default, no disk) exercise the split / lift / mask-composition / anomaly-R^2
logic, the NaN-sanitization precaution, the grid-alignment guard, Daniels assembly via an
INJECTED cache + points, and a structural-coupling integration test that feeds the returned
tuple straight into ``train_ude_closure`` and asserts it does NOT raise and does NOT poison
the field with NaN.

Opt-in real tests (``DARWINDIFF_TEST_DANIELS=1`` / ``DARWINDIFF_TEST_LLC270=1``) validate the
real eqpac numbers (Daniels 34 cells / geomean ~0.039, n_val>=5) and cross-DB (21,51)
alignment of the calcite target, iron target, and env grid.
"""
from __future__ import annotations

import os

import numpy as np
import pytest
import torch

from darwindiff.carroll6 import CARROLL_VALUES
from darwindiff.closures import EnvCalciteClosure
from darwindiff.daniels_loader import DanielsPoints
from darwindiff.ecco_darwin_loader import AOI, EQUATORIAL_PACIFIC_AOI
from darwindiff.held_out_obs import (
    SurfaceGatedClosure,
    _lift_mask_surface,
    _lift_surface,
    aoi_env_field,
    anomaly_masked_r2,
    env_regime_split,
    held_out_calcite_obs,
    held_out_iron_obs,
    log_dfe_observable,
    log_picpoc_observable,
)
from darwindiff.trainer import TransportConfig, train_ude_closure
from darwindiff.transport import w_from_continuity

F64 = torch.float64

# --- hermetic fixtures: a tiny AOI + matching synthetic cache + Daniels points ---
_AOI = AOI(name="Test", lat_min=0.0, lat_max=4.0, lon_min=0.0, lon_max=5.0)  # (5, 6) grid
_NY, _NX = 5, 6


def _synth_cache(*, sst=25.0, sss=35.0, dic=2000.0, alk=2300.0, nan_at=None) -> dict:
    """A synthetic .pt-style env cache aligned to ``_AOI`` (integer-degree centers)."""
    lats = np.arange(_AOI.lat_min, _AOI.lat_max + 0.5, 1.0)  # [0,1,2,3,4]
    lons = np.arange(_AOI.lon_min, _AOI.lon_max + 0.5, 1.0)  # [0,1,2,3,4,5]
    # SST/Omega vary in Y so the env-regime split has structure to hold out.
    sst_f = np.full((_NY, _NX), sst) + np.arange(_NY)[:, None].astype(float)
    dic_f = np.full((_NY, _NX), dic) - 30.0 * np.arange(_NY)[:, None]  # higher Omega upward
    cache = {
        "darwin_lats": lats, "darwin_lons": lons,
        "sst": sst_f.astype(np.float32),
        "sss": np.full((_NY, _NX), sss, np.float32),
        "dic_binned": dic_f.astype(np.float64),
        "alk_binned": np.full((_NY, _NX), alk, np.float64),
    }
    if nan_at is not None:
        cache["dic_binned"] = cache["dic_binned"].copy()
        cache["dic_binned"][nan_at] = np.nan
    return cache


def _daniels_points_full() -> DanielsPoints:
    """One surface Daniels sample in every AOI cell (CP/PP varies so ratios differ)."""
    lat, lon, cp, pp = [], [], [], []
    for iy in range(_NY):
        for ix in range(_NX):
            lat.append(float(iy)); lon.append(float(ix))
            cp.append(0.02 + 0.01 * ix)   # >0
            pp.append(1.0)
    n = len(lat)
    return DanielsPoints(
        lat=np.array(lat), lon=np.array(lon), depth=np.zeros(n),
        cp=np.array(cp), pp=np.array(pp),
    )


class TestObservables:
    def test_log_picpoc(self) -> None:
        f = torch.zeros(2, 5, dtype=F64)
        f[..., 4] = 2.0  # PIC
        f[..., 3] = 4.0  # POC
        assert torch.allclose(log_picpoc_observable(f), torch.log(torch.tensor(0.5, dtype=F64)))

    def test_log_dfe(self) -> None:
        f = torch.zeros(3, 7, dtype=F64)
        f[..., 0] = 0.01
        assert torch.allclose(log_dfe_observable(f), torch.log(torch.tensor(0.01, dtype=F64)))

    def test_log_floors_are_autograd_clean(self) -> None:
        f = torch.zeros(2, 5, dtype=F64, requires_grad=True)  # PIC=POC=0 -> would be -inf/nan
        log_picpoc_observable(f).sum().backward()
        assert torch.isfinite(f.grad).all()


class TestLift:
    def test_lift_surface_value_at_z0_fill_below(self) -> None:
        f = torch.arange(6, dtype=F64).reshape(2, 3)
        out = _lift_surface(f, 4, fill=-1.0)
        assert out.shape == (2, 3, 4)
        assert torch.equal(out[..., 0], f)
        assert torch.all(out[..., 1:] == -1.0)

    def test_lift_mask_surface_true_only_at_z0(self) -> None:
        m = torch.tensor([[True, False], [False, True]])
        out = _lift_mask_surface(m, 3)
        assert out.shape == (2, 2, 3)
        assert torch.equal(out[..., 0], m)
        assert not out[..., 1:].any()


class TestEnvRegimeSplit:
    def test_upper_quartile_held_out(self) -> None:
        field = torch.arange(20, dtype=F64).reshape(4, 5)  # 0..19
        cov = torch.ones(4, 5, dtype=torch.bool)
        train, val, edge = env_regime_split(field, cov, q=0.25, hold="upper")
        # top 25% -> values >= 75th percentile (14.25) -> {15,16,17,18,19}
        assert int(val.sum()) == 5
        assert bool((field[val] >= edge).all())
        assert bool((field[train] < edge).all())
        assert int((train & val).sum()) == 0
        assert int((train | val).sum()) == int(cov.sum())

    def test_lower_hold_and_coverage_respected(self) -> None:
        field = torch.arange(20, dtype=F64).reshape(4, 5)
        cov = field > 4  # exclude the 5 lowest cells from consideration
        train, val, edge = env_regime_split(field, cov, q=0.5, hold="lower")
        assert not val[~cov].any() and not train[~cov].any()  # never selects uncovered
        assert int((train | val).sum()) == int(cov.sum())

    def test_empty_coverage(self) -> None:
        field = torch.zeros(3, 3, dtype=F64)
        cov = torch.zeros(3, 3, dtype=torch.bool)
        train, val, edge = env_regime_split(field, cov, q=0.25)
        assert int(train.sum()) == 0 and int(val.sum()) == 0
        assert np.isnan(edge)

    def test_constant_field_is_rank_split_not_all_held_out(self) -> None:
        # rank-based split: a CONSTANT split channel must NOT hold out every covered cell
        # (the old `field >= quantile` threshold did -> degenerate empty train).
        field = torch.full((4, 5), 3.14, dtype=F64)
        cov = torch.ones(4, 5, dtype=torch.bool)  # 20 cells
        train, val, edge = env_regime_split(field, cov, q=0.25, hold="upper")
        assert int(val.sum()) == 5  # ceil(0.25*20), not 20
        assert int(train.sum()) == 15
        assert int((train & val).sum()) == 0

    def test_bad_hold_raises(self) -> None:
        with pytest.raises(ValueError):
            env_regime_split(torch.zeros(2, 2), torch.ones(2, 2, dtype=torch.bool), hold="sideways")


class TestAnomalyR2:
    def test_perfect_pred_is_one(self) -> None:
        t = torch.rand(5, 5, dtype=F64)
        m = torch.ones(5, 5, dtype=torch.bool)
        assert float(anomaly_masked_r2(t.clone(), t, m, basin_mean=0.3)) == pytest.approx(1.0)

    def test_predicting_basin_mean_scores_zero(self) -> None:
        t = torch.tensor([1.0, 2.0, 3.0, 4.0], dtype=F64)
        m = torch.ones(4, dtype=torch.bool)
        bm = 10.0  # a constant, far from t; pred == basin mean everywhere
        pred = torch.full_like(t, bm)
        # SS_res == SS_tot (both are sum((t-bm)^2)) -> R2 == 0 exactly
        assert float(anomaly_masked_r2(pred, t, m, basin_mean=bm)) == pytest.approx(0.0)

    def test_scored_against_basin_not_own_mean(self) -> None:
        # anomaly-R2 differs from level-R2: it references the (train) basin mean.
        t = torch.tensor([2.0, 4.0, 6.0], dtype=F64)
        m = torch.ones(3, dtype=torch.bool)
        pred = t.clone()
        # perfect pred -> 1 regardless of basin_mean; use an offset basin_mean to prove
        # SS_tot uses basin_mean, not t.mean()
        r2 = anomaly_masked_r2(pred, t, m, basin_mean=0.0)
        assert float(r2) == pytest.approx(1.0)

    def test_empty_mask_is_nan_not_perfect(self) -> None:
        # an empty held-out mask must score NaN, never a false-perfect 1.0
        t = torch.rand(4, dtype=F64)
        m = torch.zeros(4, dtype=torch.bool)
        assert np.isnan(float(anomaly_masked_r2(t.clone(), t, m, basin_mean=0.3)))


class TestSurfaceGatedClosure:
    def test_baseline_below_surface_learned_at_surface(self) -> None:
        # env [Y,X,Z,1]; a calcite closure with a NON-trivial (nonzero) readout so g != 1.
        ny, nx, nz = 2, 3, 4
        env = torch.randn(ny, nx, nz, 1, dtype=F64)
        clo = EnvCalciteClosure(env, A=1.0).to(F64)
        with torch.no_grad():
            clo.net[-1].weight.fill_(0.7)
            clo.net[-1].bias.fill_(0.3)
        gated = SurfaceGatedClosure(clo)
        state = torch.rand(ny, nx, nz, 5, dtype=F64) * 0.1 + 0.05
        mort = torch.rand(ny, nx, nz, dtype=F64) + 0.1
        out = gated(state, mort)
        base = clo.R0 * mort
        # below surface == baseline (g==1); at surface == the learned closure
        assert torch.allclose(out[..., 1:], base[..., 1:])
        assert torch.allclose(out[..., 0], clo(state, mort)[..., 0])
        # and it actually differs from baseline at the surface (g != 1 there)
        assert not torch.allclose(out[..., 0], base[..., 0])

    def test_null_closure_gating_is_a_noop(self) -> None:
        # a frozen (g==1) closure equals R0*mort everywhere; gating must not change it.
        ny, nx, nz = 2, 3, 4
        env = torch.randn(ny, nx, nz, 2, dtype=F64)
        null = EnvCalciteClosure(env, A=1.0).to(F64)  # zero-init readout -> g==1
        gated = SurfaceGatedClosure(null)
        state = torch.rand(ny, nx, nz, 5, dtype=F64) * 0.1 + 0.05
        mort = torch.rand(ny, nx, nz, dtype=F64) + 0.1
        assert torch.allclose(gated(state, mort), null(state, mort))

    def test_rejects_closure_without_R0(self) -> None:
        with pytest.raises(TypeError):
            SurfaceGatedClosure(torch.nn.Linear(2, 1))


class TestCalciteAssemblyHermetic:
    def test_shapes_masks_and_coverage(self) -> None:
        obs = held_out_calcite_obs(
            _AOI, n_z=4, points=_daniels_points_full(), cache=_synth_cache(),
            interior_ring=1, q=0.25,
        )
        assert obs.target.shape == (_NY, _NX, 4)
        assert obs.env.shape == (_NY, _NX, 4, 2)
        assert obs.hook == "calcite_closure"
        # masks disjoint, union == coverage (at surface), surface-only
        assert int((obs.train_mask & obs.val_mask).sum()) == 0
        surf_union = obs.train_mask[..., 0] | obs.val_mask[..., 0]
        assert torch.equal(surf_union, obs.coverage_mask)
        assert not obs.val_mask[..., 1:].any() and not obs.train_mask[..., 1:].any()
        assert obs.n_train + obs.n_val == int(obs.coverage_mask.sum())
        # interior ring dropped the outer boundary -> coverage strictly inside
        assert not obs.coverage_mask[0, :].any() and not obs.coverage_mask[-1, :].any()
        assert not obs.coverage_mask[:, 0].any() and not obs.coverage_mask[:, -1].any()

    def test_env_is_finite_and_standardized(self) -> None:
        obs = held_out_calcite_obs(_AOI, n_z=4, points=_daniels_points_full(), cache=_synth_cache())
        assert bool(torch.isfinite(obs.env).all())
        assert obs.env_stats["channels"] == ("sst", "omega_c")
        assert obs.env_stats["mean"].shape == (2,) and obs.env_stats["std"].shape == (2,)

    def test_nan_in_cache_is_excluded_not_propagated(self) -> None:
        # a NaN DIC at an interior covered cell must (a) drop that cell from coverage and
        # (b) NOT leave a NaN in env (which the rollout would spread and poison training).
        cache = _synth_cache(nan_at=(2, 2))
        obs = held_out_calcite_obs(_AOI, n_z=4, points=_daniels_points_full(), cache=cache)
        assert not bool(obs.coverage_mask[2, 2])
        assert bool(torch.isfinite(obs.env).all())
        assert bool(torch.isfinite(obs.target).all())

    def test_forcing_coverage_is_anded_in(self) -> None:
        base = held_out_calcite_obs(_AOI, n_z=4, points=_daniels_points_full(), cache=_synth_cache())
        fc = torch.ones(_NY, _NX, dtype=torch.bool)
        # zero out one interior cell that was covered
        covered = base.coverage_mask.clone()
        iy, ix = covered.nonzero()[0].tolist()
        fc[iy, ix] = False
        obs = held_out_calcite_obs(
            _AOI, n_z=4, points=_daniels_points_full(), cache=_synth_cache(),
            forcing_coverage=fc,
        )
        assert not bool(obs.coverage_mask[iy, ix])
        assert int(obs.coverage_mask.sum()) == int(base.coverage_mask.sum()) - 1

    def test_grid_misalignment_raises(self) -> None:
        # a cache one lon short of the AOI -> env grid (5,5) != Daniels (5,6) -> loud fail
        bad = _synth_cache()
        for k in ("sst", "sss", "dic_binned", "alk_binned"):
            bad[k] = bad[k][:, :-1]
        bad["darwin_lons"] = bad["darwin_lons"][:-1]
        with pytest.raises(ValueError, match="grid"):
            held_out_calcite_obs(_AOI, n_z=4, points=_daniels_points_full(), cache=bad)

    def test_half_degree_offset_same_shape_raises(self) -> None:
        # same cell COUNT but integer+0.5 centers -> must fail the VALUE check, not pass
        bad = _synth_cache()
        bad["darwin_lats"] = bad["darwin_lats"] + 0.5
        bad["darwin_lons"] = bad["darwin_lons"] + 0.5
        with pytest.raises(ValueError, match="CENTERS|grid"):
            held_out_calcite_obs(_AOI, n_z=4, points=_daniels_points_full(), cache=bad)

    def test_degenerate_split_raises(self) -> None:
        # only one interior cell has finite env -> coverage=1 -> n_train=0 -> loud raise,
        # never a silently-returned obs that would score a false-perfect held-out R2.
        cache = _synth_cache()
        dic = np.full((_NY, _NX), np.nan)
        dic[2, 3] = 2000.0  # a single interior finite cell
        cache["dic_binned"] = dic
        with pytest.raises(ValueError, match="degenerate"):
            held_out_calcite_obs(_AOI, n_z=4, points=_daniels_points_full(), cache=cache)


class TestIronCounterexampleHermetic:
    def test_iron_obs_assembles_with_scav_hook(self) -> None:
        dfe = np.full((_NY, _NX), 2.0e-4)  # mmol/m^3, all covered
        obs = held_out_iron_obs(_AOI, n_z=4, dfe_grid=dfe, cache=_synth_cache())
        assert obs.hook == "scav_closure"
        assert obs.target.shape == (_NY, _NX, 4)
        assert bool(torch.isfinite(obs.env).all())
        assert obs.n_train > 0 and obs.n_val > 0

    def test_iron_requires_a_source(self) -> None:
        with pytest.raises(ValueError, match="geotraces_path|dfe_grid"):
            held_out_iron_obs(_AOI, n_z=4, cache=_synth_cache())


class TestStructuralCouplingIntegration:
    def test_tuple_drives_trainer_without_raise_or_nan(self) -> None:
        """The returned tuple feeds train_ude_closure end-to-end: the structural-coupling
        guard passes (calcite_closure <-> log-PIC:POC observable), and no NaN poisons the
        field. This is the integration gate the DB-3 handoff requires."""
        obs = held_out_calcite_obs(_AOI, n_z=4, points=_daniels_points_full(), cache=_synth_cache())
        ny, nx, nz = _NY, _NX, 4
        clo = EnvCalciteClosure(obs.env, A=1.0).to(F64)
        params = torch.tensor([CARROLL_VALUES[i] for i in range(6)], dtype=F64)
        torch.manual_seed(0)
        ic = torch.rand(ny, nx, nz, 5, dtype=F64) * 0.1 + 0.05
        dx = dy = 1e5
        dz = 10.0
        u = 0.1 * torch.ones(ny, nx, dtype=F64)
        v = 0.02 * torch.ones(ny, nx, dtype=F64)
        w = w_from_continuity(u, v, dx, dy, dz, nz)
        tc = TransportConfig(dx=dx, dy=dy, dz=dz, dt=0.25, kz=50.0, kh=50.0, u=u, v=v, w=w)
        res = train_ude_closure(
            clo, ic, params, tc, n_steps=6, observable=obs.observable,
            target=obs.target, train_mask=obs.train_mask, val_mask=obs.val_mask,
            hook=obs.hook, epochs=2, lr=5e-2, checkpoint_segment=3, log_every=2,
        )
        assert bool(torch.isfinite(res.final_field).all())
        assert not any(h.get("aborted") for h in res.history)


# --- opt-in real-data tests ---------------------------------------------------
_DANIELS = os.environ.get("DARWINDIFF_TEST_DANIELS") == "1"
_LLC270 = os.environ.get("DARWINDIFF_TEST_LLC270") == "1"


@pytest.mark.skipif(not _DANIELS, reason="set DARWINDIFF_TEST_DANIELS=1 (needs D: caches + Daniels)")
class TestRealDaniels:
    def test_daniels_eqpac_raw_numbers(self) -> None:
        from darwindiff.daniels_loader import build_aoi_climatology
        v, m, _c = build_aoi_climatology(EQUATORIAL_PACIFIC_AOI)
        assert v.shape == (21, 51)
        assert int(m.sum()) == 34
        assert float(np.exp(np.log(v[m]).mean())) == pytest.approx(0.0392, abs=5e-4)

    def test_held_out_calcite_eqpac(self) -> None:
        obs = held_out_calcite_obs(EQUATORIAL_PACIFIC_AOI, n_z=6, q=0.25)
        assert obs.target.shape == (21, 51, 6)
        assert obs.env.shape == (21, 51, 6, 2)
        assert obs.n_val >= 5  # else the E2 split is under-powered; pool eqpac+natl
        assert int(obs.coverage_mask.sum()) == obs.n_train + obs.n_val
        assert bool(torch.isfinite(obs.env).all())
        # env-regime hold-out really holds the HIGH Omega band
        assert np.isfinite(obs.band_edge)


@pytest.mark.skipif(not _LLC270, reason="set DARWINDIFF_TEST_LLC270=1 (needs D: GEOTRACES nc)")
class TestRealIronCrossDB:
    _GEOTRACES = r"D:\geotraces\GEOTRACES_IDP2025_Seawater.nc"

    def test_dfe_grid_is_shared_grid_shape(self) -> None:
        from darwindiff.geotraces_loader import dfe_aoi_1deg_grid
        g = dfe_aoi_1deg_grid(self._GEOTRACES, EQUATORIAL_PACIFIC_AOI)
        assert g.shape == (21, 51)  # NOT the (20,50) of the packaged bin_to_grid

    def test_cross_db_alignment(self) -> None:
        # calcite target grid, iron target grid, and env grid must be the same cells
        from darwindiff.daniels_loader import build_aoi_climatology
        from darwindiff.geotraces_loader import dfe_aoi_1deg_grid
        cal, _m, _c = build_aoi_climatology(EQUATORIAL_PACIFIC_AOI)
        iron = dfe_aoi_1deg_grid(self._GEOTRACES, EQUATORIAL_PACIFIC_AOI)
        env = aoi_env_field(EQUATORIAL_PACIFIC_AOI)
        assert cal.shape == iron.shape == (int(env["lats"].shape[0]), int(env["lons"].shape[0]))
