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

Jon removes the physical objection to widening. The decisive experiment is cheap:
**a same-job control pair** — bounds (0.05, 1.0) vs (0.05, 2.0), otherwise the flagship config
(n=50, width 16, 2000 epochs), graded per-AOI ≥2-of-3 under all three poolers, `verify_run`
exit 0. Outcomes: alpfe stays in [0.557, 1.300] unclamped → the guardrail relaxes and alpfe
becomes reportable; it runs past → the "rails to its bound" caveat becomes a finding about the
soluble-iron flux uncertainty, which is itself worth reporting (and matches his ">1 would not
surprise me"). Implementation caveat: override bounds per-run; do not edit the registry default
(prior runs index the registry, and cross-job comparability rules still apply — the control
must ride in the same submission).

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
2. **alpfe widened-bound control pair** — the one candidate array of the closeout window
   (tracker issue filed; see below). If the no-new-arrays guardrail is held strictly instead,
   pre-register it for fall.
3. Fold answers 1–3 into the write-up's provenance and limitations sections.
4. Fall backlog: NP thorium section as standalone constraint; GEOTRACES IDP paired-station
   availability check.
5. Update the research map corpus with this round in the same commit as this finding
   (mind issue #227: claim ids are positional).
