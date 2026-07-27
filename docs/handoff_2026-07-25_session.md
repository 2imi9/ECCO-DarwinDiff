# Session handoff — 2026-07-25 (context transfer)

Read this first, then `docs/project_checkpoint_2026-07-25.md`. Nothing is committed. Branch at session
start: `2imi9/session-2026-07-21` (verify with `git branch --show-current` before any commit).

## ⚠️ FIRST ACTION IN THE NEW SESSION

`docs/paper/main.tex` has Diff-5 Parts D and E applied but **was not recompiled or stale-checked** — the
verification command was interrupted. Run this before anything else:

```bash
cd docs/paper && grep -nE "n\{=\}6|3 of 6|arbitrary sign" main.tex; pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

Expect: no stale hits, compile OK. Last known-good compile (after Diffs 1–4): **32 pages, 0 undefined
citations, 488203 bytes**.

## Hard constraints (carry these forward)

- **`docs/paper/` is LOCAL-ONLY and gitignored. NEVER `git add -f` it.** Confirmed: 0 tracked files.
- **Every main.tex core-claim edit needs the user's explicit yes first** — show exact old→new diffs, one at
  a time, and wait. This has been the working rhythm all session ("one by one").
- **The Jon email is ON HOLD.** Draft exists at `docs/findings/2026-07-25_jon_gcm_ensemble_ask_DRAFT.md`,
  never sent, To: line blank. User raised a live concern that the GCM ensemble may not be necessary
  (see "open question" below). Do not send or revive without being asked.
- House style: simple, warm, no em dashes in comms/slides, no confidence percentages. Frame `docs/paper`
  as a **write-up**, not a paper/manuscript/submission, when writing to Jon or Schultz.
- Every number must be verify_run-gated; cite the job id.

## DONE this session

**Prompt A (H-batch reframes) — complete.**
- `STATUS.md`: H1 two-component gap replaces "box tuning-exhausted"; H2 scav_rat → practical non-ID +
  refreshed counts; H3 Smallgrow softened (Biggrow kept unobservable); H5 EKI added to
  independent-validation; H6 38/40 headline qualified; ablation-ledger cross-ref de-claimed.
- `docs/results_matrix.md`: 2026-07-05 verdict retired → two-component framing; geo1 row + "Reading the
  matrix" refreshed to n=50 / 4000ep numbers.
- `docs/agu26_abstract_draft.md`: H4 both rewrites applied; banner updated to APPLIED; open item closed.
  **Char recount (excl. spaces, limit 2000): PRIMARY 1823, COMPREHENSIVE 1990.** Both pass.

**Consolidation docs (new, uncommitted).**
- `docs/ONBOARDING.md` — the "basement" cold-read onboarding doc. Every referenced file/loader/notebook
  was verified to exist.
- `docs/project_checkpoint_2026-07-25.md` — the checkpoint report (honest 6/6 verdict table, product-vs-
  research decision, defer list, confidence actions).

**main.tex diffs applied (all user-approved one by one).**
1. scav_rat → *practical*, not structural, non-ID (curved profile, all 3 AOIs). *(Used "In contrast,"
   instead of "While" to avoid a sentence fragment.)*
2. New paragraph: recoverability gap decomposes into closeable optimization (natl 20→40/50) + residual
   information (eqpac 6/50); explicitly retains 2000ep as the flagship.
3. EKI as a **third** estimator control (two→three) + **required** consistency fix: Forward-work narrowed
   to "independent inversion **of the full model** … not routed through our surrogate" (the paper had
   listed ensemble Kalman as future work while we now report running one). Cited `evensen2003` (exists);
   `iglesias2013` is NOT in the bib — offer to add it for precision.
4. One-clause seasonal hedge for Smallgrow in Forward work, marked below-standard. The ~10 "unobservable
   by construction" sites were deliberately **left untouched**.
5. Sign-flip control updated n=6 → **n=50**, five sites (A: line ~192, B: ~811, C: appendix ~1138,
   D: ~401, E: ~825).

## Diff 5 detail (most recent, verify it landed correctly)

The companion doc `docs/findings/2026-07-22_signflip_n50_result.md` **corrected an over-claim**: the n=6
"coin flip" does NOT replicate as symmetric. Verified n=50 numbers (script's own `--recheck`, blessed):

| loss | sign-positive | Wilson 95% CI | mean abs r |
|---|---|---|---|
| pattern | **17/50** (0.34) | [0.22, 0.48] | 0.884 |
| absolute | **13/50** (0.26) | [0.16, 0.40] | 0.870 |

Both CIs **exclude 0.5** → "underdetermined **with bias**", NOT "arbitrary sign"/"coin flip". Equifinality
survives and strengthens (CI half-width 0.31→0.12). Both loss variants carry **no absolute anchor** on
alpfe (checked — so the draft's "absolute anchor pins magnitude" mechanism is undisturbed). Part E fixed a
now-**backwards** sentence that apologized for a small seed budget which no longer exists.

## NEXT — the remaining ship path (continue one by one)

1. **Two red-team reruns still not folded into main.tex** (both verified, docs exist):
   - eqpac-alone basin ablation → `docs/findings/2026-07-21_eqpac_alone_ablation.md`
   - anchors-only (pattern-off) ablation → `docs/findings/2026-07-22_anchors_only_n50_verified.md`
2. **diatomgraz framing decision (a fork, needs the user's call).** The shipped draft says
   "at-chance ~4/10, data-blocked"; verified findings now show 10/10 (+MLD via bSi) and **35/50
   non-circular** (Chl+MLD, bSi off). Paper and STATUS currently disagree. Either upgrade the paper or
   keep it conservative and cite the newer result as forward work — but make them agree.
3. **Cross-link `docs/ONBOARDING.md`** from README "Documentation" and the top of STATUS.md.
4. **Reproducibility freeze:** pin ship commit in Sec:availability, `verify_run` exit 0 on flagship run
   dirs, stage Zenodo for on-acceptance DOI.
5. Then: Jon + Mick domain read + co-author consent (the real gate). AGU abstract deadline **Aug 5**.

## Open question the user raised (unresolved, do not steamroll)

"Is the GCM perturbation ensemble really necessary?" My argued position: **it is a strengthening, not a
requirement** — signs agree by construction so it only tests the *ranking*, which is near-certain; the
paper is honest without it; FeMIP/Tagliabue already supplies external support; and it costs weeks. I
recommended shipping with the caveat and treating the ensemble as a **revision response** if a referee
demands GCM validation. The user has not ruled either way. Prompt B item 1 (surrogate Jacobian through the
obs operator) was never executed — the geo1 `.pt` caches + GEOTRACES live on AICR, not locally.

## Verified facts worth not re-deriving

- **Explorer** (`ssh explorer`, key-auth, account `c.schultz`): `short` = 231 CPU nodes, 2-day limit;
  Intel build stack present; **/scratch 1.9 PB, 810 TB free**; NAS ECCO inputs return **HTTP 200**.
  Corrections to an earlier optimistic read: `/projects/schultz` is **36 TB / 8.2 TB free** (not 3.3 PB),
  and "home 111 TB" is the shared filesystem, not a personal quota. Caveat: `short` mixes 10 GbE and
  InfiniBand — confirm IB before scaling MPI to ~800 ranks.
- **AICR** is Duo-2FA gated; `ssh aicr` times out on a non-interactive probe. It holds the geo1 box data
  (`~/dd_data`) + GEOTRACES, so the surrogate Jacobian could run there in one interactive session.
- Key numbers: alpfe 49/50 · R_PICPOC 50/50 (epoch-matched anchor-off 6/50; 4/50 at 1500 ep) · scav_rat 25/50@2000ep → **41/50@4000ep**
  (natl 20→40, eqpac 6, sopac 48; job 190529) · diatomgraz 35/50 non-circular (job 190529) · trio 25/50 →
  ~41/50 vs global-scalar 0/50 · structural 3-of-4 (job 192298) · EKI job 189754 · seasonal job 189324.
