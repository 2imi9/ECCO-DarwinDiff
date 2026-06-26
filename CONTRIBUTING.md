# Contributing to ECCO-DarwinDiff

## Branch naming

All work branches use the **`<github-username>/<scope>-<short-description>`** form. For this repository, the maintainer's GitHub handle is **`2imi9`** ([github.com/2imi9](https://github.com/2imi9)), so all branches authored by the maintainer take the form `2imi9/<scope>-<short-description>`. Examples:

- `2imi9/v3.1-doc-cleanup`
- `2imi9/v2.8-darwin-ic-poc-sub`
- `2imi9/demo-colab`
- `2imi9/fixups-pr45-54-bot-comments`

The username prefix is the GitHub user namespace — it scopes the branch to its author and prevents accidental collisions on shared repositories. The scope (e.g. `v3.1`, `v2.8`, `docs`, `demo`, `fixups`) groups the change. The short description is hyphenated. Contributors using a different GitHub account (e.g. for forks or external PRs) should substitute their own handle in place of `2imi9/`.

Avoid generic prefixes like `claude/`, `feature/`, or `dev/`. They lose authorship information and produce inconsistent histories that are harder to audit.

## Pull-request titles

Use a **scope prefix** followed by a colon and a one-line subject. Examples:

- `v3.1: c_chl40_posi15 n=20 retest closes the second 5/6 reproducibility question`
- `docs: trim README from 263 → 127 lines, drop redundancy with STATUS.md`
- `demo: Colab notebook + hero badge (synthetic recovery, ~5 min on free T4)`
- `fixups: address Greptile bot P1+P2 comments on PRs #46-#49`

The scope-prefix lets the merge history read as a project changelog without per-PR drilldown.

## Commit messages

- **No `Co-Authored-By` trailers.** Commits are attributed to the GitHub user that made them; co-author trailers add noise without value at the project scale.
- **First line is the summary** (≤ 72 chars), followed by a blank line, then a body explaining the *why* (not just the *what*).
- **Verified claims only.** When a commit contains numerical results, cross-check against the underlying JSONs / artifacts before writing the message.

## Merge strategy

Use **non-squash merges** (`gh pr merge --merge`). Per-commit history is preserved on `main`, which is useful for debugging multi-commit PRs and for the project's "what shipped when" narrative. Squash merges collapse this signal.

## Adding or removing a Carroll-N parameter

The learnable-parameter layout lives in **one** place: the `PARAMS` registry in
[`src/darwindiff/carroll6.py`](src/darwindiff/carroll6.py). It is an ordered tuple
of frozen `Param(name, bounds, carroll_value, units, description, learned)`
dataclasses, and everything else is **derived** from it so the views never drift:

| Derived object | What it is | Used by |
| --- | --- | --- |
| `PARAM_NAMES` | `[p.name for p in PARAMS]` | recovery report, gating validation |
| `CARROLL_VALUES` | float32 tensor of `p.carroll_value` | recovery target / synthetic truth |
| `PARAM_BOUNDS` | `[n, 2]` float32 `(lo, hi)` tensor | `bounded_params` sigmoid map |
| `PARAM_INDEX` | `{name: position}` | `gating._PARAM_INDEX`, `carroll6_5pft.I_*` |
| `P` | `SimpleNamespace` of named indices (`P.alpfe`, …) | box steps + runner loss terms |

**Read positions by name, never by number.** Box steps and loss terms index the
params vector through `P.<name>` (e.g. `params[P.alpfe]`) or the `I_<NAME>`
constants in `carroll6_5pft.py` (themselves `PARAM_INDEX["<name>"]`). Do not
reintroduce bare `params[3]`-style positional unpacking.

### To add a parameter

1. **Append** a `Param(...)` entry to `PARAMS`. *Append at the end* — see
   reproducibility below. One entry updates all five derived views automatically.
2. **Wire the physics.** Read it in the box step(s) that use it via
   `params[P.<name>]` (`carroll6.py`, `carroll6_5pft.py`,
   `carroll6_5pft_2layer.py`) and add its tendency terms. Add an `I_<NAME>`
   alias in `carroll6_5pft.py` only if a step there needs it.
3. **Wire the loss term** that identifies it in
   [`scripts/run_v3.0_joint_multi_aoi.py`](scripts/run_v3.0_joint_multi_aoi.py),
   reading the seed prediction as `params_b[P.<name>]`.
4. **Gating (if used):** route the new name in the relevant
   `GATING_POLICIES` presets in [`src/darwindiff/gating.py`](src/darwindiff/gating.py).
   `validate_policy` *requires every* parameter to be routed to ≥1 AOI, so an
   unrouted new parameter will raise at run start rather than silently freeze at
   its initialisation.
5. **Update the golden test** `tests/test_param_registry.py`: extend
   `GOLDEN_NAMES` / `GOLDEN_CARROLL_VALUES` / `GOLDEN_BOUNDS`. The forward-output
   goldens (`GOLDEN_STEP1`, `GOLDEN_INTEG_FINAL`) legitimately change when the
   model gains a tracer/parameter — recapture them and note why in the commit.

### To remove a parameter

Reverse the steps: delete the `Param` entry, delete its physics tendency terms
and any `I_<NAME>` alias, delete the loss term that targeted it, drop the name
from every `GATING_POLICIES` preset, and update the goldens. The registry makes
the *layout* bookkeeping a one-line delete, but physics/loss code that consumed
the parameter must still be removed by hand — a leftover `P.<name>` reference
will raise `AttributeError` at import, which is the intended loud failure.

### What must stay fixed for reproducibility

- **Order is load-bearing.** Existing runs, IC caches, and recovered-value JSONs
  index parameters positionally (`params[0]..params[5]`). Appending a new entry
  is safe; **reordering or inserting** changes the on-disk layout and breaks
  bitwise reproduction of every prior result.
- **Values are frozen.** Do not edit an existing entry's `carroll_value` or
  `bounds` as part of an unrelated change — `test_param_registry.py` locks the
  current six against their pre-registry float32 values. Changing a target is a
  deliberate, separately-justified science change, not a refactor.

### Naming conventions that key off parameter names

- **Named indices:** `P.<name>`, `PARAM_INDEX["<name>"]`, and the
  `I_<NAME>` constants all resolve a parameter's position from its registry
  `name`. Keep `name` a valid Python identifier (it becomes a `P` attribute).
- **Gating policies** (`GATING_POLICIES`, `GATING_POLICY` env / JSON) reference
  parameters **by name** (e.g. `{"eqpac": ["alpfe", "diatomgraz"]}`).
- **Not param-keyed:** the runner's `AOI_W_<AOI>` and `RATIO_AOI_W_<AOI>` env
  levers key off **AOI** keys (`eqpac`, `natlsubpolar`, …), not parameter names,
  so they are unaffected by a registry change. Per-term loss weights
  (`GEOTRACES_W`, `POSI_W`, `RATIO_W`, …) are per-loss-term, not per-parameter;
  each term reads the specific parameter(s) it identifies via `P.<name>`.

## Documentation discipline

For substantive changes:

- Update [STATUS.md](STATUS.md) with verified live state.
- Update [README.md](README.md) if the headline status, project arc, or quick-links bar changes.
- Add a per-version technical writeup to `docs/findings/<version>.md` for major closeouts.

Avoid embedding fragmented dates (`"as of 2026-05-12"`, `"this week"`, `"Tonight's bug log"`) in reference docs. Per-session narrative belongs in `docs/research_notes/<date>_<topic>.md`; reference docs should age well.

## Cleaning up after merges

Once a PR is merged, delete the branch locally and on the remote:

```bash
git branch -D <branch>
git push origin --delete <branch>
```

This keeps the remote-branch list short and the work-in-flight state legible.
