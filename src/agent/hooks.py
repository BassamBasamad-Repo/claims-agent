from typing import Any
from src.tools.process_approval import APPROVAL_THRESHOLD_SAR


def pre_tool_use_hook(tool_name: str,
                      tool_input: dict) -> dict[str, Any]:
    """
    PreToolUse hook — runs BEFORE tool execution.
    Can block the tool call entirely before any write occurs.

    This is the correct pattern for business rule enforcement
    on write operations. The tool never executes if this hook
    returns blocked=True.

    Current rules enforced:
    - process_approval with amount above APPROVAL_THRESHOLD_SAR
      is blocked before the write happens.
    """
    if tool_name == "process_approval":
        amount = tool_input.get("approved_amount_sar", 0)

        if amount > APPROVAL_THRESHOLD_SAR:
            return {
                "hook_fired": True,
                "blocked": True,
                "action": "escalate",
                "reason": "amount_threshold_exceeded",
                "original_tool": tool_name,
                "original_input": tool_input,
                "blocked_result": {
                    "success": False,
                    "data": None,
                    "error": {
                        "message": (
                            f"Amount SAR {amount:,.2f} exceeds the autonomous "
                            f"approval limit of SAR {APPROVAL_THRESHOLD_SAR:,.2f}. "
                            f"This claim requires adjuster review — "
                            f"please use escalate_to_adjuster."
                        ),
                        "errorCategory": "threshold_exceeded",
                        "isRetryable": False
                    }
                }
            }

    return {
        "hook_fired": False,
        "blocked": False,
        "action": "pass_through"
    }


def post_tool_use_hook(tool_name: str,
                       tool_input: dict,
                       tool_result: dict) -> dict[str, Any]:
    """
    PostToolUse hook — runs AFTER tool execution.
    Cannot prevent writes — used for logging and routing only.

    For blocking rules, use pre_tool_use_hook instead.
    """
    # Log successful write operations for audit trail
    if tool_name == "process_approval" and tool_result.get("success"):
        print(f"  [AUDIT] Approval written: "
              f"claim={tool_input.get('claim_id')} "
              f"amount=SAR {tool_input.get('approved_amount_sar'):,.2f}")

    return {
        "hook_fired": False,
        "action": "pass_through",
        "original_result": tool_result
    }