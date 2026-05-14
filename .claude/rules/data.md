---
description: Data file protection rules
globs: src/data/*.json
---

# Data file rules

Files in src/data/ are the mock database for this project.

## Never modify these files directly
All writes to JSON files in this directory must go through
tool functions in src/tools/. Direct edits bypass validation,
hook enforcement, and structured error handling.

## Exception — manual reset
The only acceptable direct edit is resetting test data to a
clean state before a test run. Document the reset in a comment
and restore from the canonical structure in README.md.

## File ownership
- members.json — written only by setup scripts, never by agent tools
- claims.json — written only by process_approval tool
- escalations.json — written only by escalate_to_adjuster tool

## Schema changes
Any change to the JSON structure requires updating:
1. The corresponding tool function return handling
2. The update_case_facts function in loop.py
3. The relevant test fixtures