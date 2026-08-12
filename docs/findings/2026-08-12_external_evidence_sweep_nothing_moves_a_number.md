# External evidence sweep: 42 candidates, 13 verified, nothing moves a reported number

**Date:** 2026-08-12 · **Method:** 6 parallel hunt agents over disjoint threat axes, then
adversarial verification of every HIGH-severity candidate, each verifier instructed to default to
REFUTED · **Cost:** research agents only, no cluster

## Why

Before submission, the question worth asking is not "what related work exists" but **"what
published evidence would CHANGE one of our numbers or break a framing?"** The sweep was scoped that
way deliberately: hunters were given the headline claims and told that finding a paper which scoops
or refutes us is a high-value result, not a failure.

Axes: iron degeneracy · calcite/R_PICPOC · identifiability methodology · AI4Ocean datasets as
anchors · upstream ECCO-Darwin changes · competing approaches.

## Result

| | count |
|---|---|
| candidate threats raised | 42 |
| HIGH-severity, sent to adversarial verification | 13 |
| **CONFIRMED_THREAT** | **0** |
| ALREADY_KNOWN (the repo already owns it) | 5 |
| ADJACENT_ONLY (real, but does not move our numbers) | 4 |
| REFUTED (the paper is real; the inference is not) | 4 |
| dead ends recorded (useful negative information) | 34 |

**Not one verified threat survived.** Every DOI resolved — no fabricated citations — so the failures
were failures of *inference*, not of existence.

## The four REFUTED, because these are the interesting ones

**Villaverde & Massonis 2021** (`10.1371/journal.pcbi.1009032`) warns that scaling-symmetry methods
treat scaling as the only source of non-identifiability, which looked like it should soften our
"the degeneracy is breakable ONLY by a new observable". It does not: their critique targets SIM's
scaling-only *search space*, whereas our screen is a numerical Fisher-information eigendecomposition
that is not restricted to scaling symmetries.

**Camin et al. 2026** (`10.5194/os-22-791-2026`, refuted twice, on two separate claims) measures
iron-isotope fractionation for uptake (+0.11 ± 0.28 ‰) and scavenging (+0.27 ± 0.32 ‰), which
appeared to overturn the δ⁵⁶Fe "NO-GO" premise that both fractionate in the same direction. Verified
against the full text and our own box: the inference does not carry. Its second use — reversible
dissolved–particulate exchange as a missing box term — also fails, because Darwin 3's own scavenging
is `-r_scav * Fe'` with no back-flux, so the omission is **shared by box and reference model** and
is therefore not a surrogate-gap explanation.

**Han et al. 2025 + Ziveri et al. 2023** put coccolithophores at 79–90% of calcite standing stock,
which was read as making Darwin's restriction to 2 of 7 plankton types the realistic configuration
and our all-PFT flagship the unsupported one. Refuted on our own evidence: `ded32` establishes that
Darwin's two calcifiers are a large eukaryote **and Synechococcus**, not one narrow coccolithophore
group, so the observational statement does not map onto Darwin's structure the way the argument
needs.

## What the sweep is genuinely worth: citations, not corrections

The defensible novelty narrows in one place, and it is worth stating plainly. **Our gauge-symmetry
argument is not new mathematics.** `ded110`/`ded111` derive that a sink `S = r0·g_θ(x)` is
homogeneous of degree one in `r0`, so `(alpfe, r0) → (λ·alpfe, λ·r0)` is unidentifiable. That is the
published **Scaling Invariance Method** of Castro & de Boer 2020 (`10.1371/journal.pcbi.1008248`),
within the Lie-symmetry framework of Massonis & Villaverde 2020 (`10.3390/sym12030469`). The
mathematics is confirmed and no number moves — but any manuscript sentence presenting the
homogeneity argument as a contribution is refutable in one line. The correct framing is that this is
a **scaling symmetry in the sense of Castro & de Boer, instantiated in an ocean iron cycle**, and
the contribution is the domain instance plus its measured consequences.

Citations to add (all DOI-verified this session; none previously cited):

| paper | DOI | where it goes |
|---|---|---|
| Castro & de Boer 2020 | 10.1371/journal.pcbi.1008248 | at the gauge-symmetry statement — reframe as SIM |
| Massonis & Villaverde 2020 | 10.3390/sym12030469 | same place, Lie-symmetry framing |
| Villaverde & Massonis 2021 | 10.1371/journal.pcbi.1009032 | the scope caveat on scaling-only methods |
| Kern et al. 2024 | 10.5194/gmd-17-621-2024 | prior art: parameter estimation for high-dim ocean BGC |
| Kern et al. 2026 | 10.5194/gmd-19-5601-2026 | same line, BFM17/POM1D at BATS+HOTS, 42 parameters |
| Hyvernat et al. 2026 | 10.5194/bg-23-4967-2026 | related work, BGC parameter calibration |
| Ziveri et al. 2023 | — (verified) | shallow calcite dissolution, supports `abd564` |
| Toullec 2026 | 10.5194/bg-23-4361-2026 | external support for regional rain-ratio mis-specification |
| Saavedra-Pellitero et al. 2025 | — (verified) | satellite PIC exceeds coccolith PIC in the SO Pacific |
| Ridgwell 2003 | 10.1029/2003GC000512 | canonical prior questioning of the rain ratio construct |
| Jin et al. 2024 | — (verified) | physical basis for the MLD/R_PICPOC covariate interaction |

## A process signal worth recording

One verifier noted that the Monsalve-Bravo data-versus-prior decomposition it was asked to assess is
**the third independent re-derivation of `alpfe` bound geometry** — after the 2026-08-05 experiment
and my own re-proposal earlier today (issue #240, closed). Three arrivals at the same settled
question from three directions is a signal that the §1 SETTLED gate needs `alpfe`+bound to be
findable by the terms people actually search.

## The one thing the sweep did change

Not a number, but what is now *possible*: the calcite axis flagged that Marsh 2025's stated coverage
envelope was inconsistent with a zero-Southern-Ocean claim. Checking that directly gave **12
Southern Ocean cells where Daniels has 0** — see
`2026-08-12_the_southern_ocean_calcite_gap_is_the_compilation_not_the_ocean.md`. The sweep pointed;
the measurement was done here, not taken on trust.

## Honest limitations

1. Hunters ran at `sonnet`; medium/low-severity candidates were **not** adversarially verified, so
   the 24 MEDIUM rows are leads, not findings.
2. Absence of a confirmed threat is evidence of robustness against *what was searched*, across six
   axes. It is not proof that nothing exists.
3. Two axes (competing approaches, AI4Ocean datasets) return the same structural answer the repo
   already held: ocean-BGC ML remains largely unoccupied, and the AI4Ocean dataset list is six
   physical products plus PACE, whose 2024-onward era does not overlap the v05 daily era ending
   2018-12-31.
