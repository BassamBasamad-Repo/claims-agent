---
description: Agentic loop and hook implementation standards
globs: src/agent/*.py
---

# Agent implementation standards

When working on any file in src/agent/:

## Loop control flow rules
- stop_reason is the ONLY valid loop termination signal
- "tool_use" → continue, execute tools, append results, loop
- "end_turn" → extract text response, return, stop
- Never parse model text content to determine loop state
- MAX_ITERATIONS is a safety cap only — not the primary stop mechanism

## Hook rules
- pre_tool_use_hook runs BEFORE tool execution — can block writes
- post_tool_use_hook runs AFTER tool execution — logging only
- All financial threshold enforcement belongs in pre_tool_use_hook
- Never move threshold logic into the system prompt alone

## Context management rules
- Tool results must be appended to messages after every tool call
- CaseFacts must be updated after every successful tool call
- System prompt is rebuilt on every iteration with latest CaseFacts
- Never summarise numerical values in CaseFacts — preserve exact amounts