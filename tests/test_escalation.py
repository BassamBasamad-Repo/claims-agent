import sys
import json
import pytest
from pathlib import Path

sys.path.insert(0, '.')

from src.tools.escalate_to_adjuster import escalate_to_adjuster, TriggerReason

ESCALATIONS_PATH = Path("src/data/escalations.json")


def clean_escalations():
    """Reset escalations file before each test."""
    if ESCALATIONS_PATH.exists():
        ESCALATIONS_PATH.write_text("[]")


class TestEscalateToAdjuster:
    """
    Tests for escalation tool — validates trigger reasons and payload structure.

    Exam concept: escalation triggers must be explicit and objective.
    Sentiment is never a valid trigger. Explicit member request always is.
    """

    def setup_method(self):
        clean_escalations()

    def _valid_payload(self, trigger_reason: str) -> dict:
        return {
            "member_id": "MBR-001",
            "member_name": "Ahmed Al-Rashidi",
            "claim_id": "CLM-2024-004",
            "claim_status": "pending_approval",
            "amount_sar": 67000,
            "trigger_reason": trigger_reason,
            "summary": "Member requesting approval for knee surgery.",
            "context_so_far": "Verified member identity. Claim found. Hook blocked approval."
        }

    def test_valid_trigger_amount_threshold(self):
        """amount_threshold_exceeded is a valid trigger reason."""
        result = escalate_to_adjuster(
            **self._valid_payload("amount_threshold_exceeded")
        )
        assert result["success"] is True
        assert "escalation_id" in result["data"]
        assert result["data"]["adjuster_status"] == "pending_assignment"

    def test_valid_trigger_explicit_request(self):
        """explicit_member_request is a valid trigger reason."""
        result = escalate_to_adjuster(
            **self._valid_payload("explicit_member_request")
        )
        assert result["success"] is True

    def test_valid_trigger_policy_gap(self):
        """policy_gap is a valid trigger reason."""
        result = escalate_to_adjuster(
            **self._valid_payload("policy_gap")
        )
        assert result["success"] is True

    def test_sentiment_is_not_valid_trigger(self):
        """
        Sentiment-based values must be rejected.
        Exam anti-pattern: escalating because member is angry or frustrated.
        """
        for invalid_reason in [
            "member_was_angry",
            "member_frustrated",
            "negative_sentiment",
            "customer_upset"
        ]:
            result = escalate_to_adjuster(
                **self._valid_payload(invalid_reason)
            )
            assert result["success"] is False, (
                f"Expected failure for sentiment trigger: {invalid_reason}"
            )
            assert result["error"]["errorCategory"] == "validation"
            assert result["error"]["isRetryable"] is False

    def test_escalation_record_written_to_file(self):
        """Escalation must persist to the escalations log."""
        escalate_to_adjuster(**self._valid_payload("policy_gap"))

        with open(ESCALATIONS_PATH) as f:
            records = json.load(f)

        assert len(records) == 1
        assert records[0]["member_id"] == "MBR-001"
        assert records[0]["trigger_reason"] == "policy_gap"
        assert records[0]["adjuster_status"] == "pending_assignment"

    def test_escalation_payload_contains_context(self):
        """
        Escalation record must include context_so_far.
        Exam concept: adjuster must not repeat steps already completed.
        """
        payload = self._valid_payload("amount_threshold_exceeded")
        escalate_to_adjuster(**payload)

        with open(ESCALATIONS_PATH) as f:
            records = json.load(f)

        assert records[0]["context_so_far"] == payload["context_so_far"]
        assert records[0]["member_name"] == "Ahmed Al-Rashidi"

    def test_missing_required_fields_returns_validation_error(self):
        """Missing required fields must return validation error, not crash."""
        result = escalate_to_adjuster(
            member_id="",
            member_name="",
            claim_id="CLM-001",
            claim_status="pending",
            amount_sar=1000,
            trigger_reason="policy_gap",
            summary="",
            context_so_far=""
        )
        assert result["success"] is False
        assert result["error"]["errorCategory"] == "validation"

    def test_all_trigger_reason_enum_values_are_valid(self):
        """Every TriggerReason enum value must produce a successful escalation."""
        for reason in TriggerReason:
            clean_escalations()
            result = escalate_to_adjuster(
                **self._valid_payload(reason.value)
            )
            assert result["success"] is True, (
                f"TriggerReason.{reason.name} should be valid but failed"
            )