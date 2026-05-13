# Claims Resolution Agent

## Project purpose
Production-grade insurance claims resolution agent built with the Claude 
Agent SDK. Demonstrates agentic loops, MCP tool design, PostToolUse hooks, 
and context management for the CCA Foundations certification.

## Architecture
- `src/agent/` — agentic loop, hooks, session/context management
- `src/tools/` — MCP tool definitions (4 tools, read/write separated)
- `src/data/` — mock member and claim records (JSON files)
- `tests/` — unit tests per domain concept
- `.claude/rules/` — path-scoped coding rules
- `.claude/commands/` — custom slash commands

## Running the agent
```bash
python -m src.agent.loop
```

## Running tests
```bash
python -m pytest tests/ -v
```

## General coding standards
- Python 3.11+ with type hints on all function signatures
- Docstrings required on all public functions
- Never raise bare exceptions — always return structured dicts
- Never hardcode API keys — always read from environment variables
- All structured responses must include `success`, `data`, and `error` keys
- Error objects must include `errorCategory` and `isRetryable` fields

## Tool design rules
- Every tool description must include a NOT FOR clause
- Read tools and write tools must be in separate files
- Write tools require pre_tool_use_hook validation
- Maximum 4-5 tools registered per agent instance
- Tool descriptions define when to use AND when not to use the tool

## Escalation rules
- Explicit member request → always escalate, no exceptions
- Approval amount above SAR 5,000 → pre-hook blocks, agent escalates
- Policy gap or capability limit → escalate with structured summary
- Sentiment alone is never a valid escalation trigger

## What Claude Code must never do in this project
- Add tools without a NOT FOR clause in the docstring
- Use string matching on model output to detect loop termination
- Skip appending tool results to conversation history
- Modify claims.json directly — only tool functions may write data
- Remove or bypass the pre_tool_use_hook enforcement