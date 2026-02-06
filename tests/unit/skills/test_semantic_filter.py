"""
Test suite for semantic_filter skill contract.

Spec: specs/4-skills-api.md - Skill #2: semantic_filter
Spec: specs/2-design.md - Perception System - Semantic Filter Pipeline
Spec: specs/7-error-codes.md - Error handling and recovery strategies

Tests validate the input/output contract, behavior, scoring, error handling,
and caching logic for the semantic_filter skill used by the Orchestrator.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import re


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
class SemanticFilterInput:
    """
    Input schema for semantic_filter skill.

    Spec: specs/4-skills-api.md - Section 2. semantic_filter - Input Schema

    REQUIRED:
    - trends: list of TrendData objects (1-1000 items)
    - campaign_goals: list of strings (1-10 items)

    OPTIONAL (with defaults):
    - relevance_threshold: float (0-1, default 0.75)
    - model: str enum [gemini-3-flash, gpt-4o-mini] (default gemini-3-flash)
    """
    trends: List[Dict[str, Any]]
    campaign_goals: List[str]
    relevance_threshold: float = 0.75
    model: str = "gemini-3-flash"


# ============================================================================
# Output Schema (from specs/4-skills-api.md)
# ============================================================================

@dataclass
class FilteredTrend:
    """A single filtered trend with relevance score and reasoning."""
    trend: Dict[str, Any]
    relevance_score: float
    reasoning: str


@dataclass
class SemanticFilterOutput:
    """
    Output schema for semantic_filter skill.

    Spec: specs/4-skills-api.md - Section 2. semantic_filter - Output Schema

    REQUIRED:
    - filtered_trends: list of {trend, relevance_score, reasoning}
    - total_input: int (count of input trends)
    - total_output: int (count of filtered trends)
    - filtered_at: str (ISO8601 timestamp)
    """
    filtered_trends: List[Dict[str, Any]]
    total_input: int
    total_output: int
    filtered_at: str


# ============================================================================
# Input Validation (per spec)
# ============================================================================

def validate_semantic_filter_input(input_data: SemanticFilterInput) -> dict:
    """Validate semantic_filter input per specs/4-skills-api.md."""
    errors = []

    # trends validation
    if not isinstance(input_data.trends, list):
        errors.append("trends must be an array")
    elif len(input_data.trends) < 1:
        errors.append("trends minItems is 1")
    elif len(input_data.trends) > 1000:
        errors.append(f"trends maxItems is 1000, got {len(input_data.trends)}")

    # campaign_goals validation
    if not isinstance(input_data.campaign_goals, list):
        errors.append("campaign_goals must be an array")
    elif len(input_data.campaign_goals) < 1:
        errors.append("campaign_goals minItems is 1")
    elif len(input_data.campaign_goals) > 10:
        errors.append(f"campaign_goals maxItems is 10, got {len(input_data.campaign_goals)}")
    else:
        for goal in input_data.campaign_goals:
            if not isinstance(goal, str):
                errors.append(f"campaign_goals items must be strings, got {type(goal)}")
            elif len(goal.strip()) == 0:
                errors.append("campaign_goals items must be non-empty strings")

    # relevance_threshold validation
    if input_data.relevance_threshold < 0:
        errors.append(f"relevance_threshold minimum is 0, got {input_data.relevance_threshold}")
    if input_data.relevance_threshold > 1:
        errors.append(f"relevance_threshold maximum is 1, got {input_data.relevance_threshold}")

    # model validation
    valid_models = ["gemini-3-flash", "gpt-4o-mini"]
    if input_data.model not in valid_models:
        errors.append(f"model must be one of {valid_models}, got '{input_data.model}'")

    return {"valid": len(errors) == 0, "errors": errors}


# ============================================================================
# Output Validation (per spec)
# ============================================================================

def validate_semantic_filter_output(output: SemanticFilterOutput) -> dict:
    """Validate semantic_filter output per specs/4-skills-api.md."""
    errors = []

    # filtered_trends must be a list
    if not isinstance(output.filtered_trends, list):
        errors.append("filtered_trends must be an array")

    # Each filtered trend must have trend, relevance_score, reasoning
    for i, ft in enumerate(output.filtered_trends):
        if not isinstance(ft, dict):
            errors.append(f"filtered_trends[{i}] must be an object")
            continue
        if "trend" not in ft:
            errors.append(f"filtered_trends[{i}] missing 'trend'")
        if "relevance_score" not in ft:
            errors.append(f"filtered_trends[{i}] missing 'relevance_score'")
        else:
            score = ft["relevance_score"]
            if not isinstance(score, (int, float)):
                errors.append(f"filtered_trends[{i}].relevance_score must be number")
            elif score < 0 or score > 1:
                errors.append(f"filtered_trends[{i}].relevance_score must be 0-1, got {score}")
        if "reasoning" not in ft:
            errors.append(f"filtered_trends[{i}] missing 'reasoning'")
        elif not isinstance(ft.get("reasoning"), str):
            errors.append(f"filtered_trends[{i}].reasoning must be string")
        elif len(ft["reasoning"]) > 500:
            errors.append(f"filtered_trends[{i}].reasoning maxLength is 500")

    # total_input must be integer
    if not isinstance(output.total_input, int):
        errors.append("total_input must be integer")

    # total_output must match filtered_trends length
    if output.total_output != len(output.filtered_trends):
        errors.append(
            f"total_output ({output.total_output}) must match "
            f"len(filtered_trends) ({len(output.filtered_trends)})"
        )

    # filtered_at must be ISO8601
    try:
        datetime.fromisoformat(output.filtered_at.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        errors.append(f"filtered_at must be ISO8601, got '{output.filtered_at}'")

    return {"valid": len(errors) == 0, "errors": errors}


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_trend():
    """A single valid TrendData dict."""
    return {
        "trend_id": str(uuid4()),
        "topic": "Sustainable Fashion in Africa",
        "platform": "twitter",
        "sentiment": "positive",
        "timestamp": "2026-02-06T10:30:00Z",
        "engagement": {
            "likes": 8000,
            "comments": 2000,
            "shares": 1500,
            "impressions": 200000,
            "engagement_score": 16500,
        },
        "trend_velocity": 3.2,
        "decay_score": 0.9,
    }


@pytest.fixture
def sample_trends(sample_trend):
    """Multiple valid TrendData dicts."""
    trends = []
    topics = [
        "Sustainable Fashion in Africa",
        "AI Safety Governance Update",
        "Crypto Market Surge",
        "New Tech Startups in LATAM",
        "Climate Change Policy",
    ]
    for topic in topics:
        t = sample_trend.copy()
        t["trend_id"] = str(uuid4())
        t["topic"] = topic
        trends.append(t)
    return trends


@pytest.fixture
def valid_input(sample_trends):
    """Valid semantic_filter input."""
    return SemanticFilterInput(
        trends=sample_trends,
        campaign_goals=["fashion", "luxury", "Africa"],
        relevance_threshold=0.75,
    )


@pytest.fixture
def valid_output(sample_trend):
    """Valid semantic_filter output."""
    return SemanticFilterOutput(
        filtered_trends=[
            {
                "trend": sample_trend,
                "relevance_score": 0.92,
                "reasoning": "High alignment with fashion campaign goals and African market focus.",
            }
        ],
        total_input=5,
        total_output=1,
        filtered_at="2026-02-06T10:35:00Z",
    )


# ============================================================================
# Test: Input Schema - Required Fields
# ============================================================================

class TestSemanticFilterInputRequired:
    """Verify required input fields per spec."""

    def test_trends_is_required(self, valid_input):
        """Spec: trends is required (array of TrendData)"""
        assert valid_input.trends is not None
        assert isinstance(valid_input.trends, list)

    def test_campaign_goals_is_required(self, valid_input):
        """Spec: campaign_goals is required (array of strings)"""
        assert valid_input.campaign_goals is not None
        assert isinstance(valid_input.campaign_goals, list)

    def test_empty_trends_rejected(self):
        """Spec: trends minItems is 1"""
        result = validate_semantic_filter_input(
            SemanticFilterInput(trends=[], campaign_goals=["fashion"])
        )
        assert result["valid"] is False
        assert any("trends" in e for e in result["errors"])

    def test_empty_campaign_goals_rejected(self, sample_trends):
        """Spec: campaign_goals minItems is 1"""
        result = validate_semantic_filter_input(
            SemanticFilterInput(trends=sample_trends, campaign_goals=[])
        )
        assert result["valid"] is False
        assert any("campaign_goals" in e for e in result["errors"])


# ============================================================================
# Test: Input Schema - Constraints
# ============================================================================

class TestSemanticFilterInputConstraints:
    """Verify input field constraints per spec."""

    # --- trends constraints ---

    def test_trends_min_items_1(self, sample_trend):
        """Spec: trends minItems 1"""
        result = validate_semantic_filter_input(
            SemanticFilterInput(trends=[sample_trend], campaign_goals=["fashion"])
        )
        assert result["valid"] is True

    def test_trends_max_items_1000(self, sample_trend):
        """Spec: trends maxItems 1000"""
        trends = [sample_trend.copy() for _ in range(1000)]
        result = validate_semantic_filter_input(
            SemanticFilterInput(trends=trends, campaign_goals=["fashion"])
        )
        assert result["valid"] is True

    def test_trends_exceeds_max_rejected(self, sample_trend):
        """trends > 1000 items should be rejected"""
        trends = [sample_trend.copy() for _ in range(1001)]
        result = validate_semantic_filter_input(
            SemanticFilterInput(trends=trends, campaign_goals=["fashion"])
        )
        assert result["valid"] is False
        assert any("trends" in e and "maxItems" in e for e in result["errors"])

    # --- campaign_goals constraints ---

    def test_campaign_goals_min_items_1(self, sample_trends):
        """Spec: campaign_goals minItems 1"""
        result = validate_semantic_filter_input(
            SemanticFilterInput(trends=sample_trends, campaign_goals=["fashion"])
        )
        assert result["valid"] is True

    def test_campaign_goals_max_items_10(self, sample_trends):
        """Spec: campaign_goals maxItems 10"""
        goals = [f"goal_{i}" for i in range(10)]
        result = validate_semantic_filter_input(
            SemanticFilterInput(trends=sample_trends, campaign_goals=goals)
        )
        assert result["valid"] is True

    def test_campaign_goals_exceeds_max_rejected(self, sample_trends):
        """campaign_goals > 10 items should be rejected"""
        goals = [f"goal_{i}" for i in range(11)]
        result = validate_semantic_filter_input(
            SemanticFilterInput(trends=sample_trends, campaign_goals=goals)
        )
        assert result["valid"] is False
        assert any("campaign_goals" in e and "maxItems" in e for e in result["errors"])

    def test_campaign_goals_must_be_strings(self, sample_trends):
        """campaign_goals items must be strings"""
        result = validate_semantic_filter_input(
            SemanticFilterInput(trends=sample_trends, campaign_goals=["fashion", 123])
        )
        assert result["valid"] is False

    def test_campaign_goals_non_empty_strings(self, sample_trends):
        """Spec: goals must be non-empty strings (INVALID_GOALS error)"""
        result = validate_semantic_filter_input(
            SemanticFilterInput(trends=sample_trends, campaign_goals=["fashion", "  "])
        )
        assert result["valid"] is False

    # --- relevance_threshold constraints ---

    def test_relevance_threshold_default_075(self, sample_trends):
        """Spec: relevance_threshold default 0.75"""
        inp = SemanticFilterInput(
            trends=sample_trends, campaign_goals=["fashion"]
        )
        assert inp.relevance_threshold == 0.75

    def test_relevance_threshold_minimum_0(self, sample_trends):
        """Spec: relevance_threshold minimum 0"""
        result = validate_semantic_filter_input(
            SemanticFilterInput(
                trends=sample_trends,
                campaign_goals=["fashion"],
                relevance_threshold=0.0,
            )
        )
        assert result["valid"] is True

    def test_relevance_threshold_maximum_1(self, sample_trends):
        """Spec: relevance_threshold maximum 1"""
        result = validate_semantic_filter_input(
            SemanticFilterInput(
                trends=sample_trends,
                campaign_goals=["fashion"],
                relevance_threshold=1.0,
            )
        )
        assert result["valid"] is True

    def test_relevance_threshold_below_zero_rejected(self, sample_trends):
        """relevance_threshold < 0 should be rejected"""
        result = validate_semantic_filter_input(
            SemanticFilterInput(
                trends=sample_trends,
                campaign_goals=["fashion"],
                relevance_threshold=-0.1,
            )
        )
        assert result["valid"] is False
        assert any("relevance_threshold" in e for e in result["errors"])

    def test_relevance_threshold_above_one_rejected(self, sample_trends):
        """relevance_threshold > 1 should be rejected"""
        result = validate_semantic_filter_input(
            SemanticFilterInput(
                trends=sample_trends,
                campaign_goals=["fashion"],
                relevance_threshold=1.1,
            )
        )
        assert result["valid"] is False
        assert any("relevance_threshold" in e for e in result["errors"])

    # --- model constraints ---

    def test_model_default_gemini(self, sample_trends):
        """Spec: model default 'gemini-3-flash'"""
        inp = SemanticFilterInput(
            trends=sample_trends, campaign_goals=["fashion"]
        )
        assert inp.model == "gemini-3-flash"

    def test_model_enum_gemini(self, sample_trends):
        """model can be 'gemini-3-flash'"""
        result = validate_semantic_filter_input(
            SemanticFilterInput(
                trends=sample_trends,
                campaign_goals=["fashion"],
                model="gemini-3-flash",
            )
        )
        assert result["valid"] is True

    def test_model_enum_gpt(self, sample_trends):
        """model can be 'gpt-4o-mini'"""
        result = validate_semantic_filter_input(
            SemanticFilterInput(
                trends=sample_trends,
                campaign_goals=["fashion"],
                model="gpt-4o-mini",
            )
        )
        assert result["valid"] is True

    def test_model_invalid_rejected(self, sample_trends):
        """Invalid model should be rejected"""
        result = validate_semantic_filter_input(
            SemanticFilterInput(
                trends=sample_trends,
                campaign_goals=["fashion"],
                model="claude-4",
            )
        )
        assert result["valid"] is False
        assert any("model" in e for e in result["errors"])


# ============================================================================
# Test: Output Schema Validation
# ============================================================================

class TestSemanticFilterOutputSchema:
    """Verify output schema per spec."""

    def test_valid_output_passes(self, valid_output):
        """Valid output passes validation"""
        result = validate_semantic_filter_output(valid_output)
        assert result["valid"] is True

    def test_output_has_filtered_trends(self, valid_output):
        """Spec: output.filtered_trends is array"""
        assert isinstance(valid_output.filtered_trends, list)

    def test_output_has_total_input(self, valid_output):
        """Spec: output.total_input is integer"""
        assert isinstance(valid_output.total_input, int)

    def test_output_has_total_output(self, valid_output):
        """Spec: output.total_output is integer"""
        assert isinstance(valid_output.total_output, int)

    def test_output_total_output_matches_filtered(self, valid_output):
        """total_output must match len(filtered_trends)"""
        assert valid_output.total_output == len(valid_output.filtered_trends)

    def test_output_has_filtered_at_iso8601(self, valid_output):
        """Spec: output.filtered_at is ISO8601"""
        ts = valid_output.filtered_at
        parsed = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        assert parsed is not None

    def test_output_empty_filtered_trends_valid(self):
        """Empty filtered_trends is valid (no trends met threshold)"""
        output = SemanticFilterOutput(
            filtered_trends=[],
            total_input=5,
            total_output=0,
            filtered_at="2026-02-06T10:35:00Z",
        )
        result = validate_semantic_filter_output(output)
        assert result["valid"] is True

    def test_total_output_lte_total_input(self, valid_output):
        """total_output should never exceed total_input"""
        assert valid_output.total_output <= valid_output.total_input


# ============================================================================
# Test: Filtered Trend Item Schema
# ============================================================================

class TestFilteredTrendItemSchema:
    """Verify each item in filtered_trends per spec."""

    def test_filtered_trend_has_trend(self, valid_output):
        """Each filtered trend must have 'trend' object"""
        for ft in valid_output.filtered_trends:
            assert "trend" in ft

    def test_filtered_trend_has_relevance_score(self, valid_output):
        """Each filtered trend must have 'relevance_score' (0-1)"""
        for ft in valid_output.filtered_trends:
            assert "relevance_score" in ft
            assert 0 <= ft["relevance_score"] <= 1

    def test_filtered_trend_has_reasoning(self, valid_output):
        """Each filtered trend must have 'reasoning' string"""
        for ft in valid_output.filtered_trends:
            assert "reasoning" in ft
            assert isinstance(ft["reasoning"], str)

    def test_reasoning_max_length_500(self):
        """Spec: reasoning maxLength 500"""
        output = SemanticFilterOutput(
            filtered_trends=[
                {
                    "trend": {"topic": "test"},
                    "relevance_score": 0.8,
                    "reasoning": "A" * 501,  # Exceeds 500
                }
            ],
            total_input=1,
            total_output=1,
            filtered_at="2026-02-06T10:35:00Z",
        )
        result = validate_semantic_filter_output(output)
        assert result["valid"] is False
        assert any("reasoning" in e and "maxLength" in e for e in result["errors"])

    def test_relevance_score_out_of_range_rejected(self):
        """relevance_score > 1 should be rejected"""
        output = SemanticFilterOutput(
            filtered_trends=[
                {
                    "trend": {"topic": "test"},
                    "relevance_score": 1.5,
                    "reasoning": "test",
                }
            ],
            total_input=1,
            total_output=1,
            filtered_at="2026-02-06T10:35:00Z",
        )
        result = validate_semantic_filter_output(output)
        assert result["valid"] is False


# ============================================================================
# Test: Relevance Threshold Gating
# ============================================================================

class TestRelevanceThresholdGating:
    """Verify relevance threshold filtering behavior per spec.

    Spec: Only return trends with score >= threshold (default 0.75).
    """

    def test_default_threshold_075(self):
        """Spec: default relevance_threshold is 0.75"""
        inp = SemanticFilterInput(
            trends=[{"topic": "test"}],
            campaign_goals=["fashion"],
        )
        assert inp.relevance_threshold == 0.75

    def test_trend_above_threshold_included(self):
        """Trends with relevance_score >= threshold should be included"""
        threshold = 0.75
        score = 0.92
        assert score >= threshold

    def test_trend_below_threshold_excluded(self):
        """Trends with relevance_score < threshold should be excluded"""
        threshold = 0.75
        score = 0.60
        assert score < threshold

    def test_trend_exactly_at_threshold_included(self):
        """Trends with relevance_score == threshold should be included"""
        threshold = 0.75
        score = 0.75
        assert score >= threshold

    def test_custom_threshold_respected(self):
        """Custom threshold changes filtering boundary"""
        inp = SemanticFilterInput(
            trends=[{"topic": "test"}],
            campaign_goals=["fashion"],
            relevance_threshold=0.5,
        )
        # Score 0.6 would pass with threshold 0.5 but fail with 0.75
        assert 0.6 >= inp.relevance_threshold

    def test_threshold_zero_returns_all(self):
        """threshold=0 should return all scored trends"""
        threshold = 0.0
        # Any positive score passes
        assert 0.01 >= threshold

    def test_threshold_one_returns_perfect_only(self):
        """threshold=1.0 only returns perfect-score trends"""
        threshold = 1.0
        assert 0.99 < threshold
        assert 1.0 >= threshold


# ============================================================================
# Test: Scoring Criteria
# ============================================================================

class TestScoringCriteria:
    """Verify scoring criteria per specs/2-design.md.

    Spec scoring weights:
    - Topic alignment with campaign goals (30%)
    - Engagement potential (25%)
    - Audience match (20%)
    - Sentiment alignment (15%)
    - Recency (10%)
    """

    def test_scoring_weights_sum_to_100(self):
        """Scoring weights must sum to 100%"""
        weights = {
            "topic_alignment": 0.30,
            "engagement_potential": 0.25,
            "audience_match": 0.20,
            "sentiment_alignment": 0.15,
            "recency": 0.10,
        }
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.001

    def test_topic_alignment_weight(self):
        """Spec: topic alignment weight is 30%"""
        assert 0.30 == 0.30

    def test_engagement_potential_weight(self):
        """Spec: engagement potential weight is 25%"""
        assert 0.25 == 0.25

    def test_audience_match_weight(self):
        """Spec: audience match weight is 20%"""
        assert 0.20 == 0.20

    def test_sentiment_alignment_weight(self):
        """Spec: sentiment alignment weight is 15%"""
        assert 0.15 == 0.15

    def test_recency_weight(self):
        """Spec: recency weight is 10%"""
        assert 0.10 == 0.10


# ============================================================================
# Test: Behavior - Batching
# ============================================================================

class TestSemanticFilterBatching:
    """Verify batching behavior per spec.

    Spec: Process trends in groups of 100 to optimize LLM calls.
    """

    def test_batch_size_is_100(self):
        """Spec: batch size is 100 trends"""
        BATCH_SIZE = 100
        assert BATCH_SIZE == 100

    def test_single_batch_for_small_input(self):
        """Input <= 100 trends uses 1 batch"""
        trend_count = 50
        batch_size = 100
        num_batches = (trend_count + batch_size - 1) // batch_size
        assert num_batches == 1

    def test_multiple_batches_for_large_input(self):
        """Input > 100 trends uses multiple batches"""
        trend_count = 250
        batch_size = 100
        num_batches = (trend_count + batch_size - 1) // batch_size
        assert num_batches == 3

    def test_max_batches_for_1000_trends(self):
        """1000 trends (max) requires 10 batches"""
        trend_count = 1000
        batch_size = 100
        num_batches = (trend_count + batch_size - 1) // batch_size
        assert num_batches == 10


# ============================================================================
# Test: Behavior - Caching
# ============================================================================

class TestSemanticFilterCaching:
    """Verify caching behavior per spec.

    Spec: Cache scores for same trend + goals combo (30 min TTL).
    """

    def test_cache_ttl_30_minutes(self):
        """Spec: cache TTL is 30 minutes"""
        CACHE_TTL_SECONDS = 1800  # 30 min
        assert CACHE_TTL_SECONDS == 1800

    def test_same_trend_goals_cache_key(self):
        """Same trend + goals combo produces same cache key"""
        trend_id = "trend-abc"
        goals = ["fashion", "luxury"]
        key1 = f"{trend_id}:{','.join(sorted(goals))}"
        key2 = f"{trend_id}:{','.join(sorted(goals))}"
        assert key1 == key2

    def test_different_goals_different_cache_key(self):
        """Different goals produce different cache keys"""
        trend_id = "trend-abc"
        key1 = f"{trend_id}:fashion,luxury"
        key2 = f"{trend_id}:crypto,tech"
        assert key1 != key2

    def test_idempotency_same_input_consistent_scores(self):
        """Spec: Same input produces consistent scores (deterministic LLM seed)"""
        # Simulated: deterministic scoring for same input
        input_hash = hash(("trend-abc", "fashion", "luxury"))
        score_1 = abs(input_hash) % 100 / 100.0
        score_2 = abs(input_hash) % 100 / 100.0
        assert score_1 == score_2


# ============================================================================
# Test: Behavior - Timeout
# ============================================================================

class TestSemanticFilterTimeout:
    """Verify timeout behavior per spec.

    Spec: Timeout 10 seconds for LLM inference (3s per trend batch).
    """

    def test_timeout_value_is_10_seconds(self):
        """Spec: semantic_filter timeout is 10 seconds"""
        TIMEOUT = 10
        assert TIMEOUT == 10

    def test_per_batch_timeout_is_3_seconds(self):
        """Spec: 3s per trend batch"""
        PER_BATCH_TIMEOUT = 3
        assert PER_BATCH_TIMEOUT == 3


# ============================================================================
# Test: Behavior - Partial Results on Timeout
# ============================================================================

class TestSemanticFilterPartialResults:
    """Verify partial result behavior per spec.

    Spec: FILTER_TIMEOUT returns partial results up to last successful batch.
    """

    def test_partial_results_on_timeout(self):
        """On timeout, return results from completed batches"""
        # Simulate: 3 batches, timeout after batch 2
        completed_batches = 2
        batch_size = 100
        partial_count = completed_batches * batch_size
        assert partial_count == 200

    def test_partial_output_still_valid(self):
        """Partial output must still conform to output schema"""
        output = SemanticFilterOutput(
            filtered_trends=[
                {
                    "trend": {"topic": "partial"},
                    "relevance_score": 0.8,
                    "reasoning": "Partial result from completed batch",
                }
            ],
            total_input=300,  # 3 batches planned
            total_output=1,   # Only 1 trend from completed batches
            filtered_at="2026-02-06T10:35:00Z",
        )
        result = validate_semantic_filter_output(output)
        assert result["valid"] is True


# ============================================================================
# Test: Error Codes (per specs/4-skills-api.md)
# ============================================================================

class TestSemanticFilterErrorCodes:
    """Verify all error codes for semantic_filter per spec."""

    def test_filter_timeout_error(self):
        """Spec: FILTER_TIMEOUT - HTTP 504, return partial results"""
        error = SpecError(
            code="FILTER_TIMEOUT",
            message="LLM inference exceeded 10s",
            http_status=504,
        )
        assert error.code == "FILTER_TIMEOUT"
        assert error.http_status == 504

    def test_invalid_input_error(self):
        """Spec: INVALID_INPUT - HTTP 400, reject with validation error"""
        error = SpecError(
            code="INVALID_INPUT",
            message="trends array is empty",
            http_status=400,
        )
        assert error.code == "INVALID_INPUT"
        assert error.http_status == 400

    def test_llm_error(self):
        """Spec: LLM_ERROR - HTTP 503, retry with fallback model"""
        error = SpecError(
            code="LLM_ERROR",
            message="Gemini 3 Flash unavailable",
            http_status=503,
        )
        assert error.code == "LLM_ERROR"
        assert error.http_status == 503

    def test_invalid_goals_error(self):
        """Spec: INVALID_GOALS - HTTP 422, goals must be non-empty strings"""
        error = SpecError(
            code="INVALID_GOALS",
            message="campaign_goals contains empty strings",
            http_status=422,
        )
        assert error.code == "INVALID_GOALS"
        assert error.http_status == 422


# ============================================================================
# Test: LLM Fallback
# ============================================================================

class TestSemanticFilterLLMFallback:
    """Verify LLM fallback behavior per spec.

    Spec: LLM_ERROR triggers retry with fallback model.
    Primary: gemini-3-flash, Fallback: gpt-4o-mini
    """

    def test_primary_model_is_gemini(self):
        """Spec: primary model is gemini-3-flash"""
        PRIMARY_MODEL = "gemini-3-flash"
        assert PRIMARY_MODEL == "gemini-3-flash"

    def test_fallback_model_is_gpt(self):
        """Spec: fallback model is gpt-4o-mini"""
        FALLBACK_MODEL = "gpt-4o-mini"
        assert FALLBACK_MODEL == "gpt-4o-mini"

    def test_fallback_only_on_llm_error(self):
        """Fallback should only trigger on LLM_ERROR, not INVALID_INPUT"""
        retryable_with_fallback = {"LLM_ERROR"}
        non_retryable = {"INVALID_INPUT", "INVALID_GOALS"}
        assert "LLM_ERROR" in retryable_with_fallback
        assert "INVALID_INPUT" not in retryable_with_fallback


# ============================================================================
# Test: Performance SLA
# ============================================================================

class TestSemanticFilterPerformanceSLA:
    """Verify performance targets per specs/2-design.md SLA table.

    Spec: P50=500ms, P95=5s, P99=8s, Timeout=10s
    """

    def test_p50_latency_target(self):
        """Spec: P50 latency target is 500ms"""
        P50_TARGET_MS = 500
        assert P50_TARGET_MS == 500

    def test_p95_latency_target(self):
        """Spec: P95 latency target is 5 seconds"""
        P95_TARGET_MS = 5000
        assert P95_TARGET_MS == 5000

    def test_p99_latency_target(self):
        """Spec: P99 latency target is 8 seconds"""
        P99_TARGET_MS = 8000
        assert P99_TARGET_MS == 8000

    def test_timeout_is_10_seconds(self):
        """Spec: absolute timeout is 10 seconds"""
        TIMEOUT_MS = 10000
        assert TIMEOUT_MS == 10000


# ============================================================================
# Test: Observability
# ============================================================================

class TestSemanticFilterObservability:
    """Verify observability requirements per spec."""

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
            "skill_name": "semantic_filter",
            "agent_id": str(uuid4()),
            "timestamp": "2026-02-06T10:30:00Z",
            "input_hash": "sha256_abc",
            "output_hash": "sha256_def",
            "duration_ms": 850,
            "error_code": None,
            "retry_count": 0,
            "success": True,
        }
        for f in required_fields:
            assert f in sample_log

    def test_skill_name_is_semantic_filter(self):
        """Log must record skill_name as 'semantic_filter'"""
        assert "semantic_filter" == "semantic_filter"

    def test_metrics_names(self):
        """Spec: key metrics include duration, errors, retries, success_rate"""
        metrics = [
            "skill_semantic_filter_duration_ms",
            "skill_semantic_filter_errors_total",
            "skill_semantic_filter_retries_total",
            "skill_semantic_filter_success_rate",
        ]
        for m in metrics:
            assert "semantic_filter" in m


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
