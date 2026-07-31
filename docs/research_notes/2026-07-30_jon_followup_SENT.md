# Follow-up to Jon, 2026-07-30. SENT by Lucas.

**Status: sent.** Kept as the record of what was prepared and why.

**The exact text sent may differ from what is below.** Lucas sent it directly, so do not quote this
file as the wording Jon received. Treat it as the reasoning and the numbers behind the message, not
as a transcript of it.

Three things in the previous note needed revising, and two of them made the result stronger. The
Southern Ocean control landed first (jobs 238079/238080, `verify_run` exit 0), so the scavenging
paragraph carries a verified number rather than a promise.

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

I ran the control that decides whether that is real, and it holds. Fitting the Southern Ocean on its
own, with no other basin for the shared network to borrow from, scavenging still comes back in 30
of 50 seeds against zero of 50 untrained. I wrote the decision rule down before starting and I
expected the other answer, so this is the result surprising me rather than me choosing it. The two
checks I set in advance both behaved: iron solubility stayed at 50 of 50, so the fit is not broken,
and the rain ratio went to zero of 50, which it must, since the Southern Ocean has no calcite data
and there is now no other basin to inherit from. The only things in that loss are surface and
subsurface iron.

So the degeneracy is not wrong, it is not quite exact. Scavenging is about four fifths of the
surface iron sink at your values, and the rest is uptake and mixing, which do not scale with it.
The Southern Ocean is where that leftover is largest, because it is iron limited and the sink
dominates. My honest reading is that the ratio is what concentration pins everywhere, and the
Southern Ocean has just enough curvature left over to separate the two. I have not shown that is the
mechanism, only that the recovery is local.

Worth saying plainly: the other basins do still help. With all three the Southern Ocean leg is 39 to
50 of 50, alone it is 30 of 50. So there is real local information and pooling adds to it.

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

- Item 1 is **UNBLOCKED**. Jobs 238079/238080, `verify_run` exit 0 on both arms, 50/50 each.
  `scav_rat` 30/50 against untrained 0/50, P = 3.15e-24. Rule was k >= 25 and P < 0.01, both met,
  neither marginal. Controls held: `alpfe` 50/50, `R_PICPOC` 0/50.
- The first attempt (237913) gave the identical counts but **failed the gate at exit 2** because the
  config declared `DANIELS_RPICPOC_W` and `POSI_W` on a basin with zero cells for either. The re-run
  is **bitwise identical**, all six parameters, all 50 seeds, max relative difference 0.000e+00. Do
  not mention this to Jon; it is internal bookkeeping, not a result. But do not quote 237913 either.
- **Do not** claim the mechanism in the email. "Nearly flat rather than flat" is the honest framing
  and the 79.7% figure is from the shipped 2-layer box at Carroll values, not from this run. The
  separating experiment is a refit with the subsurface iron term removed, and it has not been run.
- The rain-ratio paragraph should now also carry that the live value is **0.041886**, not 0.04245,
  and that the calcifiers are types 2 and 3 which are large eukaryotes and **Synechococcus**. That
  last point is worth asking him about: a picoplankton calcifier is an unusual choice and may be a
  deliberate stand-in.
- Item 3 rests on `2026-07-30_rpicpoc_bias_tracks_large_phyto_fraction.md`. Two anchored points.
  The email already says "not claiming a law", keep that.
- The 111x PIC:POC spread is from the target caches and is a standing-stock ratio, not a production
  ratio. Daniels is a production ratio. If Jon picks this up, that distinction has to be made
  explicitly rather than glossed.
- Do not put the R_PICPOC eqpac count (5/50) in the email. It reads as a failure and it is a band
  edge on a tight, precise estimate. The bias framing is the honest one.
