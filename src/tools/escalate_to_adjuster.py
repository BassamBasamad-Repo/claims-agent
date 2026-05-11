import json
from pathlib import Path
from typing import Any
from datetime import datetime
from enum import Enum

ESCALATIONS_PATH = Path(__file__).parent.parent / "data" / "escalations.json"


class TriggerReason(str, Enum):
    EXPLICIT_MEMBER_REQUEST = "explicit_member_request"
    POLICY_GAP = "policy_gap"
    AMOUNT_THRESHOLD_EXCEEDED = "amount_threshold_exceeded"


def load_escalations() -> list:
    if not ESCALATIONS_PATH.exists():
        return []
    with open(ESCALATIONS_PATH) as f:
        return json.load(f)


def save_escalations(escalations: list) -> None:
    with open(ESCALATIONS_PATH, "w") as f:
        json.dump(escalations, f, indent=2)


def escalate_to_adjuster(
    member_id: str,
    member_name: str,
    claim_id: str,
    claim_status: str,
    amount_sar: float,
    trigger_reason: str,
    summary: str,
    context_so_far: str
) -> dict[str, Any]:
    """
    Routes an insurance case to a human adjuster for review.

    Use when the case requires human authority, falls outside the agent's
    authorised scope, the approval amount exceeds the autonomous threshold,
    or the member has explicitly requested to speak to a human.

    NOT FOR routine claim lookups or status checks — use lookup_claim instead.
    NOT FOR cases the agent can resolve autonomously — escalation is a last
    resort, not a fallback for uncertainty. Always attempt resolution first.

    Args:
        member_id: Bupa member ID of the member whose case is being escalated.
        member_name: Full name of the member for adjuster queue display.
        claim_id: The claim at the centre of this escalation.
        claim_status: Current status of the claim at time of escalation.
        amount_sar: The amount in question in Saudi Riyals.
        trigger_reason: Why this case is being escalated. Must be one of:
                        explicit_member_request | policy_gap |
                        amount_threshold_exceeded
        summary: Plain-language description of what the member asked for.
        context_so_far: What the agent already tried and found, so the
                        adjuster does not repeat completed steps.

    Returns structured dict confirming escalation or structured error.
    """
    # Validate trigger_reason is a known enum value
    valid_reasons = {r.value for r in TriggerReason}
    if trigger_reason not in valid_reasons:
        return {
            "success": False,
            "data": None,
            "error": {
                "message": (
                    f"Invalid trigger_reason '{trigger_reason}'. "
                    f"Must be one of: {', '.join(valid_reasons)}"
                ),
                "errorCategory": "validation",
                "isRetryable": False
            }
        }

    if not all([member_id, member_name, claim_id, summary, context_so_far]):
        return {
            "success": False,
            "data": None,
            "error": {
                "message": "member_id, member_name, claim_id, summary, and "
                           "context_so_far are all required fields.",
                "errorCategory": "validation",
                "isRetryable": False
            }
        }

    try:
        escalation_record = {
            "escalation_id": f"ESC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "member_id": member_id,
            "member_name": member_name,
            "claim_id": claim_id,
            "claim_status": claim_status,
            "amount_sar": amount_sar,
            "trigger_reason": trigger_reason,
            "summary": summary,
            "context_so_far": context_so_far,
            "escalated_at": datetime.now().isoformat(),
            "adjuster_status": "pending_assignment"
        }

        escalations = load_escalations()
        escalations.append(escalation_record)
        save_escalations(escalations)

        return {
            "success": True,
            "data": {
                "escalation_id": escalation_record["escalation_id"],
                "adjuster_status": "pending_assignment",
                "message": (
                    f"Your case has been escalated to our team "
                    f"(ref: {escalation_record['escalation_id']}). "
                    f"An adjuster will contact you within 2 business hours."
                )
            },
            "error": None
        }

    except Exception:
        return {
            "success": False,
            "data": None,
            "error": {
                "message": "Unable to create escalation record at this time.",
                "errorCategory": "transient",
                "isRetryable": True
            }
        }


# Tool definition for the Claude API tools parameter
ESCALATE_TO_ADJUSTER_TOOL = {
    "name": "escalate_to_adjuster",
    "description": (
        "Routes an insurance case to a human adjuster when the situation "
        "requires human authority, falls outside the agent's authorised scope, "
        "the approval amount exceeds SAR 5,000, or the member explicitly requests "
        "to speak to a human. Always include a full summary and context of what "
        "the agent already tried so the adjuster does not repeat completed steps. "
        "NOT FOR routine claim lookups or status checks — use lookup_claim instead. "
        "NOT FOR cases that can be resolved autonomously — always attempt resolution "
        "before escalating."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "member_id": {
                "type": "string",
                "description": "Bupa member ID of the member being escalated."
            },
            "member_name": {
                "type": "string",
                "description": "Full name of the member for adjuster queue display."
            },
            "claim_id": {
                "type": "string",
                "description": "The claim at the centre of this escalation."
            },
            "claim_status": {
                "type": "string",
                "description": "Current status of the claim at time of escalation."
            },
            "amount_sar": {
                "type": "number",
                "description": "The amount in question in Saudi Riyals."
            },
            "trigger_reason": {
                "type": "string",
                "enum": [
                    "explicit_member_request",
                    "policy_gap",
                    "amount_threshold_exceeded"
                ],
                "description": "Why this case is being escalated."
            },
            "summary": {
                "type": "string",
                "description": "Plain-language description of what the member asked for."
            },
            "context_so_far": {
                "type": "string",
                "description": (
                    "What the agent already tried and found. Prevents the adjuster "
                    "from repeating steps already completed."
                )
            }
        },
        "required": [
            "member_id", "member_name", "claim_id", "claim_status",
            "amount_sar", "trigger_reason", "summary", "context_so_far"
        ]
    }
}