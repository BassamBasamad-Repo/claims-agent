import json
from src.research.agents.coordinator import run_coordinator


def run_research_pipeline(member_name: str,
                           plan_type: str,
                           question: str) -> None:
    """
    Entry point for the multi-agent research pipeline.
    Runs the coordinator and prints a formatted report.
    """
    result = run_coordinator(
        member_name=member_name,
        plan_type=plan_type,
        question=question
    )

    print(f"\n{'='*60}")
    print("RESEARCH REPORT")
    print(f"{'='*60}")

    if not result["success"]:
        print(f"ERROR: {result['error']}")
        return

    synthesis = result["synthesis"]

    print(f"\nQuestion: {result['question']}")
    print(f"Member: {result['member_name']} | Plan: {result['plan_type']}")
    print(f"Procedure identified: {result['procedure']}")

    print(f"\n--- Answer ---")
    print(synthesis.get("answer_summary", "No summary available"))

    print(f"\n--- Coverage status ---")
    print(f"Covered: {synthesis.get('covered_under_plan', 'unknown')}")

    requirements = synthesis.get("key_requirements", [])
    if requirements:
        print(f"\n--- Requirements ---")
        for req in requirements:
            print(f"  • {req}")

    conflicts = synthesis.get("conflicts_found", [])
    if conflicts:
        print(f"\n--- Conflicts between plan and regulations ---")
        for conflict in conflicts:
            print(f"  Issue: {conflict.get('description')}")
            print(f"  Plan says: {conflict.get('policy_position')}")
            print(f"  Regulator says: {conflict.get('regulatory_position')}")
            print(f"  Recommendation: {conflict.get('recommendation')}")

    gaps = synthesis.get("coverage_gaps", [])
    if gaps:
        print(f"\n--- Coverage gaps ---")
        for gap in gaps:
            print(f"  ⚠ {gap}")

    next_steps = synthesis.get("next_steps", [])
    if next_steps:
        print(f"\n--- Next steps ---")
        for step in next_steps:
            print(f"  → {step}")

    rights = synthesis.get("member_rights", [])
    if rights:
        print(f"\n--- Your rights ---")
        for right in rights:
            print(f"  ✓ {right}")

    sources = synthesis.get("sources", [])
    if sources:
        print(f"\n--- Sources ---")
        for source in sources:
            print(f"  [{source}]")

    print(f"\nConfidence: {synthesis.get('confidence', 'unknown').upper()}")
    print(f"Reason: {synthesis.get('confidence_reason', '')}")

    if result.get("coverage_gaps"):
        print(f"\n⚠ Research gaps: {len(result['coverage_gaps'])} item(s) "
              f"could not be fully verified")


if __name__ == "__main__":
    # Test scenario 1 — Gold plan member asking about bariatric surgery
    print("\n" + "="*60)
    print("SCENARIO 1: Gold plan — bariatric surgery coverage")
    print("="*60)
    run_research_pipeline(
        member_name="Ahmed Al-Rashidi",
        plan_type="Gold",
        question="Does my policy cover bariatric surgery and "
                 "what are the requirements?"
    )

    # Test scenario 2 — Silver plan member — should find coverage gap
    print("\n\n" + "="*60)
    print("SCENARIO 2: Silver plan — bariatric surgery not covered")
    print("="*60)
    run_research_pipeline(
        member_name="Fatima Al-Zahrani",
        plan_type="Silver",
        question="Does my insurance cover weight loss surgery?"
    )

    # Scenario 3 — timeout simulation
    print("\n\n" + "="*60)
    print("SCENARIO 3: Regulatory agent timeout — partial failure")
    print("="*60)

    from src.research.agents import regulatory_agent as reg_module
    original_run = reg_module.run_regulatory_agent

    def simulated_timeout(procedure, question, **kwargs):
        print(f"  [TIMEOUT SIMULATION] Regulatory agent timed out")
        return {
            "success": False,
            "agent": "regulatory_agent",
            "findings": None,
            "error": "transient — agent timeout after 30 seconds"
        }

    reg_module.run_regulatory_agent = simulated_timeout

    run_research_pipeline(
        member_name="Khalid Al-Otaibi",
        plan_type="Gold",
        question="Does my policy cover bariatric surgery?"
    )

    reg_module.run_regulatory_agent = original_run
    

    # Test semantic inference directly
    print("\n" + "="*60)
    print("SEMANTIC INFERENCE TESTS")
    print("="*60)

    import anthropic, os
    from dotenv import load_dotenv
    load_dotenv(override=True)

    test_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    from src.research.agents.coordinator import extract_procedure

    test_queries = [
        "Does my plan cover my ayes?",
        "What about my teeths cleaning?",
        "Is weigh loss sergury covered?",
        "Can I get my hart checked?",
        "Coverage for having a baby?",
        "My knees are bad, is replacment covered?",
        "Do I need glasses coverage?",
    ]

    for query in test_queries:
        procedure = extract_procedure(test_client, query)
        print(f"  '{query}'")
        print(f"  → {procedure}\n")