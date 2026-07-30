# DRAFT follow-up to Jon, 2026-07-30. NOT SENT.

Three things in the last note need revising, and two of them make the result stronger. Holding
until the Southern Ocean control (job 237913) lands, since the first item depends on it.

---

## Draft

Hi Jon,

Two corrections to what I sent earlier, and one thing that came out of chasing your rain ratio
question.

**Scavenging.** I said it does not come back. That was too flat. What the runs actually show is
that it comes back in the Southern Ocean and nowhere else. Across all three observations-only
arms the Southern Ocean leg recovers in 39 to 50 of 50 seeds, against zero of 50 for an untrained
network, while the equatorial Pacific and the subpolar North Atlantic are flat zero. The headline
number I quoted was zero because I grade on a two-of-three basin rule and one basin can never form
a majority. So the fit did learn something, in the basin where the scavenging sink is the dominant
term in the iron budget, and I was reporting a property of my grading rule as though it were a
property of the model.

I am running the control that decides whether that is real. If I fit the Southern Ocean on its own,
there is no other basin for the shared network to borrow from, so whatever the rate does there is
local. If it collapses, the leg was inherited and your degeneracy reading stands unchanged. If it
holds, then Southern Ocean data breaks the degeneracy that concentration alone cannot, which would
be worth aiming the UDE at directly. I wrote the decision rule down before starting so I am not
choosing the interpretation after seeing it. Either way I will send the number.

**The diatom caveat.** I said the result leans on a small set of informative cells rather than good
coverage. That is right for the configuration without the mixed layer depth input, and wrong for
the one I was describing. In the arm I reported, diatom palatability beats its own untrained rate
separately in each of the three basins, so it is not resting on one region. Without the mixed layer
channel it drops to one basin out of three, which is the situation I had in mind. I should have
been clearer about which run I meant. One thing to keep attached to that number either way: an
untrained network already lands inside the band for this parameter about two thirds of the time,
because of where its bounds sit, so the honest comparison is against that and not against zero.

**On the rain ratio, and this is the interesting one.** Chasing why the equatorial Pacific behaved
differently, I found the offset there is not noise. Every seed lands on the same side and the
spread is a few percent, so the fit is converging tightly to a value about one and a half times
Carroll. In the subpolar North Atlantic it converges to almost exactly Carroll.

Lining that up with community composition in the two basins that actually have calcite data, the
equatorial Pacific is about half picoplankton and carries about half again as much inflation, and
the North Atlantic is nearly all large eukaryotes and carries almost none. So the size of the
offset tracks the inverse of the local large fraction, which is what you would expect if the
anchor is pinning the ratio multiplied by the calcifying fraction rather than the ratio alone.
That is only two points so I am not claiming a law, but the sign and the size both go the right
way, and it is a second line of evidence for the same reading rather than a repeat of the first.

That makes your answer on which of the three values is live more useful than I realised. If the
calcifying set and its fraction are known from the namelists, the inflation becomes something I can
predict before fitting instead of explaining afterwards.

One more number from the same place, which may matter more than any of the above. The observed PIC
to POC ratio in my three regions is 0.0065, 0.031 and 0.72. That is a spread of about a hundred
times, against a single published value of 0.042. So a scalar rain ratio is being asked to
reproduce something that varies by two orders of magnitude between basins. I do not think that
changes the calcite work, but it does make me more cautious about reporting one recovered number
for it.

**On the forward tool, no change, and I tried to break it.** I said it beats persistence at one
step but not a seasonal autoregressive baseline. The most likely way that could have been wrong is
that three of the six tracers were being scaled in the wrong space, so I retrained with them fixed
and scored both versions in two common metric spaces. Each version looks better in the space it was
trained in, and neither beats the free baseline in either. The old number reproduces. One thing did
improve: with the fix the model stops producing negative concentrations entirely, and it is far
more repeatable between runs, so I will keep it for that reason rather than for skill.

I also chased the same question on daily data, since that was the obvious next thing. Same answer,
and it moved a lot: the daily version was off by about four in the wrong units, and fixing the
scaling recovers almost all of that, but it still loses to a per-cell autoregression. Daily
autocorrelation is around 0.995, so that baseline is very hard to beat and I do not think more
capacity changes it.

Nothing here changes the growth pair or the shallow dissolution result.

Tuesday 4 August still works for me, any time.

Take care,
Lucas

---

## Notes for me, not for the email

- Item 1 is **blocked** on job 237913 and its grader 237914. The pre-registered rule is in
  `docs/findings/2026-07-30_prereg_scavrat_southern_ocean.md`: LOCAL if k >= 25 and
  P(>=k | n=50, p) < 0.01, POOLING if not above p at P < 0.05, otherwise AMBIGUOUS and reported as
  such. Do not send before it lands; the paragraph as written promises a number.
- Item 3 rests on `2026-07-30_rpicpoc_bias_tracks_large_phyto_fraction.md`. Two anchored points.
  The email already says "not claiming a law", keep that.
- The 111x PIC:POC spread is from the target caches and is a standing-stock ratio, not a production
  ratio. Daniels is a production ratio. If Jon picks this up, that distinction has to be made
  explicitly rather than glossed.
- Do not put the R_PICPOC eqpac count (5/50) in the email. It reads as a failure and it is a band
  edge on a tight, precise estimate. The bias framing is the honest one.
