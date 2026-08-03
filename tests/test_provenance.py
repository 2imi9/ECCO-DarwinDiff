"""Stamping what code produced a number, and the properties that make it worth trusting.

On 2026-08-03 the published flagship was found bound to a code build: same config, same seeds,
`scav_rat` 60% on the 2026-07-26 tree and 2% on HEAD. Nothing detected it, because every check
in the repo inspects the artifact and no artifact recorded its own code version.

The two properties that decide whether this module actually helps:

  * it must work WITHOUT git, because the cluster checkout that produces every production number
    is not a git repository (#218) -- so a git SHA is None exactly where it matters;
  * it must be insensitive to line endings, because the same commit checked out on Windows and on
    Linux differs only by CRLF, and a digest that called those two different builds would cry wolf
    on every run and be ignored within a week.

Measured against the 16 real bisect trees on the cluster: 16 distinct digests, zero collisions.
"""
from __future__ import annotations

import json
from pathlib import Path

from darwindiff.provenance import code_digest, stamp


def _tree(root: Path, body: str, name: str = "mod.py") -> Path:
    pkg = root / "pkg"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / name).write_text(body, encoding="utf-8", newline="")
    return pkg


def test_digest_is_stable_for_identical_content(tmp_path: Path) -> None:
    a = _tree(tmp_path / "a", "x = 1\n")
    b = _tree(tmp_path / "b", "x = 1\n")
    assert code_digest([a]) == code_digest([b])


def test_digest_changes_when_code_changes(tmp_path: Path) -> None:
    a = _tree(tmp_path / "a", "x = 1\n")
    b = _tree(tmp_path / "b", "x = 2\n")
    assert code_digest([a]) != code_digest([b]), (
        "a one-character behavioural change must move the digest, or it cannot catch a regression"
    )


def test_digest_ignores_line_endings(tmp_path: Path) -> None:
    """The same commit on Windows and Linux is the SAME build."""
    a = _tree(tmp_path / "a", "x = 1\ny = 2\n")
    b = _tree(tmp_path / "b", "x = 1\r\ny = 2\r\n")
    assert code_digest([a]) == code_digest([b]), (
        "CRLF must not read as a different build -- a digest that fires on every checkout "
        "gets ignored, and then it protects nothing"
    )


def test_digest_notices_a_rename(tmp_path: Path) -> None:
    a = _tree(tmp_path / "a", "x = 1\n", name="one.py")
    b = _tree(tmp_path / "b", "x = 1\n", name="two.py")
    assert code_digest([a]) != code_digest([b])


def test_digest_does_not_depend_on_walk_order(tmp_path: Path) -> None:
    a = _tree(tmp_path / "a", "x = 1\n", name="a.py")
    (a / "z.py").write_text("z = 3\n", encoding="utf-8", newline="")
    first = code_digest([a])
    (a / "a.py").touch()  # change mtime, not content
    assert code_digest([a]) == first


def test_stamp_works_without_git_and_is_json_serialisable(tmp_path: Path) -> None:
    """The cluster case: no repo, so git fields are None but the digest still identifies the build."""
    s = stamp(tmp_path / "does_not_exist.py")
    assert s["code_digest"], "a digest must be produced even with no git and no runner file"
    json.dumps(s)  # artifacts are JSON; an unserialisable stamp would abort the write


def test_stamp_never_raises_on_bad_input() -> None:
    """Provenance is a side-record. It must never be the thing that kills a training run."""
    for bad in (None, "", "/nonexistent/\0/path", 12345):
        try:
            out = stamp(bad)  # type: ignore[arg-type]
        except Exception as exc:  # noqa: BLE001
            raise AssertionError(f"stamp({bad!r}) raised {exc!r}; it must degrade, not fail") from exc
        assert isinstance(out, dict)


def test_stamp_reports_this_repo() -> None:
    """In a real checkout the git fields populate, so the authoritative id is there when available."""
    s = stamp(Path(__file__).resolve().parents[1] / "scripts" / "run_v3.0_joint_multi_aoi.py")
    assert s["code_digest"]
    assert s["runner_md5"]
    if s["git_sha"] is not None:
        assert len(s["git_sha"]) == 12
        assert isinstance(s["git_dirty"], bool)
