---
description: Tool implementation standards for MCP tool files
globs: src/tools/*.py
---

# Tool file standards

When working on any file in src/tools/:

## Before adding a new tool
- Check that no existing tool already covers this use case
- Verify the new tool name does not overlap semantically with existing tools
- Write the NOT FOR clause before writing any implementation code

## Description writing checklist
Every tool description must answer these questions:
1. What does this tool return? (the data shape)
2. When should the agent call it? (the trigger condition)  
3. What should the agent use instead for adjacent use cases? (NOT FOR)
4. What identifiers does it accept? (input hint)

## Testing requirements
Every tool function must be testable with these three cases:
1. Happy path — valid input, returns success=True
2. Not found — valid input format, record does not exist
3. Invalid input — missing required fields, returns validation error