# Tool implementation rules — src/tools/

Files in this directory are MCP tool definitions.
These rules apply in addition to the project-level CLAUDE.md.

## Every tool file must contain exactly two things
1. One or more Python functions implementing the tool logic
2. One tool definition dict named `{TOOL_NAME}_TOOL` for API registration

## Tool function rules
- Function name must exactly match the `name` field in the tool definition dict
- First lines of docstring: what it does and when to use it
- Last lines of docstring: NOT FOR clause stating what it does not do
- Return type is always `dict[str, Any]`
- Never raise exceptions — catch all errors and return structured error dict

## Tool definition dict rules
- `name`: snake_case, matches function name exactly
- `description`: must include trigger condition (when to call) and NOT FOR clause
- `input_schema`: all optional params must not be in `required` array
- Required params must be validated at the top of the function

## Error response structure — always use this exact shape
{
    "success": False,
    "data": None,
    "error": {
        "message": "Human readable explanation",
        "errorCategory": "validation | not_found | transient | threshold_exceeded | permission",
        "isRetryable": True or False
    }
}

## errorCategory decision guide
- `validation` — caller sent wrong input, isRetryable: False
- `not_found` — record does not exist, isRetryable: False  
- `transient` — system error, may resolve on retry, isRetryable: True
- `threshold_exceeded` — business rule blocked, isRetryable: False
- `permission` — caller not authorised, isRetryable: False

## Read vs write separation
- Read tools (get_member, lookup_claim): never write to any file
- Write tools (process_approval, escalate_to_adjuster): always validate
  preconditions before writing

  ## Environment — Windows specific
Python interpreter: .venv\Scripts\python.exe
Run tests with: .venv\Scripts\python.exe -m pytest tests/ -v
Run agent with: .venv\Scripts\python.exe -m src.agent.loop
Do not use bare `python` or `python3` commands — use the venv path above.