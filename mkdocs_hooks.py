"""MkDocs build hook: fix repo-relative links that escape the ``docs/`` tree.

Many of this project's Markdown docs link to source files, notebooks, scripts,
and the root-level ``README``/``STATUS`` using relative paths
(``../src/...``, ``../../notebooks/...``). Those resolve correctly on GitHub's
Markdown view but 404 on the rendered site, since only ``docs/`` is published.

For every page, this hook resolves each relative link against the page's source
location. If the target lands *outside* ``docs/`` it is rewritten to an absolute
GitHub URL — except for the handful of root docs that have an in-site
equivalent (``STATUS.md`` -> ``status.md`` etc.), which are linked within the
site. Links that stay inside ``docs/`` are left untouched for MkDocs to resolve.

Registered via ``hooks:`` in ``mkdocs.yml``; runs after the include-markdown
plugin, so included content (e.g. STATUS on the status page) is fixed too.
"""

from __future__ import annotations

import posixpath
import re

GITHUB_BLOB = "https://github.com/2imi9/ECCO-DarwinDiff/blob/main"

# Root-level docs that are also published as in-site pages — link within the
# site rather than bouncing the reader out to GitHub.
SITE_EQUIVALENTS = {
    "STATUS.md": "status.md",
    "CONTRIBUTING.md": "contributing.md",
    "data/README.md": "data.md",
}

# Matches Markdown inline links whose target is relative (starts with ./ or ../),
# capturing an optional "title" so it can be preserved.
_LINK_RE = re.compile(r'(\]\()(\.\.?/[^)\s]+?)(\s+"[^"]*")?(\))')

# Splits text into fenced-code segments (odd indices) and prose (even indices).
_FENCE_RE = re.compile(r"(```.*?```|~~~.*?~~~)", re.DOTALL)


def _strip_parent_prefix(path: str) -> str:
    """Drop leading ``../`` segments without mangling dotfiles like ``.claude``."""
    while path.startswith("../"):
        path = path[3:]
    return path


def on_page_markdown(markdown, page, config, files):  # noqa: ARG001 (MkDocs API)
    src_dir = posixpath.dirname(page.file.src_uri)  # "" for top-level pages

    def repl(match: re.Match) -> str:
        prefix, target, title, close = match.groups()
        title = title or ""
        path_part, sep, frag = target.partition("#")
        resolved = posixpath.normpath(posixpath.join(src_dir, path_part))
        if not resolved.startswith(".."):
            # Stays inside docs/ — let MkDocs resolve it natively.
            return match.group(0)
        repo_path = _strip_parent_prefix(resolved)
        if repo_path in SITE_EQUIVALENTS:
            rel = posixpath.relpath(SITE_EQUIVALENTS[repo_path], src_dir or ".")
            return f"{prefix}{rel}{sep}{frag}{title}{close}"
        return f"{prefix}{GITHUB_BLOB}/{repo_path}{sep}{frag}{title}{close}"

    parts = _FENCE_RE.split(markdown)
    for i in range(0, len(parts), 2):  # even indices are outside code fences
        parts[i] = _LINK_RE.sub(repl, parts[i])
    return "".join(parts)
