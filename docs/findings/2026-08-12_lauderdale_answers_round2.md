# Domain-expert answers, round 2 (J. Lauderdale, 2026-08-12)

**Source:** email from Jonathan Lauderdale (MIT) answering the five numbered questions from the
2026-08-05 thread (rain-ratio precedence, Black loader design, the 50-day window, the alpfe
ceiling, the North Pacific constraint, paired source/sink stations). Substance captured
faithfully; interpretation and consequences are ours. Companion to
`2026-07-29_lauderdale_answers.md` (round 1).

## 1. Rain-ratio precedence — externally CONFIRMED, second confirmation route named

> "PICPOC ratio from data.traits supersedes value in data.darwin. There may also be a file
> darwin_traits that is written out by the model with the values it uses… not sure if that is
> included in the ECCO-Darwin repo/datastore."

This was the one question flagged as unresolvable from our side, and the answer **matches the
repo's own 2026-07-30 derivation exactly** (`2026-07-30_rain_ratio_which_value_is_live.md`;
claims ded35/ded190/ded203): `DARWIN_READ_TRAITS` runs after `DARWIN_GENERATE_RANDOM` in
`darwin_init_fixed.F`, so v05 integrates **R_PICPOC = 0.0418860 from `data.traits`** and
`data.darwin`'s `val_R_PICPOC = 0.04245` is inert. The published value is ~1.4% from the live
one, inside the 5% Excellent band, so no reported number changes.

What is new: the **`darwin_traits` echo file** he names is a second, cheaper confirmation route
for **ded215** (the pending namelist-echo check — the precedence argument has never been
confirmed against a real run's own output). Action: look for `darwin_traits` in the v05
datastore / run outputs; if found, this closes ded215 without needing STDOUT.0000.

Provenance note for the write-up: the target value's derivation is now supported independently
by (a) source read-order, primary-fetched, and (b) the model's maintainer.

## 2. Black-2020 loader design (flux, not residence time) — confirmed

> "This sounds fine to me."

The loader's take-the-flux-skip-the-residence-time reasoning
(`src/darwindiff/black2020_fe_flux_loader.py` header) survives expert review unchanged.

## 3. The 50-day window — a candidate physical reading, not yet established

> "50 days seems reasonable, but I'll need to read Black more closely. Sinking particle speed is
> usually around 10 m/day = 500 m."

The window sweep (`2026-07-31_prereg_flagship_window_sweep.md`) measured that `scav_rat`
recovers only at the 50-day window (half and double both fail; dust scaling and rain ratio are
window-indifferent). Jon's scale argument offers a mechanism: at ~10 m/day, 50 days is the
transit time of a sinking particle through ~500 m — i.e. the window that lets the export signal
traverse the observed column. **Record as a hypothesis attributed to a scale match**; he has
not yet read Black closely against it. Do not promote to a claim without that check.

## 4. The alpfe ceiling at 1.0 is NOT physical — bound-widening is licensed

> "No, it's not a hard ceiling. I think there is enough uncertainty in the soluble iron flux
> that I wouldn't be surprised if values of >1 (ie the ocean wants more soluble iron input to
> satisfy surface iron concentrations). I think you were getting values of a little less than 1,
> which is also fine."

The most consequential answer. The registry box is `(0.05, 1.0)` (`carroll6.py:143`), Carroll's
0.92831 sits at log-position 0.98 of that box (abd533 — the one-sided-truncation confound), and
the standing delivery guardrail is "alpfe is a boundary diagnostic, not an accuracy number; it
rails to its bound."

**The geometry that makes this matter:** the ±40% pass band around Carroll is
[0.557, 1.300], and the 1.0 ceiling sits *inside* it. A fit that rails at the ceiling
auto-passes. So the flagship's alpfe 49/50 is partly bound-assisted, and nothing currently
distinguishes "the fit wants ≈0.93" from "the fit wants 1.4 and is clamped."

**⚠ CORRECTION (same day). My first draft of this section proposed a widened-bound control pair
as "the decisive experiment". THAT EXPERIMENT HAS ALREADY RUN** — 2026-08-05, job 276927 +
grader 276928, four arms × 50 seeds via the `DD_ALPFE_HI` lever (PR #234), recorded in
[2026-08-05_alpfe_rails_to_whatever_bound_it_is_given.md](2026-08-05_alpfe_rails_to_whatever_bound_it_is_given.md).
I filed issue #240 for it and have closed that issue. This is the §1 SETTLED failure mode, caught
before any B200 hours were spent, and it is the second time bound-geometry work has been proposed
twice.

What was already measured, and it is stronger than the pair I proposed:

| arm | upper bound | alpfe median | % of bound | per-AOI ≥2-of-3 |
|---|---|---|---|---|
| `ab_ctrl` | 1.0 | 0.9967 | 99.7% | 49/50 |
| `ab_wide` | 1.6 | 1.5940 | 99.6% | 0/50 |
| `ab_null_ctrl` | 1.0 | 0.5014 | 50.1% | 10/50 |
| `ab_null_wide` | 1.6 | 0.7865 | 49.2% | 50/50 |

The fit rails to whatever ceiling it is given and carries **no upper-side information**.

**So Jon's answer changes an interpretation, not a run — and it is the load-bearing half.** That
finding's §5 explicitly left the physics open: *"Whether 1.0 is a hard physical ceiling … is a
physics question, put to J. Lauderdale on 2026-08-05 and open. If 1.0 is physical then railing to
it is the fit correctly reporting 'at least this high, and the data cannot see further'. If it is
arbitrary then the bound is an unstated prior."*

He selected the second branch. **The alpfe upper bound is an unstated prior, now on domain-expert
authority.** Consequences, all zero-compute:

1. The permitted reading narrows further. Already permitted: "the observations say alpfe is high,
   and say so decisively against an untrained control." Now also required: the ceiling that
   statement leans on is a modelling choice, not physics, so "at least this high" cannot be
   attributed to the data reaching a physical limit.
2. `alpfe`'s place in the 4-observable denominator needs its wording checked in STATUS/README and
   the write-up. It still clears its untrained null at bound 1.0 (49/50 vs 10/50), so it is not
   demoted — but "recovered globally" must not imply a recovered *value*.
3. His ">1 would not surprise me" is independent support for the measured 1.594 at the wide bound
   being physically unremarkable rather than a divergence. That is worth one sentence in the
   limitations: the fit's preference for >1 is consistent with published soluble-iron-flux
   uncertainty.
4. No new array is licensed. The one *untested* exposure this leaves is `diatomgraz`
   (rel(upper) = 0.205, inside the 0.40 band, flagged AT RISK in that finding's §4) — and its
   value is low, because `diatomgraz` already fails the contract on prior contamination and sits
   below its own null, so a bound test would be a third independent reason rather than a new one.

## 5. North Pacific — a useful regime on its own

> "Yes, the NP is an interesting regime for iron cycling outside of the equatorial Pacific."

Licenses the NP thorium section as a standalone scavenging constraint even without equatorial
Pacific stations. Feeds the two-anchor OSSE result (ded201: +Th flux with export pinned makes
alpfe and scav_rat both individually identifiable) and the ranked observable candidates
(abd534). Fall scope.

## 6/7. Paired dissolved-Fe + thorium-export station — look in GEOTRACES

> "If there were then it would probably be in GEOTRACES. Perhaps not released in the current
> intermediate data product?"

The source-and-sink-at-the-same-station observable that would actually break the degeneracy has
one named place to look: GEOTRACES, possibly beyond the current IDP release. A data-availability
check, not an experiment. Fall scope.

## Actions

1. **Hunt the `darwin_traits` echo file** in the v05 datastore → closes ded215 (hours, local).
2. ~~alpfe widened-bound control pair~~ — **already run 2026-08-05; issue #240 closed.** Instead:
   apply the interpretive consequences above to STATUS/README/write-up wording (zero compute).
3. Fold answers 1–3 into the write-up's provenance and limitations sections.
4. Fall backlog: NP thorium section as standalone constraint; GEOTRACES IDP paired-station
   availability check.
5. Update the research map corpus with this round in the same commit as this finding
   (mind issue #227: claim ids are positional).
