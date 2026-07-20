"""Diffusion-corrector emulator for ECCO-Darwin v05 next-month state (Track-2).

Faithful adaptation of the NVIDIA CorrDiff / StormCast recipe to the ocean-BGC cube:
a deterministic **regression backbone** (our FNO) predicts the next-state mean, and an
**EDM diffusion model** (Karras et al. 2022) generates the *residual* the regression blurs,
conditioned on the current state + the regression mean. Sampling many residuals gives an
**ensemble** of next-state fields — the two things the deterministic FNO cannot do:
sharp fine-scale structure and calibrated uncertainty.

Honest scope: the deterministic skill-over-persistence ceiling (+0.52) is intrinsic to v05's
next-month predictability, so the diffusion ENSEMBLE MEAN is expected to ~match (not beat) the
FNO on RMSE. The win is spectral realism (power spectrum near truth, not blurred) + ensemble
spread. All numbers are self-consistency vs the v05 MODEL, not real observations.

Recipe refs: NVIDIA/physicsnemo examples/weather/corrdiff (regression + residual EDM diffusion),
Earth2Studio StormCast (regression + diffusion corrector, EDM Heun sampler). EDM math: Karras 2022.

Memory: data stays on CPU; only minibatches move to GPU (the full 60-ch cube is ~100+ GB stacked).

Run (CPU smoke):   uv run python scripts/diffusion_emulator.py --smoke
Run (B200 surface):python scripts/diffusion_emulator.py --cube global3d_L10_cube.npz --surface-only \
                       --regression-epochs 150 --diffusion-epochs 300 --out diff_surf.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

_SRC = Path(__file__).resolve().parent.parent / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
from darwindiff.emulator import FNO2d, SpectralConv2d  # noqa: E402


# ------------------------------------------------------------------ data ----
def load_cube(path: str):
    """Return (state [T,C,H,W] float32, ocean_mask [H,W] bool, chan_names)."""
    z = np.load(path, allow_pickle=True)
    state = z["state"]
    names = [str(s) for s in z["chan_names"]]
    if state.ndim != 4:
        raise ValueError(f"expected 4-D state, got {state.shape}")
    if state.shape[1] != len(names) and state.shape[-1] == len(names):
        state = np.moveaxis(state, -1, 1)
    mask = z["valid_mask"].astype(bool)
    return np.ascontiguousarray(state, dtype=np.float32), mask, names


def zscore(state, mask):
    """Per-channel z-score over ocean cells. Returns (z, mean, std)."""
    m = mask[None, None]
    x = np.where(m, state, np.nan)
    mean = np.nanmean(x, axis=(0, 2, 3), keepdims=True)
    std = np.nanmean((x - mean) ** 2, axis=(0, 2, 3), keepdims=True) ** 0.5
    std = np.clip(std, 1e-6, None)
    z = np.where(m, (state - mean) / std, 0.0).astype(np.float32)
    return z, mean.squeeze().astype(np.float32), std.squeeze().astype(np.float32)


def time_split(T, val_frac=0.3):
    """Return (train_t, val_t) starting indices; pair (t, t+1). Last val_frac held out."""
    n_val_t = max(2, int(round(T * val_frac)))
    split = T - n_val_t
    tr = list(range(split - 1))
    va = list(range(split, T - 1))
    return tr, va


def _batch(Z, bt, device):
    xt = Z[bt].to(device, non_blocking=True)
    yt = Z[bt + 1].to(device, non_blocking=True)
    return xt, yt


# ---------------------------------------------------- EDM diffusion core ----
class SigmaFiLMFNO(nn.Module):
    """FNO denoiser with sigma-FiLM conditioning (the EDM F_theta).

    Input : preconditioned noisy residual (c_out) + conditioning (cond_ch) channels.
    Output: raw denoiser prediction (c_out). Sigma enters via FiLM (scale/shift per block),
    from Fourier features of log-sigma.
    """

    def __init__(self, c_out, cond_ch, modes=16, width=64, n_layers=4, emb=128):
        super().__init__()
        self.lift = nn.Conv2d(c_out + cond_ch, width, 1)
        self.spectral = nn.ModuleList(
            [SpectralConv2d(width, width, modes, modes) for _ in range(n_layers)]
        )
        self.local = nn.ModuleList([nn.Conv2d(width, width, 1) for _ in range(n_layers)])
        self.film = nn.ModuleList([nn.Linear(emb, 2 * width) for _ in range(n_layers)])
        self.emb_dim = emb
        self.sig_mlp = nn.Sequential(nn.Linear(emb, emb), nn.SiLU(), nn.Linear(emb, emb))
        self.proj1 = nn.Conv2d(width, 2 * width, 1)
        self.proj2 = nn.Conv2d(2 * width, c_out, 1)

    def _sig_emb(self, c_noise):
        half = self.emb_dim // 2
        freqs = torch.exp(torch.linspace(0, math.log(1000.0), half, device=c_noise.device))
        a = c_noise[:, None] * freqs[None, :]
        return self.sig_mlp(torch.cat([torch.sin(a), torch.cos(a)], dim=1))

    def forward(self, x_in, c_noise):
        e = self._sig_emb(c_noise)
        x = self.lift(x_in)
        for sp, lo, fl in zip(self.spectral, self.local, self.film, strict=False):
            scale, shift = fl(e).chunk(2, dim=1)
            h = sp(x) + lo(x)
            h = h * (1 + scale[:, :, None, None]) + shift[:, :, None, None]
            x = nn.functional.gelu(h)
        return self.proj2(nn.functional.gelu(self.proj1(x)))


class EDMCorrector(nn.Module):
    """EDM preconditioning wrapper (Karras 2022) around the FiLM-FNO denoiser."""

    def __init__(self, c_out, cond_ch, sigma_data=0.5, **kw):
        super().__init__()
        self.net = SigmaFiLMFNO(c_out, cond_ch, **kw)
        self.sigma_data = sigma_data

    def denoise(self, y_noisy, sigma, cond):
        s = sigma.view(-1, 1, 1, 1)
        c_skip = self.sigma_data**2 / (s**2 + self.sigma_data**2)
        c_out = s * self.sigma_data / (s**2 + self.sigma_data**2).sqrt()
        c_in = 1.0 / (s**2 + self.sigma_data**2).sqrt()
        c_noise = sigma.log() / 4.0
        f = self.net(torch.cat([c_in * y_noisy, cond], dim=1), c_noise)
        return c_skip * y_noisy + c_out * f


def edm_loss(model, residual, cond, mask, P_mean=-1.2, P_std=1.2):
    """EDM denoising loss: E[ lambda(sigma) * ||D(y+n)-y||^2 ] over ocean cells."""
    b = residual.shape[0]
    sigma = (P_mean + P_std * torch.randn(b, device=residual.device)).exp()
    n = torch.randn_like(residual) * sigma.view(-1, 1, 1, 1)
    d = model.denoise(residual + n, sigma, cond)
    weight = (sigma**2 + model.sigma_data**2) / (sigma * model.sigma_data) ** 2
    se = ((d - residual) ** 2) * mask
    per = se.mean(dim=(1, 2, 3)) / mask.mean().clamp_min(1e-6)
    return (weight * per).mean()


@torch.no_grad()
def edm_sample(model, cond, shape, device, steps=18, sigma_min=0.002, sigma_max=80.0, rho=7.0):
    """Heun (2nd-order) EDM sampler -> one residual sample per cond row."""
    i = torch.arange(steps, device=device)
    t = (sigma_max ** (1 / rho) + i / (steps - 1) * (sigma_min ** (1 / rho) - sigma_max ** (1 / rho))) ** rho
    t = torch.cat([t, t.new_zeros(1)])
    x = torch.randn(shape, device=device) * t[0]
    for j in range(steps):
        s = t[j].expand(shape[0])
        d = (x - model.denoise(x, s, cond)) / t[j]
        x_next = x + (t[j + 1] - t[j]) * d
        if t[j + 1] > 0:
            s2 = t[j + 1].expand(shape[0])
            d2 = (x_next - model.denoise(x_next, s2, cond)) / t[j + 1]
            x_next = x + (t[j + 1] - t[j]) * 0.5 * (d + d2)
        x = x_next
    return x


# ------------------------------------------------ training-history probes ---
@torch.no_grad()
def _val_mse(fno, Z, va_t, mask_t, device, bs=8, max_batches=6):
    """Held-out regression MSE — cheap generalization probe for the history trace."""
    va = torch.tensor(va_t); tot = 0.0; n = 0
    for k in range(0, min(len(va), bs * max_batches), bs):
        bt = va[k : k + bs]
        xt, yt = _batch(Z, bt, device)
        mu = xt + fno(xt)
        tot += float((((mu - yt) ** 2) * mask_t).mean()) * len(bt); n += len(bt)
    return tot / max(n, 1)


@torch.no_grad()
def _val_edm(model, fno, Z, va_t, mask_t, device, bs=8, max_batches=4):
    """Held-out EDM loss. Sigma draws are seeded so the value is comparable across
    epochs; the train-vs-val gap is the overfitting signature behind under-dispersion."""
    cpu_state = torch.get_rng_state()
    cuda_state = torch.cuda.get_rng_state_all() if device == "cuda" else None
    torch.manual_seed(12345)
    va = torch.tensor(va_t); tot = 0.0; n = 0
    for k in range(0, min(len(va), bs * max_batches), bs):
        bt = va[k : k + bs]
        xt, yt = _batch(Z, bt, device)
        mu = xt + fno(xt)
        tot += float(edm_loss(model, yt - mu, torch.cat([xt, mu], dim=1), mask_t)) * len(bt); n += len(bt)
    torch.set_rng_state(cpu_state)
    if cuda_state is not None:
        torch.cuda.set_rng_state_all(cuda_state)
    return tot / max(n, 1)


@torch.no_grad()
def _light_eval(model, fno, Z, va_t, C, mask_t, device, n_ens=8, steps=16, bs=4, max_batches=2):
    """Cheap ensemble probe for the QUALITY LADDER: measured skill + calibration at a
    given training epoch. Deliberately small (few members/steps/batches) so it can run
    periodically during training; the final evaluate() is the authoritative number."""
    va = torch.tensor(va_t)[: bs * max_batches]
    ncell = mask_t.sum().item()
    sp = reg = diff = spread = 0.0
    n = 0
    for k in range(0, len(va), bs):
        bt = va[k : k + bs]
        xt, yt = _batch(Z, bt, device)
        mu = xt + fno(xt)
        cond = torch.cat([xt, mu], dim=1)
        ens = torch.stack([
            mu + edm_sample(model, cond, (len(bt), C, xt.shape[2], xt.shape[3]), device, steps=steps)
            for _ in range(n_ens)
        ])
        em = ens.mean(0)
        sp += float((((xt - yt) ** 2) * mask_t).sum())
        reg += float((((mu - yt) ** 2) * mask_t).sum())
        diff += float((((em - yt) ** 2) * mask_t).sum())
        spread += float((ens.std(0) * mask_t).sum())
        n += len(bt)
    den = max(n * C * ncell, 1e-9)
    pm, rm, dm, spd = sp / den, reg / den, diff / den, spread / den
    res = math.sqrt(max(rm, 1e-12))
    return {"reg_skill": 1 - rm / max(pm, 1e-12), "ens_skill": 1 - dm / max(pm, 1e-12),
            "spread": spd, "residual_std": res, "calib_ratio": spd / max(res, 1e-12)}


# ---------------------------------------------------------- regression ------
def train_regression(Z, tr_t, C, mask_t, device, epochs, modes, width, bs, lr=1e-3, log_every=25,
                     va_t=None, history_every=10, rollout_k=1, dt_months=None):
    """FNO predicting next-state as persistence + correction (matches emulator_poc --residual).

    rollout_k>1 = ROLLOUT-AWARE training: unroll k autoregressive steps and average the per-step loss,
    so the model learns to stay stable under its OWN errors (the standard fix for rollout drift). Start
    indices are restricted so all k targets stay inside the training split (no leakage).
    """
    fno = FNO2d(C, C, modes1=modes, modes2=modes, width=width).to(device)
    opt = torch.optim.Adam(fno.parameters(), lr=lr)
    T_total = Z.shape[0]
    split = max(tr_t) + 2 if tr_t else T_total          # first val index (train pairs use t<split-1)
    starts = [t for t in tr_t if t + rollout_k < split] if rollout_k > 1 else list(tr_t)
    starts = torch.tensor(starts)
    print(f"    [reg] rollout_k={rollout_k}  usable start points={len(starts)}", flush=True)
    hist = []
    for ep in range(epochs):
        perm = starts[torch.randperm(len(starts))]
        tot = 0.0
        for k in range(0, len(perm), bs):
            bt = perm[k : k + bs]
            # dt_months is not None => DT-SCALED RESIDUAL. The network predicts a
            # PER-MONTH tendency and the applied step is tendency * dt. Without this the
            # cube's non-uniform spacing (median 61 d, range 30-212) makes the model learn
            # the AVERAGE transition, so it overshoots on a true one-month step: measured
            # +0.0026 skill on genuinely-monthly val pairs versus +0.4756 for a model
            # trained only on them. Scaling by dt lets the long-gap pairs teach the monthly
            # rate instead of drowning it out.
            # Caveat: assumes the tendency is ~constant over the gap. That is a decent
            # approximation at 1-2 months and a poor one at 7; it is still far better than
            # treating every gap as identical, which is the current behaviour.
            if rollout_k > 1:
                x = Z[bt].to(device)
                loss = 0.0
                for j in range(1, rollout_k + 1):
                    if dt_months is None:
                        x = x + fno(x)                  # autoregressive; grad flows through all k steps
                    else:
                        s = dt_months[bt + j - 1].to(device).view(-1, 1, 1, 1)
                        x = x + fno(x) * s
                    y = Z[bt + j].to(device)
                    loss = loss + (((x - y) ** 2) * mask_t).mean()
                loss = loss / rollout_k
            else:
                xt, yt = _batch(Z, bt, device)
                if dt_months is None:
                    mu = xt + fno(xt)
                else:
                    s = dt_months[bt].to(device).view(-1, 1, 1, 1)
                    mu = xt + fno(xt) * s
                loss = (((mu - yt) ** 2) * mask_t).mean()
            opt.zero_grad(); loss.backward(); opt.step()
            tot += loss.item() * len(bt)
        rec = {"epoch": ep, "train_mse_z": tot / len(perm)}
        if va_t is not None and history_every and (ep % history_every == 0 or ep == epochs - 1):
            rec["val_mse_z"] = _val_mse(fno, Z, va_t, mask_t, device)
        hist.append(rec)
        if log_every and (ep % log_every == 0 or ep == epochs - 1):
            v = f"  val={rec['val_mse_z']:.4f}" if "val_mse_z" in rec else ""
            print(f"    [reg] epoch {ep:3d}  masked-mse(z)={rec['train_mse_z']:.4f}{v}", flush=True)
    return fno.eval(), hist


# --------------------------------------------------------------- eval -------
def radial_spectrum(field, mask):
    """Radially-averaged 2-D power spectrum of a masked field [H,W] -> 1-D array."""
    f = np.where(mask, field, 0.0)
    F = np.fft.fftshift(np.fft.fft2(f))
    P = np.abs(F) ** 2
    H, W = f.shape
    cy, cx = H // 2, W // 2
    y, x = np.indices((H, W))
    r = np.sqrt((y - cy) ** 2 + (x - cx) ** 2).astype(int)
    tbin = np.bincount(r.ravel(), P.ravel())
    nr = np.bincount(r.ravel())
    return tbin / np.clip(nr, 1, None)


def evaluate(fno, model, Z, va_t, C, mask_t, mask_np, device, n_ens=8, steps=18, bs=2):
    """Batched: regression skill vs persistence; diffusion ensemble-mean skill + spread + spectrum."""
    va_t = torch.tensor(va_t)
    ncell = mask_t.sum().item()
    sp = reg = diff = spread = 0.0
    n = 0
    spec = None
    for k in range(0, len(va_t), bs):
        bt = va_t[k : k + bs]
        xt, yt = _batch(Z, bt, device)
        with torch.no_grad():
            mu = xt + fno(xt)
            cond = torch.cat([xt, mu], dim=1)
            ens = torch.stack([
                mu + edm_sample(model, cond, (len(bt), C, xt.shape[2], xt.shape[3]), device, steps=steps)
                for _ in range(n_ens)
            ])
            ens_mean = ens.mean(0)
        sp += (((xt - yt) ** 2) * mask_t).sum().item()
        reg += (((mu - yt) ** 2) * mask_t).sum().item()
        diff += (((ens_mean - yt) ** 2) * mask_t).sum().item()
        spread += ((ens.std(0)) * mask_t).sum().item()
        n += len(bt)
        if spec is None:
            spec = {
                "truth": radial_spectrum(yt[0, 0].cpu().numpy(), mask_np).tolist(),
                "regression": radial_spectrum(mu[0, 0].cpu().numpy(), mask_np).tolist(),
                "diffusion": radial_spectrum(ens[0, 0, 0].cpu().numpy(), mask_np).tolist(),
            }
    denom = max(n * C * ncell, 1e-9)
    persist_mse, reg_mse, diff_mse = sp / denom, reg / denom, diff / denom
    st = np.array(spec["truth"]); sr = np.array(spec["regression"]); sd = np.array(spec["diffusion"])
    hi = slice(len(st) // 2, None)
    skill = lambda mse: 1.0 - mse / max(persist_mse, 1e-12)
    metrics = {
        "persistence_mse": persist_mse,
        "regression_skill": skill(reg_mse),
        "diffusion_ensmean_skill": skill(diff_mse),
        "ensemble_spread_z": spread / denom,
        "hf_power_ratio_regression": float(np.sum(sr[hi]) / max(np.sum(st[hi]), 1e-12)),
        "hf_power_ratio_diffusion": float(np.sum(sd[hi]) / max(np.sum(st[hi]), 1e-12)),
    }
    return metrics, spec


def train_diffusion(fno, Z, tr_t, C, mask_t, device, epochs, modes, width, bs, lr=1e-3,
                    sigma_data=0.5, clip=1.0, ema_decay=0.999, log_every=25,
                    ckpt_path=None, ckpt_every=0, ckpt_meta=None,
                    va_t=None, history_every=10, eval_every=0):
    cond_ch = 2 * C
    model = EDMCorrector(C, cond_ch, sigma_data=sigma_data, modes=modes, width=width).to(device)
    # NB: no fused=True — the FNO spectral weights are complex64, unsupported by fused Adam.
    opt = torch.optim.Adam(model.parameters(), lr=lr, betas=(0.9, 0.999))
    ema = {k: v.detach().clone() for k, v in model.state_dict().items()}  # EMA weights for sampling
    tr_t = torch.tensor(tr_t)
    last = 0.0
    hist = []
    for ep in range(epochs):
        perm = tr_t[torch.randperm(len(tr_t))]
        tot = 0.0
        for k in range(0, len(perm), bs):
            bt = perm[k : k + bs]
            xt, yt = _batch(Z, bt, device)
            with torch.no_grad():
                mu = xt + fno(xt)
            r = yt - mu
            cond = torch.cat([xt, mu], dim=1)
            loss = edm_loss(model, r, cond, mask_t)
            opt.zero_grad(); loss.backward()
            if clip:
                nn.utils.clip_grad_norm_(model.parameters(), clip)
            opt.step()
            with torch.no_grad():
                for kk, v in model.state_dict().items():
                    if v.is_floating_point() or v.is_complex():
                        ema[kk].mul_(ema_decay).add_(v.detach(), alpha=1 - ema_decay)
                    else:
                        ema[kk].copy_(v)
            tot += loss.item() * len(bt)
        last = tot / len(perm)
        rec = {"epoch": ep, "train_edm": last}
        is_probe = va_t is not None and history_every and (ep % history_every == 0 or ep == epochs - 1)
        is_ladder = va_t is not None and eval_every and (ep % eval_every == 0 or ep == epochs - 1)
        if is_probe or is_ladder:
            # EMA weights are what we sample from, so probe generalization on those
            live = {k: v.detach().clone() for k, v in model.state_dict().items()}
            model.load_state_dict(ema)
            if is_probe:
                rec["val_edm"] = _val_edm(model, fno, Z, va_t, mask_t, device)
                rec["val_train_gap"] = rec["val_edm"] - last  # >0 and growing => overfitting
            if is_ladder:
                # QUALITY LADDER: measured skill + calibration at this epoch
                rec["quality"] = _light_eval(model, fno, Z, va_t, C, mask_t, device)
            model.load_state_dict(live)
        hist.append(rec)
        if log_every and (ep % log_every == 0 or ep == epochs - 1):
            v = f"  val={rec['val_edm']:.4f} gap={rec['val_train_gap']:+.4f}" if "val_edm" in rec else ""
            q = (f"  [ladder] reg={rec['quality']['reg_skill']:+.3f} ens={rec['quality']['ens_skill']:+.3f} "
                 f"calib={rec['quality']['calib_ratio']:.3f}") if "quality" in rec else ""
            print(f"    [diff] epoch {ep:3d}  edm-loss={last:.4f}{v}{q}", flush=True)
        if ckpt_path and ckpt_every and (ep % ckpt_every == 0 or ep == epochs - 1):
            # distinct per-epoch checkpoints => a retained quality ladder, not one overwrite
            stem = Path(ckpt_path)
            rung = str(stem.with_name(f"{stem.stem}_ep{ep+1:05d}{stem.suffix}"))
            torch.save({"regression": fno.state_dict(), "diffusion": ema, "epoch": ep + 1,
                        "loss": last, "history": hist, "quality": rec.get("quality"),
                        **(ckpt_meta or {})}, rung)
            torch.save({"regression": fno.state_dict(), "diffusion": ema, "epoch": ep + 1,
                        "loss": last, "history": hist, **(ckpt_meta or {})}, ckpt_path)  # rolling latest
            print(f"    [ckpt] rung -> {rung}", flush=True)
    model.load_state_dict(ema)  # sample from the EMA weights (standard for EDM)
    return model.eval(), last, hist


# --------------------------------------------------------------- main -------
def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cube", default=None)
    p.add_argument("--surface-only", action="store_true", help="keep only *_k0 channels (surface)")
    p.add_argument("--log-transform", action="store_true",
                   help="log-transform tracers before z-scoring. REQUIRED for global chlorophyll: "
                        "Chl is log-normal (measured global range p99/p1 ~2.8e6x, skew +4.86 linear vs "
                        "-2.31 log). A linear z-score is set by a few bloom cells and collapses the "
                        "oligotrophic ocean to ~0, which made global reg_skill NEGATIVE (-0.097) while "
                        "single-regime eqpac worked (+0.30). Skill is then measured in LOG space — the "
                        "natural space for Chl.")
    p.add_argument("--log-floor", type=float, default=1e-4,
                   help="clip floor before log (mg/m^3). 1e-4 is below any meaningful Chl; prevents "
                        "log(~1e-11)=-25 outliers from 'PFT absent' cells dominating the z-score.")
    p.add_argument("--channels", default=None, help="explicit comma-sep channel indices to keep")
    p.add_argument("--regression-epochs", type=int, default=150)
    p.add_argument("--diffusion-epochs", type=int, default=300)
    p.add_argument("--modes", type=int, default=16)
    p.add_argument("--width", type=int, default=64)
    p.add_argument("--reg-width", type=int, default=48)
    p.add_argument("--batch-size", type=int, default=2)
    p.add_argument("--eval-batch", type=int, default=2)
    p.add_argument("--n-ensemble", type=int, default=8)
    p.add_argument("--sample-steps", type=int, default=18)
    p.add_argument("--sigma-data", type=float, default=0.5)
    p.add_argument("--n-train", type=int, default=None,
                   help="subsample training pairs to N (evenly spaced, preserves time span) — "
                        "for the data-quantity ablation: does ensemble calibration improve with n?")
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--ema-decay", type=float, default=0.999)
    p.add_argument("--history-every", type=int, default=10,
                   help="record a held-out val probe every N epochs into training_history "
                        "(train-vs-val gap = the overfitting evidence). 0 disables.")
    p.add_argument("--eval-every", type=int, default=0,
                   help="QUALITY LADDER: every N epochs run a light ensemble eval (skill + "
                        "calibration) and record it; with --ckpt-every this retains a ladder of "
                        "checkpoints each tagged with its measured quality. 0 disables.")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--cpu", action="store_true")
    p.add_argument("--rollout-train-k", type=int, default=1,
                   help="ROLLOUT-AWARE training: unroll K autoregressive steps and average per-step loss "
                        "so the model learns stability under its own errors. K=1 = single-step (default). "
                        "Applies to the regression backbone (incl. --regression-only for the ensemble).")
    p.add_argument("--regression-only", action="store_true",
                   help="train ONLY the FNO regression backbone, save it, and exit (no diffusion). "
                        "Used to build DEEP ENSEMBLES: run N seeds in parallel, then aggregate with "
                        "scripts/deep_ensemble_eval.py — the control baseline for the diffusion's UQ.")
    p.add_argument("--dt-scaled-residual", action="store_true",
                   help="network predicts a PER-MONTH tendency; the applied step is tendency*dt. "
                        "Fixes the blended-operator defect without discarding the long-gap pairs.")
    p.add_argument("--uniform-dt-only", action="store_true",
                   help="keep only training pairs whose REAL elapsed time is ~1 month "
                        "(tests pair QUALITY; the learning curve already showed pair COUNT "
                        "saturates at n~55, so quantity is not the lever)")
    p.add_argument("--uniform-dt-range", type=float, nargs=2, default=(25.0, 36.0),
                   metavar=("LO", "HI"), help="day range counted as 'one month'")
    p.add_argument("--dt-seconds", type=float, default=1200.0,
                   help="v05 LLC270 timestep (72 iters/day). NOT 900 -- see llc270_loader.")
    p.add_argument("--smoke", action="store_true", help="tiny synthetic run on CPU")
    p.add_argument("--save-model", default=None, help="path to save regression+diffusion state dicts (.pt)")
    p.add_argument("--ckpt-every", type=int, default=0, help="save a checkpoint every N diffusion epochs (kill-safe)")
    p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    torch.manual_seed(args.seed); np.random.seed(args.seed)
    device = "cpu" if (args.cpu or args.smoke or not torch.cuda.is_available()) else "cuda"

    if args.smoke:
        T, C, H, W = 20, 4, 32, 64
        rng = np.random.default_rng(0)
        base = rng.standard_normal((C, H, W)).astype(np.float32)
        state = np.stack([base * math.cos(t / 3) + 0.3 * rng.standard_normal((C, H, W)) for t in range(T)])
        mask = np.ones((H, W), bool); mask[:2] = False
        names = [f"v{i}" for i in range(C)]
        args.regression_epochs = min(args.regression_epochs, 20)
        args.diffusion_epochs = min(args.diffusion_epochs, 30)
    else:
        if not args.cube:
            print("ERROR: --cube required (or --smoke)"); return 2
        state, mask, names = load_cube(args.cube)
        if args.surface_only:
            keep = [i for i, nm in enumerate(names) if nm.endswith("_k0")] or list(range(min(6, len(names))))
            state, names = state[:, keep], [names[i] for i in keep]
        elif args.channels:
            keep = [int(c) for c in args.channels.split(",")]
            state, names = state[:, keep], [names[i] for i in keep]

    T, C, H, W = state.shape
    print(f"[data] state {state.shape} channels={names} ocean={int(mask.sum())}/{H*W} device={device}", flush=True)
    if device == "cuda":
        print(f"[gpu] {torch.cuda.get_device_name(0)} total={torch.cuda.get_device_properties(0).total_memory/1e9:.0f}GB", flush=True)
    if args.log_transform:
        lo, hi = float(np.nanmin(state[:, :, mask])), float(np.nanmax(state[:, :, mask]))
        state = np.log(np.clip(state, args.log_floor, None)).astype(np.float32)
        print(f"[log] log-transform ON (floor={args.log_floor:g}); raw ocean range [{lo:.2e}, {hi:.2e}] "
              f"-> log range [{float(np.nanmin(state[:, :, mask])):.2f}, {float(np.nanmax(state[:, :, mask])):.2f}]. "
              f"Skill is now measured in LOG space (the natural space for chlorophyll).", flush=True)
    z, mean, std = zscore(state, mask)
    del state
    Z = torch.from_numpy(z)  # CPU tensor; batches move to GPU
    tr_t, va_t = time_split(T)

    # --- uniform-dt ablation -------------------------------------------------
    # The cube is NOT a contiguous monthly series: only ~48% of consecutive index
    # pairs are truly one month apart; the rest span 2-7 months and are trained as
    # if they were single steps. The learned operator is therefore a BLEND of
    # 1-to-7-month transitions rather than a monthly operator.
    #
    # A learning curve over pair COUNT saturates at n~55, so quantity is not the
    # lever. This flag tests the other axis -- pair QUALITY -- by keeping only the
    # pairs whose real elapsed time is ~1 month. Compare against the quantity-
    # matched random subsample from the learning curve to separate the two.
    #
    # Time is derived from `iters` (x 1200 s), never from the stored `times_days`,
    # which was written with a wrong 900 s timestep.
    if getattr(args, "uniform_dt_only", False):
        _z = np.load(args.cube, allow_pickle=True)
        if "iters" not in _z:
            raise SystemExit("--uniform-dt-only needs `iters` in the cube")
        _days = np.asarray(_z["iters"], dtype=float) * args.dt_seconds / 86400.0
        _gap = np.diff(_days)                      # gap[t] = days between t and t+1
        lo, hi = args.uniform_dt_range
        keep = [t for t in tr_t if t + 1 < len(_days) and lo <= _gap[t] <= hi]
        print(f"[ablation] uniform-dt filter [{lo},{hi}] d: "
              f"{len(tr_t)} -> {len(keep)} train pairs "
              f"(median gap kept {np.median([_gap[t] for t in keep]):.1f} d, "
              f"dropped median {np.median([_gap[t] for t in tr_t if t not in keep]):.1f} d)",
              flush=True)
        tr_t = keep

    if args.n_train and args.n_train < len(tr_t):
        # evenly spaced -> preserves the training time span; only DENSITY varies (clean ablation)
        idx = np.linspace(0, len(tr_t) - 1, args.n_train).astype(int)
        tr_t = [tr_t[i] for i in sorted(set(idx.tolist()))]
        print(f"[ablation] subsampled train pairs -> {len(tr_t)}", flush=True)
    print(f"[data] train pairs={len(tr_t)} val pairs={len(va_t)}", flush=True)
    mask_t = torch.from_numpy(mask.astype(np.float32))[None, None].to(device)

    t0 = time.time()
    print("[1/3] training regression backbone (FNO)…", flush=True)
    dt_m = None
    if args.dt_scaled_residual:
        _zz = np.load(args.cube, allow_pickle=True)
        _dd = np.asarray(_zz["iters"], dtype=float) * args.dt_seconds / 86400.0
        _gm = np.diff(_dd) / 30.4375                      # gap in months, per pair index t
        dt_m = torch.tensor(np.concatenate([_gm, [_gm[-1]]]), dtype=torch.float32)
        print(f"[dt-scaled] per-month tendency; train-pair gaps median {np.median(_gm[tr_t]):.2f} mo "
              f"range {_gm[tr_t].min():.2f}-{_gm[tr_t].max():.2f}", flush=True)
    fno, reg_hist = train_regression(Z, tr_t, C, mask_t, device, args.regression_epochs, args.modes, args.reg_width, args.batch_size, lr=args.lr, va_t=va_t, history_every=args.history_every, rollout_k=args.rollout_train_k, dt_months=dt_m)
    print(f"      regression done ({time.time()-t0:.0f}s)", flush=True)
    if args.regression_only:
        # Report skill vs persistence IN THIS TRANSFORM'S SPACE. Required for cross-transform
        # comparison: raw val_mse is NOT comparable between linear and log space, because
        # persistence_mse differs in each space. Only the skill RATIO is comparable.
        with torch.no_grad():
            _va = torch.tensor(va_t); _nc = mask_t.sum().item()
            _sp = _rg = 0.0; _n = 0
            for _k in range(0, len(_va), 8):
                _bt = _va[_k : _k + 8]
                _xt, _yt = _batch(Z, _bt, device)
                # BUGFIX 2026-07-19: apply the SAME forward map the model was trained with.
                # Under --dt-scaled-residual, train_regression uses mu = x + fno(x) * dt_months
                # (the network emits a PER-MONTH TENDENCY). This block previously used the plain
                # residual x + fno(x) regardless, so a per-month tendency was applied as if it
                # were a full-step correction. On the mixed val set (median gap ~2 months) that
                # under-predicts the change by ~2x and understates the model badly. Every
                # skill/metrics value written by a --dt-scaled-residual --regression-only run
                # BEFORE this fix is invalid; recompute from the checkpoint.
                if dt_m is None:
                    _mu = _xt + fno(_xt)
                else:
                    _s = dt_m[_bt].to(device).view(-1, 1, 1, 1)
                    _mu = _xt + fno(_xt) * _s
                _sp += float((((_xt - _yt) ** 2) * mask_t).sum())
                _rg += float((((_mu - _yt) ** 2) * mask_t).sum())
                _n += len(_bt)
            _den = max(_n * C * _nc, 1e-9)
            _pm, _rm = _sp / _den, _rg / _den
        _skill = 1 - _rm / max(_pm, 1e-12)
        reg_skill_info = {"persistence_mse": _pm, "regression_mse": _rm,
                          "regression_skill": _skill,
                          "space": "log" if args.log_transform else "linear",
                          "forward_map": "x + f(x) * dt_months" if dt_m is not None else "x + f(x)"}
        print(f"[reg-only] space={reg_skill_info['space']}  persistence_mse={_pm:.6f}  "
              f"reg_mse={_rm:.6f}  SKILL vs persistence = {_skill:+.4f}", flush=True)
        if args.save_model:
            torch.save({"regression": fno.state_dict(), "mean": mean, "std": std,
                        "channels": names, "seed": args.seed, "config": vars(args),
                        "history": reg_hist}, args.save_model)
            print(f"[save] regression-only (seed {args.seed}) -> {args.save_model}", flush=True)
        out = {"config": vars(args), "channels": names, "mode": "regression_only",
               "seed": args.seed, "training_history": {"regression": reg_hist},
               "metrics": reg_skill_info,
               "n_train_pairs": len(tr_t), "n_val_pairs": len(va_t),
               "wall_s": time.time() - t0}
        if args.out:
            Path(args.out).write_text(json.dumps(out, indent=2))
            print(f"wrote {args.out}", flush=True)
        return 0
    print("[2/3] training EDM diffusion corrector…", flush=True)
    model, dloss, diff_hist = train_diffusion(fno, Z, tr_t, C, mask_t, device, args.diffusion_epochs, args.modes, args.width, args.batch_size, lr=args.lr, sigma_data=args.sigma_data, ema_decay=args.ema_decay, ckpt_path=args.save_model, ckpt_every=args.ckpt_every, ckpt_meta={"mean": mean, "std": std, "channels": names}, va_t=va_t, history_every=args.history_every, eval_every=args.eval_every)
    print(f"      diffusion done final-loss={dloss:.4f} ({time.time()-t0:.0f}s)", flush=True)
    if device == "cuda":
        print(f"[gpu] peak mem = {torch.cuda.max_memory_allocated()/1e9:.1f} GB", flush=True)
    print("[3/3] evaluating (skill + spread + spectral realism)…", flush=True)
    metrics, spec = evaluate(fno, model, Z, va_t, C, mask_t, mask, device, n_ens=args.n_ensemble, steps=args.sample_steps, bs=args.eval_batch)
    for k, v in metrics.items():
        print(f"    {k:32s} {v:+.4f}")
    print("\nInterpretation: diffusion_ensmean_skill ~ regression_skill (expected; ceiling is intrinsic).")
    print("hf_power_ratio: regression <1 (blurred) vs diffusion ~1 (sharp) = the diffusion win.")

    if args.save_model:
        torch.save({"regression": fno.state_dict(), "diffusion": model.state_dict(),
                    "mean": mean, "std": std, "channels": names,
                    "config": {k: v for k, v in vars(args).items()}}, args.save_model)
        print(f"[save] wrote {args.save_model}", flush=True)
    out = {"config": vars(args), "channels": names, "final_diffusion_loss": dloss,
           "metrics": metrics, "spectrum": spec, "wall_s": time.time() - t0,
           "peak_gpu_gb": (torch.cuda.max_memory_allocated() / 1e9 if device == "cuda" else None),
           # auditable per-epoch trace — research evidence. train_edm vs val_edm gap
           # is the overfitting signature that drives ensemble under-dispersion.
           "training_history": {"regression": reg_hist, "diffusion": diff_hist},
           "n_train_pairs": len(tr_t), "n_val_pairs": len(va_t)}
    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=2))
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
