# DarwinDiff Claude Code Skills

Project-scoped skill bundle for ECCO-Darwin / DarwinDiff research. Loaded
automatically by Claude Code when this worktree is the active project.

## Bundle contents

### ECCO-Darwin / DarwinDiff skills (project-original)

- **darwin_v05_loader** — Load Darwin v05 outputs, define AOIs, build IC +
  target caches. Foundational for any ECCO-Darwin researcher. Wraps
  `src/darwindiff/ecco_darwin_loader.py`.
- **darwin_dinn_sweep_orchestrator** — BASE_ENV + per-arc + per-config
  OUTPUT_DIR pattern with STOP sentinel, resume logic, per-arc aggregation,
  Wave chaining. Distills the v3.0 overnight pattern. Wraps
  `scripts/overnight_v3.0_basinC_refine_v2.py` and friends.
- **paper_reviewer_panel** — Adversarial reviewer-panel red-team for the
  DarwinDiff manuscript (or any inverse / parameter-recovery paper): eight
  domain-adapted reviewer lenses + a grounding contract (every objection cites
  a line; recompute, don't invent) + a completeness critic + an adversarial
  verify pass, returning objections ranked by how hard they are to rebut.
  Single agent for a quick ranked pass; run as a Workflow fan-out for an
  exhaustive pre-submission review.

### Literature search (vendored from google-deepmind/science-skills, Apache 2.0)

- **literature_search_arxiv** — arXiv (Xu BINN, Liu attention layer, future
  preprints)
- **literature_search_biorxiv** — bioRxiv (Neural-BGC family, ESSOAr
  preprints)
- **literature_search_openalex** — OpenAlex (broad academic — Carroll
  Green's-functions calibration, Mick Follows papers, ocean BGC)
- **literature_search_europepmc** — EuropePMC (biomed cross-references)

Each lit-search skill ships its own `scripts/` (uv-managed Python) with
rate-limited search + paper download utilities.

## Roadmap

Full roadmap lives at `docs/research_notes/skills_future_agenda.md`
(4 tiers, 10 candidate skills). Build when the same workflow recurs
across sessions or when onboarding a new collaborator — not
speculatively. If we ever publish a sibling "ocean-skills" bundle
(analogue to GDM's science-skills), the literature search 4 +
workflow_skill_creator pattern is the template; the rest is original
work.

## Adding a new skill

1. Create directory `skills/<skill_name>/`.
2. Write `SKILL.md` with YAML frontmatter:
   ```yaml
   ---
   name: skill-name-with-hyphens
   description: >
     One paragraph. Triggers and use cases. End with "Triggers: ..." or
     "Use when ..." for activation hints.
   ---
   ```
3. (Optional) Add `scripts/` for helper CLI tools and `references/` for docs.
4. Reference existing repo modules instead of reimplementing. The skill is
   a thin "how to use this" wrapper around source already in
   `src/darwindiff/` or `scripts/`.

## Why project-scoped?

DarwinDiff skills depend on:
- The repo layout (`src/darwindiff/`, `scripts/`, `D:\runs\`)
- The Darwin v05 data on `D:\ecco_darwin_v5\`
- The DINN architecture in `src/darwindiff/networks.py`

User-scoping (`~/.claude/skills/`) would surface these in unrelated projects.
Once a skill stabilizes and generalizes (e.g. a generic
`mitgcm_pickup_loader`), promote it to user scope or a sibling open-source
bundle.

## Licensing

- Project-original skills: same license as DarwinDiff repo.
- Vendored lit-search skills: Apache 2.0 (see `SKILL_LICENSES.md` upstream
  at https://github.com/google-deepmind/science-skills).
