# How often our primary test fires on nothing: a sham-split calibration

**Date:** 2026-08-12 · **Cost: ZERO compute** — resampling of artifacts already on disk ·
**Script:** `scripts/analysis/sham_split_false_positive_rate.py`

## The question a referee will ask and we could not answer

Every evidentiary move in the manuscript is an arm-vs-arm count comparison at n=50 — flagship 25/50
vs global-scalar 0/50, anchor-on vs anchor-off, the width arms, the epoch arms. CLAUDE.md's
three-check rule exists precisely because two such effects have already died on fresh submissions
(the per-parameter effect went 45/50 vs 34/50 → **38/50 vs 38/50** in a later job).

But nothing measured the **false-positive rate of the comparison battery itself**. *"How often does
your primary test fire on nothing, given you scan parameters × poolers × bands?"* had no answer.

## Why this needed no GPU

A sham pair is two arms differing by nothing except which seeds they drew. Any n=100 arm on disk
contains an unlimited supply: split its 100 seeds into two disjoint halves of 50 at random. Under
the null the halves are exchangeable **by construction**, so every "significant" difference is a
false positive.

This is also why the originally proposed 800-fit B200 sham experiment was cancelled — an
adversarial screen showed its pre-registered outcomes were mathematically unreachable (below) and
that the study was already free.

## The analytic reference, computed rather than assumed

Exact type-I error of two-sided Fisher at 50 vs 50, by full enumeration over both binomials:

| underlying rate p | 0.02 | 0.05 | 0.10 | 0.20 | 0.30 | 0.40 | 0.50 |
|---|---|---|---|---|---|---|---|
| type-I | 0.0004 | 0.0072 | 0.0179 | 0.0282 | 0.0307 | 0.0321 | **0.0352** |

**The test's true size never exceeds 0.0352 at a nominal 0.05.** It is conservative by
construction, because the count is discrete. Firing *near* 0.05 would be the anomaly; this also
means any pre-registered rule expecting an observed FPR of ~0.05 is unreachable.

## Measured, 2,000 sham splits per arm

Scanning **6 parameters × 3 bands (0.20 / 0.30 / 0.40) = 18 cells** per split:

| arm | per-cell FPR | Wilson 95% | P(≥1 of 18 cells significant) | Wilson 95% |
|---|---|---|---|---|
| `w16e2k` (n=100, job 258713) | **0.0173** | [0.0160, 0.0187] | **0.2425** | [0.2242, 0.2618] |
| `w39e2k` (n=100) | **0.0114** | [0.0104, 0.0126] | **0.1705** | [0.1547, 0.1876] |

Per-parameter false-positive rate:

| | alpfe | **scav_rat** | R_PICPOC | diatomgraz | Smallgrow | Biggrow |
|---|---|---|---|---|---|---|
| `w16e2k` | 0.0098 | **0.0263** | 0.0145 | 0.0080 | 0.0198 | 0.0252 |
| `w39e2k` | 0.0042 | **0.0325** | 0.0040 | 0.0000 | 0.0163 | 0.0115 |

## What this establishes

**1. The per-comparison test is conservative, not inflated.** Observed per-cell FPR of 0.011–0.017
sits below both the nominal 0.05 and the analytic ceiling of 0.0352. A single *pre-registered*
comparison at P < 0.05 is trustworthy — arguably more so than nominal.

**2. But scanning is expensive, and now quantified.** On a pair of arms that differ by **nothing**,
at least one of 18 cells comes back "significant" **17–24% of the time**. So a lone significant
cell discovered by looking across parameters and bands is roughly a 1-in-5 coin flip, not evidence.
This is the measured justification for the pre-registration discipline the repo already practises,
and it converts "we pre-register because it is good hygiene" into "we pre-register because the scan
rate is 0.24".

**3. `scav_rat` is the noisiest parameter under the null** (0.0263 and 0.0325, highest in both
arms) — 2–8× `alpfe`'s rate. The binding leg of the trio is also the one most likely to produce a
spurious difference, which is an independent reason to hold it to the geometric pooler and a
pre-registered band rather than a scanned one.

## Honest limits

1. **The scan here is 6 parameters × 3 bands only. Poolers were NOT varied** — all cells use the
   same per-AOI offset field. Real scans in this project also cross three collapses, so
   **0.17–0.24 is a lower bound** on the true scan rate, not an estimate of it.
2. Both arms are 3-AOI, 2000-epoch configurations. Single-AOI configs may differ.
3. The two halves of a split share a submission, a build and a node, so this measures the
   *seed-level* null. A cross-submission sham would additionally absorb job-to-job variation and
   would likely be worse, not better.
4. 2,000 splits gives a Wilson half-width of ~0.02 on the per-split rate — adequate for the
   qualitative claim, not for a third significant figure.

## Consequence for the write-up

State the per-cell FPR and the scan rate in the methods, and mark every headline comparison as
either **pre-registered** (and therefore reading against the 0.011–0.017 calibration) or
**discovered by scanning** (and therefore against ~0.24). This closes issue #121's calibration gap
with a measured number rather than an assumption.
