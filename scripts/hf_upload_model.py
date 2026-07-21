#!/usr/bin/env python3
"""Upload a trained DarwinDiff emulator checkpoint to the Hugging Face Hub.

Private by default. Authenticates from YOUR environment only:
  - a prior `hf auth login` (cached token in ~/.cache/huggingface/token), or
  - an exported HF_TOKEN env var.
The token is never passed on the command line and never printed.

Examples
--------
  # private repo (default) — safe for unpublished collaborative work
  python scripts/hf_upload_model.py \
      --repo BAIGroup/darwindiff-emulator \
      --files /scratch/qi/emulator_eqpac.safetensors docs/findings/emulator_poc.json

  # go public ON PURPOSE (requires the explicit flag; clear with collaborators first)
  python scripts/hf_upload_model.py --repo 2imi9/darwindiff-emulator --files model.safetensors --public
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repo", required=True, help="Hub repo id, e.g. 'BAIGroup/darwindiff-emulator'.")
    p.add_argument("--files", nargs="+", required=True, help="Local file(s) to upload.")
    p.add_argument("--repo-type", default="model", choices=["model", "dataset"], help="Hub repo type.")
    p.add_argument("--path-in-repo", default=None,
                   help="Destination name for a SINGLE file (default: its basename).")
    p.add_argument("--public", action="store_true",
                   help="Create/keep the repo PUBLIC. Off by default; publishing unpublished "
                        "collaborative work is a deliberate act — clear it with collaborators first.")
    p.add_argument("--commit-message", default="Upload DarwinDiff emulator checkpoint")
    args = p.parse_args(argv)

    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("error: pip install huggingface_hub (into the active env) first.", file=sys.stderr)
        return 2

    files = [Path(f) for f in args.files]
    missing = [str(f) for f in files if not f.is_file()]
    if missing:
        print(f"error: file(s) not found: {missing}", file=sys.stderr)
        return 2
    if args.path_in_repo and len(files) != 1:
        print("error: --path-in-repo only valid with exactly one --files entry.", file=sys.stderr)
        return 2

    # token: cached login (token=None) or HF_TOKEN env — never from argv, never printed.
    token = os.environ.get("HF_TOKEN") or None
    api = HfApi(token=token)
    try:
        who = api.whoami()
    except Exception as e:  # noqa: BLE001
        print(f"error: not authenticated. Run `hf auth login` or export HF_TOKEN. ({e})", file=sys.stderr)
        return 1
    print(f"authenticated as: {who.get('name')} (orgs: {[o['name'] for o in who.get('orgs', [])]})")

    private = not args.public
    print(f"repo: {args.repo}  type: {args.repo_type}  visibility: {'PRIVATE' if private else 'PUBLIC'}")
    if args.public:
        print("  !! PUBLIC upload — this publishes to the open internet. Ctrl-C now to abort.", flush=True)

    api.create_repo(repo_id=args.repo, repo_type=args.repo_type, private=private, exist_ok=True)

    for f in files:
        dest = args.path_in_repo if args.path_in_repo else f.name
        print(f"  uploading {f}  ->  {dest} ({f.stat().st_size / 1e6:.1f} MB) ...", flush=True)
        api.upload_file(
            path_or_fileobj=str(f),
            path_in_repo=dest,
            repo_id=args.repo,
            repo_type=args.repo_type,
            commit_message=args.commit_message,
        )

    url = f"https://huggingface.co/{args.repo}"
    print(f"done -> {url}  ({'private' if private else 'public'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
