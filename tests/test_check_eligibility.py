import pytest
from src.tools.check_eligibility import check_eligibility


class TestCheckEligibilityHappyPath:
    def test_check_eligibility_happy_path_inpatient(self):
        result = check_eligibility("MBR-001", "inpatient")
        assert result["success"] is True
        assert result["error"] is None
        assert result["data"]["eligible"] is True
        assert result["data"]["member_id"] == "MBR-001"
        assert result["data"]["care_category"] == "inpatient"
        assert result["data"]["remaining_benefit_sar"] > 0

    def test_check_eligibility_happy_path_returns_remaining_benefit(self):
        # MBR-001: annual_limit=500000, used=123400, deductible=500
        # remaining = 500000 - 123400 - 500 = 376100
        result = check_eligibility("MBR-001", "outpatient")
        assert result["success"] is True
        assert result["data"]["eligible"] is True
        assert result["data"]["remaining_benefit_sar"] == pytest.approx(376100.0)

    def test_check_eligibility_happy_path_maternity(self):
        # MBR-002 has maternity coverage
        result = check_eligibility("MBR-002", "maternity")
        assert result["success"] is True
        assert result["data"]["eligible"] is True


class TestCheckEligibilityNotFound:
    def test_check_eligibility_not_found(self):
        result = check_eligibility("MBR-999", "inpatient")
        assert result["success"] is False
        assert result["data"] is None
        assert result["error"]["errorCategory"] == "not_found"

    def test_check_eligibility_not_found_is_retryable(self):
        result = check_eligibility("MBR-999", "inpatient")
        assert result["error"]["isRetryable"] is False


class TestCheckEligibilityInvalidInput:
    def test_check_eligibility_invalid_input_missing_member_id(self):
        result = check_eligibility("", "inpatient")
        assert result["success"] is False
        assert result["error"]["errorCategory"] == "validation"
        assert result["error"]["isRetryable"] is False

    def test_check_eligibility_invalid_input_missing_care_category(self):
        result = check_eligibility("MBR-001", "")
        assert result["success"] is False
        assert result["error"]["errorCategory"] == "validation"

    def test_check_eligibility_invalid_input_unknown_category(self):
        result = check_eligibility("MBR-001", "surgery")
        assert result["success"] is False
        assert result["error"]["errorCategory"] == "validation"
        assert "surgery" in result["error"]["message"]


class TestCheckEligibilityErrorCategory:
    def test_check_eligibility_error_category_not_found(self):
        result = check_eligibility("MBR-000", "outpatient")
        assert result["error"]["errorCategory"] == "not_found"

    def test_check_eligibility_error_category_validation_on_bad_category(self):
        result = check_eligibility("MBR-001", "cosmetics")
        assert result["error"]["errorCategory"] == "validation"

    def test_check_eligibility_error_category_policy_suspended(self):
        # MBR-003 has status=suspended
        result = check_eligibility("MBR-003", "inpatient")
        assert result["success"] is True
        assert result["data"]["eligible"] is False
        assert result["data"]["reason"] == "policy_suspended"

    def test_check_eligibility_error_category_coverage_not_included(self):
        # MBR-001 has dental=false
        result = check_eligibility("MBR-001", "dental")
        assert result["success"] is True
        assert result["data"]["eligible"] is False
        assert result["data"]["reason"] == "coverage_not_included"


class TestCheckEligibilityIsRetryable:
    def test_check_eligibility_is_retryable_not_found(self):
        result = check_eligibility("MBR-000", "inpatient")
        assert result["error"]["isRetryable"] is False

    def test_check_eligibility_is_retryable_validation(self):
        result = check_eligibility("MBR-001", "unknown_type")
        assert result["error"]["isRetryable"] is False

    def test_check_eligibility_ineligible_result_has_no_error(self):
        # Ineligible is a valid business outcome, not an error
        result = check_eligibility("MBR-001", "dental")
        assert result["success"] is True
        assert result["error"] is None
        assert result["data"]["eligible"] is False
        assert result["data"]["remaining_benefit_sar"] == 0.0

    def test_check_eligibility_suspended_has_zero_remaining(self):
        result = check_eligibility("MBR-003", "inpatient")
        assert result["data"]["remaining_benefit_sar"] == 0.0
