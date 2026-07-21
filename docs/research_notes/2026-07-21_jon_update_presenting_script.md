# Presenting script — DarwinDiff update for Jon (internal, informal)

A talk-track for the 6-slide deck (`DarwinDiff_Jon_update_2026-07-21.pptx`). Spoken register,
first person, honest hedges built in. ~10–12 min if you walk all six; the starred lines are the
ones to hit if you're short on time. Backup numbers + anticipated Q&A at the bottom.

---

## Slide 1 — Title / framing (~30 s)

> This is an internal update on the parameter-identifiability work — no slides being sent anywhere,
> just where things stand. The one-line story: ★ **the iron degeneracy we've been fighting isn't a
> flaw in our method — it's the same degeneracy the whole ocean-iron-modelling field lives with.**
> Everything here is a consistency study against your published Carroll values plus an external
> grounding in the literature. Nothing is a real-data discovery claim, and I've flagged the open
> questions as open.

## Slide 2 — FeMIP headline (~2 min) ★ the core

> Here's the heart of it. In a single-box steady state, dissolved-iron concentration constrains the
> **ratio** of source to scavenging — but not the two individually. Residence time is a free
> direction. I wanted to know whether that's just our box or something real, so I checked it against
> **Tagliabue's 2016 FeMIP intercomparison, Table 2 — all 13 models.**
>
> Look at the bars. Concentration — the thing everyone actually measures — is agreed to about **2×**.
> Residence time roams **169×**. And the identity **τ = inventory / input** reproduces every model's
> residence number exactly, so that 169× decomposes cleanly as **~130× from the input flux × ~1.3×
> from inventory.** It's *one* degeneracy, driven by the **sedimentary iron source**, which spans
> zero to 194 gigamol a year across models — all of them landing near 0.5 nM by compensating with
> scavenging.
>
> Somes 2021 did the controlled version — varied the source about 5× and retuned scavenging to hold
> concentration — and it lands right on our prediction: **τ ×4.8.**
>
> ★ The contribution isn't discovering the degeneracy — the field *measures* it. It's **naming it as
> a formal identifiability / sloppiness problem**, which as far as I could find hasn't been done for
> the iron cycle.

*Honesty line (say it):* "I should flag — Tagliabue's full text was paywalled, so this rests on the
Table 2 numbers plus the internal check that τ = inventory/input reproduces the published residence
column for all 13 models. It's checkable, but it's not the full paper."

## Slide 3 — What's identifiable (~2 min) ★

> So what *can* we identify. The cleanest quantitative result: ★ **the trio alpfe / scav_rat /
> R_PICPOC holds 7 of 10 seeds with a per-cell network, and 0 of 10 with a single global vector.**
> Per-cell prediction is load-bearing.
>
> But I want to be precise, because the three aren't equal:
> - **alpfe** recovers both ways — a gradient-free Nelder-Mead reaches it too — so it's
>   method-independent, but near-saturated: it doesn't discriminate much.
> - **scav_rat** is the one actually driving the "38 of 40" joint number — but it recovers only
>   *in-band*, CV about 43%. It is **not point-identified.** I don't want to oversell that one.
> - **R_PICPOC** is the most strongly identified, 10/10, lands around 0.05 — but that is **not a
>   validation of 0.0425.** Your own value there is under-constrained, so all I can honestly say is
>   they're consistent within a wide band.
>
> diatomgraz and the growth pair don't identify from the staged data — more on the growth pair in the
> backup if you want it, there's a nuance there.

## Slide 4 — Two sanity checks (~1.5 min)

> Two quick sanity checks. First, **alpfe** — following the reframing from last time — it's a
> near-unity scalar, **0.928, on already-soluble iron**, not a solubility. Darwin3's own docs say set
> it to 1 if the ironfile is already soluble, and v05 forces with the soluble Mahowald product. We
> fixed the "iron dust solubility" mislabel in our code.
>
> Second, the **iron residence time** we recover: about **1 to 8 days** across the three regions —
> honestly 0.8 days in the Southern Ocean up to ~13 in the equatorial Pacific — which is the order of
> the observed *upper-ocean* envelope, not the whole-ocean model range. And within the data-consistent
> band it barely roams — because fitting the real section per-cell escapes the global-mean-only
> degeneracy. That's the concrete version of Somes' point: it's the **full section profile** that
> breaks it, not the mean.

## Slide 5 — Forward plan (~2 min)

> Where the compute goes. The plan is a **structure-preserving spatial UDE** — keep Darwin's known
> physics as real equations, learn only the uncertain closures, and crucially **learn only the
> identifiable directions.**
>
> ★ But I owe you a reconciliation up front: the **July 9–10 study already fit a differentiable-
> transport UDE to real GEOTRACES iron and found scav_rat *not* identifiable** — observability-
> limited, structural, more iron data wouldn't close it. That negative stands. So the new UDE's first
> job is to do something genuinely different — **target the section profile, not the field-mean** —
> and demonstrate it actually moves that July result. **This is feasibility and design, not a
> real-data result.**
>
> Two method imports worth adopting: **Markov Neural Operators** for stable long rollout, and the
> **Ensemble-Kalman-Inversion / Calibrate-Emulate-Sample** line out of Caltech as an independent-
> inversion route we don't currently cite. Our sloppiness diagnostic is exactly the tool that says
> which parameters such an inversion could hope to constrain.

## Slide 6 — Open question (~1.5 min)

> One thing I want to **flag rather than hide.** We'd concluded the forward-emulator rollout ceiling
> is irreducible. I'm now less sure. The test that supported it only ruled out a *constant* per-cell
> bias — 0.22% of variance. But the mechanism that actually matters is a **flat 2-D FFT on a curved,
> land-masked grid**, which produces a state-dependent, boundary-concentrated error a constant
> correction can't capture — so 0.22% doesn't rule it out.
>
> I tried to test it directly this week and couldn't: the global cube is off disk, and the AOI cubes
> can't resolve coastal-versus-interior. So it's **contested, not resolved.** The clean experiment —
> a geometry-aware operator versus the flat FFT on a rebuilt global cube — is scoped, and worth doing
> before we call the ceiling fundamental.

*Close:* "That's the update. The honest headline is — we've turned the iron degeneracy from a
weakness of our method into a framing of a field-wide problem, and we've got a clean map of what's
identifiable and what isn't. Happy to go deeper on any of it."

---

## Anticipated questions (with honest answers)

- **"Are the recovery numbers seed-luck?"** No — the multi-seed sweep (partial, ~20/30) shows each
  verdict is *tight*: Smallgrow recovers 7/7 at rel-err 0.005 (range 0.001–0.009); Biggrow fails 0/7
  at 0.70 (range 0.68–0.71); scav_rat fails 0/6. Parameters robustly pass or robustly fail, not by
  luck. (Full sweep still running; I'll fold final numbers in.)
- **"Is the growth pair really unobservable?"** Careful distinction: in the *silicate-scope synthetic*
  config, **Smallgrow *is* cleanly identifiable once the Si cycle is in** (7/7, rel-err 0.005) —
  Biggrow is not. The "unobservable by construction" claim is about *real* observing systems: no
  product isolates size-class growth rate from biomass. So: identifiable-in-principle-from-perfect-
  data, but not from any real product. Both true; don't conflate them.
- **"How sloppy, quantitatively?"** Per-AOI CRLB gives ≈ 3.96 decades of sloppiness in the Eq.
  Pacific. **But** the θ* Hessian carries a zero/negative eigenvalue — θ* is a saddle, not a clean
  minimum — so I won't quote a hard decade-span until the multi-start re-optimisation lands a
  positive-definite θ*. The *qualitative* rank-structure (concentration stiff, residence-time sloppy)
  is solid; the exact number isn't yet.
- **"Why not just validate on held-out real iron?"** At box scale the 0-D homogenizes, so held-out R²
  goes negative; and going spatial didn't automatically fix it (the July negative). That's the honest
  wall the forward plan has to move, not route around.

## Appendix — what actually ran on the cluster this session (incl. nulls)

| run | job | state | result |
|---|---|---|---|
| Boundary-rail pilot | 8503326 | done | diatomgraz rails to the physical ceiling 1.0 — a bound, not a convergence failure |
| Identifiability array (± silicate) | 8510248 (×4) | timed out @8h, **partial output kept** | diatomgraz stays railed ~1.0 even with Si; run conditioning improves with Si (min-eig 0.01→3.2) |
| Iron residence time (3 AOIs) | 8510828 (×3) | done | surface τ ≈ 0.8–13 d; τ pinned within the data band except S. Ocean (weakest Fe gradient) |
| Recovery-config + per-AOI CRLB | 8512523 (×3) | done | ≈3.96 sloppiness decades (Eq. Pac); θ* has a zero eigenvalue (saddle) |
| Multi-seed variance sweep | 8512053 (×30) | ~20/30 done, running | verdicts seed-tight (see Q&A); Smallgrow 7/7, Biggrow 0/7, scav_rat 0/6 |
| Emulator geometry test | 8512977 / 8512998 | fail / done | **inconclusive** — AOI cubes non-geographic (empty interior); global cube off disk |

*All recovery numbers are synthetic self-recovery (θ* vs Carroll) unless stated; the FeMIP and
residence-time comparisons are against primary sources with the caveats noted above.*
