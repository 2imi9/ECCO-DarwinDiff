"""Write build.sha256: the hashes of the figure sources and the SVGs built from them.

tests/test_readme_figures.py recomputes these hashes, so a .tex or style edit committed without
re-running build.sh (or a hand-edited SVG) fails CI, although CI has no TeX to rebuild with.
Line endings are normalised to LF before hashing, so a CRLF checkout hashes the same.
Usage: python3 manifest.py  (run by build.sh)
"""
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIGURES = ("readme_method", "readme_components", "readme_loop")


def tracked_files() -> list[str]:
    return ["dd-readme.sty"] + [f"{f}.{ext}" for f in FIGURES for ext in ("tex", "svg")]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


if __name__ == "__main__":
    lines = [f"{digest(HERE / name)}  {name}" for name in tracked_files()]
    (HERE / "build.sha256").write_text("\n".join(lines) + "\n")
    print(f"wrote build.sha256 ({len(lines)} files)")
