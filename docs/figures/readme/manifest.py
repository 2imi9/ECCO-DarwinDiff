"""Update build.sha256: the hashes of the figure sources and the SVGs built from them.

tests/test_readme_figures.py recomputes these hashes, so a .tex or style edit committed without
re-running build.sh (or a hand-edited SVG) fails CI, although CI has no TeX to rebuild with.
Only the figures actually built are re-hashed, and the shared style only when every figure was
built, so a partial build cannot vouch for a figure it did not rebuild.
Line endings are normalised to LF before hashing, so a CRLF checkout hashes the same.
Usage: python3 manifest.py [FIGURE ...]  (run by build.sh with the figures it built)
"""
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "build.sha256"
STYLE = "dd-readme.sty"
FIGURES = ("readme_method", "readme_components")


def figure_files(figure: str) -> list[str]:
    return [f"{figure}.tex", f"{figure}.svg"]


def tracked_files() -> list[str]:
    return [STYLE] + [name for f in FIGURES for name in figure_files(f)]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def read_manifest() -> dict[str, str]:
    if not MANIFEST.exists():
        return {}
    pairs = (line.split(maxsplit=1) for line in MANIFEST.read_text().splitlines())
    return {name: h for h, name in pairs}


if __name__ == "__main__":
    built = sys.argv[1:] or list(FIGURES)
    unknown = sorted(set(built) - set(FIGURES))
    if unknown:
        sys.exit(f"unknown figure(s): {unknown}")
    recorded = read_manifest()
    refresh = [name for f in built for name in figure_files(f)]
    if set(built) == set(FIGURES):
        refresh.append(STYLE)
    for name in refresh:
        recorded[name] = digest(HERE / name)
    lines = [f"{recorded[name]}  {name}" for name in tracked_files() if name in recorded]
    MANIFEST.write_text("\n".join(lines) + "\n")
    print(f"updated build.sha256 for {', '.join(sorted(refresh))}")
