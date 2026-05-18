from typing import Any

# This is the canonical extraction schema.
# Exam concept: required contains only fields guaranteed to exist.
# Optional fields use nullable types to prevent hallucination.

CLAIM_EXTRACTION_SCHEMA = {
    "name": "extract_claim_data",
    "description": (
        "Extracts structured data from an insurance claim form. "
        "For missing or illegible fields, return null — never invent values. "
        "For bilingual documents with conflicting data, extract both versions."
    ),
    "input_schema": {
        "type": "object",
        "properties": {

            # --- Always present — required ---
            "claim_reference": {
                "type": "string",
                "description": "Claim reference or ID from the document"
            },
            "member_id": {
                "type": "string",
                "description": "Member ID (format: MBR-XXX)"
            },
            "amount_claimed_sar": {
                "type": "number",
                "description": "Total amount claimed in SAR"
            },

            # --- Usually present — nullable ---
            "member_name": {
                "type": ["string", "null"],
                "description": "Full name of the member or null if absent"
            },
            "policy_number": {
                "type": ["string", "null"],
                "description": "Policy number or null if absent"
            },
            "date_of_service": {
                "type": ["string", "null"],
                "description": "Date of service (any format found) or null"
            },
            "provider_name": {
                "type": ["string", "null"],
                "description": "Healthcare provider name or null if absent"
            },
            "physician_name": {
                "type": ["string", "null"],
                "description": "Attending physician name or null if absent"
            },

            # --- Clinical fields — nullable, hallucination risk ---
            "primary_diagnosis_icd": {
                "type": ["string", "null"],
                "description": (
                    "Primary ICD-10 code exactly as written. "
                    "Return null if absent — never infer or complete partial codes."
                )
            },
            "primary_diagnosis_text": {
                "type": ["string", "null"],
                "description": "Primary diagnosis description or null"
            },
            "secondary_diagnosis_icd": {
                "type": ["string", "null"],
                "description": "Secondary ICD-10 code or null if absent"
            },
            "procedure_code": {
                "type": ["string", "null"],
                "description": "CPT or procedure code or null if absent"
            },
            "procedure_description": {
                "type": ["string", "null"],
                "description": "Procedure description or null"
            },

            # --- Bilingual conflict fields ---
            # These only populate when Arabic and English sections conflict
            "icd_conflict": {
                "type": ["object", "null"],
                "description": (
                    "Populated only when Arabic and English ICD codes differ. "
                    "Null for monolingual documents or when codes match."
                ),
                "properties": {
                    "arabic_icd": {"type": "string"},
                    "english_icd": {"type": "string"},
                    "arabic_diagnosis": {"type": ["string", "null"]},
                    "english_diagnosis": {"type": ["string", "null"]}
                }
            },

            # --- Quality signals ---
            "document_language": {
                "type": "string",
                "enum": ["english", "arabic", "bilingual"],
                "description": "Primary language of the document"
            },
            "ocr_quality": {
                "type": "string",
                "enum": ["high", "medium", "low", "unknown"],
                "description": "Estimated quality of document text"
            },
            "extraction_confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": (
                    "Overall confidence in extraction accuracy. "
                    "Low when: OCR quality is low, fields are missing, "
                    "or data conflicts exist."
                )
            },
            "fields_requiring_review": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "List of field names that need human verification. "
                    "Include: missing required fields, partial codes, "
                    "OCR artifacts, bilingual conflicts."
                )
            }
        },
        "required": [
            "claim_reference",
            "member_id",
            "amount_claimed_sar",
            "document_language",
            "ocr_quality",
            "extraction_confidence",
            "fields_requiring_review"
        ]
    }
}


def get_tool_definition() -> dict:
    """Returns the tool definition for use in Claude API calls."""
    return CLAIM_EXTRACTION_SCHEMA


def get_required_fields() -> list[str]:
    """Returns the list of fields that must always be present."""
    return CLAIM_EXTRACTION_SCHEMA["input_schema"]["required"]


def get_nullable_fields() -> list[str]:
    """Returns fields that may legitimately be null."""
    all_fields = set(
        CLAIM_EXTRACTION_SCHEMA["input_schema"]["properties"].keys()
    )
    required = set(get_required_fields())
    return list(all_fields - required)