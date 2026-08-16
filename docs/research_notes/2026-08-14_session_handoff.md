# Session handoff — 2026-08-14

Everything scientific is in git and in the map. This note carries only what is **not** recoverable
from the repo: live state, open decisions, and traps discovered but not yet institutionalised.

Read [docs/research_map.md](../research_map.md) §1 and §6 first, as always.

## Live state a fresh session cannot see

| thing | state |
|---|---|
| **Repo visibility** | **PRIVATE** since 2026-08-13. It was PUBLIC from 2026-04-30 with the full research trail visible (0 forks, 0 stars). |
| **Cluster `git pull`** | **BROKEN.** The AICR remote is HTTPS with no credentials, and privatising the repo killed it. Scripts must be `scp`'d until this is fixed with an SSH remote or a deploy token. This will re-open issue #218 (checkout drift) if left. |
| **Public release tree** | Built and green at `C:/ddpub/darwindiff-public` — 128 files, 703 tests passing, independently leak-scanned. **No public repo has been created or pushed.** Rebuild any time with `python scripts/build_public_release.py --out <dir>`. |
| **PR #242** | Open, unmerged, ~25 commits. |
| **`v1.0-evidence` tag** | Not yet created. |
| **Cluster queue** | Empty. Last job 358528/358529 (mvdrep) complete. |

## Decisions waiting on Lucas, not on work

1. **Public repo name.** Suggested `2imi9/darwindiff`. Nothing is published until this is chosen.
2. **Whether a curated `STATUS.md` ships publicly** — currently excluded; the README carries the
   headline table instead.
3. **Two drafted emails to Jon, unsent:**
   - [2026-08-12_jon_reply_round2_DRAFT.md](2026-08-12_jon_reply_round2_DRAFT.md) — his six answers
   - [2026-08-13_jon_reply_pavia_DRAFT.md](2026-08-13_jon_reply_pavia_DRAFT.md) — the Pavia lead,
     **carrying the Black source-vs-sink correction**. He reviewed the old (wrong) description and
     said "this sounds fine to me", so this correction is owed to him.
4. **CCAI NeurIPS workshop** (#241) — due **29 Aug AoE**. OpenReview account was recommended by
   ~15 Aug and creation can take two weeks. Gated on Jon + Cris agreeing.

## Traps found this session, in the order they will bite again

**The map mirror goes stale on any docs commit.** The `DOCUMENT` table is built from `git ls-files`
over `docs/findings/` and `docs/research_notes/`, so *adding a findings doc* changes
`research_map.json` and the navigator with no corpus edit at all. This turned CI red twice in two
days. Now guarded by `scripts/check_map_mirror_current.py`; **wire it as a pre-commit hook**:

```
printf '#!/bin/sh\nexec python scripts/check_map_mirror_current.py\n' > .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

**Nulls: architecture-matched, not loss-matched.** A null at `lr=0` never trains, so it is shared
across arms differing only in *loss weights* (verified bitwise identical). It can **not** be shared
across arms differing in width, sharing, or channel count. Getting this backwards costs either
wasted runs or an invalid comparison.

**Settled results can be unfindable.** The width/DOF dose-response was fully run at n=100 and
invisible to `settled "degrees of freedom"`, which returns the *sharing* ladder. That gap nearly
produced a fifth re-derivation — a 5-hour sweep at half the existing n. Now indexed under `trunk
width` and `hidden_dim`. **When a result is settled, index it under the words a future session will
actually search.**

**Screen before submitting.** Adversarial screening stopped three wasted runs this session: the
flagship replication (already done twice), the 800-fit sham study (outcomes mathematically
unreachable, and free on disk), and the width sweep. Each screen cost minutes.

## What changed scientifically (all in the map; pointers only)

- **`R_PICPOC`'s anchor-conditionality replicated** at n=100 — 98/100 → 50/100, P = 2.7e-16, with
  the straddle mechanism (1/100 vs 42/100 seeds, P = 5.1e-14).
- **Southern Ocean `scav_rat` replicated** on fresh seeds, 50/50 geometric, powered to fail.
- **The primary test is calibrated**: per-cell FPR 0.011–0.017 against a 0.0352 analytic ceiling,
  but a 0.17–0.24 scan rate.
- **Three architecture questions all returned "not architecture-shaped"** — coupled physical models
  (26× CRLB degradation), Laplace, and RNO.
- **The forward model is bitwise stable** across the August refactor, values and gradients.
- **Marsh 2025 gives the Southern Ocean 12 calcite cells** where Daniels has 0.

## Immediate next actions

1. Merge #242, tag `v1.0-evidence` (blocked only on CI green).
2. Wire the pre-commit hook.
3. Fix the cluster git remote.
4. Send the two emails; create the OpenReview account if CCAI is wanted.
5. Then: write. The evidence base is ahead of the manuscript, and no experiment is blocking it.
