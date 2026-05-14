# Python coding standards

## Type hints
- Required on all function signatures
- Use `X | None` not `Optional[X]` (Python 3.10+ union syntax)
- Use `dict[str, Any]` not `Dict[str, Any]` (lowercase generics)

## Docstrings
- Required on all public functions and classes
- First line: one sentence stating what it does
- Args section: every parameter with type and purpose
- Returns section: describe the return structure
- For tool functions: include NOT FOR clause as final section

## Error handling
- Never raise bare exceptions from tool functions
- Always return structured dict with success/data/error keys
- Catch specific exceptions — never use bare `except:`
- FileNotFoundError and generic Exception are the minimum two catches
  for any function that reads from disk

## Imports
- Standard library first
- Third party second  
- Local imports last
- One blank line between each group

## Constants
- Module-level constants in SCREAMING_SNAKE_CASE
- Business rule constants (thresholds, limits) must be named constants
  never magic numbers inline in logic