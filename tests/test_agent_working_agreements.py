"""Claude and Codex must load the same DarwinDiff working agreement."""

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
CLAUDE = ROOT / "CLAUDE.md"
AGENTS = ROOT / "AGENTS.md"
CODEX_HOOKS = ROOT / ".codex" / "hooks.json"


def _codex_render(claude_text: str) -> str:
    return (
        claude_text
        .replace("working agreement for Claude Code", "working agreement for Codex", 1)
        .replace("loaded into every Claude Code session", "loaded into every Codex session", 1)
        .replace("`.claude/settings.json`", "`.codex/hooks.json`", 1)
    )


def test_codex_agreement_is_an_exact_agent_specific_render() -> None:
    claude_text = CLAUDE.read_text(encoding="utf-8")
    agents_text = AGENTS.read_text(encoding="utf-8")
    assert agents_text == _codex_render(claude_text)


@pytest.mark.skipif(
    not CODEX_HOOKS.is_file(),
    reason=".codex/ is machine-local (untracked); the hook check only runs where it exists",
)
def test_codex_session_hook_points_back_to_agents_agreement() -> None:
    hooks = json.loads(CODEX_HOOKS.read_text(encoding="utf-8"))
    command = hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    assert "AGENTS.md" in command
    assert "gh issue list" in command
