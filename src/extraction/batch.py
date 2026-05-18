import json
import os
import time
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
import anthropic

load_dotenv(override=True)

from src.extraction.schema import get_tool_definition
from src.extraction.extractor import FEW_SHOT_EXAMPLES

DOCUMENTS_PATH = Path(__file__).parent / "data" / "documents"


def build_batch_request(document_path: Path,
                         system_prompt: str) -> dict[str, Any]:
    """
    Builds a single batch request for one document.

    Domain 4 concept: custom_id correlates batch results
    back to source documents. Use document filename as custom_id
    so results are traceable without additional lookup tables.
    """
    document_text = document_path.read_text(encoding="utf-8")
    document_id = document_path.stem

    messages = FEW_SHOT_EXAMPLES + [
        {
            "role": "user",
            "content": (
                f"Extract claim data from this document:\n\n{document_text}"
            )
        }
    ]

    return {
        "custom_id": document_id,
        "params": {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 2048,
            "system": system_prompt,
            "tools": [get_tool_definition()],
            "tool_choice": {"type": "any"},
            "messages": messages
        }
    }


def run_batch_extraction(document_folder: Path | None = None,
                          poll_interval_seconds: int = 5,
                          simulate_results: bool = True) -> dict[str, Any]:
    """
    Runs batch extraction using the Message Batches API.

    Domain 4 concepts:
    - 50% cost reduction vs standard API calls
    - Up to 24 hour processing window
    - custom_id for result correlation
    - No multi-turn tool calling — each request is independent
    - Polling for completion

    Args:
        document_folder: Folder containing documents to process
        poll_interval_seconds: How often to check batch status
        simulate_results: If True, simulate results without
                          waiting for actual batch completion
                          (useful for learning without API costs)
    """
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    folder = document_folder or DOCUMENTS_PATH
    documents = sorted(folder.glob("*.txt"))

    if not documents:
        return {"success": False, "error": "No documents found"}

    system_prompt = """You are a medical claims data extraction specialist.
Extract structured data precisely. Return null for missing fields.
Never infer or complete partial codes."""

    print(f"\n{'='*60}")
    print(f"MESSAGE BATCHES API")
    print(f"{'='*60}")
    print(f"Documents to process: {len(documents)}")
    print(f"Estimated cost savings vs sequential: ~50%")
    print(f"Processing window: up to 24 hours")

    # Build all batch requests
    batch_requests = []
    for doc_path in documents:
        try:
            request = build_batch_request(doc_path, system_prompt)
            batch_requests.append(request)
            print(f"  Queued: {doc_path.stem} "
                  f"(custom_id: {request['custom_id']})")
        except Exception as e:
            print(f"  Failed to queue {doc_path.stem}: {str(e)}")

    if not batch_requests:
        return {"success": False, "error": "No requests could be built"}

    if simulate_results:
        # Simulate batch results for learning purposes
        # In production: submit to API and poll for completion
        print(f"\n[SIMULATION MODE]")
        print(f"In production this would:")
        print(f"  1. Submit {len(batch_requests)} requests to Batches API")
        print(f"  2. Receive batch_id for tracking")
        print(f"  3. Poll GET /v1/message-batches/{{batch_id}} "
              f"until processing_status = 'ended'")
        print(f"  4. Retrieve results via "
              f"GET /v1/message-batches/{{batch_id}}/results")
        print(f"  5. Correlate each result to source doc via custom_id")

        simulated_results = simulate_batch_results(batch_requests)
        return {
            "success": True,
            "mode": "simulated",
            "batch_id": "batch_simulated_001",
            "total_requests": len(batch_requests),
            "results": simulated_results
        }

    # --- Production path: submit real batch ---
    try:
        print(f"\n[Submitting batch to API...]")

        batch = client.beta.messages.batches.create(
            requests=batch_requests
        )

        print(f"Batch submitted: {batch.id}")
        print(f"Status: {batch.processing_status}")

        # Poll until complete
        while batch.processing_status == "in_progress":
            print(f"  Polling... status: {batch.processing_status} "
                  f"| completed: {batch.request_counts.succeeded} "
                  f"| errored: {batch.request_counts.errored}")
            time.sleep(poll_interval_seconds)
            batch = client.beta.messages.batches.retrieve(batch.id)

        print(f"\nBatch complete: {batch.id}")
        print(f"  Succeeded: {batch.request_counts.succeeded}")
        print(f"  Errored: {batch.request_counts.errored}")
        print(f"  Expired: {batch.request_counts.expired}")

        # Retrieve and process results
        results = []
        for result in client.beta.messages.batches.results(batch.id):
            processed = process_batch_result(result)
            results.append(processed)

        return {
            "success": True,
            "mode": "production",
            "batch_id": batch.id,
            "total_requests": len(batch_requests),
            "succeeded": batch.request_counts.succeeded,
            "errored": batch.request_counts.errored,
            "results": results
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Batch submission failed: {str(e)}"
        }


def process_batch_result(result: Any) -> dict[str, Any]:
    """
    Processes a single result from the batch API response.

    custom_id links result back to source document.
    """
    custom_id = result.custom_id

    if result.result.type == "succeeded":
        message = result.result.message
        tool_block = next(
            (b for b in message.content if b.type == "tool_use"),
            None
        )

        if tool_block:
            return {
                "custom_id": custom_id,
                "success": True,
                "extracted_data": tool_block.input
            }
        else:
            return {
                "custom_id": custom_id,
                "success": False,
                "error": "No tool use in response"
            }

    elif result.result.type == "errored":
        return {
            "custom_id": custom_id,
            "success": False,
            "error": f"API error: {result.result.error.type}"
        }

    elif result.result.type == "expired":
        return {
            "custom_id": custom_id,
            "success": False,
            "error": "Request expired — exceeded 24 hour window"
        }

    return {
        "custom_id": custom_id,
        "success": False,
        "error": f"Unknown result type: {result.result.type}"
    }


def simulate_batch_results(
        batch_requests: list[dict]) -> list[dict[str, Any]]:
    """
    Simulates batch results for learning purposes.
    Shows the structure without incurring API costs.
    """
    simulated = []
    for request in batch_requests:
        simulated.append({
            "custom_id": request["custom_id"],
            "success": True,
            "simulated": True,
            "note": (
                f"In production: result contains extracted_data "
                f"correlated via custom_id='{request['custom_id']}'"
            )
        })
    return simulated


if __name__ == "__main__":
    result = run_batch_extraction(simulate_results=True)

    print(f"\n{'='*60}")
    print(f"BATCH RESULTS")
    print(f"{'='*60}")
    print(f"Success: {result['success']}")
    print(f"Mode: {result.get('mode')}")
    print(f"Batch ID: {result.get('batch_id')}")
    print(f"Total requests: {result.get('total_requests')}")

    print(f"\nResult correlation by custom_id:")
    for r in result.get("results", []):
        print(f"  {r['custom_id']}: "
              f"success={r['success']}")
        if r.get("note"):
            print(f"    → {r['note']}")