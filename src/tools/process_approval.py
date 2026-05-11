import json
from pathlib import Path
from typing import Any
from datetime import datetime

DATA_PATH = Path(__file__).parent.parent / "data" / "claims.json"

# Business rule constant — single source of truth
APPROVAL_THRESHOLD_SAR = 5000


def load_claims() -> dict:
    with open(DATA_PATH) as f:
        return json.load(f)


def save_claims(claims: dict) -> None:
    with open(DATA_PATH, "w") as f:
        json.dump(claims, f, indent=2)


def process_approval(claim_id: str,
                     approved_amount_sar: float,
                     notes: str | None = None) -> dict[str, Any]:
    """
    Submits an approval decision for a pending claim.

    Use this tool only when you have verified the member's eligibility,
    confirmed the claim is in pending_approval status, and the approved
    amount is within the autonomous approval threshold.

    NOT FOR claim lookups or status checks — use lookup_claim for those.
    NOT FOR amounts above SAR 5,000 — those require adjuster review and
    will be intercepted by the PostToolUse hook before execution.

    This is a write operation and is irreversible once submitted.

    Args:
        claim_id: The claim to approve (format: CLM-YYYY-XXX).
        approved_amount_sar: The amount being approved in Saudi Riyals.
        notes: Optional processing notes to attach to the claim record.

    Returns structured dict confirming approval or structured error.
    """
    if not claim_id:
        return {
            "success": False,
            "data": None,
            "error": {
                "message": "claim_id is required to process an approval.",
                "errorCategory": "validation",
                "isRetryable": False
            }
        }

    if approved_amount_sar <= 0:
        return {
            "success": False,
            "data": None,
            "error": {
                "message": "Approved amount must be greater than zero.",
                "errorCategory": "validation",
                "isRetryable": False
            }
        }

    try:
        claims = load_claims()
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

        # Only pending claims can be approved
        if claim["status"] != "pending_approval":
            return {
                "success": False,
                "data": None,
                "error": {
                    "message": (
                        f"Claim {claim_id} has status '{claim['status']}' "
                        f"and cannot be approved. Only claims with "
                        f"status 'pending_approval' can be processed."
                    ),
                    "errorCategory": "validation",
                    "isRetryable": False
                }
            }

        # Update the claim record
        claim["status"] = "approved"
        claim["amount_approved_sar"] = approved_amount_sar
        claim["notes"] = notes or claim.get("notes", "")
        claim["approved_at"] = datetime.now().isoformat()
        claims[claim_id] = claim
        save_claims(claims)

        return {
            "success": True,
            "data": {
                "claim_id": claim_id,
                "status": "approved",
                "amount_approved_sar": approved_amount_sar,
                "approved_at": claim["approved_at"],
                "message": (
                    f"Claim {claim_id} has been approved for "
                    f"SAR {approved_amount_sar:,.2f}."
                )
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
                "message": "An unexpected error occurred processing the approval.",
                "errorCategory": "transient",
                "isRetryable": True
            }
        }


# Tool definition for the Claude API tools parameter
PROCESS_APPROVAL_TOOL = {
    "name": "process_approval",
    "description": (
        "Submits an approval decision for a pending insurance claim. "
        "Use only after verifying member eligibility and confirming the claim "
        "is in pending_approval status. This is a write operation — it updates "
        "the claim record and cannot be undone. "
        "NOT FOR claim lookups or status checks — use lookup_claim for those. "
        "NOT FOR amounts above SAR 5,000 — those require adjuster review."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "claim_id": {
                "type": "string",
                "description": "The claim to approve (format: CLM-YYYY-XXX)."
            },
            "approved_amount_sar": {
                "type": "number",
                "description": (
                    "Amount to approve in Saudi Riyals. "
                    "Must be greater than zero and within approval threshold."
                )
            },
            "notes": {
                "type": "string",
                "description": "Optional processing notes to attach to the claim record."
            }
        },
        "required": ["claim_id", "approved_amount_sar"]
    }
}