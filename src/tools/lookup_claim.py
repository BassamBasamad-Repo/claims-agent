import json
from pathlib import Path
from typing import Any

DATA_PATH = Path(__file__).parent.parent / "data" / "claims.json"


def load_claims() -> dict:
    with open(DATA_PATH) as f:
        return json.load(f)


def lookup_claim(claim_id: str | None = None,
                 member_id: str | None = None) -> dict[str, Any]:
    """
    Retrieves claim records for a specific claim or all claims for a member.

    Use this tool when the member asks about a claim they submitted,
    wants to know why a claim was denied, needs the current processing
    status of a claim, or asks about amounts approved versus claimed.

    NOT FOR member profile, policy details, plan type, or coverage
    categories. For anything about who the member is or what their
    plan covers, use get_member instead.

    Args:
        claim_id: Specific claim identifier (format: CLM-YYYY-XXX).
                  Use when the member references a particular claim.
        member_id: Bupa member ID (format: MBR-XXX).
                   Use when the member wants all their claims listed,
                   or when you need to find a claim without a claim ID.

    Returns structured dict with claim data or structured error.
    """
    if not claim_id and not member_id:
        return {
            "success": False,
            "data": None,
            "error": {
                "message": "Either claim_id or member_id must be provided.",
                "errorCategory": "validation",
                "isRetryable": False
            }
        }

    try:
        claims = load_claims()

        # Single claim lookup by claim_id
        if claim_id:
            claim = claims.get(claim_id)
            if not claim:
                return {
                    "success": False,
                    "data": None,
                    "error": {
                        "message": f"No claim found with ID {claim_id}.",
                        "errorCategory": "not_found",
                        "isRetryable": False
                    }
                }
            return {
                "success": True,
                "data": claim,
                "error": None
            }

        # All claims for a member by member_id
        member_claims = [
            c for c in claims.values()
            if c["member_id"] == member_id
        ]

        if not member_claims:
            return {
                "success": False,
                "data": None,
                "error": {
                    "message": f"No claims found for member {member_id}.",
                    "errorCategory": "not_found",
                    "isRetryable": False
                }
            }

        return {
            "success": True,
            "data": {
                "member_id": member_id,
                "total_claims": len(member_claims),
                "claims": member_claims
            },
            "error": None
        }

    except FileNotFoundError:
        return {
            "success": False,
            "data": None,
            "error": {
                "message": "Claims data source is currently unavailable.",
                "errorCategory": "transient",
                "isRetryable": True
            }
        }
    except Exception:
        return {
            "success": False,
            "data": None,
            "error": {
                "message": "An unexpected error occurred retrieving claim data.",
                "errorCategory": "transient",
                "isRetryable": True
            }
        }


# Tool definition for the Claude API tools parameter
LOOKUP_CLAIM_TOOL = {
    "name": "lookup_claim",
    "description": (
        "Retrieves claim records including status, amounts, claim type, denial reason, "
        "and processing notes for a specific claim or all claims belonging to a member. "
        "Use when the member asks about a claim they submitted, wants to know why a claim "
        "was denied, or needs the current status of a claim in progress. "
        "Accepts claim_id for a specific claim or member_id to retrieve all claims for "
        "that member. "
        "NOT FOR member profile, policy details, or coverage categories — "
        "use get_member for those."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "claim_id": {
                "type": "string",
                "description": (
                    "Specific claim ID (format: CLM-YYYY-XXX). "
                    "Use when the member references a particular claim."
                )
            },
            "member_id": {
                "type": "string",
                "description": (
                    "Bupa member ID (format: MBR-XXX). "
                    "Use when the member wants all their claims listed "
                    "or when no claim ID is available."
                )
            }
        },
        "required": []
    }
}