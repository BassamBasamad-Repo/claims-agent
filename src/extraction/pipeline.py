import json
import os
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
import anthropic

load_dotenv(override=True)

from src.extraction.extractor import extract_claim, FEW_SHOT_EXAMPLES
from src.extraction.validator import validate_extraction, build_retry_prompt
from src.extraction.schema import get_tool_definition

DOCUMENTS_PATH = Path(__file__).parent / "data" / "documents"
MAX_RETRIES = 2


def process_document(document_path: Path) -> dict[str, Any]:
    """
    Processes a single document through the extraction pipeline.

    Domain 4 concepts:
    - tool_use forces structured output
    - Validation catches schema violations
    - Retry sends specific error context back to model
    - Confidence routing — low confidence → human review queue

    Args:
        document_path: Path to the document file

    Returns full processing result including
    extraction, validation, and routing decision.
    """
    document_id = document_path.stem
    print(f"\n[Pipeline] Processing: {document_id}")

    # Read document
    try:
        document_text = document_path.read_text(encoding="utf-8")
    except Exception as e:
        return {
            "success": False,
            "document_id": document_id,
            "error": f"Could not read document: {str(e)}"
        }

    # --- Attempt 1: Initial extraction ---
    print(f"  [Attempt 1] Extracting...")
    result = extract_claim(document_text, document_id)

    if not result["success"]:
        return {
            "success": False,
            "document_id": document_id,
            "attempts": 1,
            "error": result["error"]
        }

    validation = validate_extraction(result["extracted_data"], document_id)
    print(f"  [Attempt 1] Valid: {validation['valid']} | "
          f"Errors: {validation['error_count']}")

    if validation["valid"]:
        return build_success_result(
            document_id, result["extracted_data"],
            validation, attempts=1
        )

    # --- Retry loop: up to MAX_RETRIES additional attempts ---
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    current_data = result["extracted_data"]
    current_validation = validation

    for attempt in range(2, MAX_RETRIES + 2):
        print(f"  [Attempt {attempt}] Retrying with error context...")

        retry_prompt = build_retry_prompt(
            document_text, current_data, current_validation
        )

        # Send retry with original few-shot examples preserved
        messages = FEW_SHOT_EXAMPLES + [
            {"role": "user", "content": retry_prompt}
        ]

        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                tools=[get_tool_definition()],
                tool_choice={"type": "any"},
                messages=messages
            )

            tool_block = next(
                (b for b in response.content if b.type == "tool_use"),
                None
            )

            if not tool_block:
                print(f"  [Attempt {attempt}] No tool use in retry response")
                break

            current_data = tool_block.input
            current_validation = validate_extraction(
                current_data, document_id
            )
            print(f"  [Attempt {attempt}] Valid: {current_validation['valid']} | "
                  f"Errors: {current_validation['error_count']}")

            if current_validation["valid"]:
                return build_success_result(
                    document_id, current_data,
                    current_validation, attempts=attempt
                )

        except Exception as e:
            print(f"  [Attempt {attempt}] Error: {str(e)}")
            break

    # All retries exhausted — return best attempt with validation errors
    print(f"  [Pipeline] Max retries reached — routing to human review")
    return {
        "success": False,
        "document_id": document_id,
        "attempts": MAX_RETRIES + 1,
        "extracted_data": current_data,
        "validation": current_validation,
        "routing": "human_review",
        "routing_reason": "validation_failed_after_retries",
        "error": f"Validation failed after {MAX_RETRIES + 1} attempts"
    }


def build_success_result(document_id: str,
                          extracted_data: dict,
                          validation: dict,
                          attempts: int) -> dict[str, Any]:
    """
    Builds the final success result with confidence-based routing.

    Domain 5 concept: confidence calibration drives routing.
    Low confidence → human review regardless of validation passing.
    """
    confidence = extracted_data.get("extraction_confidence", "low")
    fields_for_review = extracted_data.get("fields_requiring_review", [])

    # Routing decision based on confidence and review flags
    if confidence == "low" or len(fields_for_review) > 3:
        routing = "human_review"
        routing_reason = (
            f"low_confidence" if confidence == "low"
            else f"high_review_field_count_{len(fields_for_review)}"
        )
    elif confidence == "medium" or len(fields_for_review) > 0:
        routing = "supervisor_spot_check"
        routing_reason = "medium_confidence_or_fields_flagged"
    else:
        routing = "auto_process"
        routing_reason = "high_confidence_no_review_flags"

    return {
        "success": True,
        "document_id": document_id,
        "attempts": attempts,
        "extracted_data": extracted_data,
        "validation": validation,
        "routing": routing,
        "routing_reason": routing_reason,
        "error": None
    }


def run_pipeline(document_folder: Path | None = None) -> list[dict]:
    """
    Runs the extraction pipeline on all documents in the folder.
    Returns results for all documents with routing decisions.
    """
    folder = document_folder or DOCUMENTS_PATH
    documents = sorted(folder.glob("*.txt"))

    if not documents:
        print(f"No documents found in {folder}")
        return []

    print(f"\n{'='*60}")
    print(f"EXTRACTION PIPELINE")
    print(f"Processing {len(documents)} documents")
    print(f"{'='*60}")

    results = []
    for doc_path in documents:
        result = process_document(doc_path)
        results.append(result)

    # Summary report
    print(f"\n{'='*60}")
    print(f"PIPELINE SUMMARY")
    print(f"{'='*60}")

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print(f"Total processed: {len(results)}")
    print(f"Successful extractions: {len(successful)}")
    print(f"Failed extractions: {len(failed)}")

    if successful:
        routing_counts = {}
        for r in successful:
            routing = r.get("routing", "unknown")
            routing_counts[routing] = routing_counts.get(routing, 0) + 1

        print(f"\nRouting breakdown:")
        for routing, count in routing_counts.items():
            print(f"  {routing}: {count}")

    if failed:
        print(f"\nFailed documents:")
        for r in failed:
            print(f"  {r['document_id']}: {r.get('error', 'unknown error')}")

    return results


if __name__ == "__main__":
    results = run_pipeline()

    print(f"\n{'='*60}")
    print(f"DETAILED RESULTS")
    print(f"{'='*60}")

    for result in results:
        print(f"\n--- {result['document_id']} ---")
        print(f"Success: {result['success']}")
        print(f"Attempts: {result.get('attempts', 'N/A')}")
        print(f"Routing: {result.get('routing', 'N/A')}")
        print(f"Routing reason: {result.get('routing_reason', 'N/A')}")

        if result.get("extracted_data"):
            data = result["extracted_data"]
            print(f"Member ID: {data.get('member_id')}")
            print(f"Amount: SAR {data.get('amount_claimed_sar')}")
            print(f"Confidence: {data.get('extraction_confidence')}")
            print(f"Language: {data.get('document_language')}")

            icd_conflict = data.get("icd_conflict")
            if icd_conflict:
                print(f"ICD CONFLICT DETECTED:")
                print(f"  Arabic: {icd_conflict.get('arabic_icd')}")
                print(f"  English: {icd_conflict.get('english_icd')}")

            review_fields = data.get("fields_requiring_review", [])
            if review_fields:
                print(f"Fields for review: {', '.join(review_fields)}")