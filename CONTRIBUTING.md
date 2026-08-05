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
of frozen `Param(name, bounds, carroll_value, units, description, learned, scale)`
dataclasses, and everything else is **derived** from it so the views never drift:

| Derived object | What it is | Used by |
| --- | --- | --- |
| `PARAM_NAMES` | `[p.name for p in PARAMS]` | recovery report, gating validation |
| `CARROLL_VALUES` | float32 tensor of `p.carroll_value` | recovery target / synthetic truth |
| `PARAM_BOUNDS` | `[n, 2]` float32 `(lo, hi)` tensor | `bounded_params` sigmoid map |
| `PARAM_INDEX` | `{name: position}` | `gating._PARAM_INDEX`, `carroll6_5pft.I_*` |
| `P` | `SimpleNamespace` of named indices (`P.alpfe`, …) | box steps + runner loss terms |
| `N_PARAMS` | `len(PARAMS)` | **network head width** — never hardcode `6` |
| `PARAM_LOG_MASK` | bool mask of `scale == "log"` entries | opt-in log bounding |

**Never write the parameter count as a literal.** Network heads take
`n_outputs=N_PARAMS`, so appending a registry entry widens the per-cell DINN
automatically (its head is a 1×1 conv, so the parameter axis is the only thing
that changes). Before 2026-07-28 there were 85 hardcoded `6`s and *nothing* read
the count from the registry — the registry was the source of truth for parameter
*values* but not for parameter *count*.

**`scale` picks the bounding geometry.** `"linear"` (default) or `"log"`. A
parameter spanning decades wants `"log"`: a linear map over `scav_rat`'s 100×
range spends **90.9 %** of the sigmoid on the top decade, so only 7.5 % of the
initialisation distribution starts below Carroll and the median start is 2.52×
Carroll. The field is metadata only — it changes nothing unless a caller passes
the derived mask via `bounded_params(log_mask=...)`, or the runner is given
`PARAM_LOG_SCALE=<names>`. That keeps every published run bitwise reproducible.

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
6. **Run `tests/test_param_registry_wiring.py`.** It is registry-driven, so it
   picks up the new entry with no edit, and it will **fail** if the parameter
   does not measurably change the 2-layer box state. That is the guard against
   the worst failure mode: a parameter that is registered but never wired into
   the physics fails *silently* — the head grows a channel, the value is bounded,
   collapsed per AOI and graded, and a recovery count is reported for something
   no observation could have constrained.
7. **Establish its chance baseline before believing any recovery count.**
   "Recovered" means `rel <= 0.40`, and how much of a parameter's prior already
   satisfies that depends entirely on its bounds. Run the prior control —
   `NB23_LR=0 NB23_N_EPOCHS=1`, which leaves the networks at initialisation and
   scores them through the identical pipeline — and grade with
   `scripts/analysis/grade_all_params.py --baseline <prior_dir>`.

   This is not hypothetical. Measured at n=50 (job 227777), the untrained chance
   rates are `diatomgraz` **0.640**, `alpfe` 0.200, `Smallgrow` 0.120, and
   `scav_rat` / `Biggrow` / `R_PICPOC` **0.000**. A parameter whose bounds
   midpoint falls inside the ±40 % band scores as "recovered" from an untrained
   network most of the time. **Choose bounds so the midpoint sits outside the
   band**, and so that neither bound sits inside the ±40 % band around the target, and report every count next to its baseline. `alpfe` shows the second failure: its upper bound 1.0 is only 7.72 % above Carroll 0.92831, so trained per-AOI medians are 0.99226 / 0.99937 / 0.99924, 27/45/49 of 50 seeds land within 1 % of the bound, and the band sweep is a step function (0/50 at 0.05 and 0.06, 49/50 at 0.08 and above). The signal there is real (98/100 vs untrained 0/100 at band 0.10), but the count cannot establish accuracy: the recovery distribution is a spike at the rail, and the precision stays unresolved pending a widened-bound arm.
8. **If you add a DINN input channel, the baseline must match the architecture.**
   Changing `n_input_channels` changes the initialisation distribution and hence
   the chance rate, so a covariate result graded against a different-architecture
   baseline is graded against the wrong null.
9. **Re-run the trust gate and confirm it actually grades the new parameter.**
   `python scripts/verify_run.py <run_dir> --expect-seeds <n>` must exit 0, and
   the new name must appear in its per-parameter printout. The gate derives
   `PARAMS` and `CARROLL` from the registry (since 2026-07-29), so a new entry is
   picked up with no edit — but confirm it, because before that change the gate
   kept a private hardcoded list and would have **silently skipped** the new
   parameter while still exiting 0 `VERIFIED`. A run artifact carrying a
   parameter the gate does not know is now rejected as `MALFORMED` rather than
   partially graded. Add `--require-baseline` in loops and CI so a number can
   never be recorded without the step-7 chance baseline attached. `verify_run.py` does **not** grade the per-AOI collapse, so any `scav_rat` count must also pass `python scripts/analysis/pooler_audit.py <run_dir>`; the collapse keys exist only from 2026-07-29, 119 of 211 run dirs carry none, and on those the audit prints `<absent>` and exits 2 — that is a gate, not a fallback to the arithmetic number.

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
