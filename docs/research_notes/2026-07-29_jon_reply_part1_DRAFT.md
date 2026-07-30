# Draft reply to Jon Lauderdale, part 1 of 2 — NOT SENT

**Status: draft only. Lucas sends this, not the agent.**

Part 1 covers everything that does not improve when tonight's array lands. Part 2 (observations
only, at n=50, with the initial-condition dependency actually closed) goes tomorrow.

Why split: the earlier full draft asked Jon to arbitrate whether observations-only should be the
headline, but the `obsonly_mld_litic` arm running tonight answers the initial-condition half of that
question ourselves, and `obsonly_mld` takes diatomgraz from n=10 to n=50. Three of that draft's
weakest sentences are hours from being replaceable with measured numbers. Asking him to weigh in on
stale premises would cost a correction email afterwards.

---

**Subject:** Rain ratio precedence: data.traits wins, and val_R_PICPOC is inert

Hi Jon,

Short answer to your question: the model loads the `data.traits` value, **0.0418860**, and the
`data.darwin` one is never used.

The three values you are seeing are:

- **0.04245** in `data.darwin` line 53, under `&DARWIN_RANDOM_PARAMS` as `val_R_PICPOC`. Inert.
- **0.0418860** in `data.traits` line 92, under `&DARWIN_TRAITS`. This is what runs.
- **0.0** in the same line, for the five non-calcifying plankton types.

The array reads `R_PICPOC = 0.0, 2*4.1886E-2, 4*0.0`, so types 2 and 3 (the calcifiers) carry
0.0418860 and the rest carry zero. That is where the third number comes from. It is the zero on the
non-calcifiers, not a separate namelist entry.

On precedence, in `darwin_init_fixed.F`: `DARWIN_GENERATE_RANDOM` runs at line 357 and fills the
array from `val_R_PICPOC`, then `DARWIN_READ_TRAITS` runs last at line 382 and overwrites it. The
proof this is live rather than just what the source implies is that the two files already disagree,
and the loaded number is 0.0418860. So editing `val_R_PICPOC` in `data.darwin` does nothing. We
checked against the cloned v05 config and the pinned darwin3 source, 24885b71.

Two things fell out that you may want:

- **`alpfe` and `scav_rat` are the opposite case.** They are read by `darwin_read_params.F` and
  appear in neither the traits reader nor the generator, so editing those in `data.darwin` does
  work. `diatomgraz` lives in `PALAT` and the growth pair in `PCMAX`, both in `data.traits`.
- **Carroll's published `R_PICPOC` is 0.04245, but v05 integrates 0.0418860.** About 1.4 percent.
  Far inside our tolerance so it changes no result, but our recovery target and the model's running
  value are not quite the same number.

One caveat. This is a source precedence argument plus the file disagreement. We have not grepped the
namelist echo out of `STDOUT.0000` on a real run. We have a script that does it in one command if
you want it, or if you point us at your input directory we can confirm it there.

**On dissolution.** Your point changed how we read one of our own negatives, in a good way. We
tested whether Omega drives the calcite ratio and found nothing. But our test was against the
surface production ratio, not against dissolution. If Omega mainly governs dissolution, and shallow
dissolution above the horizon is grazing mediated rather than saturation driven, then our null is
what you would expect rather than a data problem. Related, and you may already know it: v05 has no
`disscSelect` switch at all. The Omega dependent modes are a later darwin3 addition, so v05
dissolves calcite at a constant rate by construction. Our own box does the same between 50 and
1000 m. **If you have the actual `Kdissc` that v05 runs at, that would help**, since our default
looks roughly an order of magnitude fast.

**On the rain ratio varying regionally.** We agree, and the independent data supports it. The
Daniels CP:PP production ratio puts the equatorial Pacific around 1.6 times the global mean, and
Sarmiento 2002 spans 20 to 30 times regionally. One thing we will not claim, because it looks like
support and is not: in our learner a single global scalar recovers the ratio in 0 of 50 seeds while
a per cell field recovers it in 50 of 50. That is a fact about our estimator needing spatial
structure, not a measurement that the true ratio is regional. The Daniels number is the real
evidence.

**One retraction we owe you.** A while back we tested a particulate to dissolved iron ratio as a
route to the scavenging rate. It looked like a clean win and it did not survive checking, so we
retracted it, and I do not think we ever told you. The ratio reduces to the scavenging rate times
POC over the sinking rate, so dissolved iron cancels exactly. On the realism question, in GEOTRACES
IDP2025 surface data only 76 samples worldwide carry both total particulate and dissolved iron under
strict co-location, 4 of them in our equatorial Pacific box, and where both exist the ratio spans
about 2.6 orders of magnitude.

**One ask on chlorophyll.** All the chlorophyll in our loss is Darwin's own output rather than
satellite. We have MODIS chlorophyll compared against v05, but it is bulk, not per class, so it
cannot separate the two growth rates on its own. **If you know of a size fractionated or per class
chlorophyll product for the 2003 to 2018 era, that would help us more than anything else here.**

I will follow up tomorrow on dropping the Darwin output. We have that configuration running at 50
seeds right now, including a version that also drops Darwin's initial conditions, so I would rather
send you measured numbers than my current guess.

Thanks again. The precedence answer alone saved us a wasted perturbation experiment.

Best,
Lucas

---

## Checklist before sending

- [ ] Confirm the 76 / 4 GEOTRACES co-location counts are the strict same-station-same-sample-index
      match (they are a floor on co-location, not a count of ocean locations).
- [ ] Do not attach the per-cell versus global-scalar contrast as regional-variability evidence.
- [ ] Part 2 goes only after `verify_run` exit 0 on the obs-only arms and grading against
      `prior_mld_n50` / `prior_ctrl_n50`.
