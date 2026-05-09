# Bupa Claims Resolution Agent

## Project purpose
Production-grade insurance claims resolution agent built with the Claude Agent SDK.
Demonstrates agentic loops, MCP tool design, PostToolUse hooks, and context management.

## Architecture overview
- `src/agent/` — agentic loop, hooks, session/context management
- `src/tools/` — MCP tool definitions (4 tools, read/write separated)
- `src/data/` — mock member and claim records
- `tests/` — unit tests per domain concept

## Coding standards
- Python 3.11+
- All tool functions must return structured dicts with `success`, `data`, and `error` keys
- Error responses must include `errorCategory` and `isRetryable` fields
- Never raise bare exceptions from tool functions — always return structured errors
- Type hints required on all function signatures
- Docstrings required on all tool functions — description must include NOT FOR clause

## Tool design rules
- Every tool description must state what it does AND what it does not do
- Read tools and write tools must be in separate files
- Write tools (process_approval) require hook validation before execution
- Maximum 4-5 tools registered per agent instance

## Escalation rules
- Explicit member request to speak to human → always escalate, no exceptions
- Approval amount above SAR 5,000 → escalate via PostToolUse hook (deterministic)
- Policy gap or capability limit → escalate with structured summary
- Sentiment alone is never a valid escalation trigger

## What Claude Code should never do in this project
- Add tools without a NOT FOR clause in the docstring
- Use string matching on model output to detect loop termination
- Skip appending tool results to conversation history
- Hardcode the API key anywhere in source files