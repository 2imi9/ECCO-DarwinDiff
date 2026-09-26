# Carroll's growth parameters are growth TIMES in Darwin; the box uses them as RATES

**Date:** 2026-09-26 · **Cost:** a source read, no compute · **Status:** open. The code is not
changed: correcting it changes the box's dynamics, so every downstream result would need re-running.

## What the source says

In Carroll's ECCO-Darwin v04 build (`MITgcm-contrib/ecco_darwin`, commit `ec435f9`,
`v04/llc270_JAMES_paper/code_darwin/`):

- `darwin_init_fixed.F:159-162`, inside `#ifdef GEIDER`:
  `c note these are in terms of days - converted to 1/s later`, then
  `Smallgrow = 0.66098 _d 0` and `Biggrow = 0.43148 _d 0`.
- `darwin_generate_phyto.F:191-210` sets `growthdays = Biggrow` for large types and
  `growthdays = Smallgrow` for small types.
- `darwin_generate_phyto.F:226-227`: `mu(np) = 1.0 _d 0/(growthdays*pday)`.

So in Darwin these two numbers are growth **times in days**. The maximum growth rates are their
inverses: 1/0.66098 = 1.51 d⁻¹ for small phytoplankton and 1/0.43148 = 2.32 d⁻¹ for large.

## What the box does

- `src/darwindiff/carroll6.py:166-179` registers `Smallgrow` and `Biggrow` with
  `units="d^-1"` and describes them as growth rates.
- `src/darwindiff/carroll6_5pft_2layer.py` uses them directly as the maximum specific growth rate of
  the high-light *Prochlorococcus* pool (`Smallgrow`) and the other-large-eukaryote pool (`Biggrow`).
- `src/darwindiff/carroll6_5pft.py:107-109` fixes the diatom, *Synechococcus* and low-light
  *Prochlorococcus* growth rates to the same two numbers (0.43148 and 0.66098), also as d⁻¹.

So every phytoplankton type in the box grows at the Carroll value read as a rate. Compared with
Darwin, that is 2.29 times slower for the small types (1.51 / 0.66098) and 5.37 times slower for
the large types (2.32 / 0.43148).

## What it affects, and what it does not

- The growth pair is already excluded from the recovery results (`Biggrow` unobservable by
  construction, `Smallgrow` not identifiable from time-mean observables), so no reported count for
  those two parameters changes. Their Carroll reference values in `CARROLL_VALUES` are, however, in
  the wrong unit for the box.
- The fixed rates of the other three types come from the same numbers, so the box's whole
  phytoplankton community grows more slowly than Darwin's. That changes the state every other
  parameter is fitted through. Whether it moves any reported result is **not known**: it needs a run
  with the corrected rates.
- The box's growth also carries no light limitation (`LIGHT = 1`), which partly offsets slow growth,
  so the net effect on biomass is not simply a factor of 2.3–5.4.

## Next step

Decide whether the box should use `1/Smallgrow` and `1/Biggrow` (in d⁻¹) and the matching fixed
rates. If so, re-run the flagship and its matched controls in one job and compare. Until then, treat
the box's growth rates as a known departure from Darwin, alongside the other simplifications the
README lists.
