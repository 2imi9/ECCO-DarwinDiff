# ECCO-DarwinDiff work log

Reverse-chronological record of what was done each session, with the commits each session produced. Newest at the top.

---

## 2026-05-02 — Identifiability work + Darwin 3 audit + Thursday call prep

**What was done**

- Added 4-parameter closed-loop NPZ system (μ, m_lin, m_quad, r_remin) with mass-conservation test pattern (the new validation pattern that earlier tests did not provide).
- Diagnosed flow-rate degeneracy in steady-state-only 4-parameter recovery (μ over-predicted ~9× with closed-loop r_remin). Fixed initial-bias issue and lowered r_remin true profile, then identified residual degeneracy as a real scientific limit, not a code bug.
- Built notebook 4 with steady-state vs trajectory observation comparison. Confirmed time-resolved observations dramatically improve μ recovery (79 % → 11 %) but only partially help m_lin / r_remin and barely help m_quad. r_remin retains a ~88 % residual partial degeneracy with the mortality terms because of multiplicative coupling.
- Audited Darwin 3 (v06) parameter inventory by reading `data.darwin` (267 lines) and `data.traits` (93 lines) in full. **100 distinct tunable parameter names**, **657 individual values** when arrays are expanded.
- Tightened Darwin 1 inventory: hardcoded per-phyto identity traits exact count is **35** (7 trait arrays × 5 phyto types), not "~35". Replaced earlier estimates with exact counts throughout.
- Added Appendices A, B, C to the parameter inventory listing every parameter name explicitly across both Darwin 1 and Darwin 3.
- Drafted the Thursday May 7 follow-up email + ORCD pitch + the `findings_2026_05_02.md` snapshot.

**Headline finding**

Identifiability is per-parameter and per-observation-type. The right scientific framing for the call is *not* "the method scales to many parameters trivially," it is "we can quantify which parameters are identifiable from which observation regimes."

**Commits on origin/main**

- `9c91350` Add findings snapshot 2026-05-02
- `c679398` Add 4-param closed-loop NPZ + notebook 4 (identifiability finding)
- `b20f80f` Add multi-parameter recovery: notebook 3 + test (mu 6.1 %, mortality 8.6 %)
- `296b6c0` Add appendices A/B/C with every parameter name explicitly listed
- `0f9f057` Replace Darwin 3 ~101 with exact 100 tunable names; exact 657 individual values
- `6795358` Fix Darwin 1 ~35 to exact 35; add verified Darwin 3 audit
- `1afe422` Add verified ECCO-Darwin parameter inventory

---

## 2026-05-01 — Notebooks 1 and 2 + parameter inventory

**What was done**

- Set up cu128 PyTorch source in `pyproject.toml` so the RTX 5090 (Blackwell, sm_120) is the default target via `uv sync`.
- Wrote and ran notebook 1 (single-tracer 1D toy reaction-diffusion). λ(z) recovery at 2.33 % relative RMSE; 3 tests passing.
- Wrote and ran notebook 2 (coupled nutrient + phytoplankton). μ(z) recovery at 11.5 %; partial-identifiability gap visible (N fit 1.6 %, P fit 10.3 %).
- Created the verified parameter inventory doc (`docs/ecco_darwin_parameter_inventory.md`) for Darwin 1, working from the Carroll 2020 build in `v04/llc270_JAMES_paper`. First pass at 103 tunable + ~estimated counts.

**Commits on origin/main**

- `d8ab937` Add coupled two-tracer (NPZ) prototype + notebook 2 demo
- `b75a840` Add executed recovery demo notebook
- `f9280c9` Add micro prototype: 1D toy reaction-diffusion + recovery test

---

## 2026-04-30 — Doc refinement + Lauderdale email reply prep

**What was done**

- Refined the README plan section: TBD region/parameters, added compute line, renamed scope heading.
- Stage-based plan adopted; attribution moved to "ECCO-DarwinDiff contributors"; premature self-citation dropped.
- Added Savelli et al. 2026 (GMD) and Catão et al. 2025 (TUPANN, arXiv) references with verified URLs.
- Method lineage links inlined; data/README trimmed; tightened bibliography across the board.

**Commits on origin/main**

- `1baf5b1` Plan section: TBD region/params, add compute, rename heading
- `b7ac63f` Stage-based plan; contributor-collective attribution; drop premature self-citation
- `edb09fe` Refine docs: Savelli + Catão refs, Method lineage links, data/README trim

---

## 2026-04-29 — Initial scaffolding

**What was done**

- Created repo: README, MIT LICENSE, .gitignore, pyproject.toml, src/darwindiff/ + tests/ + data/ + notebooks/ + references/ layout.
- First push to `git@github.com:2imi9/ECCO-DarwinDiff.git` (later switched to HTTPS for credential-manager auth).
- Bibliography cleanup: replaced confabulated Kochkov DOI with verified arXiv (2311.07222) provided by user; trimmed BINN entry to brief-faithful; dropped the speculative uv link.
- Repo flipped from public to private during this session; Jonathan Lauderdale (`@seamanticscience`) added as collaborator.

**Commits on origin/main**

- `28e3666` Fix bibliography: verified Kochkov arXiv, brief-faithful BINN, drop uv link
- `820a907` Initial scaffolding: README, MIT license, pyproject, dir layout

---

## How to add a new entry

When adding a session, copy this template at the top (under the title and above the most recent existing entry):

```
## YYYY-MM-DD — short headline of what was done

**What was done**

- bullet
- bullet

**Commits on origin/main**

- `hash` short commit message
```

Keep entries terse but specific. Cross-reference relevant files with backticks. Note any meaningful scientific findings, even (especially) when they are negative.
