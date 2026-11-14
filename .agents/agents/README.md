# Agent definitions (canonical source)

This folder is the single source of truth for custom subagents. Each tool
(Claude Code, OpenCode, OpenAI/Codex-based tools, ...) reads its own
generated copy — never hand-edit those copies, edit here and resync.

## Layout

Each agent is one folder:

```
.agents/agents/<agent-name>/
  agent.json   # metadata
  prompt.md    # system prompt body
```

`<agent-name>` must be lowercase kebab-case (`[a-z0-9-]+`) — it becomes the
filename in every generated target.

## `agent.json` schema

```json
{
  "description": "One-line summary of when to invoke this agent. Required.",
  "model": "optional model id/alias, omit to inherit the tool's default",
  "tools": ["optional", "normalized", "tool", "names"],
  "targets": {
    "claude": { "...optional per-tool overrides, e.g. color...": true },
    "opencode": { "mode": "subagent", "temperature": 0.2 },
    "openai": "skip"
  }
}
```

- `description` is the only required field.
- `targets.<tool>` can hold tool-specific overrides merged on top of the
  shared fields, or the literal string `"skip"` to exclude that agent from
  one tool's output.

## Regenerating per-tool files

```
task agents:sync    # writes .claude/agents/, .opencode/agent/, and the
                     # OpenAI reference catalog at .agents/export/
task agents:check   # same, but fails (no writes) if anything is stale —
                     # wire this into CI
```

The generator lives at `.agents/scripts/sync_agents.py`. Adding support for
another tool means adding one render function + one entry in that script —
no new agent files needed here.
