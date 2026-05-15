import json
import os
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
import anthropic

load_dotenv(override=True)

REGULATIONS_PATH = Path(__file__).parent.parent / "data" / "regulations.json"


def load_regulations() -> dict:
    with open(REGULATIONS_PATH) as f:
        return json.load(f)


def run_regulatory_agent(procedure: str,
                         question: str) -> dict[str, Any]:
    """
    Specialised subagent — reads regulatory requirements for a procedure.

    Operates with isolated context. Independent of policy agent.
    Returns regulatory findings with source attribution.
    """
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    try:
        regulations = load_regulations()
        procedure_key = procedure.lower().replace(" ", "_")
        reg_data = regulations.get(procedure_key)

        if not reg_data:
            return {
                "success": False,
                "agent": "regulatory_agent",
                "findings": None,
                "error": f"No regulatory data found for procedure: {procedure}"
            }

        prompt = f"""You are a healthcare regulatory specialist.

Your task: Analyse the regulatory requirements below and answer
the specific question provided. Focus on what regulators mandate
versus what is left to insurer discretion.

Procedure: {procedure}
Question: {question}

Regulatory data:
{json.dumps(reg_data, indent=2)}

Respond in this exact JSON structure:
{{
  "mandatory_criteria": ["list of criteria the member must meet"],
  "insurer_obligations": ["list of what the insurer must do"],
  "member_rights": ["list of member rights"],
  "regulatory_summary": "one sentence summary of regulatory position",
  "conflicts_with_plan_terms": "note any areas where plan terms commonly conflict with regulations",
  "source": "{reg_data.get('regulatory_body', 'Health Regulatory Authority')}"
}}

Return only the JSON object. No preamble."""

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        raw_text = response.content[0].text.strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        findings = json.loads(raw_text)

        return {
            "success": True,
            "agent": "regulatory_agent",
            "procedure": procedure,
            "findings": findings,
            "error": None
        }

    except json.JSONDecodeError as e:
        return {
            "success": False,
            "agent": "regulatory_agent",
            "findings": None,
            "error": f"Failed to parse agent response as JSON: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "agent": "regulatory_agent",
            "findings": None,
            "error": f"Regulatory agent failed: {str(e)}"
        }