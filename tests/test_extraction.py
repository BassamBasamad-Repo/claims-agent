import sys
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, '.')

from src.extraction.schema import (
    get_tool_definition,
    get_required_fields,
    get_nullable_fields,
    CLAIM_EXTRACTION_SCHEMA
)
from src.extraction.validator import validate_extraction, build_retry_prompt


class TestSchemaDesign:
    """
    Tests for JSON schema design decisions.

    Exam concept: required fields vs nullable fields.
    Required = must always exist.
    Nullable = may legitimately be absent.
    Default values do not prevent hallucination — nullable types do.
    """

    def test_required_fields_are_minimal(self):
        """
        Only fields guaranteed to exist should be required.
        Clinical fields like ICD codes must be nullable.
        """
        required = get_required_fields()
        nullable = get_nullable_fields()

        # Clinical fields must be nullable — never required
        for clinical_field in [
            "primary_diagnosis_icd",
            "secondary_diagnosis_icd",
            "procedure_code",
            "physician_name"
        ]:
            assert clinical_field in nullable, (
                f"{clinical_field} must be nullable — "
                f"it may be absent in real documents"
            )
            assert clinical_field not in required, (
                f"{clinical_field} must not be required — "
                f"requiring it forces hallucination when absent"
            )

    def test_nullable_fields_use_null_type(self):
        """
        Nullable fields must use ["type", "null"] union type.
        A field with type "string" and no null cannot return null.
        """
        properties = CLAIM_EXTRACTION_SCHEMA[
            "input_schema"]["properties"]
        nullable_fields = get_nullable_fields()

        for field_name in nullable_fields:
            field_def = properties.get(field_name, {})
            field_type = field_def.get("type")

            if field_type is not None:
                assert isinstance(field_type, list), (
                    f"Nullable field '{field_name}' must use list type "
                    f"like ['string', 'null'], not '{field_type}'"
                )
                assert "null" in field_type, (
                    f"Nullable field '{field_name}' must include 'null' "
                    f"in its type list"
                )

    def test_amount_is_required(self):
        """Amount claimed must always be present — it is the core claim value."""
        assert "amount_claimed_sar" in get_required_fields()

    def test_member_id_is_required(self):
        """Member ID is required for claim correlation."""
        assert "member_id" in get_required_fields()

    def test_icd_conflict_is_nullable(self):
        """
        ICD conflict field must be nullable.
        Monolingual documents will never have a conflict.
        Making it required would force false positives.
        """
        assert "icd_conflict" in get_nullable_fields()


class TestValidation:
    """
    Tests for the validation-retry loop pattern.

    Exam concept: validation sends specific errors back to model.
    The retry prompt includes the original document, the failed
    extraction, and the exact errors — enabling targeted correction.
    """

    def _valid_extraction(self) -> dict:
        """Minimal valid extraction for testing."""
        return {
            "claim_reference": "CLM-001",
            "member_id": "MBR-001",
            "amount_claimed_sar": 1500.0,
            "document_language": "english",
            "ocr_quality": "high",
            "extraction_confidence": "high",
            "fields_requiring_review": []
        }

    def test_valid_extraction_passes(self):
        """A complete valid extraction must pass validation."""
        result = validate_extraction(
            self._valid_extraction(), "test_doc"
        )
        assert result["valid"] is True
        assert result["error_count"] == 0

    def test_missing_required_field_fails(self):
        """Missing required field must produce a validation error."""
        data = self._valid_extraction()
        del data["member_id"]

        result = validate_extraction(data, "test_doc")

        assert result["valid"] is False
        assert result["error_count"] > 0
        field_names = [e["field"] for e in result["errors"]]
        assert "member_id" in field_names

    def test_null_required_field_fails(self):
        """
        Required field set to null must fail validation.
        Exam concept: required fields cannot be null —
        that forces hallucination. Nullable types are the solution.
        """
        data = self._valid_extraction()
        data["member_id"] = None

        result = validate_extraction(data, "test_doc")

        assert result["valid"] is False
        errors = [e for e in result["errors"]
                  if e["field"] == "member_id"]
        assert len(errors) > 0
        assert errors[0]["issue"] == "required_field_null"

    def test_negative_amount_fails(self):
        """Amount must be positive — negative claims are invalid."""
        data = self._valid_extraction()
        data["amount_claimed_sar"] = -500

        result = validate_extraction(data, "test_doc")

        assert result["valid"] is False
        errors = [e for e in result["errors"]
                  if e["field"] == "amount_claimed_sar"]
        assert len(errors) > 0

    def test_invalid_enum_value_fails(self):
        """
        Invalid enum values must fail validation.
        Exam concept: enums prevent free-text hallucination
        in categorical fields.
        """
        data = self._valid_extraction()
        data["document_language"] = "spanish"

        result = validate_extraction(data, "test_doc")

        assert result["valid"] is False
        errors = [e for e in result["errors"]
                  if e["field"] == "document_language"]
        assert len(errors) > 0
        assert errors[0]["issue"] == "invalid_enum_value"

    def test_nullable_fields_can_be_null(self):
        """
        Nullable fields set to null must pass validation.
        This is the core nullable field test.
        """
        data = self._valid_extraction()
        data["primary_diagnosis_icd"] = None
        data["physician_name"] = None
        data["procedure_code"] = None
        data["icd_conflict"] = None

        result = validate_extraction(data, "test_doc")

        assert result["valid"] is True, (
            f"Nullable fields set to null should pass validation. "
            f"Errors: {result['errors']}"
        )

    def test_retry_prompt_contains_specific_errors(self):
        """
        Retry prompt must include the specific validation errors.
        Vague retry prompts produce the same errors repeatedly.
        Specific error context enables targeted correction.
        """
        data = self._valid_extraction()
        data["amount_claimed_sar"] = -100

        validation = validate_extraction(data, "test_doc")
        retry = build_retry_prompt("original document", data, validation)

        assert "amount_claimed_sar" in retry
        assert "original document" in retry
        assert "validation errors" in retry.lower()

    def test_retry_prompt_includes_original_document(self):
        """
        Retry must include original document so model can re-read it.
        Without the document, model cannot correct extraction errors.
        """
        data = self._valid_extraction()
        data["member_id"] = None

        validation = validate_extraction(data, "test_doc")
        retry = build_retry_prompt(
            "CLAIM FORM Member: Ahmed", data, validation
        )

        assert "CLAIM FORM Member: Ahmed" in retry


class TestBilingual:
    """
    Tests for bilingual document handling.

    Exam concept: conflicting source data must be preserved
    with attribution. Never arbitrarily select one language.
    """

    def test_icd_conflict_structure(self):
        """ICD conflict must capture both codes with attribution."""
        data = {
            "claim_reference": "CLM-002",
            "member_id": "MBR-002",
            "amount_claimed_sar": 4200.0,
            "document_language": "bilingual",
            "ocr_quality": "high",
            "extraction_confidence": "medium",
            "fields_requiring_review": ["icd_conflict"],
            "icd_conflict": {
                "arabic_icd": "I50.0",
                "english_icd": "I50.1",
                "arabic_diagnosis": "فشل القلب الاحتقاني",
                "english_diagnosis": "Congestive heart failure"
            }
        }

        result = validate_extraction(data, "test_bilingual")

        assert result["valid"] is True
        assert data["icd_conflict"]["arabic_icd"] == "I50.0"
        assert data["icd_conflict"]["english_icd"] == "I50.1"

    def test_icd_conflict_null_for_monolingual(self):
        """
        ICD conflict must be null for monolingual documents.
        A non-null icd_conflict on a monolingual doc is a false positive.
        """
        data = self._valid_extraction_bilingual()
        data["document_language"] = "english"
        data["icd_conflict"] = None

        result = validate_extraction(data, "test_mono")
        assert result["valid"] is True

    def _valid_extraction_bilingual(self) -> dict:
        return {
            "claim_reference": "CLM-002",
            "member_id": "MBR-002",
            "amount_claimed_sar": 4200.0,
            "document_language": "bilingual",
            "ocr_quality": "high",
            "extraction_confidence": "medium",
            "fields_requiring_review": [],
            "icd_conflict": None
        }


class TestConfidenceRouting:
    """
    Tests for confidence-based routing decisions.

    Exam concept: confidence calibration drives human review routing.
    Low confidence → human review regardless of validation passing.
    """

    def test_low_confidence_routes_to_human_review(self):
        """
        Low confidence extraction must route to human review
        even if validation passes completely.
        """
        from src.extraction.pipeline import build_success_result

        data = {
            "claim_reference": "CLM-004",
            "member_id": "MBR-004",
            "amount_claimed_sar": 650.0,
            "document_language": "english",
            "ocr_quality": "low",
            "extraction_confidence": "low",
            "fields_requiring_review": [
                "primary_diagnosis_icd",
                "physician_name"
            ]
        }
        validation = {"valid": True, "errors": [], "warnings": []}

        result = build_success_result("CLM-004", data, validation, 1)

        assert result["routing"] == "human_review"
        assert result["success"] is True

    def test_high_confidence_no_flags_routes_to_auto(self):
        """High confidence with no review flags routes to auto processing."""
        from src.extraction.pipeline import build_success_result

        data = {
            "claim_reference": "CLM-001",
            "member_id": "MBR-001",
            "amount_claimed_sar": 3000.0,
            "document_language": "english",
            "ocr_quality": "high",
            "extraction_confidence": "high",
            "fields_requiring_review": []
        }
        validation = {"valid": True, "errors": [], "warnings": []}

        result = build_success_result("CLM-001", data, validation, 1)

        assert result["routing"] == "auto_process"

    def test_medium_confidence_routes_to_spot_check(self):
        """Medium confidence routes to supervisor spot check."""
        from src.extraction.pipeline import build_success_result

        data = {
            "claim_reference": "CLM-002",
            "member_id": "MBR-002",
            "amount_claimed_sar": 4200.0,
            "document_language": "bilingual",
            "ocr_quality": "high",
            "extraction_confidence": "medium",
            "fields_requiring_review": ["icd_conflict"]
        }
        validation = {"valid": True, "errors": [], "warnings": []}

        result = build_success_result("CLM-002", data, validation, 1)

        assert result["routing"] == "supervisor_spot_check"