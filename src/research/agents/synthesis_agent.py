import json
import os
from typing import Any
from dotenv import load_dotenv
import anthropic

load_dotenv(override=True)


def run_synthesis_agent(
    question: str,
    member_name: str,
    plan_type: str,
    policy_findings: dict | None,
    regulatory_findings: dict | None,
    coverage_gaps: list[str]
) -> dict[str, Any]:
    """
    Synthesis subagent — reconciles findings from policy and regulatory agents.

    Receives explicit context injected by coordinator.
    Never communicates directly with other subagents.
    Surfaces conflicts rather than resolving them arbitrarily.

    Domain 5 concept: conflicting source data must be preserved
    with attribution — never arbitrarily select one source.
    """
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Build the context block — passed explicitly, never inherited
    context_block = f"""
Member: {member_name}
Plan type: {plan_type}
Original question: {question}

Policy agent findings:
{json.dumps(policy_findings, indent=2) if policy_findings else "NOT AVAILABLE — policy agent failed or timed out"}

Regulatory agent findings:
{json.dumps(regulatory_findings, indent=2) if regulatory_findings else "NOT AVAILABLE — regulatory agent failed or timed out"}

Coverage gaps in this research:
{chr(10).join(f'- {gap}' for gap in coverage_gaps) if coverage_gaps else "None identified"}
"""

    prompt = f"""You are a senior insurance coverage analyst.

Your task: Synthesise the research findings below into a clear,
accurate answer for the member. 

Critical rules:
- If policy findings and regulatory findings conflict, preserve BOTH
  with clear attribution — never arbitrarily choose one
- If a source is missing, explicitly state what could not be verified
- Never fabricate information not present in the findings
- Use plain language — the member is not an insurance expert

{context_block}

Respond in this exact JSON structure:
{{
  "answer_summary": "2-3 sentence plain language answer",
  "covered_under_plan": true or false or "conditional" or "unknown",
  "key_requirements": ["list of requirements member must meet"],
  "member_rights": ["list of relevant member rights"],
  "conflicts_found": [
    {{
      "description": "description of conflict",
      "policy_position": "what the plan says",
      "regulatory_position": "what the regulator requires",
      "recommendation": "how member should proceed"
    }}
  ],
  "coverage_gaps": ["list of things that could not be verified"],
  "next_steps": ["list of concrete actions member should take"],
  "sources": ["list of sources used"],
  "confidence": "high or medium or low",
  "confidence_reason": "why this confidence level"
}}

Return only the JSON object. No preamble."""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        )

        raw_text = response.content[0].text.strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        synthesis = json.loads(raw_text)

        return {
            "success": True,
            "agent": "synthesis_agent",
            "synthesis": synthesis,
            "error": None
        }

    except json.JSONDecodeError as e:
        return {
            "success": False,
            "agent": "synthesis_agent",
            "synthesis": None,
            "error": f"Failed to parse synthesis response: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "agent": "synthesis_agent",
            "synthesis": None,
            "error": f"Synthesis agent failed: {str(e)}"
        }