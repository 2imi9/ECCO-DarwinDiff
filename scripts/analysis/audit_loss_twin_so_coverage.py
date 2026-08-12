#!/usr/bin/env python3
"""Audit job 320993 coverage provenance without quoting gated SO results."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import shlex
import subprocess
import tarfile
from pathlib import Path

JOB = 320993
N_TASKS = 75
REMOTE_LOG_DIR = "/scratch/qi_zim_neu/twin"
REMOTE_SOURCES = (
    "~/emulator_poc/data/daniels/Daniels_etal_2018_PANGAEA_888182.tab",
    "~/dd_data/geotraces/GEOTRACES_IDP2025_Seawater.nc",
)

START_RE = re.compile(r"\[start\].*?task=(\d+).*?tag=(\S+).*?AOIS=(\S+)")
RC_RE = re.compile(r"^=== rc=(\d+).*?tag=(\S+) ===$", re.MULTILINE)
DANIELS_RE = re.compile(r"Daniels R_PICPOC target: (\d+) cells \((\d+) samples\)")
BSI_RE = re.compile(r"GEOTRACES bSi in-AOI surface bins .*?: (\d+),")
NO_DANIELS = "no Daniels coverage in AOI"
FAILURE_RE = re.compile(
    r"(?:Daniels|GEOTRACES).*?(?:failed|failure|error|missing)|Traceback",
    re.IGNORECASE,
)


class AuditError(ValueError):
    """Raised when the source or coverage provenance is incomplete."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def expected_aoi(task: int) -> str:
    arm = task // 5
    if arm in {0, 1, 2, 3, 12}:
        return "eqpac"
    if arm in {4, 5, 6, 7, 13}:
        return "natlsubpolar"
    if arm in {8, 9, 10, 11, 14}:
        return "southernoceanpac"
    raise AuditError(f"task {task}: no registered arm")


def audit(
    logs: dict[int, bytes],
    source_sizes: dict[str, int],
    *,
    host: str,
    job: int = JOB,
) -> dict[str, object]:
    """Verify coverage cause while preserving the non-zero verifier gate."""
    expected_tasks = set(range(N_TASKS))
    _require(set(logs) == expected_tasks, "expected exactly task logs 0..74")
    _require(len(source_sizes) == len(REMOTE_SOURCES), "expected both staged sources")
    _require(all(size > 0 for size in source_sizes.values()), "a staged source is empty")

    coverage: dict[str, set[tuple[int, int, int]]] = {
        "eqpac": set(),
        "natlsubpolar": set(),
        "southernoceanpac": set(),
    }
    so_no_daniels = 0
    so_zero_bsi = 0
    completed = 0
    hashes: dict[str, str] = {}

    for task in sorted(logs):
        raw = logs[task]
        text = raw.decode("utf-8", errors="replace")
        hashes[str(task)] = hashlib.sha256(raw).hexdigest()
        start = START_RE.search(text)
        finish = RC_RE.search(text)
        _require(start is not None, f"task {task}: start marker missing")
        _require(finish is not None, f"task {task}: completion marker missing")
        _require(int(start.group(1)) == task, f"task {task}: embedded task differs")
        aoi = start.group(3)
        _require(aoi == expected_aoi(task), f"task {task}: unexpected AOI {aoi}")
        _require(int(finish.group(1)) == 0, f"task {task}: non-zero run rc")
        _require(FAILURE_RE.search(text) is None, f"task {task}: source failure text")
        completed += 1

        bsi = BSI_RE.search(text)
        _require(bsi is not None, f"task {task}: bSi coverage line missing")
        daniels = DANIELS_RE.search(text)
        if aoi == "southernoceanpac":
            _require(NO_DANIELS in text, f"task {task}: expected-zero Daniels warning missing")
            _require(daniels is None, f"task {task}: contradictory Daniels target")
            _require(int(bsi.group(1)) == 0, f"task {task}: expected zero bSi cells")
            so_no_daniels += 1
            so_zero_bsi += 1
            coverage[aoi].add((0, 0, 0))
        else:
            _require(daniels is not None, f"task {task}: Daniels coverage line missing")
            coverage[aoi].add(
                (int(daniels.group(1)), int(daniels.group(2)), int(bsi.group(1)))
            )

    _require(coverage["eqpac"] == {(34, 123, 7)}, "EqPac sibling coverage drifted")
    _require(
        coverage["natlsubpolar"] == {(26, 116, 4)},
        "North Atlantic sibling coverage drifted",
    )
    _require(
        coverage["southernoceanpac"] == {(0, 0, 0)},
        "Southern Ocean coverage is not uniformly zero",
    )
    _require(so_no_daniels == 25, "expected 25 SO Daniels expected-zero warnings")
    _require(so_zero_bsi == 25, "expected 25 SO zero-bSi observations")

    digest_input = "".join(f"{task}:{hashes[str(task)]}\n" for task in range(N_TASKS))
    return {
        "schema_version": 1,
        "verified": True,
        "job": job,
        "host": host,
        "task_logs": completed,
        "log_sha256": hashes,
        "log_set_sha256": hashlib.sha256(digest_input.encode()).hexdigest(),
        "source_sizes_bytes": dict(sorted(source_sizes.items())),
        "coverage": {
            "eqpac": {"task_logs": 25, "daniels_cells": 34, "daniels_samples": 123, "bsi_cells": 7},
            "natlsubpolar": {
                "task_logs": 25,
                "daniels_cells": 26,
                "daniels_samples": 116,
                "bsi_cells": 4,
            },
            "southernoceanpac": {
                "task_logs": 25,
                "daniels_cells": 0,
                "bsi_cells": 0,
                "expected_zero_warnings": 25,
                "source_failure_markers": 0,
            },
        },
        "cause": "expected-geographic-zero-not-source-staging-failure",
        "reporting": "excluded: declared-on Daniels and POSi terms have zero active cells",
    }


def fetch_logs(host: str, job: int, remote_log_dir: str) -> dict[int, bytes]:
    """Fetch the immutable Slurm log set as an in-memory tar stream."""
    pattern = f"dd-twin_{int(job)}_*.out"
    command = f"cd {shlex.quote(remote_log_dir)} && tar -cf - {pattern}"
    proc = subprocess.run(
        ["ssh", host, command],
        check=False,
        capture_output=True,
    )
    if proc.returncode:
        raise AuditError(proc.stderr.decode(errors="replace").strip())

    logs: dict[int, bytes] = {}
    name_re = re.compile(rf"(?:.*/)?dd-twin_{int(job)}_(\d+)\.out$")
    with tarfile.open(fileobj=io.BytesIO(proc.stdout), mode="r:") as archive:
        for member in archive.getmembers():
            match = name_re.fullmatch(member.name)
            if match is None or not member.isfile():
                continue
            handle = archive.extractfile(member)
            _require(handle is not None, f"cannot read {member.name}")
            logs[int(match.group(1))] = handle.read()
    return logs


def fetch_source_sizes(host: str) -> dict[str, int]:
    def remote_arg(path: str) -> str:
        if path.startswith("~/"):
            return f'"$HOME/{path[2:]}"'
        return shlex.quote(path)

    paths = " ".join(remote_arg(path) for path in REMOTE_SOURCES)
    proc = subprocess.run(
        ["ssh", host, f"stat -c '%n|%s' {paths}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode:
        raise AuditError(proc.stderr.strip())
    result: dict[str, int] = {}
    for line in proc.stdout.splitlines():
        path, separator, size = line.rpartition("|")
        _require(bool(separator), f"unparseable stat line: {line}")
        result[path] = int(size)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="aicr")
    parser.add_argument("--job", type=int, default=JOB)
    parser.add_argument("--remote-log-dir", default=REMOTE_LOG_DIR)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    try:
        result = audit(
            fetch_logs(args.host, args.job, args.remote_log_dir),
            fetch_source_sizes(args.host),
            host=args.host,
            job=args.job,
        )
    except (AuditError, OSError, tarfile.TarError) as exc:
        print(f"COVERAGE AUDIT FAILED: {exc}")
        return 2

    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        "VERIFIED job 320993 coverage cause: SO=25/25 expected geographic zero, "
        "source failures=0; result remains excluded"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
