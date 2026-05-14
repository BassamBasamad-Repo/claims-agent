# Claims Resolution Agent

## What this project is
A production-grade insurance claims resolution agent built with the 
Claude Agent SDK. Demonstrates all five CCA Foundations exam domains 
through working code. All data is fictional — no real insurance systems 
are connected.

## How to run
```bash
# Run the agent
python -m src.agent.loop

# Run all tests
python -m pytest tests/ -v

# Run compliance review via Claude Code
/review-agent src/agent/loop.py

# Run CI code review (non-interactive)
claude -p "Review this file for issues" \
  --output-format json \
  src/agent/loop.py
```

## Project structure
- `src/agent/` — agentic loop, hooks, session management
- `src/tools/` — MCP tool definitions (read/write separated)
- `src/data/` — mock JSON records (members, claims, escalations)
- `tests/` — unit tests per domain concept
- `.claude/rules/` — path-scoped Claude Code rules
- `.claude/commands/` — custom slash commands

## Coding standards
@import .claude/standards/python.md

## Architecture decisions
@import .claude/standards/architecture.md

## What Claude Code must never do
- Modify any file in src/data/ directly — only tool functions write data
- Remove or bypass pre_tool_use_hook in hooks.py
- Add stop conditions based on text content parsing
- Introduce bare except clauses — always catch specific exceptions
- Add tools without a NOT FOR clause in both docstring and tool definition
- Commit .env files or hardcoded API keys