import json
import os
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
import anthropic

load_dotenv(override=True)

PLANS_PATH = Path(__file__).parent.parent / "data" / "plans.json"


def load_plans() -> dict:
    with open(PLANS_PATH) as f:
        return json.load(f)


def run_policy_agent(plan_type: str,
                     procedure: str,
                     question: str) -> dict[str, Any]:
    """
    Specialised subagent — reads plan terms for a specific procedure.

    Operates with isolated context. Receives only what it needs:
    plan type, procedure name, and the specific question to answer.
    Returns structured findings with source attribution.
    """
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    try:
        plans = load_plans()
        plan_data = plans.get(plan_type)

        if not plan_data:
            return {
                "success": False,
                "agent": "policy_agent",
                "findings": None,
                "error": f"No plan data found for plan type: {plan_type}"
            }

        # Build focused subagent prompt — only what this agent needs
        prompt = f"""You are a plan coverage specialist. 
        
Your task: Analyse the insurance plan terms below and answer 
the specific question provided. Be precise and factual.
Only report what the plan data explicitly states.
Never infer or assume coverage — if it is not stated, say so.

Plan type: {plan_type}
Procedure in question: {procedure}
Question: {question}

Plan data:
{json.dumps(plan_data, indent=2)}

Respond in this exact JSON structure:
{{
  "covered": true or false or "conditional",
  "coverage_summary": "one sentence summary",
  "requirements": ["list", "of", "requirements"],
  "exclusions": ["list", "of", "exclusions"],
  "max_benefit_sar": number or null,
  "gaps_or_uncertainties": "anything unclear or unstated in the plan data",
  "source": "AlShifa Insurance {plan_type} Plan Terms"
}}

Return only the JSON object. No preamble."""

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        raw_text = response.content[0].text.strip()

        # Clean JSON if wrapped in markdown code blocks
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        findings = json.loads(raw_text)

        return {
            "success": True,
            "agent": "policy_agent",
            "plan_type": plan_type,
            "procedure": procedure,
            "findings": findings,
            "error": None
        }

    except json.JSONDecodeError as e:
        return {
            "success": False,
            "agent": "policy_agent",
            "findings": None,
            "error": f"Failed to parse agent response as JSON: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "agent": "policy_agent",
            "findings": None,
            "error": f"Policy agent failed: {str(e)}"
        }