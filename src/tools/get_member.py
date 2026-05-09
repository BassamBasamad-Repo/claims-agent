import json
from pathlib import Path
from typing import Any

DATA_PATH = Path(__file__).parent.parent / "data" / "members.json"


def load_members() -> dict:
    with open(DATA_PATH) as f:
        return json.load(f)


def get_member(member_id: str | None = None,
               national_id: str | None = None) -> dict[str, Any]:
    """
    Retrieves a member's profile, policy details, and coverage information.

    Use this tool when you need to look up who a member is, what plan they
    are on, whether their policy is active, and what categories of care
    their plan covers (inpatient, outpatient, maternity, optical, dental).

    NOT FOR: retrieving claim history, claim status, or approval amounts.
    For anything claim-related, use lookup_claim instead.

    Args:
        member_id: The Bupa member ID (format: MBR-XXX). Use this when
                   the member provides their membership card number.
        national_id: The member's national ID number. Use this when the
                     member does not know their member ID.

    Returns structured dict with member profile or structured error.
    """
    if not member_id and not national_id:
        return {
            "success": False,
            "data": None,
            "error": {
                "message": "Either member_id or national_id must be provided.",
                "errorCategory": "validation",
                "isRetryable": False
            }
        }

    try:
        members = load_members()

        # Search by member_id directly
        if member_id:
            member = members.get(member_id)
        else:
            # Search by national_id
            member = next(
                (m for m in members.values()
                 if m["national_id"] == national_id),
                None
            )

        if not member:
            return {
                "success": False,
                "data": None,
                "error": {
                    "message": f"No member found with the provided identifier.",
                    "errorCategory": "not_found",
                    "isRetryable": False
                }
            }

        return {
            "success": True,
            "data": member,
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
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": {
                "message": "An unexpected error occurred retrieving member data.",
                "errorCategory": "transient",
                "isRetryable": True
            }
        }


# Tool definition for the Claude API tools parameter
GET_MEMBER_TOOL = {
    "name": "get_member",
    "description": (
        "Retrieves a member's profile, policy details, and coverage categories. "
        "Use when you need to know who the member is, whether their policy is active, "
        "and what types of care their plan covers. "
        "NOT FOR claim history, claim status, or approval amounts — use lookup_claim for those."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "member_id": {
                "type": "string",
                "description": "Bupa member ID (format: MBR-XXX). Use when member provides membership card number."
            },
            "national_id": {
                "type": "string",
                "description": "Member's national ID number. Use when member does not know their member ID."
            }
        },
        "required": []
    }
}