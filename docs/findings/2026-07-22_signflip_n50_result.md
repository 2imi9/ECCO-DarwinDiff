# Sign-flip control at n=50 — the equifinality claim survives, but "coin flip" must soften (2026-07-22)

Robustifies the manuscript's conceptual heart ("fitting ≠ identifying") — the only headline that had
never been taken past n=6 (3/6, Wilson [0.19,0.81]). Red-team "REQUIRES A RERUN" item, now done.

**Setup.** `scripts/synthetic_signflip_control.py` (extracted verbatim from the demo-notebook cells; the
n=6 smoke reproduced the archived result). A synthetic self-twin: a spatially-varying ground truth for
{alpfe, Smallgrow} vs a synthetic SST gradient, target = the box's own steady-state biomass, so there is
ZERO surrogate gap and NO absolute-magnitude anchor on alpfe — leaving its *sign* free. n=50 seeds,
300 epochs, CPU. Blessed by the script's own `--recheck` (recomputed = stored, match=True, both arms).

## Result

| loss | sign-positive | Wilson 95% CI | mean\|r_alpfe\| | verdict |
|---|---|---|---|---|
| pattern | 17/50 (0.34) | [0.224, 0.478] | 0.884 | BIASED_BUT_STILL_EQUIFINAL |
| absolute | 13/50 (0.26) | [0.159, 0.396] | 0.870 | BIASED_BUT_STILL_EQUIFINAL |

## Interpretation — the middle outcome (pre-registered), and it is the honest one

- **The n=6 "coin flip" does NOT replicate as symmetric.** Both Wilson CIs **exclude 0.5**; at n=50 the
  recovered sign is biased toward negative (~26–34% positive), not a 50/50 double-well.
- **But the equifinality claim SURVIVES.** The fit is strong (mean|r| ≈ 0.88) yet **both signs still occur
  across seeds** (17 pos / 33 neg; 13 pos / 37 neg) — so the observable genuinely does **not** determine
  alpfe's sign, which is the whole point ("fitting ≠ identifying"). The mechanism is *imperfect
  symmetry-breaking* (an init-dependent bias), not a perfect coin flip.

## Manuscript action

Soften the headline language from "coin flip / symmetric double-well" to: *"the recovered sign of alpfe is
init-dependent and not data-determined — at n=50, 13–17/50 seeds recover a positive sign (Wilson CI
excludes 0.5) despite an excellent fit (|r|≈0.88), across both loss conventions."* Report both loss kinds
(they differ: pattern 17/50 vs absolute 13/50). The claim is *strengthened* by n=50 (the CI half-width
shrinks from ~0.31 at n=6 to ~0.12, so it could have falsified equifinality and did not) — but the exact
framing must be "underdetermined-with-bias," not "coin flip."
