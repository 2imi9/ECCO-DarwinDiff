# Overnight recovery sweep (Group A) — verified results (2026-07-23)

10 configs, n=10, all verify_run-gated (exit 0), flagship-full base varying one knob. Per-AOI ≥2-of-3.
Two results are significant enough to warrant n=50 confirmation (launched, job 190529) — because tonight
already taught us an n=10 "9/10" can be seed luck (the subiron arm0 regressed to 26/50).

## Full table (per-AOI ≥2/3)

| config | alpfe | scav_rat | diatomgraz | R_PICPOC | iron_pair | note |
|---|---|---|---|---|---|---|
| **epochs-4000** | 10/10 | **9/10** | 0/10 | 10/10 | **9/10** | scav_rat jumps (natl 9/10); ridge still "intact" |
| patternw-0p5 | 10/10 | 7/10 | 0/10 | 10/10 | 7/10 | |
| patternw-2 | 10/10 | 7/10 | 1/10 | 9/10 | 7/10 | |
| pocw6 | 7/10 | 6/10 | 0/10 | 10/10 | 5/10 | POC_SUB_W=6 helps scav_rat but hurts alpfe |
| **dgchl** | 9/10 | 0/10 | **7/10** | 9/10 | 0/10 | diatomgraz recovers with POSi/bSi OFF |
| pat030-mld | 10/10 | 2/10 | 0/10 | 10/10 | 2/10 | 4-of-4 shot: diatomgraz NOT rescued |
| pat050-mld | 10/10 | 1/10 | 0/10 | 10/10 | 1/10 | |
| pat010-mld | 10/10 | 1/10 | 0/10 | 9/10 | 1/10 | |
| pat030-mld-dan8 | 5/10 | 1/10 | 0/10 | 10/10 | 0/10 | heavy Daniels hurts alpfe |
| geo2surf | 10/10 | 2/10 | 1/10 | 10/10 | 2/10 | surface-iron up-weight does NOT help scav_rat |

## What this VERIFIES

1. **No robust 4-of-4 — confirmed across the pattern-MLD crossover.** MLD fails to rescue diatomgraz at
   every pattern weight tested (0.1/0.3/0.5 → diatomgraz 0/10), reproducing job 185779 (full+MLD → 0/10) and
   killing the "mild pattern keeps scav_rat while MLD rescues diatomgraz" hypothesis. The
   identifiability ≠ recoverability / no-single-4-of-4 result **stands**, now with the crossover mapped.
2. **scav_rat is pattern-assisted, and MLD hurts it.** pattern 0.5/2 → scav_rat 7/10; add MLD → 2/10; surface
   or subsurface iron up-weight → 2/10. Consistent with STATUS ("scav_rat partly pattern-assisted").
3. **Per-AOI scav_rat profiles all CURVED (jobs 189403+189870); the profile SPAN tracks recovery order,
   conditioning does not fully.** Profile span: eqpac 3.69 > natl 1.30 > sopac 1.12 — the **same ordering as
   the recovery** (sopac 49/50 > natl 19/50 > eqpac 8/50). The per-AOI 2×2 conditioning is
   **sopac 2.22 < eqpac 34.7 < natl 50.8**: it cleanly separates the well-conditioned Southern Ocean from the
   two degenerate basins, but it does **not** rank eqpac vs natl — natl is *worse*-conditioned than eqpac yet
   recovers *better* (19/50 vs 8/50). So conditioning explains the SO/degenerate split; the flatter-profile
   (span) metric is what tracks the eqpac-vs-natl recovery order. scav_rat is constrained everywhere (all
   CURVED) — practical, not structural, non-identifiability.

## Two SIGNIFICANT leads — BOTH CONFIRMED at n=50 (job 190529, VERIFIED exit 0)

### A. scav_rat is substantially OPTIMIZATION-limited — CONFIRMED. **26/50 → 41/50 at 4000 epochs.**
At 4000 epochs (vs 2000) scav_rat per-AOI holds **41/50** at n=50 (natl 40/50, up from 19/50; sopac 48/50;
eqpac stays hard at 6/50). alpfe 49/50, R_PICPOC 50/50 unchanged. The n=10 9/10 was NOT seed luck — it held.
**So scav_rat's weakness is substantially an under-optimization artifact, not a pure information wall**: more
compute (no new data) raises the weak leg from ~52% to ~82% per-AOI, mainly by tightening North-Atlantic
convergence. The equatorial Pacific (6/50) remains information-limited — even 4000 epochs cannot fix its
degeneracy (cond 35, flattest profile span 3.69). **The trio {alpfe, scav_rat, R_PICPOC} rises from 25/50
toward ~41/50 with 2× epochs.** This is the sharpest possible statement of identifiability ≠ recoverability:
the recoverability gap has a large, closeable optimization component AND a residual information component
(eqpac). Median scav_rat 4.30e-7 vs Carroll 6.03e-7 (still Cal-grade; the gain is variance-tightening — more
seeds cross threshold in natl).

### B. diatomgraz has a NON-CIRCULAR handle — CONFIRMED. **35/50 from Chl+MLD with bSi OFF.**
The dgchl config (`POSI_W=0, POSI_DARWIN_W=0` — no biogenic-silica target, the M11-circular channel) recovers
diatomgraz **35/50** at n=50 (eqpac 45/50, natl 35/50, sopac 28/50; median 0.788 vs Carroll 0.83, within 5%),
constrained through the **chlorophyll pattern + MLD** (diatoms are a Chl-bearing PFT). The n=10 7/10 held.
**So diatomgraz does NOT require the bSi biomass tautology — it has a non-circular observational handle.** This
is the direct answer to reviewer M11. Framing caveat (load-bearing): the Chl target is Darwin's own Chl1-5 (a
consistency check vs Carroll, not independent real data), so the honest claim is "recoverable from a non-bSi
observable," not "recovered from independent real data." Still a real strengthening: it moves diatomgraz from
"only via a circular diagnostic" to "via a non-circular (if model-internal) observable." (scav_rat is 3/50
here — this config zeros the pattern term it needs, so it is a diatomgraz-isolating config, not a 4-of-4.)

## Verdict on "significant improvement, verified" for Group A
- Verified now: no-4-of-4 stands; scav_rat pattern-assisted; profile/conditioning/recovery gradient coherent.
- Pending n=50 (the two above): either could be a genuine positive (scav_rat optimization-limited; diatomgraz
  non-circular). Deliberately NOT claimed until the n=50 grade lands — the honest discipline that caught the
  arm0 seed-luck tonight. **UPDATE: both CONFIRMED at n=50 (§ above); see also the 4-of-4 resolution below.**

## The 4-of-4 retry — RESOLVED: the trade-off is STRUCTURAL, not an optimization limit (job 192298, VERIFIED)

Since scav_rat responded to more optimization (41/50 at 4000ep), the natural question was whether
full-loss + MLD at 4000 epochs would *also* rescue diatomgraz — the first robust 4-of-4. Answer: **no.**

| config (4000ep) | alpfe | scav_rat | diatomgraz | R_PICPOC |
|---|---|---|---|---|
| full + MLD | 4/10 | 6/10 | **0/10** | 10/10 |
| pattern=0.3 + MLD | 10/10 | 1/10 | **0/10** | 9/10 |

diatomgraz stays **0/10** in both arms even at 4000 epochs — so its MLD-rescue failing when the pattern term
is present is **NOT under-optimization; it is a genuine loss-landscape conflict.** Worse, adding MLD to the
full-loss 4000ep run *degrades* alpfe (49/50 → 4/10) and scav_rat (41/50 → 6/10): the MLD channel actively
disrupts the iron params. **Conclusion: {scav_rat (needs Darwin-pattern), diatomgraz (needs MLD)} is a real,
structural trade-off** — flagship-full+4000ep holds {alpfe, scav_rat, R_PICPOC} (~41/50 trio); the dgchl
lineage holds {diatomgraz, alpfe, R_PICPOC}; no config holds all four, and 2× optimization does not bridge it.
This closes the 4-of-4 question with a clean, verified identifiability-limit result rather than an open "maybe."

Note: this run required `TORCH_COMPILE_BATCHED=0` — the MLD 2-channel graph at 4000 epochs deadlocks
`torch.compile` at the first step (reproduced on 4 nodes; see [[reference_aicr_overnight_orchestration]]).
