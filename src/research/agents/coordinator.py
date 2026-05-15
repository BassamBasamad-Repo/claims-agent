import os
from typing import Any
from dotenv import load_dotenv
import anthropic
import concurrent.futures
import time

load_dotenv(override=True)


def run_coordinator(
    member_name: str,
    plan_type: str,
    question: str
) -> dict[str, Any]:
    """
    Coordinator agent — orchestrates the research pipeline.

    Responsibilities:
    1. Decompose the question into subagent tasks
    2. Run independent subagents (policy + regulatory) 
    3. Collect results and identify failures
    4. Pass structured findings to synthesis subagent
    5. Return final synthesis to caller

    Domain 1 concept: coordinator manages all inter-subagent
    communication. Subagents never communicate directly.
    """
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    print(f"\n{'='*60}")
    print(f"Coordinator: starting research pipeline")
    print(f"Member: {member_name} | Plan: {plan_type}")
    print(f"Question: {question}")
    print(f"{'='*60}")

    # Import here to avoid circular imports
    from src.research.agents.policy_agent import run_policy_agent
    from src.research.agents.regulatory_agent import run_regulatory_agent
    from src.research.agents.synthesis_agent import run_synthesis_agent

    procedure = extract_procedure(client, question)
    print(f"\n[Coordinator] Identified procedure: {procedure}")

    # --- PHASE 1: Parallel independent research ---
    # Policy and regulatory agents are independent of each other.
    # Run both simultaneously using ThreadPoolExecutor.
    # Total wait time = max(policy_time, regulatory_time)
    # NOT sum(policy_time + regulatory_time)

    print(f"\n[Coordinator] Spawning policy and regulatory agents in parallel...")

    # At the start of Phase 1
    phase1_start = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:

        policy_future = executor.submit(
            run_policy_agent,
            plan_type=plan_type,
            procedure=procedure,
            question=question
        )

        regulatory_future = executor.submit(
            run_regulatory_agent,
            procedure=procedure,
            question=question
        )

       # Collect policy result
    try:
        policy_result = policy_future.result(timeout=60)
    except concurrent.futures.TimeoutError:
        print(f"[Coordinator] WARNING: Policy agent timed out")
        policy_result = {
            "success": False,
            "agent": "policy_agent",
            "findings": None,
            "error": "transient — agent timeout after 60 seconds"
        }

    # Collect regulatory result
    try:
        regulatory_result = regulatory_future.result(timeout=60)
    except concurrent.futures.TimeoutError:
        print(f"[Coordinator] WARNING: Regulatory agent timed out")
        regulatory_result = {
            "success": False,
            "agent": "regulatory_agent",
            "findings": None,
            "error": "transient — agent timeout after 60 seconds"
        }

    print(f"[Coordinator] Policy agent: success={policy_result['success']}")
    print(f"[Coordinator] Regulatory agent: success={regulatory_result['success']}")
    phase1_duration = time.time() - phase1_start
    print(f"[Coordinator] Parallel research completed in "
      f"{phase1_duration:.1f}s")
    
    
    # --- PHASE 2: Assess partial failures ---
    coverage_gaps = []

    if not policy_result["success"]:
        coverage_gaps.append(
            f"Plan terms could not be retrieved: {policy_result['error']}"
        )
        print(f"[Coordinator] WARNING: Policy agent failed — "
              f"proceeding with gap annotation")

    if not regulatory_result["success"]:
        coverage_gaps.append(
            f"Regulatory requirements could not be retrieved: "
            f"{regulatory_result['error']}"
        )
        print(f"[Coordinator] WARNING: Regulatory agent failed — "
              f"proceeding with gap annotation")

    # If both agents failed — cannot produce useful synthesis
    if not policy_result["success"] and not regulatory_result["success"]:
        return {
            "success": False,
            "question": question,
            "synthesis": None,
            "error": (
                "Both research agents failed. Unable to produce "
                "a reliable answer. Please contact support."
            )
        }

    # --- PHASE 3: Pass findings explicitly to synthesis agent ---
    # Coordinator extracts findings — synthesis agent receives structured data
    # not raw agent outputs
    print(f"\n[Coordinator] Spawning synthesis agent with collected findings...")

    policy_findings = policy_result.get("findings") if policy_result[
        "success"] else None
    regulatory_findings = regulatory_result.get("findings") if regulatory_result[
        "success"] else None

    synthesis_result = run_synthesis_agent(
        question=question,
        member_name=member_name,
        plan_type=plan_type,
        policy_findings=policy_findings,
        regulatory_findings=regulatory_findings,
        coverage_gaps=coverage_gaps
    )

    print(f"[Coordinator] Synthesis agent: "
          f"success={synthesis_result['success']}")

    if not synthesis_result["success"]:
        return {
            "success": False,
            "question": question,
            "synthesis": None,
            "error": f"Synthesis failed: {synthesis_result['error']}"
        }

    return {
        "success": True,
        "question": question,
        "member_name": member_name,
        "plan_type": plan_type,
        "procedure": procedure,
        "policy_result": policy_result,
        "regulatory_result": regulatory_result,
        "synthesis": synthesis_result["synthesis"],
        "coverage_gaps": coverage_gaps,
        "error": None
    }


def extract_procedure(client: anthropic.Anthropic,
                      question: str) -> str:
    """
    Extracts and normalises the medical procedure from the member's question.

    Uses semantic inference to handle:
    - Typos and misspellings ("ayes" → ophthalmology)
    - Informal language ("teeth cleaning" → dental_cleaning)
    - Body part references ("my eyes" → ophthalmology_consultation)
    - Ambiguous phrasing ("heart stuff" → cardiology_consultation)

    Returns a normalised snake_case procedure name matching
    the data store vocabulary.
    """
    known_procedures = [
        "bariatric_surgery",
        "ophthalmology_consultation",
        "dental_cleaning",
        "dental_surgery",
        "cardiology_consultation",
        "physiotherapy",
        "maternity_delivery",
        "knee_replacement",
        "hip_replacement",
        "cataract_surgery",
        "general_surgery",
        "outpatient_consultation",
        "inpatient_admission"
    ]

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=128,
        messages=[{
            "role": "user",
            "content": f"""You are a medical terminology specialist.

A member asked: "{question}"

Your task:
1. Identify what medical procedure or service the member is asking about
2. Handle typos, informal language, and body part references
3. Return the best matching procedure from this list:
{chr(10).join(f'   - {p}' for p in known_procedures)}

If none match closely, return the most accurate snake_case medical 
term you can infer from the question.

Examples:
- "my ayes" or "eye coverage" → ophthalmology_consultation
- "teeth" or "dental stuff" → dental_cleaning
- "weight loss surgery" or "stomach surgery" → bariatric_surgery
- "heart checkup" → cardiology_consultation
- "having a baby" → maternity_delivery

Return only the procedure name in snake_case. No explanation."""
        }]
    )

    result = response.content[0].text.strip().lower()
    result = result.replace(" ", "_").replace("-", "_")

    # Remove any punctuation that slipped through
    result = "".join(c for c in result if c.isalnum() or c == "_")

    print(f"  [Procedure extraction] '{question[:50]}...' → '{result}'")
    return result


