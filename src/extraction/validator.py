import json
from typing import Any
from src.extraction.schema import get_required_fields


class ValidationError(Exception):
    """Raised when extracted data fails schema validation."""
    pass


def validate_extraction(extracted_data: dict[str, Any],
                         document_id: str) -> dict[str, Any]:
    """
    Validates extracted data against schema requirements.

    Domain 4 concept: validation-retry loop.
    Returns structured validation result — never raises.
    The caller decides whether to retry based on the result.
    """
    errors = []
    warnings = []
    required_fields = get_required_fields()

    # Check required fields are present and not null
    for field in required_fields:
        if field not in extracted_data:
            errors.append({
                "field": field,
                "issue": "required_field_missing",
                "detail": f"Field '{field}' is required but absent from extraction"
            })
        elif extracted_data[field] is None:
            errors.append({
                "field": field,
                "issue": "required_field_null",
                "detail": f"Field '{field}' is required but returned null"
            })

    # Validate amount is positive number
    amount = extracted_data.get("amount_claimed_sar")
    if amount is not None:
        if not isinstance(amount, (int, float)):
            errors.append({
                "field": "amount_claimed_sar",
                "issue": "wrong_type",
                "detail": f"Expected number, got {type(amount).__name__}"
            })
        elif amount <= 0:
            errors.append({
                "field": "amount_claimed_sar",
                "issue": "invalid_value",
                "detail": "Amount must be greater than zero"
            })

    # Validate enum fields
    valid_languages = {"english", "arabic", "bilingual"}
    doc_lang = extracted_data.get("document_language")
    if doc_lang and doc_lang not in valid_languages:
        errors.append({
            "field": "document_language",
            "issue": "invalid_enum_value",
            "detail": f"'{doc_lang}' is not a valid language. "
                      f"Must be one of: {valid_languages}"
        })

    valid_confidence = {"high", "medium", "low"}
    confidence = extracted_data.get("extraction_confidence")
    if confidence and confidence not in valid_confidence:
        errors.append({
            "field": "extraction_confidence",
            "issue": "invalid_enum_value",
            "detail": f"'{confidence}' is not valid. "
                      f"Must be one of: {valid_confidence}"
        })

    # Validate ICD conflict structure if present
    icd_conflict = extracted_data.get("icd_conflict")
    if icd_conflict is not None:
        if not isinstance(icd_conflict, dict):
            errors.append({
                "field": "icd_conflict",
                "issue": "wrong_type",
                "detail": "icd_conflict must be an object when present"
            })
        else:
            for required_key in ["arabic_icd", "english_icd"]:
                if required_key not in icd_conflict:
                    errors.append({
                        "field": f"icd_conflict.{required_key}",
                        "issue": "required_subfield_missing",
                        "detail": f"icd_conflict.{required_key} is required "
                                  f"when icd_conflict is present"
                    })

    # Warnings — not blocking but worth noting
    fields_for_review = extracted_data.get("fields_requiring_review", [])
    if len(fields_for_review) > 5:
        warnings.append(
            f"High number of fields requiring review ({len(fields_for_review)}) "
            f"— consider manual processing for this document"
        )

    return {
        "valid": len(errors) == 0,
        "document_id": document_id,
        "errors": errors,
        "warnings": warnings,
        "error_count": len(errors),
        "warning_count": len(warnings)
    }


def build_retry_prompt(document_text: str,
                        extracted_data: dict,
                        validation_result: dict) -> str:
    """
    Builds a targeted retry prompt when validation fails.

    Domain 4 concept: retry with specific error context.
    The model receives the original document, its previous attempt,
    and the exact validation errors — enabling targeted correction.

    This is more effective than re-running the original prompt
    because the model can see exactly what went wrong.
    """
    error_descriptions = []
    for error in validation_result["errors"]:
        error_descriptions.append(
            f"- Field '{error['field']}': {error['detail']}"
        )

    return f"""Your previous extraction attempt had validation errors.

Original document:
{document_text}

Your previous extraction:
{json.dumps(extracted_data, indent=2)}

Validation errors that must be fixed:
{chr(10).join(error_descriptions)}

Please re-extract the data, fixing only the identified errors.
Do not change fields that passed validation.
Remember: return null for missing fields — never invent values."""