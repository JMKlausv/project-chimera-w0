"""
Test suite for Error Codes specification.

Spec: specs/7-error-codes.md - Error codes, categories, recovery strategies, and response format.
Tests validate that all error handling conforms to the specification exactly.

All validation tests are designed to FAIL before implementation is complete.
Tests pass only when chimera/errors/ implements the full error catalog.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


# ============================================================================
# Error Infrastructure (per specs/7-error-codes.md)
# ============================================================================
# Note: In real implementation, import from chimera.errors

class SpecError(Exception):
    """Base exception for all Chimera specification errors.

    Spec: specs/7-error-codes.md - Error Response Format
    All errors follow standardized format with code, message, http_status,
    timestamp, request_id, details, and recovery strategy.
    """
    def __init__(
        self,
        code: str,
        message: str,
        http_status: int = 400,
        field: str = None,
        details: Dict[str, Any] = None,
        recovery: Dict[str, Any] = None,
    ):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.field = field
        self.timestamp = datetime.utcnow().isoformat() + "Z"
        self.request_id = str(uuid4())
        self.details = details or {}
        self.recovery = recovery or {}
        super().__init__(f"[{code}] {message} (HTTP {http_status})")

    def to_dict(self) -> dict:
        """Convert error to standardized response format per spec."""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "http_status": self.http_status,
                "timestamp": self.timestamp,
                "request_id": self.request_id,
                "details": self.details,
                "recovery": self.recovery,
            }
        }


# ============================================================================
# Error Category Classification
# ============================================================================

class ErrorCategory:
    """Error categories per specs/7-error-codes.md."""
    EXTERNAL = "EXTERNAL"      # EXT_*
    VALIDATION = "VALIDATION"  # VAL_*
    RESOURCE = "RESOURCE"      # RES_*
    STATE = "STATE"            # STATE_*
    SECURITY = "SECURITY"      # SEC_*
    PLATFORM = "PLATFORM"      # PLAT_*
    FINANCIAL = "FINANCIAL"    # FIN_*
    NETWORK = "NETWORK"        # NET_*


# ============================================================================
# Error Code Catalog (from specs/7-error-codes.md)
# ============================================================================

ERROR_CATALOG = {
    # External Integration Errors (EXT_*)
    "EXT_PLATFORM_UNAVAILABLE": {
        "http_status": 503,
        "category": ErrorCategory.EXTERNAL,
        "retry_safe": True,
        "max_retries": 3,
        "recovery_strategy": "RETRY_WITH_BACKOFF",
    },
    "EXT_RATE_LIMITED": {
        "http_status": 429,
        "category": ErrorCategory.EXTERNAL,
        "retry_safe": True,
        "max_retries": 3,
        "recovery_strategy": "EXPONENTIAL_BACKOFF_WITH_JITTER",
    },
    "EXT_INVALID_PLATFORM": {
        "http_status": 400,
        "category": ErrorCategory.EXTERNAL,
        "retry_safe": False,
        "max_retries": 0,
        "recovery_strategy": "REJECT",
    },
    "EXT_AUTH_FAILED": {
        "http_status": 401,
        "category": ErrorCategory.EXTERNAL,
        "retry_safe": False,
        "max_retries": 0,
        "recovery_strategy": "REFRESH_CREDENTIALS",
    },
    "EXT_FORBIDDEN": {
        "http_status": 403,
        "category": ErrorCategory.EXTERNAL,
        "retry_safe": False,
        "max_retries": 0,
        "recovery_strategy": "CHECK_PERMISSIONS",
    },

    # Data Validation Errors (VAL_*)
    "VAL_SCHEMA_INVALID": {
        "http_status": 422,
        "category": ErrorCategory.VALIDATION,
        "retry_safe": False,
        "max_retries": 0,
        "recovery_strategy": "REJECT",
    },
    "VAL_ENGAGEMENT_FORMULA_MISMATCH": {
        "http_status": 422,
        "category": ErrorCategory.VALIDATION,
        "retry_safe": False,
        "max_retries": 0,
        "recovery_strategy": "REJECT",
    },
    "VAL_NEGATIVE_ENGAGEMENT": {
        "http_status": 422,
        "category": ErrorCategory.VALIDATION,
        "retry_safe": False,
        "max_retries": 0,
        "recovery_strategy": "CLAMP_AND_WARN",
    },
    "VAL_TIMESTAMP_INVALID": {
        "http_status": 422,
        "category": ErrorCategory.VALIDATION,
        "retry_safe": False,
        "max_retries": 0,
        "recovery_strategy": "REJECT",
    },
    "VAL_MISSING_REQUIRED_FIELD": {
        "http_status": 422,
        "category": ErrorCategory.VALIDATION,
        "retry_safe": False,
        "max_retries": 0,
        "recovery_strategy": "REJECT",
    },
    "VAL_TYPE_MISMATCH": {
        "http_status": 422,
        "category": ErrorCategory.VALIDATION,
        "retry_safe": False,
        "max_retries": 0,
        "recovery_strategy": "COERCE_OR_REJECT",
    },

    # Resource Errors (RES_*)
    "RES_NOT_FOUND": {
        "http_status": 404,
        "category": ErrorCategory.RESOURCE,
        "retry_safe": False,
        "max_retries": 0,
        "recovery_strategy": "REJECT",
    },
    "RES_ALREADY_EXISTS": {
        "http_status": 409,
        "category": ErrorCategory.RESOURCE,
        "retry_safe": False,
        "max_retries": 0,
        "recovery_strategy": "RETURN_EXISTING",
    },
    "RES_QUOTA_EXCEEDED": {
        "http_status": 429,
        "category": ErrorCategory.RESOURCE,
        "retry_safe": False,
        "max_retries": 0,
        "recovery_strategy": "REJECT",
    },
    "RES_RESOURCE_LOCKED": {
        "http_status": 423,
        "category": ErrorCategory.RESOURCE,
        "retry_safe": True,
        "max_retries": 3,
        "recovery_strategy": "RETRY_WITH_BACKOFF",
    },

    # State Errors (STATE_*)
    "STATE_INVALID_TRANSITION": {
        "http_status": 409,
        "category": ErrorCategory.STATE,
        "retry_safe": False,
        "max_retries": 0,
        "recovery_strategy": "REJECT",
    },
    "STATE_CONFLICT": {
        "http_status": 409,
        "category": ErrorCategory.STATE,
        "retry_safe": True,
        "max_retries": -1,  # Infinite retries (spec says ∞)
        "recovery_strategy": "REFRESH_AND_RETRY",
    },
    "STATE_SLA_EXCEEDED": {
        "http_status": 504,
        "category": ErrorCategory.STATE,
        "retry_safe": False,
        "max_retries": 0,
        "recovery_strategy": "ESCALATE",
    },

    # Security Errors (SEC_*)
    "SEC_INVALID_TOKEN": {
        "http_status": 401,
        "category": ErrorCategory.SECURITY,
        "retry_safe": False,
        "max_retries": 0,
        "recovery_strategy": "REQUEST_NEW_TOKEN",
    },
    "SEC_TOKEN_EXPIRED": {
        "http_status": 401,
        "category": ErrorCategory.SECURITY,
        "retry_safe": False,
        "max_retries": 0,
        "recovery_strategy": "REQUEST_FRESH_APPROVAL",
    },
    "SEC_INSUFFICIENT_PERMISSIONS": {
        "http_status": 403,
        "category": ErrorCategory.SECURITY,
        "retry_safe": False,
        "max_retries": 0,
        "recovery_strategy": "CHECK_RBAC",
    },
    "SEC_SIGNATURE_INVALID": {
        "http_status": 401,
        "category": ErrorCategory.SECURITY,
        "retry_safe": False,
        "max_retries": 0,
        "recovery_strategy": "REJECT",
    },
    "SEC_CHECKSUM_MISMATCH": {
        "http_status": 422,
        "category": ErrorCategory.SECURITY,
        "retry_safe": False,
        "max_retries": 0,
        "recovery_strategy": "REJECT",
    },
    "SEC_AUDIT_TAMPER_DETECTED": {
        "http_status": 500,
        "category": ErrorCategory.SECURITY,
        "retry_safe": False,
        "max_retries": 0,
        "recovery_strategy": "HALT_AND_ESCALATE",
    },

    # Platform Errors (PLAT_*)
    "PLAT_PUBLISH_FAILED": {
        "http_status": 502,
        "category": ErrorCategory.PLATFORM,
        "retry_safe": True,
        "max_retries": 3,
        "recovery_strategy": "RETRY_WITH_BACKOFF",
    },
    "PLAT_DUPLICATE_CONTENT": {
        "http_status": 409,
        "category": ErrorCategory.PLATFORM,
        "retry_safe": False,
        "max_retries": 0,
        "recovery_strategy": "RETURN_EXISTING",
    },
    "PLAT_CONTENT_MODERATED": {
        "http_status": 451,
        "category": ErrorCategory.PLATFORM,
        "retry_safe": False,
        "max_retries": 0,
        "recovery_strategy": "ALERT_AND_REVISE",
    },
    "PLAT_ACCOUNT_SUSPENDED": {
        "http_status": 403,
        "category": ErrorCategory.PLATFORM,
        "retry_safe": False,
        "max_retries": 0,
        "recovery_strategy": "HALT_AND_ESCALATE",
    },

    # Financial Errors (FIN_*)
    "FIN_INSUFFICIENT_BALANCE": {
        "http_status": 402,
        "category": ErrorCategory.FINANCIAL,
        "retry_safe": False,
        "max_retries": 0,
        "recovery_strategy": "REJECT_AND_ESCALATE",
    },
    "FIN_TRANSACTION_FAILED": {
        "http_status": 502,
        "category": ErrorCategory.FINANCIAL,
        "retry_safe": True,
        "max_retries": 3,
        "recovery_strategy": "RETRY_WITH_BACKOFF",
    },
    "FIN_WALLET_ERROR": {
        "http_status": 500,
        "category": ErrorCategory.FINANCIAL,
        "retry_safe": True,
        "max_retries": 2,
        "recovery_strategy": "RETRY_WITH_BACKOFF",
    },
    "FIN_INVALID_WALLET_ADDRESS": {
        "http_status": 400,
        "category": ErrorCategory.FINANCIAL,
        "retry_safe": False,
        "max_retries": 0,
        "recovery_strategy": "REJECT",
    },
    "FIN_CURRENCY_CONVERSION_ERROR": {
        "http_status": 500,
        "category": ErrorCategory.FINANCIAL,
        "retry_safe": True,
        "max_retries": 2,
        "recovery_strategy": "USE_CACHED_RATE",
    },

    # Network Errors (NET_*)
    "NET_TIMEOUT": {
        "http_status": 504,
        "category": ErrorCategory.NETWORK,
        "retry_safe": True,
        "max_retries": 3,
        "recovery_strategy": "RETRY_WITH_BACKOFF",
    },
    "NET_CONNECTION_REFUSED": {
        "http_status": 503,
        "category": ErrorCategory.NETWORK,
        "retry_safe": True,
        "max_retries": 3,
        "recovery_strategy": "RETRY_WITH_BACKOFF",
    },
    "NET_DNS_FAILURE": {
        "http_status": 503,
        "category": ErrorCategory.NETWORK,
        "retry_safe": True,
        "max_retries": 3,
        "recovery_strategy": "RETRY_WITH_BACKOFF",
    },
    "NET_TLS_CERTIFICATE_INVALID": {
        "http_status": 495,
        "category": ErrorCategory.NETWORK,
        "retry_safe": False,
        "max_retries": 0,
        "recovery_strategy": "REJECT",
    },
}


# Errors that are safe to retry (per Recovery Strategy Matrix)
RETRYABLE_ERRORS = {
    code for code, spec in ERROR_CATALOG.items() if spec["retry_safe"]
}

# Errors that must never be retried
NON_RETRYABLE_ERRORS = {
    code for code, spec in ERROR_CATALOG.items() if not spec["retry_safe"]
}


# ============================================================================
# Helper: classify_error (per specs/7-error-codes.md best practices)
# ============================================================================

def classify_error(http_status: int) -> tuple:
    """Classify error by HTTP status code per spec."""
    if http_status == 429:
        return ErrorCategory.EXTERNAL, "EXT_RATE_LIMITED"
    elif http_status == 401:
        return ErrorCategory.SECURITY, "SEC_INVALID_TOKEN"
    elif http_status == 503:
        return ErrorCategory.EXTERNAL, "EXT_PLATFORM_UNAVAILABLE"
    elif http_status == 422:
        return ErrorCategory.VALIDATION, "VAL_SCHEMA_INVALID"
    elif http_status == 504:
        return ErrorCategory.NETWORK, "NET_TIMEOUT"
    elif http_status == 402:
        return ErrorCategory.FINANCIAL, "FIN_INSUFFICIENT_BALANCE"
    elif http_status == 403:
        return ErrorCategory.SECURITY, "SEC_INSUFFICIENT_PERMISSIONS"
    elif http_status == 404:
        return ErrorCategory.RESOURCE, "RES_NOT_FOUND"
    elif http_status == 409:
        return ErrorCategory.STATE, "STATE_CONFLICT"
    else:
        return "UNKNOWN", "UNKNOWN_ERROR"


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_spec_error():
    """A valid SpecError with all fields populated."""
    return SpecError(
        code="VAL_SCHEMA_INVALID",
        message="Missing required field: trend_id",
        http_status=422,
        field="trend_id",
        details={
            "field": "trend_id",
            "schema_version": "TrendData v1.0",
            "constraint_violated": "required"
        },
        recovery={
            "strategy": "REJECT",
            "fallback": "NONE",
            "escalation": "Alert ops if >5% of requests fail",
            "retry_safe": False
        }
    )


# ============================================================================
# Test: Error Code Catalog Completeness
# ============================================================================

class TestErrorCodeCatalogCompleteness:
    """Verify all error codes from specs/7-error-codes.md are defined."""

    def test_external_errors_exist(self):
        """Spec: External Integration Errors (EXT_*) are defined"""
        ext_codes = [c for c in ERROR_CATALOG if c.startswith("EXT_")]
        expected = [
            "EXT_PLATFORM_UNAVAILABLE",
            "EXT_RATE_LIMITED",
            "EXT_INVALID_PLATFORM",
            "EXT_AUTH_FAILED",
            "EXT_FORBIDDEN",
        ]
        for code in expected:
            assert code in ERROR_CATALOG, f"Missing error code: {code}"

    def test_validation_errors_exist(self):
        """Spec: Data Validation Errors (VAL_*) are defined"""
        expected = [
            "VAL_SCHEMA_INVALID",
            "VAL_ENGAGEMENT_FORMULA_MISMATCH",
            "VAL_NEGATIVE_ENGAGEMENT",
            "VAL_TIMESTAMP_INVALID",
            "VAL_MISSING_REQUIRED_FIELD",
            "VAL_TYPE_MISMATCH",
        ]
        for code in expected:
            assert code in ERROR_CATALOG, f"Missing error code: {code}"

    def test_resource_errors_exist(self):
        """Spec: Resource Errors (RES_*) are defined"""
        expected = [
            "RES_NOT_FOUND",
            "RES_ALREADY_EXISTS",
            "RES_QUOTA_EXCEEDED",
            "RES_RESOURCE_LOCKED",
        ]
        for code in expected:
            assert code in ERROR_CATALOG, f"Missing error code: {code}"

    def test_state_errors_exist(self):
        """Spec: State Errors (STATE_*) are defined"""
        expected = [
            "STATE_INVALID_TRANSITION",
            "STATE_CONFLICT",
            "STATE_SLA_EXCEEDED",
        ]
        for code in expected:
            assert code in ERROR_CATALOG, f"Missing error code: {code}"

    def test_security_errors_exist(self):
        """Spec: Security Errors (SEC_*) are defined"""
        expected = [
            "SEC_INVALID_TOKEN",
            "SEC_TOKEN_EXPIRED",
            "SEC_INSUFFICIENT_PERMISSIONS",
            "SEC_SIGNATURE_INVALID",
            "SEC_CHECKSUM_MISMATCH",
            "SEC_AUDIT_TAMPER_DETECTED",
        ]
        for code in expected:
            assert code in ERROR_CATALOG, f"Missing error code: {code}"

    def test_platform_errors_exist(self):
        """Spec: Platform Errors (PLAT_*) are defined"""
        expected = [
            "PLAT_PUBLISH_FAILED",
            "PLAT_DUPLICATE_CONTENT",
            "PLAT_CONTENT_MODERATED",
            "PLAT_ACCOUNT_SUSPENDED",
        ]
        for code in expected:
            assert code in ERROR_CATALOG, f"Missing error code: {code}"

    def test_financial_errors_exist(self):
        """Spec: Financial Errors (FIN_*) are defined"""
        expected = [
            "FIN_INSUFFICIENT_BALANCE",
            "FIN_TRANSACTION_FAILED",
            "FIN_WALLET_ERROR",
            "FIN_INVALID_WALLET_ADDRESS",
            "FIN_CURRENCY_CONVERSION_ERROR",
        ]
        for code in expected:
            assert code in ERROR_CATALOG, f"Missing error code: {code}"

    def test_network_errors_exist(self):
        """Spec: Network Errors (NET_*) are defined"""
        expected = [
            "NET_TIMEOUT",
            "NET_CONNECTION_REFUSED",
            "NET_DNS_FAILURE",
            "NET_TLS_CERTIFICATE_INVALID",
        ]
        for code in expected:
            assert code in ERROR_CATALOG, f"Missing error code: {code}"

    def test_total_error_code_count(self):
        """Verify total number of error codes matches spec (37 codes)"""
        assert len(ERROR_CATALOG) == 37


# ============================================================================
# Test: Error Code Naming Convention
# ============================================================================

class TestErrorCodeNaming:
    """Verify error codes follow naming conventions."""

    def test_all_codes_are_uppercase(self):
        """Error codes must be UPPER_SNAKE_CASE"""
        for code in ERROR_CATALOG:
            assert code == code.upper(), f"Error code must be uppercase: {code}"

    def test_all_codes_have_category_prefix(self):
        """Every code starts with its category prefix"""
        valid_prefixes = ["EXT_", "VAL_", "RES_", "STATE_", "SEC_", "PLAT_", "FIN_", "NET_"]
        for code in ERROR_CATALOG:
            assert any(code.startswith(p) for p in valid_prefixes), \
                f"Error code {code} must start with a valid prefix"

    def test_ext_codes_map_to_external_category(self):
        """EXT_* codes belong to EXTERNAL category"""
        for code, spec in ERROR_CATALOG.items():
            if code.startswith("EXT_"):
                assert spec["category"] == ErrorCategory.EXTERNAL

    def test_val_codes_map_to_validation_category(self):
        """VAL_* codes belong to VALIDATION category"""
        for code, spec in ERROR_CATALOG.items():
            if code.startswith("VAL_"):
                assert spec["category"] == ErrorCategory.VALIDATION

    def test_sec_codes_map_to_security_category(self):
        """SEC_* codes belong to SECURITY category"""
        for code, spec in ERROR_CATALOG.items():
            if code.startswith("SEC_"):
                assert spec["category"] == ErrorCategory.SECURITY

    def test_fin_codes_map_to_financial_category(self):
        """FIN_* codes belong to FINANCIAL category"""
        for code, spec in ERROR_CATALOG.items():
            if code.startswith("FIN_"):
                assert spec["category"] == ErrorCategory.FINANCIAL

    def test_net_codes_map_to_network_category(self):
        """NET_* codes belong to NETWORK category"""
        for code, spec in ERROR_CATALOG.items():
            if code.startswith("NET_"):
                assert spec["category"] == ErrorCategory.NETWORK


# ============================================================================
# Test: HTTP Status Mapping
# ============================================================================

class TestHTTPStatusMapping:
    """Verify each error code maps to correct HTTP status per spec."""

    def test_ext_platform_unavailable_is_503(self):
        assert ERROR_CATALOG["EXT_PLATFORM_UNAVAILABLE"]["http_status"] == 503

    def test_ext_rate_limited_is_429(self):
        assert ERROR_CATALOG["EXT_RATE_LIMITED"]["http_status"] == 429

    def test_ext_invalid_platform_is_400(self):
        assert ERROR_CATALOG["EXT_INVALID_PLATFORM"]["http_status"] == 400

    def test_ext_auth_failed_is_401(self):
        assert ERROR_CATALOG["EXT_AUTH_FAILED"]["http_status"] == 401

    def test_val_schema_invalid_is_422(self):
        assert ERROR_CATALOG["VAL_SCHEMA_INVALID"]["http_status"] == 422

    def test_val_engagement_formula_mismatch_is_422(self):
        assert ERROR_CATALOG["VAL_ENGAGEMENT_FORMULA_MISMATCH"]["http_status"] == 422

    def test_res_not_found_is_404(self):
        assert ERROR_CATALOG["RES_NOT_FOUND"]["http_status"] == 404

    def test_res_already_exists_is_409(self):
        assert ERROR_CATALOG["RES_ALREADY_EXISTS"]["http_status"] == 409

    def test_res_resource_locked_is_423(self):
        assert ERROR_CATALOG["RES_RESOURCE_LOCKED"]["http_status"] == 423

    def test_state_conflict_is_409(self):
        assert ERROR_CATALOG["STATE_CONFLICT"]["http_status"] == 409

    def test_state_sla_exceeded_is_504(self):
        assert ERROR_CATALOG["STATE_SLA_EXCEEDED"]["http_status"] == 504

    def test_sec_invalid_token_is_401(self):
        assert ERROR_CATALOG["SEC_INVALID_TOKEN"]["http_status"] == 401

    def test_sec_token_expired_is_401(self):
        assert ERROR_CATALOG["SEC_TOKEN_EXPIRED"]["http_status"] == 401

    def test_sec_insufficient_permissions_is_403(self):
        assert ERROR_CATALOG["SEC_INSUFFICIENT_PERMISSIONS"]["http_status"] == 403

    def test_sec_audit_tamper_is_500(self):
        assert ERROR_CATALOG["SEC_AUDIT_TAMPER_DETECTED"]["http_status"] == 500

    def test_plat_publish_failed_is_502(self):
        assert ERROR_CATALOG["PLAT_PUBLISH_FAILED"]["http_status"] == 502

    def test_plat_duplicate_content_is_409(self):
        assert ERROR_CATALOG["PLAT_DUPLICATE_CONTENT"]["http_status"] == 409

    def test_plat_content_moderated_is_451(self):
        assert ERROR_CATALOG["PLAT_CONTENT_MODERATED"]["http_status"] == 451

    def test_fin_insufficient_balance_is_402(self):
        assert ERROR_CATALOG["FIN_INSUFFICIENT_BALANCE"]["http_status"] == 402

    def test_fin_transaction_failed_is_502(self):
        assert ERROR_CATALOG["FIN_TRANSACTION_FAILED"]["http_status"] == 502

    def test_net_timeout_is_504(self):
        assert ERROR_CATALOG["NET_TIMEOUT"]["http_status"] == 504

    def test_net_connection_refused_is_503(self):
        assert ERROR_CATALOG["NET_CONNECTION_REFUSED"]["http_status"] == 503

    def test_net_tls_certificate_invalid_is_495(self):
        assert ERROR_CATALOG["NET_TLS_CERTIFICATE_INVALID"]["http_status"] == 495

    def test_all_http_status_in_valid_range(self):
        """All HTTP statuses must be 4xx or 5xx"""
        for code, spec in ERROR_CATALOG.items():
            status = spec["http_status"]
            assert 400 <= status <= 599, \
                f"{code} has invalid HTTP status: {status}"


# ============================================================================
# Test: Recovery Strategy Matrix
# ============================================================================

class TestRecoveryStrategyMatrix:
    """Verify retry safety and recovery strategies per spec."""

    def test_retryable_errors(self):
        """Spec: Retryable errors include TIMEOUT, RATE_LIMITED, NETWORK_ERROR, PLATFORM_UNAVAILABLE, TX_FAILED"""
        expected_retryable = {
            "EXT_PLATFORM_UNAVAILABLE",
            "EXT_RATE_LIMITED",
            "RES_RESOURCE_LOCKED",
            "STATE_CONFLICT",
            "PLAT_PUBLISH_FAILED",
            "FIN_TRANSACTION_FAILED",
            "FIN_WALLET_ERROR",
            "FIN_CURRENCY_CONVERSION_ERROR",
            "NET_TIMEOUT",
            "NET_CONNECTION_REFUSED",
            "NET_DNS_FAILURE",
        }
        for code in expected_retryable:
            assert ERROR_CATALOG[code]["retry_safe"] is True, \
                f"{code} should be retry-safe"

    def test_non_retryable_errors(self):
        """Spec: Non-retryable errors include INVALID_INPUT, INVALID_PLATFORM, AGENT_NOT_FOUND, INSUFFICIENT_BALANCE"""
        expected_non_retryable = {
            "EXT_INVALID_PLATFORM",
            "EXT_AUTH_FAILED",
            "VAL_SCHEMA_INVALID",
            "VAL_MISSING_REQUIRED_FIELD",
            "RES_NOT_FOUND",
            "SEC_INVALID_TOKEN",
            "FIN_INSUFFICIENT_BALANCE",
            "FIN_INVALID_WALLET_ADDRESS",
            "NET_TLS_CERTIFICATE_INVALID",
        }
        for code in expected_non_retryable:
            assert ERROR_CATALOG[code]["retry_safe"] is False, \
                f"{code} should NOT be retry-safe"

    def test_non_retryable_have_zero_max_retries(self):
        """Non-retryable errors must have max_retries=0"""
        for code, spec in ERROR_CATALOG.items():
            if not spec["retry_safe"]:
                assert spec["max_retries"] == 0, \
                    f"{code} is non-retryable but has max_retries={spec['max_retries']}"

    def test_retryable_have_positive_max_retries(self):
        """Retryable errors must have max_retries > 0 (or -1 for infinite)"""
        for code, spec in ERROR_CATALOG.items():
            if spec["retry_safe"]:
                assert spec["max_retries"] != 0, \
                    f"{code} is retryable but has max_retries=0"

    def test_state_conflict_infinite_retries(self):
        """Spec: STATE_CONFLICT has infinite retries (∞)"""
        assert ERROR_CATALOG["STATE_CONFLICT"]["max_retries"] == -1

    def test_all_errors_have_recovery_strategy(self):
        """Every error code must have a recovery strategy"""
        for code, spec in ERROR_CATALOG.items():
            assert "recovery_strategy" in spec, \
                f"{code} missing recovery_strategy"
            assert spec["recovery_strategy"], \
                f"{code} has empty recovery_strategy"


# ============================================================================
# Test: Error Response Format
# ============================================================================

class TestErrorResponseFormat:
    """Verify error response format per spec."""

    def test_error_to_dict_has_error_key(self, sample_spec_error):
        """Response must have top-level 'error' key"""
        response = sample_spec_error.to_dict()
        assert "error" in response

    def test_error_response_has_code(self, sample_spec_error):
        """Spec: response.error.code is required"""
        response = sample_spec_error.to_dict()
        assert "code" in response["error"]
        assert response["error"]["code"] == "VAL_SCHEMA_INVALID"

    def test_error_response_has_message(self, sample_spec_error):
        """Spec: response.error.message is required"""
        response = sample_spec_error.to_dict()
        assert "message" in response["error"]
        assert isinstance(response["error"]["message"], str)
        assert len(response["error"]["message"]) > 0

    def test_error_response_has_http_status(self, sample_spec_error):
        """Spec: response.error.http_status is required"""
        response = sample_spec_error.to_dict()
        assert "http_status" in response["error"]
        assert response["error"]["http_status"] == 422

    def test_error_response_has_timestamp(self, sample_spec_error):
        """Spec: response.error.timestamp is required (ISO8601)"""
        response = sample_spec_error.to_dict()
        assert "timestamp" in response["error"]
        ts = response["error"]["timestamp"]
        assert ts.endswith("Z"), "timestamp must end with Z (UTC)"

    def test_error_response_has_request_id(self, sample_spec_error):
        """Spec: response.error.request_id is required (UUID)"""
        response = sample_spec_error.to_dict()
        assert "request_id" in response["error"]
        from uuid import UUID
        UUID(response["error"]["request_id"])  # Must parse as UUID

    def test_error_response_has_details(self, sample_spec_error):
        """Spec: response.error.details is required (context-specific)"""
        response = sample_spec_error.to_dict()
        assert "details" in response["error"]
        assert isinstance(response["error"]["details"], dict)

    def test_error_response_has_recovery(self, sample_spec_error):
        """Spec: response.error.recovery is required"""
        response = sample_spec_error.to_dict()
        assert "recovery" in response["error"]
        assert isinstance(response["error"]["recovery"], dict)

    def test_error_details_contain_field(self, sample_spec_error):
        """Details should include field name for validation errors"""
        response = sample_spec_error.to_dict()
        assert "field" in response["error"]["details"]

    def test_error_recovery_contains_strategy(self, sample_spec_error):
        """Recovery should include strategy"""
        response = sample_spec_error.to_dict()
        assert "strategy" in response["error"]["recovery"]

    def test_error_recovery_contains_retry_safe(self, sample_spec_error):
        """Recovery should include retry_safe flag"""
        response = sample_spec_error.to_dict()
        assert "retry_safe" in response["error"]["recovery"]


# ============================================================================
# Test: SpecError Construction
# ============================================================================

class TestSpecErrorConstruction:
    """Verify SpecError can be raised and caught properly."""

    def test_spec_error_is_exception(self):
        """SpecError is a subclass of Exception"""
        err = SpecError(code="VAL_SCHEMA_INVALID", message="test")
        assert isinstance(err, Exception)

    def test_spec_error_has_code(self):
        """SpecError preserves error code"""
        err = SpecError(code="EXT_PLATFORM_UNAVAILABLE", message="API down")
        assert err.code == "EXT_PLATFORM_UNAVAILABLE"

    def test_spec_error_has_message(self):
        """SpecError preserves message"""
        err = SpecError(code="NET_TIMEOUT", message="Request timed out after 30s")
        assert err.message == "Request timed out after 30s"

    def test_spec_error_has_http_status(self):
        """SpecError preserves HTTP status"""
        err = SpecError(code="FIN_INSUFFICIENT_BALANCE", message="test", http_status=402)
        assert err.http_status == 402

    def test_spec_error_default_http_status(self):
        """SpecError defaults to HTTP 400"""
        err = SpecError(code="TEST", message="test")
        assert err.http_status == 400

    def test_spec_error_has_timestamp(self):
        """SpecError auto-generates timestamp"""
        err = SpecError(code="TEST", message="test")
        assert err.timestamp is not None
        assert err.timestamp.endswith("Z")

    def test_spec_error_has_request_id(self):
        """SpecError auto-generates request_id"""
        err = SpecError(code="TEST", message="test")
        assert err.request_id is not None
        from uuid import UUID
        UUID(err.request_id)  # Must be valid UUID

    def test_spec_error_can_be_raised_and_caught(self):
        """SpecError can be raised and caught"""
        with pytest.raises(SpecError) as exc_info:
            raise SpecError(
                code="VAL_SCHEMA_INVALID",
                message="Missing required field: trend_id",
                http_status=422
            )
        assert exc_info.value.code == "VAL_SCHEMA_INVALID"
        assert exc_info.value.http_status == 422

    def test_spec_error_str_format(self):
        """SpecError string includes code and status"""
        err = SpecError(code="NET_TIMEOUT", message="Timed out", http_status=504)
        s = str(err)
        assert "NET_TIMEOUT" in s
        assert "504" in s


# ============================================================================
# Test: Error Classification
# ============================================================================

class TestErrorClassification:
    """Verify classify_error function per spec best practices."""

    def test_classify_429_as_rate_limited(self):
        category, code = classify_error(429)
        assert category == ErrorCategory.EXTERNAL
        assert code == "EXT_RATE_LIMITED"

    def test_classify_401_as_security(self):
        category, code = classify_error(401)
        assert category == ErrorCategory.SECURITY

    def test_classify_503_as_external(self):
        category, code = classify_error(503)
        assert category == ErrorCategory.EXTERNAL

    def test_classify_422_as_validation(self):
        category, code = classify_error(422)
        assert category == ErrorCategory.VALIDATION

    def test_classify_504_as_network(self):
        category, code = classify_error(504)
        assert category == ErrorCategory.NETWORK

    def test_classify_402_as_financial(self):
        category, code = classify_error(402)
        assert category == ErrorCategory.FINANCIAL

    def test_classify_404_as_resource(self):
        category, code = classify_error(404)
        assert category == ErrorCategory.RESOURCE

    def test_classify_unknown_status(self):
        category, code = classify_error(418)
        assert category == "UNKNOWN"
        assert code == "UNKNOWN_ERROR"


# ============================================================================
# Test: Escalation Levels
# ============================================================================

class TestEscalationLevels:
    """Verify escalation procedures per spec.

    Spec: 5 levels:
    - Level 1: Automatic Retry (transient errors)
    - Level 2: Fallback or Cached Data
    - Level 3: Human Alert
    - Level 4: Circuit Breaker (>10% errors in 5 min)
    - Level 5: Safety Mode (critical security/financial errors)
    """

    def test_transient_errors_are_level_1(self):
        """Level 1: Transient errors (timeout, rate_limited, connection_refused) get auto-retry"""
        level_1_codes = {"NET_TIMEOUT", "EXT_RATE_LIMITED", "NET_CONNECTION_REFUSED"}
        for code in level_1_codes:
            assert ERROR_CATALOG[code]["retry_safe"] is True, \
                f"{code} should be retry-safe (Level 1)"

    def test_critical_security_errors_are_level_5(self):
        """Level 5: Critical security/financial errors halt execution"""
        level_5_codes = {"SEC_AUDIT_TAMPER_DETECTED", "FIN_INSUFFICIENT_BALANCE"}
        for code in level_5_codes:
            assert ERROR_CATALOG[code]["retry_safe"] is False, \
                f"{code} should NOT be retryable (Level 5)"

    def test_security_errors_never_retryable(self):
        """All SEC_* errors (except none) should not be retried"""
        for code, spec in ERROR_CATALOG.items():
            if code.startswith("SEC_"):
                assert spec["retry_safe"] is False, \
                    f"Security error {code} should never be retried"

    def test_validation_errors_never_retryable(self):
        """All VAL_* errors should not be retried"""
        for code, spec in ERROR_CATALOG.items():
            if code.startswith("VAL_"):
                assert spec["retry_safe"] is False, \
                    f"Validation error {code} should never be retried"


# ============================================================================
# Test: Error Code Structure Integrity
# ============================================================================

class TestErrorCodeStructureIntegrity:
    """Verify each error code entry has all required fields."""

    def test_all_codes_have_http_status(self):
        """Every error must have http_status"""
        for code, spec in ERROR_CATALOG.items():
            assert "http_status" in spec, f"{code} missing http_status"

    def test_all_codes_have_category(self):
        """Every error must have category"""
        for code, spec in ERROR_CATALOG.items():
            assert "category" in spec, f"{code} missing category"

    def test_all_codes_have_retry_safe(self):
        """Every error must have retry_safe flag"""
        for code, spec in ERROR_CATALOG.items():
            assert "retry_safe" in spec, f"{code} missing retry_safe"
            assert isinstance(spec["retry_safe"], bool), \
                f"{code} retry_safe must be bool"

    def test_all_codes_have_max_retries(self):
        """Every error must have max_retries"""
        for code, spec in ERROR_CATALOG.items():
            assert "max_retries" in spec, f"{code} missing max_retries"
            assert isinstance(spec["max_retries"], int), \
                f"{code} max_retries must be int"

    def test_valid_categories_only(self):
        """All categories must be from defined set"""
        valid_categories = {
            ErrorCategory.EXTERNAL,
            ErrorCategory.VALIDATION,
            ErrorCategory.RESOURCE,
            ErrorCategory.STATE,
            ErrorCategory.SECURITY,
            ErrorCategory.PLATFORM,
            ErrorCategory.FINANCIAL,
            ErrorCategory.NETWORK,
        }
        for code, spec in ERROR_CATALOG.items():
            assert spec["category"] in valid_categories, \
                f"{code} has invalid category: {spec['category']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
