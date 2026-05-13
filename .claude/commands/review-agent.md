---
description: Reviews the agentic loop implementation for exam compliance
argument-hint: [file to review, e.g. src/agent/loop.py]
context: fork
---

Review the file $ARGUMENTS for CCA Foundations exam compliance.

Check the following and report findings for each:

**Domain 1 — Agentic loop:**
- [ ] Loop terminates on stop_reason only (not text parsing, not iteration count)
- [ ] tool_use branch executes tools and appends results to messages
- [ ] end_turn branch extracts text and returns — does not continue looping
- [ ] Tool results are appended before the next API call
- [ ] MAX_ITERATIONS exists as a safety cap but is not the primary stop

**Domain 2 — Tool integration:**
- [ ] All tool descriptions include a NOT FOR clause
- [ ] pre_tool_use_hook is called before tool execution
- [ ] post_tool_use_hook is called after tool execution
- [ ] Structured error responses use errorCategory and isRetryable fields

**Domain 5 — Context management:**
- [ ] CaseFacts is updated after successful tool calls
- [ ] System prompt includes CaseFacts block on every iteration
- [ ] No numerical values are summarised — exact amounts preserved

For each item: PASS, FAIL with line number, or NOT APPLICABLE.
End with a summary score and the top 2 issues to fix.