import json
import os
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
import anthropic

load_dotenv(override=True)

from src.extraction.schema import get_tool_definition


# Few-shot examples — the most effective technique for
# consistent extraction across varied document formats.
# Examples show ambiguous case handling, not just happy path.
# Exam concept: few-shot for ambiguous scenarios, not obvious ones.

FEW_SHOT_EXAMPLES = [
    {
        "role": "user",
        "content": """Extract claim data from this document:

CLAIM FORM
Member: John Smith | ID: MBR-999
Diagnosis: hart falure
ICD: I50 (doctor wrote this — unclear if complete)
Amount: SR 2000"""
    },
    {
        "role": "assistant",
        "content": json.dumps({
            "claim_reference": "NOT_FOUND",
            "member_id": "MBR-999",
            "amount_claimed_sar": 2000,
            "member_name": "John Smith",
            "policy_number": None,
            "date_of_service": None,
            "provider_name": None,
            "physician_name": None,
            "primary_diagnosis_icd": "I50",
            "primary_diagnosis_text": "Heart failure",
            "secondary_diagnosis_icd": None,
            "procedure_code": None,
            "procedure_description": None,
            "icd_conflict": None,
            "document_language": "english",
            "ocr_quality": "low",
            "extraction_confidence": "low",
            "fields_requiring_review": [
                "claim_reference",
                "primary_diagnosis_icd",
                "policy_number",
                "date_of_service"
            ]
        })
    },
    {
        "role": "user",
        "content": """Extract claim data from this document:

نموذج مطالبة
العضو: محمد العتيبي | رقم العضو: MBR-777
ICD عربي: J18.9
ENGLISH SECTION: Member: Mohammed Al-Otaibi
ICD English: J18.1
Amount claimed: SAR 1,500"""
    },
    {
        "role": "assistant",
        "content": json.dumps({
            "claim_reference": "NOT_FOUND",
            "member_id": "MBR-777",
            "amount_claimed_sar": 1500,
            "member_name": "Mohammed Al-Otaibi",
            "policy_number": None,
            "date_of_service": None,
            "provider_name": None,
            "physician_name": None,
            "primary_diagnosis_icd": "J18.1",
            "primary_diagnosis_text": None,
            "secondary_diagnosis_icd": None,
            "procedure_code": None,
            "procedure_description": None,
            "icd_conflict": {
                "arabic_icd": "J18.9",
                "english_icd": "J18.1",
                "arabic_diagnosis": None,
                "english_diagnosis": None
            },
            "document_language": "bilingual",
            "ocr_quality": "high",
            "extraction_confidence": "medium",
            "fields_requiring_review": [
                "primary_diagnosis_icd",
                "icd_conflict"
            ]
        })
    }
]


def extract_claim(document_text: str,
                  document_id: str) -> dict[str, Any]:
    """
    Extracts structured claim data from a document using tool_use.

    Domain 4 concepts demonstrated:
    - tool_use forces structured output — no markdown, no prose
    - Few-shot examples handle ambiguous cases
    - Nullable fields prevent hallucination on missing data
    - Explicit criteria: "return null if absent — never infer"

    Args:
        document_text: Raw text content of the claim form
        document_id: Identifier for tracking and error reporting

    Returns structured dict with extracted data or error.
    """
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    system_prompt = """You are a medical claims data extraction specialist.

Extract structured data from insurance claim forms with precision.

Critical extraction rules:
1. Return null for ANY field not explicitly present in the document
   Never infer, complete, or guess missing values
2. For ICD codes: extract exactly as written — do not complete partial codes
   "I50" stays "I50" — do not expand to "I50.9"
3. For bilingual documents: if Arabic and English ICD codes differ,
   populate the icd_conflict field with both values
4. OCR quality signals: misspellings, garbled text, [illegible] markers
   all indicate low OCR quality
5. Fields requiring review: include any field where you have uncertainty,
   any partial data, any bilingual conflict, any OCR artifact
6. Amount extraction: convert to number — "SR 1,500" becomes 1500.0
   If currency is ambiguous, use the numeric value only"""

    # Build messages with few-shot examples
    messages = FEW_SHOT_EXAMPLES + [
        {
            "role": "user",
            "content": f"Extract claim data from this document:\n\n{document_text}"
        }
    ]

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            system=system_prompt,
            tools=[get_tool_definition()],
            tool_choice={"type": "any"},
            messages=messages
        )

        # Extract tool use block from response
        tool_use_block = next(
            (block for block in response.content
             if block.type == "tool_use"),
            None
        )

        if not tool_use_block:
            return {
                "success": False,
                "document_id": document_id,
                "extracted_data": None,
                "error": "Model did not use extraction tool — "
                         "unexpected response format"
            }

        extracted_data = tool_use_block.input

        return {
            "success": True,
            "document_id": document_id,
            "extracted_data": extracted_data,
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "document_id": document_id,
            "extracted_data": None,
            "error": f"Extraction failed: {str(e)}"
        }