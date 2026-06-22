# Issue tracker conventions

How DarwinDiff issues are filed, labeled, and prioritized. Sibling to `CONTRIBUTING.md` (branch / PR / commit conventions).

## Label taxonomy

Each issue gets at minimum one `type:*` label, plus optional tier and status labels.

### Type (required, exactly one)

| Label | Use for | Examples |
|---|---|---|
| `type:infra` | Cluster setup, account provisioning, environment, CI, hardware. | #84 Engaging onboarding |
| `type:code` | Model, library, or training-loop code work. | #85 time-resolved fitting; #86 box-model extension |
| `type:paper` | Manuscript drafting, figures, submission. | #87 paper #1 draft |
| `type:demo` | Examples, walkthroughs, outreach assets. | #88 Colab badge restore |
| `type:research-question` | Open scientific question, not directly actionable until sharpened. | #6 mass conservation; #7 mechanistic vs pure-NN |

### Priority (optional, one)

Tier reflects expected cluster EV per [`docs/cluster_roadmap.md`](cluster_roadmap.md). Apply only to issues that compete for compute time or define the critical path.

| Label | Use for |
|---|---|
| `tier-1` | Highest cluster EV; do first when capacity opens. |
| `tier-2` | Secondary cluster EV; deferred until tier-1 is unblocked. |

### Status (optional, one or more)

| Label | Use for |
|---|---|
| `gated` | Blocked on another open issue or external dependency. Name the blocker in the issue body. |
| `parallelizable` | Explicitly safe to advance in parallel with other in-flight work; not on the critical path. |

### Default GitHub labels

The repo retains the GitHub defaults (`bug`, `documentation`, `enhancement`, `good first issue`, `help wanted`, `question`, `wontfix`, `duplicate`, `invalid`). Use them when they fit *in addition to* a `type:*` label so the issue stays filterable in the project taxonomy.

## How to file a new issue

1. **Title prefix.** Short scope marker that matches the type:

    - `infra: <description>`
    - `v3.2: <description>` (or whatever the version is)
    - `paper #1: <description>`
    - `demo: <description>`
    - For research questions, prefer a question form: `Mass conservation at decadal rollouts?`

    Keep titles under ~70 characters; use the body for detail.

2. **Body.** Cover:

    - **Goal** — what we want to be true when the issue closes.
    - **Success criterion** — concrete, checkable. Numbers if possible.
    - **Dependencies** — link blockers; explicitly call out if `gated`.
    - **Context** — link to `STATUS.md`, `docs/findings/*`, prior PRs, or external papers as relevant.

3. **Labels.** At minimum one `type:*`. Add tier and status if appropriate. Don't stack labels for the sake of it — every label should change how someone triaging the issue would treat it.

4. **Milestone / project board.** If a project board exists for the current cycle (e.g., paper #1, v3.2 cluster), link the issue.

## How to triage an incoming issue

When something lands without labels:

1. Read the issue. If it's not clear what the goal or success criterion is, comment asking for clarification before labeling.
2. Apply exactly one `type:*` label.
3. If the issue is on the cluster critical path, add `tier-1` or `tier-2` per the cluster roadmap.
4. If it depends on something open, add `gated` and link the blocker in a comment.
5. If two issues are about the same thing, close the duplicate with a back-link rather than merging text.

## Cross-references

- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — branch naming, commit / PR conventions, merge policy.
- [`docs/cluster_roadmap.md`](cluster_roadmap.md) — tier-1 / tier-2 EV ranking and decision tree.
- [`STATUS.md`](../STATUS.md) — live state of model + sweep results.
- [`docs/findings/v3.1_closeout.md`](findings/v3.1_closeout.md) — paper-prep technical writeup.

## Current label snapshot

State as of 2026-05-21. Maintained manually; re-sync when issues open/close.

| Issue | Title | Labels |
|---|---|---|
| #6 | Mechanistic vs pure-NN extrapolation under climate-perturbation forcing | `type:research-question` |
| #7 | Mass conservation in the differentiable Darwin setup at decadal rollouts | `type:research-question` |
| #84 | infra: MIT ORCD Engaging onboarding + first SLURM job (gates AICR) | `type:infra`, `tier-1` |
| #85 | v3.2: time-resolved fitting on cluster (Tier 1, highest-EV vs 5/6 ceiling) | `type:code`, `tier-1`, `gated` (on #84) |
| #86 | v3.2: box-model extension toward Darwin 3 (Tier 1, zooplankton + DOM) | `type:code`, `tier-1`, `gated` (on #84) |
| #87 | paper #1: proof-of-concept manuscript draft (writeable from v3.1 results) | `type:paper`, `parallelizable` |
| #88 | demo: restore Colab badge when repo goes public | `type:demo` |
