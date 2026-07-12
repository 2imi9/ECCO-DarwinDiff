"""Aggregate the Track-2 emulator PoC array (prognostic seeds + forcing seeds) into one
verdict + a findings markdown. Reads the per-run JSONs written by scripts/emulator_poc.py.

Headline question: does an FNO beat PERSISTENCE (skill = 1 - MSE_model/MSE_persistence > 0)
on held-out v05 next-month state, robustly across seeds — and does environmental forcing help?

Usage:
    python scripts/emulator_poc_aggregate.py <dir_or_jsons...> \
        --json docs/findings/emulator_poc.json --md docs/findings/emulator_poc_scored.md
"""
from __future__ import annotations

import argparse
import glob
import json
import statistics as st
from pathlib import Path


def _load(paths):
    runs = []
    for p in paths:
        d = json.loads(Path(p).read_text(encoding="utf-8"))
        cfg = d.get("config", {})
        tag = "forc" if cfg.get("forcing") else "prog"
        runs.append({
            "file": Path(p).name, "tag": tag, "seed": cfg.get("seed"),
            "skill": d.get("headline_overall_skill_vs_persistence"),
            "beats": d.get("beats_persistence"),
            "anom_r2": d.get("metrics", {}).get("overall_anomaly_r2_vs_climatology"),
            "persist_vs_clim": d.get("metrics", {}).get("persistence_skill_vs_climatology"),
            "per_tracer": {k: v.get("skill_vs_persistence") for k, v in d.get("metrics", {}).get("per_tracer", {}).items()},
            "rollout_stable": d.get("rollout", {}).get("stable"),
            "rollout_beats_final": d.get("rollout", {}).get("beats_persistence_at_final_step"),
            "max_mass_drift": d.get("rollout", {}).get("max_abs_relative_mass_drift"),
            "verdict": d.get("verdict"),
            "n_val_pairs": d.get("data", {}).get("n_val_pairs"),
            "epochs": cfg.get("epochs"),
        })
    return sorted(runs, key=lambda r: (r["tag"], r["seed"] if r["seed"] is not None else -1))


def _grp(runs, tag):
    return [r for r in runs if r["tag"] == tag]


def _stat(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    return {"mean": st.mean(vals), "min": min(vals), "max": max(vals),
            "std": st.pstdev(vals) if len(vals) > 1 else 0.0, "n": len(vals),
            "n_positive": sum(1 for v in vals if v > 0)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--json", required=True)
    ap.add_argument("--md", required=True)
    args = ap.parse_args()

    paths = []
    for x in args.inputs:
        if Path(x).is_dir():
            paths += sorted(glob.glob(str(Path(x) / "emu_*.json")))
        else:
            paths.append(x)
    runs = _load(paths)
    if not runs:
        print("no runs found in", paths)
        return 1

    prog = _grp(runs, "prog")
    forc = _grp(runs, "forc")
    prog_skill = _stat([r["skill"] for r in prog])
    forc_skill = _stat([r["skill"] for r in forc])
    all_skill = _stat([r["skill"] for r in runs])

    # per-tracer mean skill across prognostic seeds
    tracer_names = list(prog[0]["per_tracer"].keys()) if prog else []
    per_tracer_prog = {t: _stat([r["per_tracer"].get(t) for r in prog]) for t in tracer_names}

    prog_beats = (prog_skill and prog_skill["n_positive"] == prog_skill["n"] and prog_skill["n"] > 0)
    any_beats = all_skill and all_skill["n_positive"] > 0
    forcing_helps = (prog_skill and forc_skill and forc_skill["mean"] > prog_skill["mean"] + 0.01)

    if prog_beats:
        verdict = "MAKE — FNO beats persistence across all prognostic seeds"
    elif any_beats:
        verdict = "MARGINAL — FNO beats persistence in some seeds only"
    else:
        verdict = "BREAK — FNO does not beat persistence (learned operator no better than copying x(t))"

    summary = {
        "experiment": "emulator_poc_next_state_vs_persistence_ensemble",
        "platform": "Explorer H200 (cuda/float32)",
        "verdict": verdict,
        "prognostic_skill": prog_skill, "forcing_skill": forc_skill,
        "forcing_helps": bool(forcing_helps),
        "per_tracer_skill_prognostic": per_tracer_prog,
        "runs": runs,
    }
    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json).write_text(json.dumps(summary, indent=2), encoding="utf-8")

    def fmt(s):
        return f"{s['mean']:+.4f} ± {s['std']:.4f} (n={s['n']}, {s['n_positive']} skill>0, range [{s['min']:+.3f},{s['max']:+.3f}])" if s else "—"
    rows = "\n".join(
        f"| {r['tag']} | {r['seed']} | {r['skill']:+.4f} | {'yes' if r['beats'] else 'no'} | "
        f"{r['anom_r2']:+.3f} | {'yes' if r['rollout_stable'] else 'no'} | {r['verdict']} |"
        for r in runs)
    tracer_rows = "\n".join(
        f"| {t} | {fmt(s)} |" for t, s in per_tracer_prog.items()) if per_tracer_prog else ""
    pvc = prog[0]["persist_vs_clim"] if prog else None

    md = f"""# Track-2 emulator PoC — scored (H200, next-state vs persistence)

**Source:** Explorer H200 array (job 8302755), `scripts/emulator_poc.py`. eqpac AOI (21×51),
tracers DIC/ALK/PIC/POC/FeT/Chl1, surface, {runs[0]['epochs']} epochs, temporal hold-out
(n_val_pairs={runs[0]['n_val_pairs']}). **Local-only — not committed to GitHub.**

Headline metric = **skill over persistence** = 1 − MSE(model)/MSE(persistence) on held-out months,
ocean cells only, standardized units. >0 means the learned operator beats copying x(t). Persistence
is a **strong** baseline here (persistence skill vs climatology = {pvc:+.3f} — it already captures
most of the month-to-month structure), so beating it is the real bar.

## Verdict: {verdict}

- prognostic (no forcing): skill {fmt(prog_skill)}
- forcing-augmented (SST/wind/MLD): skill {fmt(forc_skill)}
- environmental forcing helps: **{'yes' if forcing_helps else 'no'}**

## Per-run

| config | seed | skill vs persistence | beats? | anomaly-R² vs clim | rollout stable | verdict |
|---|---|---|---|---|---|---|
{rows}

## Per-tracer skill (mean across prognostic seeds)

| tracer | skill vs persistence |
|---|---|
{tracer_rows}

## Reading this honestly

- A single AOI, small held-out set (n_val_pairs={runs[0]['n_val_pairs']}) — this is a **go/no-go
  signal for the emulator direction**, not a converged benchmark. Seeds give the robustness read.
- The model predicts the **full next state** (not a persistence residual), so positive skill is real
  learned month-to-month change; negative skill means the FNO is worse than copying — i.e. at this
  scale/data it has not learned usable dynamics, and the emulator needs more data / resolution / a
  residual formulation before B200 scale-up is warranted.
- Rollout stability + mass-drift are reported per run; a 1-step win with a diverging rollout is not a
  usable emulator.
"""
    Path(args.md).parent.mkdir(parents=True, exist_ok=True)
    Path(args.md).write_text(md, encoding="utf-8")
    print(f"verdict: {verdict}")
    print(f"prognostic skill: {fmt(prog_skill)}")
    print(f"wrote {args.json} and {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
