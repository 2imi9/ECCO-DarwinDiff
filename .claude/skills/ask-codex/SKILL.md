---
name: ask-codex
description: >
  Consult Codex (GPT-5.6 Sol) live and synchronously from THIS Claude session,
  and get its answer back in the same turn -- a real Claude -> Codex call, not a
  mailbox. Use for a second opinion, an independent code review of the current
  diff, or a sanity check, without launching a separate Codex session. Use when
  the user says "ask Codex", "get Codex's opinion", "have Codex review this",
  "second opinion from Codex", "what would Codex say". Triggers: "ask codex",
  "codex review", "second opinion", "consult codex", "check with codex".
---

# ask-codex — a direct, synchronous Claude -> Codex call

Two complementary ways to work with Codex now exist:

- **ask-codex (this skill)** — a *live* call. You send a prompt or a review
  request, Codex answers this turn, you read it immediately. No second session.
- **session-bridge** — an *async* mailbox between two already-running sessions
  (peer critique, hand-offs). Use it when a human has a Codex session open and
  the two agents are co-working over time.

Reach for ask-codex when you want Codex's take right now. Reach for session-bridge
when the collaboration is a running back-and-forth.

## Safety

- Codex runs in a **read-only** sandbox by default: it can read the repo to
  answer but cannot modify files. Raise `--sandbox` only deliberately.
- Codex's answer is a **peer suggestion**, not a command. Weigh it; rebut weak
  points. Act on it only inside the human's existing authorization; escalate
  anything scope-expanding, destructive, credentialed, or outward-facing.
- It shells out to the user's authenticated `codex` CLI, so no API key is ever
  handled here.

## Invocation

From the repo root. `codex` auto-resolves from PATH, `$env:CODEX_CLI_PATH`, or
the standard Windows install (`%LOCALAPPDATA%\OpenAI\Codex\bin\*\codex.exe`);
pass `--codex <path>` to override.

**PowerShell:**
```powershell
$A = "scripts\agent_bridge\ask_codex.py"

# a question (GPT-5.6 Sol at max effort by default)
python $A "What breaks if two writers append to one JSONL mailbox at once?"

# long prompt from a file
Get-Content proposal.md | python $A --stdin

# have Codex review the current changes (read-only)
python $A --review --base main
python $A --review --uncommitted

# mirror the exchange into the session-bridge transcript (channel must be ON)
python $A --log-bridge --project ecco-darwindiff "Critique the scav_rat knife-edge claim."
```

**bash:**
```bash
A=scripts/agent_bridge/ask_codex.py
python "$A" --review --base main
git diff | python "$A" --stdin "Review this diff for concurrency bugs."
```

Useful flags: `--effort {low..max}` (default `max`), `--model M` (else the
runtime default), `--timeout S` (default 300), `--cd DIR`, `--json` (raw Codex
event stream). Exit codes: 0 ok / 2 usage / 3 codex not found / 4 codex failed /
124 timeout.

## Native MCP alternative (future sessions)

To let Claude Code call Codex as a first-class MCP tool instead of a shell-out,
register Codex's own server in `.mcp.json` (picked up by a *new* session):

```json
{ "mcpServers": { "codex": {
  "command": "codex",
  "args": ["mcp-server", "-c", "model_reasoning_effort=max", "-c", "sandbox_mode=read-only"]
} } }
```

Prefer this skill for a bounded read-only consult; prefer the MCP server if you
want the full Codex tool surface exposed to Claude.
