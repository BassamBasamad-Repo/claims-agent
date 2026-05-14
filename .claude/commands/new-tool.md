---
description: Generates boilerplate for a new MCP tool
argument-hint: tool_name (snake_case, e.g. check_eligibility)
context: fork
---

Generate a new MCP tool file for this claims agent project.

Tool name: $ARGUMENTS

Create the file at src/tools/$ARGUMENTS.py with:

1. A load function that reads from the appropriate JSON file in src/data/
2. A main tool function named $ARGUMENTS with:
   - Full type hints on all parameters
   - Docstring with: purpose, when to use it, NOT FOR clause, args, returns
   - Input validation at the top returning validation errorCategory on failure
   - try/except with FileNotFoundError and generic Exception
   - Structured return: success/data/error keys on all paths
3. A tool definition dict named {TOOL_NAME_UPPER}_TOOL with:
   - name field matching function name exactly
   - description with trigger condition AND NOT FOR clause
   - input_schema with all properties and required array
4. All error responses must include errorCategory and isRetryable fields

Use get_member.py as the reference implementation for style and structure.
Do not create the file — show me the code first for review.