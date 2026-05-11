from dataclasses import dataclass, field
from typing import Any


@dataclass
class CaseFacts:
    """
    Persistent structured facts extracted from the conversation.

    These are kept separate from conversation history and included
    in every prompt. They survive context summarisation and ensure
    critical transactional data is never lost to the middle of a
    long conversation.

    Domain 5 concept: lost-in-the-middle prevention.
    """
    member_id: str | None = None
    member_name: str | None = None
    policy_number: str | None = None
    plan_type: str | None = None
    claim_ids_mentioned: list[str] = field(default_factory=list)
    amounts_mentioned: list[float] = field(default_factory=list)
    escalation_triggered: bool = False
    escalation_id: str | None = None
    resolved_concerns: list[str] = field(default_factory=list)

    def update_from_member(self, member_data: dict) -> None:
        """Update facts when get_member tool returns successfully."""
        self.member_id = member_data.get("member_id")
        self.member_name = member_data.get("name")
        self.policy_number = member_data.get("policy_number")
        self.plan_type = member_data.get("plan_type")

    def update_from_claim(self, claim_data: dict) -> None:
        """Update facts when lookup_claim tool returns successfully."""
        claim_id = claim_data.get("claim_id")
        if claim_id and claim_id not in self.claim_ids_mentioned:
            self.claim_ids_mentioned.append(claim_id)
        amount = claim_data.get("amount_claimed_sar")
        if amount and amount not in self.amounts_mentioned:
            self.amounts_mentioned.append(amount)

    def to_prompt_block(self) -> str:
        """
        Renders facts as a structured block injected into every prompt.
        Placed at the top of the system prompt so it is never lost.
        """
        lines = ["## Verified case facts"]
        lines.append(f"Member ID: {self.member_id or 'not yet identified'}")
        lines.append(f"Member name: {self.member_name or 'not yet identified'}")
        lines.append(f"Policy: {self.policy_number or 'not yet retrieved'}")
        lines.append(f"Plan: {self.plan_type or 'not yet retrieved'}")
        if self.claim_ids_mentioned:
            lines.append(f"Claims discussed: {', '.join(self.claim_ids_mentioned)}")
        if self.amounts_mentioned:
            formatted = [f"SAR {a:,.2f}" for a in self.amounts_mentioned]
            lines.append(f"Amounts mentioned: {', '.join(formatted)}")
        if self.escalation_triggered:
            lines.append(f"Escalation: triggered (ref: {self.escalation_id})")
        if self.resolved_concerns:
            lines.append(f"Resolved: {', '.join(self.resolved_concerns)}")
        return "\n".join(lines)