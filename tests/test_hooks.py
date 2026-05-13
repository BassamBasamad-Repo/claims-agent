import sys
import pytest

sys.path.insert(0, '.')

from src.agent.hooks import pre_tool_use_hook, post_tool_use_hook
from src.tools.process_approval import APPROVAL_THRESHOLD_SAR


class TestPreToolUseHook:
    """
    Tests for the PreToolUse hook — the deterministic enforcement layer.

    Exam concept: hooks enforce business rules regardless of model reasoning.
    A prompt instruction is probabilistic. A hook is guaranteed.
    """

    def test_hook_fires_above_threshold(self):
        """Hook must block process_approval when amount exceeds threshold."""
        tool_input = {
            "claim_id": "CLM-2024-004",
            "approved_amount_sar": APPROVAL_THRESHOLD_SAR + 1
        }
        result = pre_tool_use_hook("process_approval", tool_input)

        assert result["hook_fired"] is True
        assert result["blocked"] is True
        assert result["action"] == "escalate"
        assert result["reason"] == "amount_threshold_exceeded"

    def test_hook_does_not_fire_at_threshold(self):
        """Hook must NOT block when amount equals threshold exactly."""
        tool_input = {
            "claim_id": "CLM-2024-005",
            "approved_amount_sar": APPROVAL_THRESHOLD_SAR
        }
        result = pre_tool_use_hook("process_approval", tool_input)

        assert result["hook_fired"] is False
        assert result["blocked"] is False
        assert result["action"] == "pass_through"

    def test_hook_does_not_fire_below_threshold(self):
        """Hook must NOT block when amount is within autonomous limit."""
        tool_input = {
            "claim_id": "CLM-2024-005",
            "approved_amount_sar": 1800
        }
        result = pre_tool_use_hook("process_approval", tool_input)

        assert result["hook_fired"] is False
        assert result["blocked"] is False

    def test_blocked_result_has_correct_error_structure(self):
        """Blocked result must include errorCategory and isRetryable."""
        tool_input = {
            "claim_id": "CLM-2024-004",
            "approved_amount_sar": 67000
        }
        result = pre_tool_use_hook("process_approval", tool_input)

        error = result["blocked_result"]["error"]
        assert "errorCategory" in error
        assert "isRetryable" in error
        assert error["errorCategory"] == "threshold_exceeded"
        assert error["isRetryable"] is False

    def test_hook_does_not_fire_for_read_tools(self):
        """Hook must not interfere with read-only tools."""
        for tool_name in ["get_member", "lookup_claim"]:
            result = pre_tool_use_hook(tool_name, {"member_id": "MBR-001"})
            assert result["hook_fired"] is False
            assert result["blocked"] is False

    def test_escalate_blocked_without_member_id(self):
        """Escalation without verified member_id must be blocked."""
        tool_input = {
            "member_id": "",
            "member_name": "Test",
            "claim_id": "CLM-001",
            "claim_status": "pending",
            "amount_sar": 1000,
            "trigger_reason": "policy_gap",
            "summary": "Test",
            "context_so_far": "Test"
        }
        result = pre_tool_use_hook("escalate_to_adjuster", tool_input)

        assert result["hook_fired"] is True
        assert result["blocked"] is True
        assert result["reason"] == "missing_member_id"


class TestPostToolUseHook:
    """
    Tests for PostToolUse hook — logging only, never blocking.

    Exam concept: PostToolUse cannot prevent writes. It fires after
    execution. Use PreToolUse for any blocking business rules.
    """

    def test_post_hook_never_blocks(self):
        """PostToolUse hook must always pass through — never block."""
        tool_result = {"success": True, "data": {"claim_id": "CLM-001"}}
        result = post_tool_use_hook(
            "process_approval",
            {"claim_id": "CLM-001", "approved_amount_sar": 1000},
            tool_result
        )
        assert result["action"] == "pass_through"
        assert result["hook_fired"] is False

    def test_post_hook_passes_through_errors(self):
        """PostToolUse hook must not modify error results."""
        tool_result = {
            "success": False,
            "error": {"errorCategory": "not_found", "isRetryable": False}
        }
        result = post_tool_use_hook("lookup_claim", {}, tool_result)
        assert result["action"] == "pass_through"