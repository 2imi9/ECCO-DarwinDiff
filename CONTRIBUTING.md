# Contributing to ECCO-DarwinDiff

## Branch naming

All work branches use the **`2imi9/<scope>-<short-description>`** form. Examples:

- `2imi9/v3.1-doc-cleanup`
- `2imi9/v2.8-darwin-ic-poc-sub`
- `2imi9/demo-colab`
- `2imi9/fixups-pr45-54-bot-comments`

The `2imi9/` prefix is the GitHub user namespace. The scope (e.g. `v3.1`, `v2.8`, `docs`, `demo`, `fixups`) groups the change. The short description is hyphenated.

Avoid generic prefixes like `claude/`, `feature/`, or `dev/`. They lose information and produce inconsistent histories.

## Pull-request titles

Use a **scope prefix** followed by a colon and a one-line subject. Examples:

- `v3.1: c_chl40_posi15 n=20 retest closes the second 5/6 reproducibility question`
- `docs: trim README from 263 → 127 lines, drop redundancy with STATUS.md`
- `demo: Colab notebook + hero badge (synthetic recovery, ~5 min on free T4)`
- `fixups: address Greptile bot P1+P2 comments on PRs #46-#49`

The scope-prefix lets the merge history read as a project changelog without per-PR drilldown.

## Commit messages

- **No `Co-Authored-By` trailers.** Commits are attributed to the GitHub user that made them; co-author trailers add noise without value at the project scale.
- **First line is the summary** (≤ 72 chars), followed by a blank line, then a body explaining the *why* (not just the *what*).
- **Verified claims only.** When a commit contains numerical results, cross-check against the underlying JSONs / artifacts before writing the message.

## Merge strategy

Use **non-squash merges** (`gh pr merge --merge`). Per-commit history is preserved on `main`, which is useful for debugging multi-commit PRs and for the project's "what shipped when" narrative. Squash merges collapse this signal.

## Documentation discipline

For substantive changes:

- Update [STATUS.md](STATUS.md) with verified live state.
- Update [README.md](README.md) if the headline status, project arc, or quick-links bar changes.
- Add a per-version technical writeup to `docs/findings/<version>.md` for major closeouts.

Avoid embedding fragmented dates (`"as of 2026-05-12"`, `"this week"`, `"Tonight's bug log"`) in reference docs. Per-session narrative belongs in `docs/research_notes/<date>_<topic>.md`; reference docs should age well.

## Cleaning up after merges

Once a PR is merged, delete the branch locally and on the remote:

```bash
git branch -D <branch>
git push origin --delete <branch>
```

This keeps the remote-branch list short and the work-in-flight state legible.
