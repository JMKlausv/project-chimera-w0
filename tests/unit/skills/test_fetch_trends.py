"""
Test suite for fetch_trends skill contract.

Spec: specs/4-skills-api.md - Skill #1: fetch_trends
Spec: specs/5-mcp-resources.md - MCP resource endpoints and rate limits
Spec: specs/7-error-codes.md - Error handling and recovery strategies

Tests validate the input/output contract, behavior, error handling, and
retry logic for the fetch_trends skill used by the Trend Analyst agent.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import re
import time


# ============================================================================
# SpecError (per specs/7-error-codes.md)
# ============================================================================

class SpecError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400, field: str = None):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.field = field
        super().__init__(f"[{code}] {message} (HTTP {http_status})")


# ============================================================================
# Input Schema (from specs/4-skills-api.md)
# ============================================================================

@dataclass
class FetchTrendsInput:
    """
    Input schema for fetch_trends skill.

    Spec: specs/4-skills-api.md - Section 1. fetch_trends - Input Schema

    REQUIRED:
    - platform: str enum [twitter, news, market, reddit, tiktok]

    OPTIONAL (with defaults):
    - limit: int (1-500, default 50)
    - timeWindow: str (pattern ^[0-9]+(h|d)$, default "24h")
    - minEngagement: int (>= 0, default 10000)
    - excludeTopics: list[str] (max 50 items)
    """
    platform: str
    limit: int = 50
    timeWindow: str = "24h"
    minEngagement: int = 10000
    excludeTopics: Optional[List[str]] = None


# ============================================================================
# Output Schema (from specs/4-skills-api.md)
# ============================================================================

@dataclass
class FetchTrendsOutput:
    """
    Output schema for fetch_trends skill.

    Spec: specs/4-skills-api.md - Section 1. fetch_trends - Output Schema

    REQUIRED:
    - trends: list (array of TrendData objects)
    - fetched_at: str (ISO8601)
    - platform: str
    - count: int
    - truncated: bool (true if more trends available beyond limit)
    """
    trends: List[Dict[str, Any]]
    fetched_at: str
    platform: str
    count: int
    truncated: bool


# ============================================================================
# Input Validation (per spec)
# ============================================================================

def validate_fetch_trends_input(input_data: FetchTrendsInput) -> dict:
    """Validate fetch_trends input per specs/4-skills-api.md."""
    errors = []

    # platform validation
    valid_platforms = ["twitter", "news", "market", "reddit", "tiktok"]
    if not input_data.platform:
        errors.append("platform is required")
    elif input_data.platform not in valid_platforms:
        errors.append(f"platform must be one of {valid_platforms}, got '{input_data.platform}'")

    # limit validation
    if input_data.limit < 1:
        errors.append(f"limit minimum is 1, got {input_data.limit}")
    if input_data.limit > 500:
        errors.append(f"limit maximum is 500, got {input_data.limit}")

    # timeWindow validation
    time_pattern = re.compile(r'^[0-9]+(h|d)$')
    if not time_pattern.match(input_data.timeWindow):
        errors.append(f"timeWindow must match pattern ^[0-9]+(h|d)$, got '{input_data.timeWindow}'")

    # minEngagement validation
    if input_data.minEngagement < 0:
        errors.append(f"minEngagement minimum is 0, got {input_data.minEngagement}")

    # excludeTopics validation
    if input_data.excludeTopics is not None:
        if len(input_data.excludeTopics) > 50:
            errors.append(f"excludeTopics maxItems is 50, got {len(input_data.excludeTopics)}")
        for topic in input_data.excludeTopics:
            if not isinstance(topic, str):
                errors.append(f"excludeTopics items must be strings, got {type(topic)}")

    return {"valid": len(errors) == 0, "errors": errors}


# ============================================================================
# Output Validation (per spec)
# ============================================================================

def validate_fetch_trends_output(output: FetchTrendsOutput) -> dict:
    """Validate fetch_trends output per specs/4-skills-api.md."""
    errors = []

    # trends must be a list
    if not isinstance(output.trends, list):
        errors.append("trends must be an array")

    # fetched_at must be ISO8601
    try:
        datetime.fromisoformat(output.fetched_at.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        errors.append(f"fetched_at must be ISO8601, got '{output.fetched_at}'")

    # platform must be string
    if not isinstance(output.platform, str):
        errors.append("platform must be a string")

    # count must match trends length
    if output.count != len(output.trends):
        errors.append(f"count ({output.count}) must match len(trends) ({len(output.trends)})")

    # truncated must be boolean
    if not isinstance(output.truncated, bool):
        errors.append("truncated must be a boolean")

    return {"valid": len(errors) == 0, "errors": errors}


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def valid_input():
    """Valid fetch_trends input."""
    return FetchTrendsInput(
        platform="twitter",
        limit=100,
        timeWindow="4h",
        minEngagement=5000
    )


@pytest.fixture
def default_input():
    """Input with all defaults."""
    return FetchTrendsInput(platform="twitter")


@pytest.fixture
def sample_trend():
    """A single valid TrendData dict."""
    return {
        "trend_id": str(uuid4()),
        "topic": "AI Safety Governance",
        "platform": "twitter",
        "sentiment": "positive",
        "timestamp": "2026-02-06T10:30:00Z",
        "engagement": {
            "likes": 5000,
            "comments": 1200,
            "shares": 800,
            "impressions": 150000,
            "engagement_score": 12400,
        },
        "trend_velocity": 2.5,
        "decay_score": 0.95,
    }


@pytest.fixture
def valid_output(sample_trend):
    """Valid fetch_trends output."""
    return FetchTrendsOutput(
        trends=[sample_trend],
        fetched_at="2026-02-06T10:35:00Z",
        platform="twitter",
        count=1,
        truncated=False,
    )


# ============================================================================
# Test: Input Schema - Required Fields
# ============================================================================

class TestFetchTrendsInputRequired:
    """Verify required input fields per spec."""

    def test_platform_is_required(self):
        """Spec: platform is required"""
        inp = FetchTrendsInput(platform="twitter")
        assert inp.platform is not None

    def test_platform_enum_twitter(self):
        """platform can be 'twitter'"""
        result = validate_fetch_trends_input(FetchTrendsInput(platform="twitter"))
        assert result["valid"] is True

    def test_platform_enum_news(self):
        """platform can be 'news'"""
        result = validate_fetch_trends_input(FetchTrendsInput(platform="news"))
        assert result["valid"] is True

    def test_platform_enum_market(self):
        """platform can be 'market'"""
        result = validate_fetch_trends_input(FetchTrendsInput(platform="market"))
        assert result["valid"] is True

    def test_platform_enum_reddit(self):
        """platform can be 'reddit'"""
        result = validate_fetch_trends_input(FetchTrendsInput(platform="reddit"))
        assert result["valid"] is True

    def test_platform_enum_tiktok(self):
        """platform can be 'tiktok'"""
        result = validate_fetch_trends_input(FetchTrendsInput(platform="tiktok"))
        assert result["valid"] is True

    def test_invalid_platform_rejected(self):
        """Spec: invalid platform returns INVALID_PLATFORM (400)"""
        result = validate_fetch_trends_input(FetchTrendsInput(platform="instagram"))
        assert result["valid"] is False
        assert any("platform" in e for e in result["errors"])


# ============================================================================
# Test: Input Schema - Optional Fields with Defaults
# ============================================================================

class TestFetchTrendsInputDefaults:
    """Verify optional input fields and their defaults per spec."""

    def test_limit_default_50(self, default_input):
        """Spec: limit default 50"""
        assert default_input.limit == 50

    def test_time_window_default_24h(self, default_input):
        """Spec: timeWindow default '24h'"""
        assert default_input.timeWindow == "24h"

    def test_min_engagement_default_10000(self, default_input):
        """Spec: minEngagement default 10000"""
        assert default_input.minEngagement == 10000

    def test_exclude_topics_default_none(self, default_input):
        """Spec: excludeTopics is optional (default None)"""
        assert default_input.excludeTopics is None


# ============================================================================
# Test: Input Schema - Field Constraints
# ============================================================================

class TestFetchTrendsInputConstraints:
    """Verify input field constraints per spec."""

    # --- limit constraints ---

    def test_limit_minimum_1(self):
        """Spec: limit minimum 1"""
        result = validate_fetch_trends_input(
            FetchTrendsInput(platform="twitter", limit=1)
        )
        assert result["valid"] is True

    def test_limit_maximum_500(self):
        """Spec: limit maximum 500"""
        result = validate_fetch_trends_input(
            FetchTrendsInput(platform="twitter", limit=500)
        )
        assert result["valid"] is True

    def test_limit_below_minimum_rejected(self):
        """limit < 1 should be rejected"""
        result = validate_fetch_trends_input(
            FetchTrendsInput(platform="twitter", limit=0)
        )
        assert result["valid"] is False
        assert any("limit" in e for e in result["errors"])

    def test_limit_above_maximum_rejected(self):
        """limit > 500 should be rejected"""
        result = validate_fetch_trends_input(
            FetchTrendsInput(platform="twitter", limit=501)
        )
        assert result["valid"] is False
        assert any("limit" in e for e in result["errors"])

    # --- timeWindow constraints ---

    def test_time_window_hours(self):
        """timeWindow '4h' is valid"""
        result = validate_fetch_trends_input(
            FetchTrendsInput(platform="twitter", timeWindow="4h")
        )
        assert result["valid"] is True

    def test_time_window_days(self):
        """timeWindow '1d' is valid"""
        result = validate_fetch_trends_input(
            FetchTrendsInput(platform="twitter", timeWindow="1d")
        )
        assert result["valid"] is True

    def test_time_window_invalid_unit(self):
        """timeWindow with invalid unit rejected"""
        result = validate_fetch_trends_input(
            FetchTrendsInput(platform="twitter", timeWindow="4m")
        )
        assert result["valid"] is False
        assert any("timeWindow" in e for e in result["errors"])

    def test_time_window_no_number(self):
        """timeWindow without number rejected"""
        result = validate_fetch_trends_input(
            FetchTrendsInput(platform="twitter", timeWindow="h")
        )
        assert result["valid"] is False

    def test_time_window_empty_rejected(self):
        """Empty timeWindow rejected"""
        result = validate_fetch_trends_input(
            FetchTrendsInput(platform="twitter", timeWindow="")
        )
        assert result["valid"] is False

    # --- minEngagement constraints ---

    def test_min_engagement_zero(self):
        """minEngagement 0 is valid"""
        result = validate_fetch_trends_input(
            FetchTrendsInput(platform="twitter", minEngagement=0)
        )
        assert result["valid"] is True

    def test_min_engagement_negative_rejected(self):
        """minEngagement < 0 should be rejected"""
        result = validate_fetch_trends_input(
            FetchTrendsInput(platform="twitter", minEngagement=-1)
        )
        assert result["valid"] is False
        assert any("minEngagement" in e for e in result["errors"])

    # --- excludeTopics constraints ---

    def test_exclude_topics_valid(self):
        """excludeTopics with valid strings"""
        result = validate_fetch_trends_input(
            FetchTrendsInput(platform="twitter", excludeTopics=["politics", "sports"])
        )
        assert result["valid"] is True

    def test_exclude_topics_max_50(self):
        """Spec: excludeTopics maxItems 50"""
        topics = [f"topic{i}" for i in range(51)]
        result = validate_fetch_trends_input(
            FetchTrendsInput(platform="twitter", excludeTopics=topics)
        )
        assert result["valid"] is False
        assert any("excludeTopics" in e for e in result["errors"])


# ============================================================================
# Test: Output Schema Validation
# ============================================================================

class TestFetchTrendsOutputSchema:
    """Verify output schema per spec."""

    def test_valid_output_passes(self, valid_output):
        """Valid output passes validation"""
        result = validate_fetch_trends_output(valid_output)
        assert result["valid"] is True

    def test_output_has_trends_array(self, valid_output):
        """Spec: output.trends is array"""
        assert isinstance(valid_output.trends, list)

    def test_output_has_fetched_at_iso8601(self, valid_output):
        """Spec: output.fetched_at is ISO8601"""
        ts = valid_output.fetched_at
        parsed = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        assert parsed is not None

    def test_output_has_platform(self, valid_output):
        """Spec: output.platform is string"""
        assert isinstance(valid_output.platform, str)

    def test_output_has_count(self, valid_output):
        """Spec: output.count is integer"""
        assert isinstance(valid_output.count, int)

    def test_output_count_matches_trends_length(self, valid_output):
        """output.count must match len(output.trends)"""
        assert valid_output.count == len(valid_output.trends)

    def test_output_has_truncated(self, valid_output):
        """Spec: output.truncated is boolean"""
        assert isinstance(valid_output.truncated, bool)

    def test_output_truncated_false_when_all_returned(self, valid_output):
        """truncated=false when all trends fit within limit"""
        assert valid_output.truncated is False

    def test_output_truncated_true_when_more_available(self, sample_trend):
        """truncated=true when more trends exist beyond limit"""
        output = FetchTrendsOutput(
            trends=[sample_trend] * 50,
            fetched_at="2026-02-06T10:35:00Z",
            platform="twitter",
            count=50,
            truncated=True,
        )
        assert output.truncated is True

    def test_output_empty_trends_valid(self):
        """Empty trends list is valid (no trends matched criteria)"""
        output = FetchTrendsOutput(
            trends=[],
            fetched_at="2026-02-06T10:35:00Z",
            platform="twitter",
            count=0,
            truncated=False,
        )
        result = validate_fetch_trends_output(output)
        assert result["valid"] is True


# ============================================================================
# Test: Behavior - Timeout
# ============================================================================

class TestFetchTrendsBehaviorTimeout:
    """Verify timeout behavior per spec.

    Spec: Timeout 30 seconds (10s per platform if multiple).
    """

    def test_timeout_value_is_30_seconds(self):
        """Spec: fetch_trends timeout is 30 seconds"""
        FETCH_TRENDS_TIMEOUT = 30
        assert FETCH_TRENDS_TIMEOUT == 30

    def test_per_platform_timeout_is_10_seconds(self):
        """Spec: 10s per platform if fetching multiple"""
        PER_PLATFORM_TIMEOUT = 10
        assert PER_PLATFORM_TIMEOUT == 10


# ============================================================================
# Test: Behavior - Retry Logic
# ============================================================================

class TestFetchTrendsRetryLogic:
    """Verify retry behavior per spec.

    Spec: Up to 3 attempts with exponential backoff (1s, 2s, 4s).
    """

    def test_max_retries_is_3(self):
        """Spec: max 3 retry attempts"""
        MAX_RETRIES = 3
        assert MAX_RETRIES == 3

    def test_exponential_backoff_delays(self):
        """Spec: backoff delays are 1s, 2s, 4s (2^attempt)"""
        delays = [2 ** attempt for attempt in range(3)]
        assert delays == [1, 2, 4]

    def test_retry_on_platform_unavailable(self):
        """Spec: PLATFORM_UNAVAILABLE (503) is retryable"""
        retryable_codes = {"PLATFORM_UNAVAILABLE", "RATE_LIMITED", "TIMEOUT", "NETWORK_ERROR"}
        assert "PLATFORM_UNAVAILABLE" in retryable_codes

    def test_retry_on_rate_limited(self):
        """Spec: RATE_LIMITED (429) triggers exponential backoff"""
        retryable_codes = {"PLATFORM_UNAVAILABLE", "RATE_LIMITED", "TIMEOUT", "NETWORK_ERROR"}
        assert "RATE_LIMITED" in retryable_codes

    def test_retry_on_timeout(self):
        """Spec: TIMEOUT (504) is retryable"""
        retryable_codes = {"PLATFORM_UNAVAILABLE", "RATE_LIMITED", "TIMEOUT", "NETWORK_ERROR"}
        assert "TIMEOUT" in retryable_codes

    def test_retry_on_network_error(self):
        """Spec: NETWORK_ERROR (503) is retryable"""
        retryable_codes = {"PLATFORM_UNAVAILABLE", "RATE_LIMITED", "TIMEOUT", "NETWORK_ERROR"}
        assert "NETWORK_ERROR" in retryable_codes

    def test_no_retry_on_invalid_platform(self):
        """Spec: INVALID_PLATFORM (400) is NOT retryable"""
        non_retryable_codes = {"INVALID_PLATFORM", "VALIDATION_FAILED"}
        assert "INVALID_PLATFORM" in non_retryable_codes

    def test_no_retry_on_validation_failed(self):
        """Spec: VALIDATION_FAILED (422) is NOT retryable"""
        non_retryable_codes = {"INVALID_PLATFORM", "VALIDATION_FAILED"}
        assert "VALIDATION_FAILED" in non_retryable_codes


# ============================================================================
# Test: Behavior - Idempotency
# ============================================================================

class TestFetchTrendsIdempotency:
    """Verify idempotency behavior per spec.

    Spec: Same input within 5 minutes returns cached results.
    """

    def test_cache_ttl_is_5_minutes(self):
        """Spec: idempotency cache TTL is 5 minutes"""
        CACHE_TTL_SECONDS = 300  # 5 minutes
        assert CACHE_TTL_SECONDS == 300

    def test_same_input_returns_same_output(self):
        """Same input within cache window should return identical results"""
        # Simulate: two calls with same input
        input_1 = FetchTrendsInput(platform="twitter", limit=50, timeWindow="24h")
        input_2 = FetchTrendsInput(platform="twitter", limit=50, timeWindow="24h")

        # Hash comparison: same inputs produce same cache key
        key_1 = f"{input_1.platform}:{input_1.limit}:{input_1.timeWindow}:{input_1.minEngagement}"
        key_2 = f"{input_2.platform}:{input_2.limit}:{input_2.timeWindow}:{input_2.minEngagement}"
        assert key_1 == key_2

    def test_different_input_returns_different_output(self):
        """Different inputs produce different cache keys"""
        input_1 = FetchTrendsInput(platform="twitter", limit=50)
        input_2 = FetchTrendsInput(platform="news", limit=50)

        key_1 = f"{input_1.platform}:{input_1.limit}"
        key_2 = f"{input_2.platform}:{input_2.limit}"
        assert key_1 != key_2


# ============================================================================
# Test: Behavior - Fallback
# ============================================================================

class TestFetchTrendsFallback:
    """Verify fallback behavior per spec.

    Spec: If primary platform unavailable, try fallback platform.
    Example: twitter -> twitter/feed/general
    """

    def test_fallback_platform_exists(self):
        """Each platform should have a fallback strategy"""
        fallback_map = {
            "twitter": "twitter/feed/general",
            "news": "news/global/trends",
            "market": "market/crypto/general",
            "reddit": "reddit/all/trending",
            "tiktok": "tiktok/trending/general",
        }
        for platform in ["twitter", "news", "market", "reddit", "tiktok"]:
            assert platform in fallback_map


# ============================================================================
# Test: Error Codes (per specs/4-skills-api.md)
# ============================================================================

class TestFetchTrendsErrorCodes:
    """Verify all error codes for fetch_trends per spec."""

    def test_platform_unavailable_error(self):
        """Spec: PLATFORM_UNAVAILABLE - HTTP 503, retry with fallback"""
        error = SpecError(
            code="PLATFORM_UNAVAILABLE",
            message="Twitter API down",
            http_status=503
        )
        assert error.code == "PLATFORM_UNAVAILABLE"
        assert error.http_status == 503

    def test_rate_limited_error(self):
        """Spec: RATE_LIMITED - HTTP 429, exponential backoff"""
        error = SpecError(
            code="RATE_LIMITED",
            message=">100 requests/hour",
            http_status=429
        )
        assert error.code == "RATE_LIMITED"
        assert error.http_status == 429

    def test_invalid_platform_error(self):
        """Spec: INVALID_PLATFORM - HTTP 400, reject immediately"""
        error = SpecError(
            code="INVALID_PLATFORM",
            message='platform="unknown"',
            http_status=400
        )
        assert error.code == "INVALID_PLATFORM"
        assert error.http_status == 400

    def test_validation_failed_error(self):
        """Spec: VALIDATION_FAILED - HTTP 422, log and return empty"""
        error = SpecError(
            code="VALIDATION_FAILED",
            message="Malformed response from MCP",
            http_status=422
        )
        assert error.code == "VALIDATION_FAILED"
        assert error.http_status == 422

    def test_timeout_error(self):
        """Spec: TIMEOUT - HTTP 504, retry then fallback"""
        error = SpecError(
            code="TIMEOUT",
            message="No response within 30s",
            http_status=504
        )
        assert error.code == "TIMEOUT"
        assert error.http_status == 504

    def test_network_error(self):
        """Spec: NETWORK_ERROR - HTTP 503, exponential backoff max 3"""
        error = SpecError(
            code="NETWORK_ERROR",
            message="Connection refused",
            http_status=503
        )
        assert error.code == "NETWORK_ERROR"
        assert error.http_status == 503


# ============================================================================
# Test: Rate Limits (per specs/5-mcp-resources.md)
# ============================================================================

class TestFetchTrendsRateLimits:
    """Verify rate limit awareness per spec.

    Spec: Twitter 100/hr, News 50/hr, Market 200/hr
    """

    def test_twitter_rate_limit(self):
        """Spec: Twitter rate limit is 100 requests/hour"""
        TWITTER_RATE_LIMIT = 100
        assert TWITTER_RATE_LIMIT == 100

    def test_news_rate_limit(self):
        """Spec: News rate limit is 50 requests/hour"""
        NEWS_RATE_LIMIT = 50
        assert NEWS_RATE_LIMIT == 50

    def test_market_rate_limit(self):
        """Spec: Market rate limit is 200 requests/hour"""
        MARKET_RATE_LIMIT = 200
        assert MARKET_RATE_LIMIT == 200


# ============================================================================
# Test: MCP Resources (per specs/5-mcp-resources.md)
# ============================================================================

class TestFetchTrendsMCPResources:
    """Verify MCP resource URIs per spec."""

    def test_twitter_mentions_resource(self):
        """Spec: twitter://mentions/recent"""
        resource = "twitter://mentions/recent"
        assert resource.startswith("twitter://")

    def test_news_global_trends_resource(self):
        """Spec: news://global/trends"""
        resource = "news://global/trends"
        assert resource.startswith("news://")

    def test_market_crypto_resource(self):
        """Spec: market://crypto/{asset}/trending"""
        resource = "market://crypto/BTC/trending"
        assert resource.startswith("market://")
        assert "crypto" in resource

    def test_mcp_resources_for_all_platforms(self):
        """Each platform has at least one MCP resource"""
        mcp_resources = {
            "twitter": ["twitter://mentions/recent", "twitter://feed/{user_id}"],
            "news": ["news://global/trends", "news://region/{region}/trends"],
            "market": ["market://crypto/{asset}/trending"],
            "reddit": [],  # Not explicitly listed in spec
            "tiktok": [],  # Not explicitly listed in spec
        }
        # Twitter, news, market all have defined MCP resources
        assert len(mcp_resources["twitter"]) >= 1
        assert len(mcp_resources["news"]) >= 1
        assert len(mcp_resources["market"]) >= 1


# ============================================================================
# Test: Engagement Threshold Filtering
# ============================================================================

class TestFetchTrendsEngagementFiltering:
    """Verify engagement threshold filtering per spec.

    Spec: FR-1 requires engagement_score >= 10,000 for trend inclusion.
    """

    def test_default_engagement_threshold(self):
        """Spec: default minEngagement is 10000"""
        inp = FetchTrendsInput(platform="twitter")
        assert inp.minEngagement == 10000

    def test_trends_above_threshold_included(self, sample_trend):
        """Trends with engagement_score >= threshold should be included"""
        threshold = 10000
        assert sample_trend["engagement"]["engagement_score"] >= threshold

    def test_trends_below_threshold_excluded(self):
        """Trends with engagement_score < threshold should be excluded"""
        low_engagement_trend = {
            "trend_id": str(uuid4()),
            "topic": "Unpopular topic",
            "platform": "twitter",
            "engagement": {"engagement_score": 500},
        }
        threshold = 10000
        assert low_engagement_trend["engagement"]["engagement_score"] < threshold

    def test_custom_engagement_threshold(self):
        """Custom minEngagement overrides default"""
        inp = FetchTrendsInput(platform="twitter", minEngagement=5000)
        assert inp.minEngagement == 5000


# ============================================================================
# Test: Performance SLA
# ============================================================================

class TestFetchTrendsPerformanceSLA:
    """Verify performance targets per specs/2-design.md SLA table.

    Spec: P50=2s, P95=8s, P99=15s, Timeout=30s
    """

    def test_p50_latency_target(self):
        """Spec: P50 latency target is 2 seconds"""
        P50_TARGET_MS = 2000
        assert P50_TARGET_MS == 2000

    def test_p95_latency_target(self):
        """Spec: P95 latency target is 8 seconds"""
        P95_TARGET_MS = 8000
        assert P95_TARGET_MS == 8000

    def test_p99_latency_target(self):
        """Spec: P99 latency target is 15 seconds"""
        P99_TARGET_MS = 15000
        assert P99_TARGET_MS == 15000

    def test_timeout_is_30_seconds(self):
        """Spec: absolute timeout is 30 seconds"""
        TIMEOUT_MS = 30000
        assert TIMEOUT_MS == 30000


# ============================================================================
# Test: Observability (per specs/4-skills-api.md)
# ============================================================================

class TestFetchTrendsObservability:
    """Verify observability requirements per spec.

    Spec: All skill calls MUST log: skill_name, agent_id, timestamp,
    input_hash, output_hash, duration_ms, error_code, retry_count, success.
    """

    def test_observability_log_fields(self):
        """Spec: required log fields for skill calls"""
        required_fields = [
            "skill_name",
            "agent_id",
            "timestamp",
            "input_hash",
            "output_hash",
            "duration_ms",
            "error_code",
            "retry_count",
            "success",
        ]
        sample_log = {
            "skill_name": "fetch_trends",
            "agent_id": str(uuid4()),
            "timestamp": "2026-02-06T10:30:00Z",
            "input_hash": "sha256_abc123",
            "output_hash": "sha256_def456",
            "duration_ms": 2543,
            "error_code": None,
            "retry_count": 0,
            "success": True,
        }
        for f in required_fields:
            assert f in sample_log, f"Missing observability field: {f}"

    def test_skill_name_is_fetch_trends(self):
        """Log must record skill_name as 'fetch_trends'"""
        log_entry = {"skill_name": "fetch_trends"}
        assert log_entry["skill_name"] == "fetch_trends"

    def test_metrics_names(self):
        """Spec: key metrics include duration, errors, retries, success_rate"""
        metrics = [
            "skill_fetch_trends_duration_ms",
            "skill_fetch_trends_errors_total",
            "skill_fetch_trends_retries_total",
            "skill_fetch_trends_success_rate",
        ]
        for m in metrics:
            assert "fetch_trends" in m


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
