import os
import json
from typing import Any
from dotenv import load_dotenv
from anthropic import Anthropic

from src.tools.get_member import get_member, GET_MEMBER_TOOL
from src.tools.lookup_claim import lookup_claim, LOOKUP_CLAIM_TOOL
from src.tools.process_approval import process_approval, PROCESS_APPROVAL_TOOL
from src.tools.escalate_to_adjuster import escalate_to_adjuster, ESCALATE_TO_ADJUSTER_TOOL
from src.tools.check_eligibility import check_eligibility, CHECK_ELIGIBILITY_TOOL
from src.agent.hooks import post_tool_use_hook,pre_tool_use_hook
from src.agent.session import CaseFacts


load_dotenv(override=True)


# All tools registered for this agent
TOOLS = [
    GET_MEMBER_TOOL,
    LOOKUP_CLAIM_TOOL,
    CHECK_ELIGIBILITY_TOOL,
    PROCESS_APPROVAL_TOOL,
    ESCALATE_TO_ADJUSTER_TOOL
]

# Tool dispatcher — maps tool name to function
TOOL_FUNCTIONS = {
    "get_member": get_member,
    "lookup_claim": lookup_claim,
    "check_eligibility": check_eligibility,
    "process_approval": process_approval,
    "escalate_to_adjuster": escalate_to_adjuster
}

# Safety cap — never the primary stop mechanism
MAX_ITERATIONS = 10


def build_system_prompt(case_facts: CaseFacts) -> str:
    """
    Builds the system prompt with the case facts block injected at top.
    Case facts are placed first so they are never lost in long contexts.
    Domain 5: lost-in-the-middle prevention pattern.
    """
    return f"""
{case_facts.to_prompt_block()}

## Your role
You are a Bupa Arabia claims resolution agent. Your goal is to resolve 
member inquiries about insurance claims, policy coverage, and billing 
with accuracy and empathy. Target: resolve 80%+ of cases without escalation.

## Resolution approach
1. Identify the member using get_member before taking any action
2. Look up relevant claims using lookup_claim when the member asks about 
   a specific claim or their claim history
3. Process approvals using process_approval only for claims in 
   pending_approval status and amounts within the autonomous threshold
4. Escalate using escalate_to_adjuster only when:
   - The member explicitly requests to speak to a human
   - The case falls outside your authorised scope (policy gap)
   - The approval amount exceeds the autonomous threshold
   Sentiment and frustration alone are never valid escalation triggers.

## Communication standards
- Be clear, professional, and empathetic
- Always confirm what you found before taking action
- For denied claims, explain the reason clearly and mention appeal rights
- For escalations, reassure the member and provide the reference number
- Never fabricate policy details — only report what tools return

## Hard rules
- Never approve a claim without first verifying member identity
- Never escalate due to member sentiment alone
- Never use your own knowledge to fill gaps — use tools
""".strip()


def execute_tool(tool_name: str, tool_input: dict) -> dict[str, Any]:
    """
    Executes a tool by name.
    Runs PreToolUse hook first — if blocked, returns hook result without
    executing the tool. Runs PostToolUse hook after execution for logging.
    """
    tool_fn = TOOL_FUNCTIONS.get(tool_name)
    if not tool_fn:
        return {
            "success": False,
            "data": None,
            "error": {
                "message": f"Unknown tool: {tool_name}",
                "errorCategory": "validation",
                "isRetryable": False
            }
        }

    # --- PRE TOOL USE HOOK ---
    # Runs before execution — can block write operations
    pre_hook = pre_tool_use_hook(tool_name, tool_input)
    if pre_hook.get("blocked"):
        print(f"  [PRE-HOOK] Blocked {tool_name} — "
              f"reason: {pre_hook['reason']}")
        return pre_hook["blocked_result"]

    # Execute the tool — only reaches here if pre-hook did not block
    raw_result = tool_fn(**tool_input)

    # --- POST TOOL USE HOOK ---
    # Runs after execution — for logging and audit only
    post_tool_use_hook(tool_name, tool_input, raw_result)

    return raw_result


def update_case_facts(tool_name: str,
                      tool_result: dict,
                      case_facts: CaseFacts) -> None:
    """
    Updates the persistent case facts block after successful tool calls.
    Domain 5: ensures critical transactional data survives context compression.
    """
    if not tool_result.get("success"):
        return

    data = tool_result.get("data", {})
    if not data:
        return

    if tool_name == "get_member":
        case_facts.update_from_member(data)

    elif tool_name == "lookup_claim":
        # Handle both single claim and list response
        if "claims" in data:
            for claim in data["claims"]:
                case_facts.update_from_claim(claim)
        else:
            case_facts.update_from_claim(data)

    elif tool_name == "process_approval":
        approved_amount = data.get("amount_approved_sar")
        if approved_amount is not None and approved_amount not in case_facts.amounts_mentioned:
            case_facts.amounts_mentioned.append(approved_amount)
        resolved_claim_id = data.get("claim_id")
        if resolved_claim_id and resolved_claim_id not in case_facts.claim_ids_mentioned:
            case_facts.claim_ids_mentioned.append(resolved_claim_id)
        if resolved_claim_id and approved_amount is not None:
            case_facts.resolved_concerns.append(
                f"Claim {resolved_claim_id} approved for SAR {float(approved_amount):,.2f}"
            )

    elif tool_name == "check_eligibility":
        category = data.get("care_category", "")
        eligible = data.get("eligible")
        if eligible is not None:
            status = "eligible" if eligible else f"not eligible ({data.get('reason', 'unknown')})"
            entry = f"Eligibility checked: {category} = {status}"
            if entry not in case_facts.resolved_concerns:
                case_facts.resolved_concerns.append(entry)

    elif tool_name == "escalate_to_adjuster":
        case_facts.escalation_triggered = True
        case_facts.escalation_id = data.get("escalation_id")
    


def run_agent(member_message: str) -> str:
    """
    Main agentic loop — the core of the Claims Resolution Agent.

    Implements:
    - stop_reason based loop control (Domain 1)
    - Tool execution with PostToolUse hook (Domain 1)
    - Tool result appended to conversation history (Domain 1)
    - Case facts block updated on every tool call (Domain 5)
    - Safety iteration cap as secondary guard only (Domain 1)

    Args:
        member_message: The member's request in plain language.

    Returns:
        The agent's final response as a string.
    """
    client = Anthropic()
    case_facts = CaseFacts()
    messages = [{"role": "user", "content": member_message}]
    iteration = 0

    print(f"\n{'='*60}")
    print(f"Member: {member_message}")
    print(f"{'='*60}")

    while iteration < MAX_ITERATIONS:
        iteration += 1
        print(f"\n[Iteration {iteration}]")

        # Build fresh system prompt with latest case facts on every turn
        system_prompt = build_system_prompt(case_facts)

        # Call the Claude API
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system_prompt,
            tools=TOOLS,
            messages=messages
        )

        print(f"  stop_reason: {response.stop_reason}")

        # --- TERMINATION CHECK ---
        # stop_reason is the ONLY correct loop termination signal
        if response.stop_reason == "end_turn":
            final_text = next(
                (block.text for block in response.content
                 if hasattr(block, "text")),
                "I have completed processing your request."
            )
            print(f"\nAgent: {final_text}")
            return final_text

        # --- TOOL EXECUTION ---
        # stop_reason == "tool_use" — find and execute all requested tools
        if response.stop_reason == "tool_use":

            # Append assistant message to history
            messages.append({
                "role": "assistant",
                "content": response.content
            })

            # Process every tool call in this response
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                tool_name = block.name
                tool_input = block.input
                print(f"  Tool call: {tool_name}({json.dumps(tool_input)})")

                # Execute tool + run hook
                tool_result = execute_tool(tool_name, tool_input)
                print(f"  Tool result: success={tool_result.get('success')}")

                # Update case facts from successful tool results
                update_case_facts(tool_name, tool_result, case_facts)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(tool_result)
                })

            # Append tool results to history so model sees them next iteration
            messages.append({
                "role": "user",
                "content": tool_results
            })

        else:
                print(f"  Unexpected stop_reason: {response.stop_reason}")
                return (
                    f"I was unable to complete your request "
                    f"(reason: {response.stop_reason}). "
                    f"Please contact support if this persists."
                )

    # Safety cap reached — should not happen in normal operation
    return "I was unable to complete your request. Please contact support."


if __name__ == "__main__":
    # Quick smoke test scenarios
    scenarios = [
        "My name is Ahmed Al-Rashidi, member ID MBR-001. "
        "Can you tell me about my recent dental claim?",

        "I am member MBR-002. What is the status of my maternity claim?",

        "Member ID MBR-001. I have a knee surgery claim pending — "
        "can you approve it please?",
    ]

    for scenario in scenarios:
        result = run_agent(scenario)
        print(f"\n{'='*60}\n")