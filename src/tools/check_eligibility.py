import json
from pathlib import Path
from typing import Any

DATA_PATH = Path(__file__).parent.parent / "data" / "members.json"

VALID_CARE_CATEGORIES = frozenset(
    {"inpatient", "outpatient", "dental", "optical", "maternity"}
)


def load_members() -> dict:
    with open(DATA_PATH) as f:
        return json.load(f)


def check_eligibility(member_id: str, care_category: str) -> dict[str, Any]:
    """
    Checks whether a member is eligible to receive a specific category of care.

    Use this tool before approving or processing a claim to confirm that
    the member's plan covers the requested care type, the policy is active,
    and the member has remaining annual benefit after deductible.

    NOT FOR retrieving raw member profile data — use get_member for that.
    NOT FOR looking up claim records or approval status — use lookup_claim.
    NOT FOR checking eligibility on behalf of a claim that is already
    approved or denied — the determination has already been made.

    Args:
        member_id: Bupa member ID (format: MBR-XXX).
        care_category: The category of care to check. Must be one of:
                       inpatient | outpatient | dental | optical | maternity

    Returns structured dict with eligibility result or structured error.
    """
    if not member_id or not care_category:
        return {
            "success": False,
            "data": None,
            "error": {
                "message": "Both member_id and care_category are required.",
                "errorCategory": "validation",
                "isRetryable": False
            }
        }

    if care_category not in VALID_CARE_CATEGORIES:
        return {
            "success": False,
            "data": None,
            "error": {
                "message": (
                    f"Invalid care_category '{care_category}'. "
                    f"Must be one of: {', '.join(sorted(VALID_CARE_CATEGORIES))}"
                ),
                "errorCategory": "validation",
                "isRetryable": False
            }
        }

    try:
        members = load_members()
        member = members.get(member_id)

        if not member:
            return {
                "success": False,
                "data": None,
                "error": {
                    "message": f"No member found with ID {member_id}.",
                    "errorCategory": "not_found",
                    "isRetryable": False
                }
            }

        if member["status"] != "active":
            return {
                "success": True,
                "data": {
                    "member_id": member_id,
                    "care_category": care_category,
                    "eligible": False,
                    "reason": "policy_suspended",
                    "reason_detail": (
                        "Member policy is currently suspended. "
                        "Coverage is not active."
                    ),
                    "remaining_benefit_sar": 0.0
                },
                "error": None
            }

        if not member["coverage"].get(care_category, False):
            return {
                "success": True,
                "data": {
                    "member_id": member_id,
                    "care_category": care_category,
                    "eligible": False,
                    "reason": "coverage_not_included",
                    "reason_detail": (
                        f"The member's {member['plan_type']} plan does not "
                        f"include {care_category} coverage."
                    ),
                    "remaining_benefit_sar": 0.0
                },
                "error": None
            }

        annual_limit = member["annual_limit_sar"]
        used = member["used_limit_sar"]
        deductible = member["deductible_sar"]
        remaining = max(0.0, annual_limit - used - deductible)

        if remaining <= 0:
            return {
                "success": True,
                "data": {
                    "member_id": member_id,
                    "care_category": care_category,
                    "eligible": False,
                    "reason": "annual_limit_reached",
                    "reason_detail": (
                        f"Annual benefit limit of SAR {annual_limit:,.2f} "
                        f"has been reached after deductible."
                    ),
                    "remaining_benefit_sar": 0.0
                },
                "error": None
            }

        return {
            "success": True,
            "data": {
                "member_id": member_id,
                "care_category": care_category,
                "eligible": True,
                "reason": None,
                "reason_detail": None,
                "remaining_benefit_sar": remaining
            },
            "error": None
        }

    except FileNotFoundError:
        return {
            "success": False,
            "data": None,
            "error": {
                "message": "Member data source is currently unavailable.",
                "errorCategory": "transient",
                "isRetryable": True
            }
        }
    except Exception:
        return {
            "success": False,
            "data": None,
            "error": {
                "message": "An unexpected error occurred checking eligibility.",
                "errorCategory": "transient",
                "isRetryable": True
            }
        }


# Tool definition for the Claude API tools parameter
CHECK_ELIGIBILITY_TOOL = {
    "name": "check_eligibility",
    "description": (
        "Checks whether a member is eligible for a specific category of care "
        "by verifying policy status, plan coverage, and remaining annual benefit. "
        "Use before processing an approval or when the member asks whether a "
        "specific treatment type is covered under their plan. "
        "Returns eligible (True/False), the reason if not eligible, and the "
        "remaining benefit amount in SAR if eligible. "
        "NOT FOR raw member profile data — use get_member for that. "
        "NOT FOR claim record lookups or approval status — use lookup_claim."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "member_id": {
                "type": "string",
                "description": "Bupa member ID (format: MBR-XXX)."
            },
            "care_category": {
                "type": "string",
                "enum": ["inpatient", "outpatient", "dental", "optical", "maternity"],
                "description": (
                    "The category of care to check eligibility for. "
                    "Must be one of the listed enum values."
                )
            }
        },
        "required": ["member_id", "care_category"]
    }
}
