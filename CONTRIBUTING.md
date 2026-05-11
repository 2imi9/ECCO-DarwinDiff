# Contributing — ECCO-DarwinDiff

Project conventions for PRs, commits, branches, and code style. Short doc; the goal is consistency so the git history reads well and future searches land on the right thing.

## PR titles

Format: `<scope>: <descriptive action>` where `<scope>` matches one of:

| Scope | Use for | Examples |
|---|---|---|
| `Notebook NN` | New notebook (with optional version tag) | `Notebook 22: hybrid GLODAP/Darwin fit (v2.1 Phase 1)` |
| `Track 1 vX.Y` | Version closeouts on the parameter-learner track | `Track 1 v2.0 closeout: gradient-based Green's-functions replacement` |
| `Track 2 ...` | Emulator track work | `Track 2 scoping: neural surrogate architecture options` |
| `Day N` | Day-numbered incremental work inside a closeout | `Day 6: v2.0 findings doc + README/STATUS bump` |
| `docs:` | Doc-only changes | `docs: Day 9 MITgcm CTRL + adjoint audit` |
| `infra:` or `cluster:` | SLURM / ORCD / data-loader infrastructure | `cluster: ORCD Engaging compaction (Jonathan-ready)` |
| `tests:` | Test-only PRs | `tests: opt-in real-data integration for carbonate vars` |
| `fix:` | Bug fixes | `fix: NaN propagation in carbonate solver at land cells` |

Title under 70 characters where possible; put detail in the body.

## Commit messages

Same scope-prefix pattern as PR titles. Subject line under ~70 characters; body in bullet points with the *why*, not just the *what*.

**No `Co-Authored-By:` trailer.** Final attribution is handled at project end, not per-commit.

Example:

```
Day 4 follow-up: nb20 executed end-to-end (v2.0 headline result)

Ran notebooks/20_carbonate_extension_eqpac.ipynb on RTX 5090 against
the D:\ecco_darwin_v5 tree. ~80 min wall-clock total (DINN baseline +
DINNDeep). All 7 tracer targets loaded successfully. Outputs baked
into the notebook in place via jupyter nbconvert --execute --inplace.

HEADLINE RESULT (DINN baseline + 7-tracer carbonate vs nb14 FeT-only):
  alpfe:    0.033 -> 0.011 off Carroll (CLOSER, within 1.1%)
  scav_rat: 0.798 -> 0.401 off Carroll (CLOSER, halved 80% gap)
  ...

This is the v2.0 publishable result. Full interpretation in the
Day 6 findings doc (docs/findings/v2_track1_closeout.md).
```

Multi-line commit messages are preferred for any non-trivial change. Hard wrap at ~72 chars in the body.

## Branch naming

Existing pattern, keep using it:

| Pattern | Use for |
|---|---|
| `claude/<descriptive-slug>` | Feature work driven by an agent session (most common) |
| `claude/nbNN-<topic>` | Notebook-specific branches |
| `claude/vX.Y-<topic>` | Version-scoped work (e.g. `claude/v2.1-glodap-real-obs`) |
| `docs/<topic>` | Documentation-only branches |
| `fix/<topic>` | Bug-fix branches |

Worktrees live under `.claude/worktrees/<random-name>/` and are gitignored; safe to delete after the branch is merged.

## Merge strategy

- **Non-squash merge by default** for multi-commit PRs (preserves day-by-day commit structure for archaeology).
- **Squash** only for trivially-tiny PRs (single-purpose, single commit's worth of content).
- Never force-push to main.
- Tag version closeouts: `git tag -a vX.Y -m "..."` at the merge commit.

## Code style

- Python 3.11+, line length 100 (per `pyproject.toml`).
- Ruff for linting; mypy in lax mode. See `pyproject.toml` for per-file ignores.
- BGC modules (`carroll6.py`, `carbonate.py`, etc.) use chemistry-equation naming (`K0`, `K1`, `K2`, `DFe`, `ALK`) — per-file-ignored on N802/N806/RUF002 because it matches published literature.
- Notebooks should be reproducible from the corresponding `scripts/build_nbNN.py` builder. The build script is the source of truth; the `.ipynb` is the executed snapshot.
- Tests: pytest, no fixtures-in-conftest unless reused across files. Opt-in real-data tests guarded by `DARWINDIFF_TEST_LLC270=1` env var.

## Docs

- New scientific findings go to `docs/findings/<descriptive_name>.md` (date-stamped or topic-stamped). Reference from README + STATUS for headline results.
- README and STATUS are the public face — keep them in sync with each release.
- Cluster ops docs in `docs/cluster_setup.md`. Update when partition names / module paths change.
