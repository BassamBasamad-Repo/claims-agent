# Architecture decisions

## Why PreToolUse over PostToolUse for enforcement
PreToolUse fires before execution and can block writes entirely.
PostToolUse fires after execution — the write has already happened.
All financial thresholds and business rule enforcement must use
PreToolUse. PostToolUse is for logging and audit only.

## Why four tools instead of one
A single generic tool causes model misrouting on similar queries.
Four bounded tools with NOT FOR clauses give the model unambiguous
selection criteria. Maximum 4-5 tools per agent instance.

## Why read and write tools are in separate files
Write tools require hook validation and carry irreversibility risk.
Separation makes the boundary explicit and ensures hooks are never
accidentally omitted.

## Why CaseFacts injects at system prompt top
Lost-in-the-middle effect: transformer models process beginning and
end of long contexts reliably. Middle sections are unreliable.
CaseFacts places critical transactional data at the start of every
system prompt so it is never in the unreliable middle zone.

## When to use plan mode
Use plan mode when:
- Making changes across more than two files simultaneously
- Modifying the agentic loop control flow
- Adding a new tool (requires changes in loop.py, hooks.py, and tool file)
- Refactoring session or context management
- Any change where getting it wrong would require data recovery

Use direct execution when:
- Single file changes with clear bounded scope
- Adding a docstring or type hint
- Fixing a specific named bug
- Writing a new test for existing behaviour