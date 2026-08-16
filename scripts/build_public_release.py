"""Build a curated PUBLIC release tree from this private working repo.

CONTEXT. 2imi9/ECCO-DarwinDiff was public from 2026-04-30 to 2026-08-13 and is now PRIVATE.
The research trail (378 findings, 48 research notes, 77 archive docs, 60 notebooks, the full
evidence corpus) stays private. The public artifact is a NEW repository containing only what is
needed to make the method work, plus the headline results.

WHY A NEW REPO RATHER THAN DELETING HERE. Deleting from HEAD does not remove anything from a git
history that has already been published; it only creates the appearance of privacy. A fresh
repository with a fresh history is the only mechanism that actually holds.

WHAT THIS SCRIPT DOES. Copies an explicit ALLOW-LIST into an output directory. Nothing is deleted
from the working repo. It is deny-by-default: a file is excluded unless a rule names it, so
forgetting to think about a directory keeps it private rather than publishing it.

It also scrubs machine-specific absolute paths and account names, which are a real leak surface in
a research repo (they appear in a dozen tracked scripts here).

Run:
    python scripts/build_public_release.py --out ../darwindiff-public [--dry-run]
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from pathlib import Path

# ---------------------------------------------------------------- allow-list --
# Whole directories that make the method work.
ALLOW_DIRS = [
    "src/darwindiff",          # box model, loaders, closures, networks, trainer, transport
    "scripts/configs",         # the pinned flagship config - required to reproduce a fit
    "scripts/fetch",           # public data fetch helpers
]

# Individual files: the runner, the gates, the graders, and the provenance tooling.
ALLOW_FILES = [
    "scripts/run_v3.0_joint_multi_aoi.py",
    "scripts/verify_run.py",
    "scripts/build_darwin_ic_cache.py",
    "scripts/physics_verify.py",
    "scripts/analysis/pooler_audit.py",
    "scripts/analysis/grade_all_params.py",
    "scripts/analysis/per_aoi_leg_audit.py",
    "scripts/analysis/grader_crosscheck.py",
    "scripts/analysis/grade_joint_percell.py",
    "scripts/analysis/contract_report.py",     # the identifiability contract report
    "scripts/aggregate_daniels_recovery.py",
    "scripts/aggregate_rpicpoc_env.py",
    "scripts/analysis/build_results_manifest.py",
    "scripts/analysis/forward_model_equivalence.py",
    "scripts/analysis/forward_model_equivalence_grad.py",
    "scripts/analysis/sham_split_false_positive_rate.py",
    "pyproject.toml",
    "LICENSE",
    ".gitignore",
    "uv.lock",            # pinned dependency set - required for a reproducible install
    ".python-version",
    ".gitattributes",
]

# CI: keep the workflow that runs the test suite, so the public repo self-verifies.
ALLOW_DIRS_CI = [".github/workflows"]

# Headline results only - NOT the 378-finding trail.
ALLOW_RESULTS = [
    "docs/findings/2026-08-13_results_manifest.json",
]

# Tests are included, minus those that bind to the private research-map machinery.
TEST_EXCLUDE_SUBSTRINGS = [
    # bind to the private research-map / evidence machinery
    "research_map", "evidence_navigator", "citation_audit", "doc_", "docsync",
    "loss_twin", "seasonal_twin", "explicit_zooplankton", "canonical_numbers",
    # bind to internal tooling or to Track-2 / exploratory work that is out of scope
    # for a "make the method work" release
    "agent_bridge", "emulator", "diffusion_dt_scaling", "eki_core",
    "measure_memory_scaling", "symbolic_distill",
    # assert on internal repo documents (the closeout deck, AGENTS.md working agreements)
    # that are deliberately not part of the public tree
    "summer_closeout_deck", "agent_working_agreements",
]

# ------------------------------------------------------------------- scrubbing --
SCRUB = [
    (re.compile(r"C:/Users/Frank[^\s\"']*", re.I), "<DATA_ROOT>"),
    (re.compile(r"C:\\\\Users\\\\Frank[^\s\"']*", re.I), "<DATA_ROOT>"),
    (re.compile(r"/home/qi_zim_neu[^\s\"']*"), "<CLUSTER_HOME>"),
    (re.compile(r"/scratch/qi_zim_neu[^\s\"']*"), "<SCRATCH>"),
    (re.compile(r"qi_zim_neu"), "<CLUSTER_USER>"),
    (re.compile(r"qi\.zim@northeastern\.edu"), "<EMAIL>"),
    (re.compile(r"frankziming[^\s\"']*"), "<EMAIL>"),
    (re.compile(r"p2026_0089_neu"), "<SLURM_ACCOUNT>"),
]
SCRUB_EXT = {".py", ".sh", ".md", ".toml", ".cfg", ".txt", ".sbatch"}


def tracked(repo: Path) -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=repo, capture_output=True, text=True)
    return [l for l in out.stdout.splitlines() if l.strip()]


def wanted(path: str) -> bool:
    if "__pycache__" in path or path.endswith(".pyc"):
        return False
    if path in ALLOW_FILES or path in ALLOW_RESULTS:
        return True
    if any(path.startswith(d + "/") for d in ALLOW_DIRS + ALLOW_DIRS_CI):
        return True
    if path.startswith("tests/") and path.endswith(".py"):
        return not any(s in path for s in TEST_EXCLUDE_SUBSTRINGS)
    return False


def scrub_text(text: str) -> tuple[str, int]:
    n = 0
    for pat, repl in SCRUB:
        text, k = pat.subn(repl, text)
        n += k
    return text, n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[1]
    out = Path(args.out).resolve()

    files = tracked(repo)
    keep = [f for f in files if wanted(f)]
    drop = [f for f in files if not wanted(f)]

    by_area: dict[str, int] = {}
    for f in drop:
        by_area[f.split("/")[0]] = by_area.get(f.split("/")[0], 0) + 1

    print(f"tracked in private repo : {len(files)}")
    print(f"INCLUDED in public tree : {len(keep)}")
    print(f"excluded                : {len(drop)}\n")
    print("excluded by top-level area:")
    for a, n in sorted(by_area.items(), key=lambda x: -x[1]):
        print(f"   {a:20s} {n:>5}")

    print("\nincluded by area:")
    inc: dict[str, int] = {}
    for f in keep:
        inc[f.split("/")[0]] = inc.get(f.split("/")[0], 0) + 1
    for a, n in sorted(inc.items(), key=lambda x: -x[1]):
        print(f"   {a:20s} {n:>5}")

    if args.dry_run:
        print("\n--dry-run: nothing written")
        return 0

    if out.exists():
        shutil.rmtree(out)
    scrubbed_files, scrubbed_hits = 0, 0
    for f in keep:
        src, dst = repo / f, out / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix.lower() in SCRUB_EXT:
            try:
                t = src.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                shutil.copy2(src, dst); continue
            t2, n = scrub_text(t)
            if n:
                scrubbed_files += 1; scrubbed_hits += n
            dst.write_text(t2, encoding="utf-8")
        else:
            shutil.copy2(src, dst)

    print(f"\nwrote {len(keep)} files to {out}")
    print(f"scrubbed {scrubbed_hits} machine-specific strings across {scrubbed_files} files")

    # residual leak check on the OUTPUT tree
    residual = []
    for p in out.rglob("*"):
        if p.is_file() and p.suffix.lower() in SCRUB_EXT:
            try:
                t = p.read_text(encoding="utf-8")
            except Exception:
                continue
            for pat, _ in SCRUB:
                if pat.search(t):
                    residual.append(str(p.relative_to(out))); break
    print(f"residual leak check: {len(residual)} file(s) still matching" +
          ("" if not residual else " -> " + ", ".join(residual[:5])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
