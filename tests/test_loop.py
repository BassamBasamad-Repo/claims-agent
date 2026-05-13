import sys
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, '.')

from src.agent.session import CaseFacts
from src.agent.hooks import pre_tool_use_hook
from src.agent.loop import execute_tool, update_case_facts, TOOL_FUNCTIONS


class TestStopReasonControlFlow:
    """
    Tests for the agentic loop control flow.

    Exam concept: stop_reason is the ONLY valid loop termination signal.
    Never parse text content. Never use iteration count as primary stop.
    """

    def test_pre_hook_blocks_before_tool_executes(self):
        """
        When pre-hook blocks, the tool function must never be called.
        Exam concept: PreToolUse prevents write — PostToolUse cannot.
        """
        call_tracker = []

        original_fn = TOOL_FUNCTIONS["process_approval"]

        def tracking_approval(**kwargs):
            call_tracker.append(kwargs)
            return original_fn(**kwargs)

        with patch.dict(TOOL_FUNCTIONS, {"process_approval": tracking_approval}):
            result = execute_tool(
                "process_approval",
                {"claim_id": "CLM-2024-004", "approved_amount_sar": 67000}
            )

        # Hook should have blocked — tool function never called
        assert len(call_tracker) == 0
        assert result["success"] is False
        assert result["error"]["errorCategory"] == "threshold_exceeded"

    def test_pre_hook_passes_through_for_small_amount(self):
        """
        When pre-hook does not block, tool function must execute normally.
        """
        result = execute_tool(
            "process_approval",
            {"claim_id": "CLM-NONEXISTENT", "approved_amount_sar": 100}
        )
        # Hook did not block — tool ran and returned not_found
        assert result["success"] is False
        assert result["error"]["errorCategory"] == "not_found"

    def test_unknown_tool_returns_structured_error(self):
        """Unknown tool name must return structured error, not raise exception."""
        result = execute_tool("nonexistent_tool", {})

        assert result["success"] is False
        assert result["error"]["errorCategory"] == "validation"
        assert result["error"]["isRetryable"] is False


class TestCaseFacts:
    """
    Tests for the CaseFacts context management pattern.

    Exam concept: persistent structured facts survive context compression.
    Critical numerical values must never be summarised or lost.
    """

    def test_case_facts_updated_from_member_tool(self):
        """Member identity facts must be captured after get_member succeeds."""
        facts = CaseFacts()
        tool_result = {
            "success": True,
            "data": {
                "member_id": "MBR-001",
                "name": "Ahmed Al-Rashidi",
                "policy_number": "POL-2024-001",
                "plan_type": "Gold"
            },
            "error": None
        }
        update_case_facts("get_member", tool_result, facts)

        assert facts.member_id == "MBR-001"
        assert facts.member_name == "Ahmed Al-Rashidi"
        assert facts.policy_number == "POL-2024-001"
        assert facts.plan_type == "Gold"

    def test_case_facts_not_updated_on_failure(self):
        """Failed tool results must not mutate CaseFacts."""
        facts = CaseFacts()
        facts.member_id = "MBR-001"

        tool_result = {
            "success": False,
            "data": None,
            "error": {"errorCategory": "not_found", "isRetryable": False}
        }
        update_case_facts("get_member", tool_result, facts)

        # Facts unchanged — failed result must not overwrite existing data
        assert facts.member_id == "MBR-001"

    def test_claim_ids_accumulated_across_calls(self):
        """Multiple claim lookups must accumulate all claim IDs."""
        facts = CaseFacts()

        for claim_id in ["CLM-2024-001", "CLM-2024-003"]:
            result = {
                "success": True,
                "data": {
                    "claim_id": claim_id,
                    "amount_claimed_sar": 1000
                },
                "error": None
            }
            update_case_facts("lookup_claim", result, facts)

        assert "CLM-2024-001" in facts.claim_ids_mentioned
        assert "CLM-2024-003" in facts.claim_ids_mentioned
        assert len(facts.claim_ids_mentioned) == 2

    def test_amounts_not_duplicated_in_case_facts(self):
        """Same amount must not be added twice to amounts_mentioned."""
        facts = CaseFacts()

        for _ in range(3):
            result = {
                "success": True,
                "data": {"claim_id": "CLM-001", "amount_claimed_sar": 1800},
                "error": None
            }
            update_case_facts("lookup_claim", result, facts)

        assert facts.amounts_mentioned.count(1800) == 1

    def test_case_facts_prompt_block_contains_member_info(self):
        """
        Prompt block must include member identity at the top.
        Exam concept: case facts placed first prevents lost-in-middle issue.
        """
        facts = CaseFacts()
        facts.member_id = "MBR-001"
        facts.member_name = "Ahmed Al-Rashidi"
        facts.policy_number = "POL-2024-001"
        facts.amounts_mentioned = [67000.0]

        block = facts.to_prompt_block()

        assert "MBR-001" in block
        assert "Ahmed Al-Rashidi" in block
        assert "POL-2024-001" in block
        assert "67,000.00" in block

    def test_resolved_concerns_tracked_after_approval(self):
        """
        Approved claims must appear in resolved_concerns.
        Exam concept: prevents agent from attempting to re-approve same claim.
        """
        facts = CaseFacts()
        tool_result = {
            "success": True,
            "data": {
                "claim_id": "CLM-2024-005",
                "status": "approved",
                "amount_approved_sar": 1800.0,
                "approved_at": "2026-01-01T00:00:00"
            },
            "error": None
        }
        update_case_facts("process_approval", tool_result, facts)

        assert any("CLM-2024-005" in c for c in facts.resolved_concerns)
        assert any("1,800.00" in c for c in facts.resolved_concerns)