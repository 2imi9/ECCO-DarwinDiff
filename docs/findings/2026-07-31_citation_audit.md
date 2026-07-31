# Citation audit: every DOI in the committed documentation, resolved against Crossref

**Date:** 2026-07-31 · **Scope:** 130 DOI citations (124 unique) scraped from `docs/**/*.md`, each
passed to the verifier **together with the sentence that cites it**, so a mismatch is detectable
rather than just a dead link · **Method:** Crossref REST as the authority, with `doi.org`, arXiv and
dataset landing pages as fallbacks, in 10 parallel batches ·
**Verdict: 129 of 130 clean. One mismatch, and it is the one project memory already flagged.**

## Headline

| verdict | count |
|---|---|
| RESOLVES_MATCHES | **129** |
| RESOLVES_MISMATCH | **1** |
| DEAD | 0 |
| SUSPECT_FABRICATED | 0 |

**There is no fabrication problem in this repo.** Every DOI resolves. That is worth stating
positively, because it was the thing most worth ruling out.

## The one mismatch

| | |
|---|---|
| DOI | `10.1029/2005PA001258` |
| claimed as | "Parekh et al. **2006** (Paleoceanography) — the iron-cycle model underlying Darwin's routines" |
| **actually is** | **"Physical and biological regulation of the soft tissue carbon pump"**, Parekh, Follows, Dutkiewicz & Ito (2006), *Paleoceanography* |
| why it slipped through | right first author, adjacent year, plausible journal, and the DOI resolves. Every surface check passes. Only reading the title catches it. |

The correct iron-cycle reference is **Parekh, Follows & Boyle 2005**, `10.1029/2004GB002280`, which
this audit verified independently as correct.

### Only one of the two citing sites was a defect

- `docs/findings/2026-07-07_jon_schultz_meeting_capture.md:69` asserted the DOI **is** the
  iron-cycle basis for Darwin. False. **Fixed 2026-07-31**: the iron attribution now belongs to the
  2005 GBC paper alone, and the 2006 paper is listed separately as what it actually is.
- `docs/research_notes/2026-07-20_external_validation_iron_residence_alpfe.md:185` cites the DOI
  *precisely in order to record that it is wrong*, and already names the correct replacement.
  **Left untouched.** Editing it would delete the repo's own memory of the error.

## The finding that matters more than the count

**Writing a finding down does not repair the document that carries the error.**

This DOI was identified as wrong on 2026-07-20, written into a research note, and stored in project
memory. Eleven days later the bad citation was still sitting in the findings doc, unchanged. The
knowledge propagated into the places we record knowledge and not into the place that was wrong.

That is a general failure mode of a findings-based record, and it is the same shape as the four
re-derivations that prompted `docs/research_map.md`: **an index of what we know is not the same as
the documents being correct.** Both need a mechanical link, not a habit.

## One guard that would have caught it on the day

A CI check that, for every DOI in `docs/**/*.md`, fetches the Crossref record and fails when the
**first-author surname or publication year** in that record does not appear within a short window of
text around the citation.

In this case the document says "2006" beside a DOI whose Crossref record says 2006 but whose title
is about the soft-tissue pump, so a year check alone would not have caught it; an **author + title
keyword** check would. Pair it with an allowlist so
`2026-07-20_external_validation_iron_residence_alpfe.md:185` can keep citing the bad DOI
deliberately without failing the build.

This is not implemented. It is recorded here as the concrete next step, not as something done.

## A prior of mine that was wrong, recorded because it was

Before the audit ran I flagged `10.1029/2026GL123123` as a probable fabrication on the grounds that
the sequential `123123` tail looks synthetic. **It is real**: "Neural-BGC: An Observation-Driven
Emulator for Hybrid Physical-Biogeochemical Modeling", Ouala & Lachkar, *GRL* 2026, which matches
what project memory already records about that paper. Verified directly against Crossref after the
audit disagreed with me.

Pattern-matching on the shape of an identifier is not evidence. The audit was right and the prior
was wrong.
