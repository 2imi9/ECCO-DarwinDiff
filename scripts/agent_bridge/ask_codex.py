#!/usr/bin/env python3
"""ask_codex -- a direct, synchronous Claude -> Codex call.

The file bridge (bridge.py) is an async mailbox between two *already running*
sessions. This is the other half: it lets THIS session reach into Codex live,
get GPT-5.6 Sol's answer back in the same turn, and (optionally) log the
exchange to the bridge transcript -- no second human-driven Codex session
required.

It shells out to the user's authenticated `codex` CLI, so it never handles an
API key. It defaults to a **read-only** sandbox: Codex can read the repo to form
its answer but cannot modify files. Raise that only deliberately.

Examples
--------
  # ask Codex a question, print its final answer
  python ask_codex.py "What breaks if two writers append to a JSONL mailbox at once?"

  # long prompt from stdin, and mirror the exchange into the bridge transcript
  type notes.md | python ask_codex.py --stdin --log-bridge --project ecco-darwindiff

  # have Codex review the current diff (read-only)
  python ask_codex.py --review --base main
  python ask_codex.py --review --uncommitted

Exit codes: 0 ok / 2 usage / 3 codex not found / 4 codex failed / 124 timeout.
"""
from __future__ import annotations

import argparse
import contextlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

EFFORTS = ("low", "medium", "high", "xhigh", "ultra", "max")


def _force_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(Exception):
            stream.reconfigure(encoding="utf-8", errors="replace")


def resolve_codex(explicit: str | None) -> str | None:
    # 1) explicit flag, 2) env, 3) PATH
    for cand in (explicit, os.environ.get("CODEX_CLI_PATH"), shutil.which("codex")):
        if cand and (Path(cand).is_file() or shutil.which(cand)):
            return cand
    # 4) the standard Windows install: %LOCALAPPDATA%\OpenAI\Codex\bin\<hash>\codex.exe
    #    (the hash dir changes on update, so glob and take the newest rather than pin it).
    roots = []
    local = os.environ.get("LOCALAPPDATA")
    if local:
        roots.append(Path(local) / "OpenAI" / "Codex" / "bin")
    roots.append(Path.home() / "AppData" / "Local" / "OpenAI" / "Codex" / "bin")
    for root in roots:
        if root.is_dir():
            hits = sorted(root.glob("*/codex.exe"), key=lambda p: p.stat().st_mtime, reverse=True)
            if hits:
                return str(hits[0])
    return "codex" if shutil.which("codex") else None


def _log_to_bridge(project: str, prompt: str, answer: str, max_len: int = 4000) -> None:
    """Best-effort mirror of the exchange into the bridge transcript. Never fatal:
    the live answer has already been delivered by the time we get here."""
    bridge = Path(__file__).with_name("bridge.py")
    if not bridge.is_file():
        return

    def _send(kind: str, frm: str, to: str, body: str) -> None:
        clipped = body if len(body) <= max_len else body[:max_len] + "\n...[truncated for transcript]"
        with contextlib.suppress(Exception):
            subprocess.run(
                [sys.executable, str(bridge), "--project", project, "send",
                 "--as", frm, "--to", to, "--kind", kind, "--text", clipped],
                capture_output=True, text=True, timeout=30, check=False,
            )

    _send("question", "claude", "codex", prompt)
    _send("answer", "codex", "claude", answer)


def build_cmd(codex: str, args: argparse.Namespace, out_file: str | None) -> list[str]:
    cmd = [codex, "exec"]
    if args.review:
        cmd.append("review")
    cmd += ["-s", args.sandbox, "--ephemeral", "--skip-git-repo-check",
            "-c", f"model_reasoning_effort={args.effort}"]
    if args.model:
        cmd += ["-m", args.model]
    if args.cd:
        cmd += ["-C", args.cd]
    if args.review:
        if args.base:
            cmd += ["--base", args.base]
        if args.uncommitted:
            cmd.append("--uncommitted")
        if args.commit:
            cmd += ["--commit", args.commit]
    elif out_file:
        cmd += ["-o", out_file]
    return cmd


def main(argv: list[str] | None = None) -> int:
    _force_utf8()
    p = argparse.ArgumentParser(prog="ask_codex", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("prompt", nargs="?", help="what to ask Codex (or use --stdin)")
    p.add_argument("--stdin", action="store_true", help="read the prompt from stdin")
    p.add_argument("--review", action="store_true", help="run `codex exec review` instead of a Q&A")
    p.add_argument("--base", help="review: base branch to diff against")
    p.add_argument("--uncommitted", action="store_true", help="review: staged+unstaged+untracked")
    p.add_argument("--commit", help="review: a specific commit SHA")
    p.add_argument("--effort", default="max", choices=EFFORTS, help="model_reasoning_effort (default max)")
    p.add_argument("--model", help="override the Codex model (else the runtime default)")
    p.add_argument("--sandbox", default="read-only",
                   choices=("read-only", "workspace-write", "danger-full-access"),
                   help="Codex sandbox (default read-only; raise deliberately)")
    p.add_argument("--cd", help="working root for Codex (default: current dir)")
    p.add_argument("--timeout", type=float, default=300.0, help="seconds before giving up")
    p.add_argument("--codex", help="path to the codex binary (else $CODEX_CLI_PATH / PATH)")
    p.add_argument("--log-bridge", action="store_true", help="mirror the exchange into the bridge transcript")
    p.add_argument("--project", default="shared", help="bridge project for --log-bridge")
    p.add_argument("--json", action="store_true", help="stream Codex JSONL events instead of just the answer")
    args = p.parse_args(argv)

    prompt = sys.stdin.read() if args.stdin else (args.prompt or "")
    if not args.review and not prompt.strip():
        print("ask_codex: no prompt (pass a prompt, --stdin, or --review).", file=sys.stderr)
        return 2

    codex = resolve_codex(args.codex)
    if not codex:
        print("ask_codex: could not find the `codex` CLI. Pass --codex <path> or set CODEX_CLI_PATH.",
              file=sys.stderr)
        return 3

    out_file = None
    if not args.review and not args.json:
        fd, out_file = tempfile.mkstemp(prefix="codex_last_", suffix=".txt")
        os.close(fd)
    cmd = build_cmd(codex, args, out_file)
    if args.json:
        cmd.append("--json")

    try:
        proc = subprocess.run(
            cmd,
            input=None if (args.review or not prompt) else prompt,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=args.timeout, cwd=args.cd or None, check=False,
        )
    except FileNotFoundError:
        print(f"ask_codex: cannot execute {codex!r}.", file=sys.stderr)
        return 3
    except subprocess.TimeoutExpired:
        print(f"ask_codex: Codex did not answer within {args.timeout:.0f}s. "
              f"Try a lower --effort or a shorter prompt.", file=sys.stderr)
        return 124

    # Prefer the clean last-message file; fall back to stdout (review / json / empty).
    answer = ""
    if out_file:
        with contextlib.suppress(OSError):
            answer = Path(out_file).read_text(encoding="utf-8", errors="replace").strip()
        with contextlib.suppress(OSError):
            os.unlink(out_file)
    if not answer:
        answer = (proc.stdout or "").strip()

    if proc.returncode != 0 and not answer:
        print(f"ask_codex: codex exited {proc.returncode}.", file=sys.stderr)
        if proc.stderr:
            print(proc.stderr.strip()[-1500:], file=sys.stderr)
        return 4

    print(answer if answer else "(codex returned no text)")
    if args.log_bridge and answer and not args.json:
        _log_to_bridge(args.project, prompt if not args.review else f"[review] base={args.base} uncommitted={args.uncommitted}", answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
