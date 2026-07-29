# GP15 does reach the equatorial Pacific — my earlier finding was wrong

**Date:** 2026-07-28 · **Corrects:** commit `1e4b9ac` and the coverage claim in
[PR #204](https://github.com/2imi9/ECCO-DarwinDiff/pull/204)

## What I claimed

That GP15 has **zero samples** in all three flagship AOIs, and therefore the top-ranked
iron-scavenging rate observable "cannot rescue" the basins where `scav_rat` fails. I read that as
an observing-system limit and called it a method contribution: *ranking observables without
checking spatial coverage funds the wrong cruise.*

## What is actually true

Both staged CSVs are **Leg 1 only** — Seattle → Hilo, spanning **19.68 °N to 56.06 °N**. The
filename says so: `leg1_dissolved_total_po_pb.csv`. The longitude convention is fine (−156.96 to
−152.00, correctly inside the eqpac box); it is latitude that never reaches the equator.

GP15 is a two-leg campaign. **Leg 2 (Hilo → Papeete, RR1815, Oct–Nov 2018) crosses the equator**,
and its dissolved + total ²¹⁰Po/²¹⁰Pb is published:

> BCO-DMO dataset **883797** — dissolved and total water-column ²¹⁰Po and ²¹⁰Pb, GP15 Leg 2.
> DOI **10.26008/1912/bco-dmo.883797.1**, CC-BY-4.0.

So the observable is **not unavailable at the equator**. We had not staged the leg that goes there.

## Why the error survived my own test

The test asserted `sum(counts.values()) > 0` — that GP15 covers *some* registered AOI. It does:
npac 50, npsg 25. That passed, and I read the three zeros as an observing-system fact instead of
asking why a transect documented as *Alaska → Tahiti* stopped at 19.68 °N. The filename answered it
and I did not look.

A coverage test that does not check the data against the campaign it claims to represent will
confirm whatever subset happens to be on disk.

## Consequence

| | before | after |
|---|---|---|
| Rate observable in eqpac | unavailable (observing-system limit) | **available, not staged** (fixable by download) |
| "Ranking must be joint over information and coverage" | supported by a real negative | **still true as a method point, but this is no longer its evidence** |
| Observation-design experiment | blocked for the failing basins | **unblocked, pending a download** |

The method argument survives — spatial support genuinely must enter the ranking. But it is now a
*design principle*, not something demonstrated by a measured failure, and it must not be written up
as the latter.

## Next

1. Download BCO-DMO 883797 (Leg 2) and stage beside Leg 1.
2. Re-run the coverage test — it should now report non-zero eqpac.
3. Re-run the observation-design ranking with Leg 2 included, and check whether the iron-block
   condition number collapses **in eqpac specifically**, which is the basin that stays at 6/50 even
   at 4000 epochs.

That is the experiment the earlier finding wrongly closed off.

---

## Update — Leg 2 downloaded and verified (2026-07-28)

Fetched `leg2.csv` (10.76 KB) from BCO-DMO 883797 and staged as
`data/cochran_gp15_po_pb/leg2_dissolved_total_po_pb.csv`. **The existing loader parses it with no
code changes** — identical schema to Leg 1.

| | Leg 1 (was staged) | **Leg 2 (new)** |
|---|---|---|
| latitude span | 19.68 … 56.06 °N | **−20.00 … 18.91 °N** |
| longitude | −156.96 … −152.00 | −155.26 … −151.99 |
| samples | 89 | **121** |
| **eqpac samples** | **0** | **67** |

So the anchor **does** reach the equatorial Pacific. My earlier finding is fully retracted.

### But the useful phase is the dissolved one, and this is a trap

Within eqpac:

| phase | finite samples | depths | stations |
|---|---|---|---|
| **T** (total) | **3** / 67 | 0 m only | 3 |
| **D** (dissolved) | **64** / 67 | **20 – 5340 m** | 3 |

`load_scavenging_anchor` defaults to `phase="T"`. In eqpac that yields **three surface points**. Anyone
wiring this into the loss with the default would get an almost-empty anchor in the one basin that
matters, and no error. Pinned by `test_the_dissolved_phase_is_the_usable_one`.

### Why the depth coverage is the good news

The observation-design study found that a **subsurface** measurement is nearly as powerful as a rate
observable (~1260× variance reduction) *because `alpfe` injects iron only at the surface*, so depth
resolution breaks the source/sink symmetry. Leg 2's dissolved phase gives full-depth profiles
(20–5340 m) at three eqpac stations — exactly the geometry that breaks the degeneracy.

### Honest limit

**Three stations.** That is thin spatial sampling for constraining a field, and it is the real
constraint now — not the absence of data. The informative content is the *depth structure*, not
horizontal coverage.

### Next

Re-run the observation-design ranking with Leg 2's dissolved-phase profiles included, scoring the
iron-block condition number **in eqpac specifically**. That is the experiment my earlier error
wrongly closed, and it is now unblocked with data on disk.
