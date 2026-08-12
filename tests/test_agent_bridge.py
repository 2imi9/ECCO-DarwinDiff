"""Lifecycle and transport edge-case tests for the two-session peer bridge CLI.

Covers the acceptance list from Codex's peer review: lifecycle, off-as-a-hard-
boundary (no --force), two independent readers, concurrent-send seq/id integrity,
malformed JSONL, stale locks, the message-count and byte caps, unicode, and the
message schema fields.
"""
import importlib.util
from pathlib import Path

import pytest

_BRIDGE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "agent_bridge" / "bridge.py"

pytestmark = pytest.mark.skipif(not _BRIDGE_PATH.is_file(), reason="bridge.py not present")


def _load():
    spec = importlib.util.spec_from_file_location("agent_bridge_bridge", _BRIDGE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bridge = _load()


def run(*argv):
    return bridge.main(list(argv))


def test_on_send_recv_off_lifecycle(tmp_path):
    d = str(tmp_path)
    assert run("--dir", d, "on") == 0
    assert run("--dir", d, "send", "--as", "codex", "--to", "claude",
               "--kind", "critique", "--text", "tighten the band") == 0
    assert run("--dir", d, "recv", "--as", "claude") == 0
    # cursor advanced: nothing new the second time
    assert bridge._pull(Path(d), "claude")[0] == []
    assert run("--dir", d, "off") == 0


def test_off_blocks_send_but_reading_stays_open(tmp_path):
    d = str(tmp_path)
    run("--dir", d, "on")
    run("--dir", d, "send", "--as", "codex", "--to", "claude", "--text", "hi")
    run("--dir", d, "off")
    assert run("--dir", d, "send", "--as", "codex", "--to", "claude", "--text", "blocked") == 3
    # the blocked message was never written
    assert len(bridge._read_all(Path(d))) == 1
    # reading still works while off
    assert run("--dir", d, "recv", "--as", "claude") == 0
    assert run("--dir", d, "tail") == 0


def test_send_has_no_force_bypass(tmp_path):
    d = str(tmp_path)
    run("--dir", d, "on")
    run("--dir", d, "off")
    # --force is not a valid send flag anymore; argparse rejects it
    with pytest.raises(SystemExit):
        run("--dir", d, "send", "--as", "codex", "--to", "claude", "--text", "x", "--force")


def test_message_budget_cap(tmp_path):
    d = str(tmp_path)
    run("--dir", d, "on", "--max-messages", "2")
    assert run("--dir", d, "send", "--as", "a", "--text", "1") == 0
    assert run("--dir", d, "send", "--as", "a", "--text", "2") == 0
    assert run("--dir", d, "send", "--as", "a", "--text", "3") == 4  # budget exhausted


def test_payload_byte_cap(tmp_path):
    d = str(tmp_path)
    run("--dir", d, "on", "--max-bytes", "16")
    assert run("--dir", d, "send", "--as", "a", "--text", "x" * 5) == 0
    assert run("--dir", d, "send", "--as", "a", "--text", "x" * 100) == 6  # too large


def test_two_readers_have_independent_cursors(tmp_path):
    d = Path(tmp_path)
    run("--dir", str(d), "on")
    run("--dir", str(d), "send", "--as", "claude", "--to", "all", "--text", "broadcast")
    assert len(bridge._pull(d, "codex")[0]) == 1
    run("--dir", str(d), "recv", "--as", "codex")           # codex consumes
    assert bridge._pull(d, "codex")[0] == []
    # a distinct instance id still has it unread -> cursors are per-id
    assert len(bridge._pull(d, "codex-b")[0]) == 1


def test_sender_does_not_receive_own_messages(tmp_path):
    d = Path(tmp_path)
    run("--dir", str(d), "on")
    run("--dir", str(d), "send", "--as", "codex", "--to", "claude", "--text", "mine")
    assert bridge._pull(d, "codex")[0] == []                # codex never gets its own


def test_malformed_jsonl_is_skipped(tmp_path):
    d = Path(tmp_path)
    run("--dir", str(d), "on")
    run("--dir", str(d), "send", "--as", "codex", "--to", "claude", "--text", "good")
    with (d / "messages.jsonl").open("a", encoding="utf-8") as fh:
        fh.write("this is not json\n")
        fh.write('{"partial": true}\n')                     # dict but no seq -> dropped
    recs = bridge._read_all(d)
    assert len(recs) == 1 and recs[0]["text"] == "good"
    assert run("--dir", str(d), "recv", "--as", "claude") == 0


def test_stale_lock_times_out(tmp_path, monkeypatch):
    d = Path(tmp_path)
    d.mkdir(exist_ok=True)
    (d / ".lock").write_text("held", encoding="utf-8")      # a stuck session's lock
    monkeypatch.setenv("AGENT_BRIDGE_LOCK_TIMEOUT", "0.2")
    with pytest.raises(SystemExit) as ei:
        run("--dir", str(d), "on")
    assert ei.value.code == 5


def test_unicode_roundtrip(tmp_path, capsys):
    d = str(tmp_path)
    run("--dir", d, "on")
    body = "σ = √(2 ln 1.4) ≈ 0.82, ±0.05, ×"
    run("--dir", d, "send", "--as", "codex", "--to", "claude", "--text", body)
    capsys.readouterr()                                     # drop the send confirmation
    run("--dir", d, "recv", "--as", "claude")
    assert body in capsys.readouterr().out


def test_concurrent_sends_get_distinct_seqs_and_ids(tmp_path):
    d = Path(tmp_path)
    run("--dir", str(d), "on")
    run("--dir", str(d), "send", "--as", "a", "--text", "one")
    run("--dir", str(d), "send", "--as", "b", "--text", "two")
    recs = bridge._read_all(d)
    assert [r["seq"] for r in recs] == [1, 2]
    assert len({r["message_id"] for r in recs}) == 2


def test_schema_fields_present(tmp_path):
    d = Path(tmp_path)
    run("--dir", str(d), "on")
    run("--dir", str(d), "send", "--as", "codex", "--to", "claude", "--kind", "review",
        "--topic", "band", "--reply-to", "1", "--artifact", "a.py", "--artifact", "b.py",
        "--text", "see files")
    rec = bridge._read_all(d)[0]
    assert rec["schema_version"] == bridge.SCHEMA_VERSION
    assert rec["topic"] == "band" and rec["reply_to"] == 1
    assert rec["artifacts"] == ["a.py", "b.py"]
    assert len(rec["message_id"]) >= 8
    assert rec["kind"] == "review"
