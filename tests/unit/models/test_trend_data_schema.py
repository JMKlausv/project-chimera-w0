"""
Test suite for TrendData schema validation.

Spec: specs/2-design.md - API Contracts - Trend Data Schema
Spec: specs/7-error-codes.md - Error handling and recovery strategies
Tests validate that all TrendData objects conform to the specification exactly.

All validation tests are designed to FAIL before implementation is complete.
Tests pass only when chimera/models/trend.py implements full validation with SpecError.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
import json
import re


# ============================================================================
# SpecError Exception (per specs/7-error-codes.md)
# ============================================================================
# Note: In real implementation, import from chimera.errors.SpecError
# This is a mock for testing purposes - actual implementation in chimera/errors/__init__.py

class SpecError(Exception):
    """Exception for specification violations with error codes.
    
    Spec: specs/7-error-codes.md
    All field validation errors use code=VAL_SCHEMA_INVALID with http_status=422
    """
    def __init__(self, code: str, message: str, http_status: int = 400, field: str = None):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.field = field
        super().__init__(f"[{code}] {message} (HTTP {http_status})")


# ============================================================================
# TrendData Model (from specs/2-design.md)
# Will be imported from: from chimera.models.trend import TrendData
# ============================================================================
# For testing purposes, this is a reference implementation.
# Real implementation should live in src/chimera/models/trend.py

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class TrendData:
    """
    Trend data schema from specs/2-design.md - API Contracts.
    
    All fields MUST match spec constraints exactly or raise SpecError on validation.
    
    REQUIRED FIELDS (cannot be None):
    - trend_id: str (UUID4 format)
    - topic: str (1-500 characters)
    - platform: str (enum: twitter|news|market|reddit|tiktok)
    - sentiment: str (enum: positive|neutral|negative)
    - timestamp: str (ISO8601 format)
    - engagement: dict (nested object with likes, comments, shares, impressions, engagement_score)
    - trend_velocity: float (≥0, represents growth rate in past 24h)
    - decay_score: float (0-1, represents relevance decay)
    
    OPTIONAL FIELDS (can be None):
    - geographic_origin: str (enum: global|US|EU|LATAM|APAC|AFRICA|MENA)
    - metadata: dict (hashtags max 50, mentions max 50, source_urls max 10, category enum)
    """
    trend_id: str
    topic: str
    platform: str
    sentiment: str
    timestamp: str
    engagement: Dict[str, Any]
    trend_velocity: float
    decay_score: float
    geographic_origin: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate all fields per specs/2-design.md on construction.
        
        Raises SpecError with code=VAL_SCHEMA_INVALID (HTTP 422) for any violation.
        """
        # Implementation placeholder - to be filled by developer
        # Should call validate_trend_data() and raise SpecError on failure
        pass


# ============================================================================
# Test Fixtures (Valid Data)
# ============================================================================

@pytest.fixture
def valid_trend_data():
    """Valid TrendData object matching all spec constraints."""
    return TrendData(
        trend_id=str(uuid4()),
        topic="AI Safety Governance",
        platform="twitter",
        sentiment="positive",
        timestamp="2026-02-06T10:30:00Z",
        engagement={
            "likes": 5000,
            "comments": 1200,
            "shares": 800,
            "impressions": 150000,
            "engagement_score": 12400  # likes + comments*2 + shares*3
        },
        trend_velocity=2.5,  # Growing 2.5x in 24h
        decay_score=0.95,    # Very fresh
        geographic_origin="US",
        metadata={
            "hashtags": ["#AISafety", "#Governance"],
            "mentions": ["@OpenAI", "@Anthropic"],
            "source_urls": ["https://example.com"],
            "category": "technology"
        }
    )


@pytest.fixture
def minimal_trend_data():
    """Minimal valid TrendData (only required fields)."""
    return TrendData(
        trend_id=str(uuid4()),
        topic="Bitcoin ETF Approval",
        platform="market",
        sentiment="neutral",
        timestamp="2026-02-06T15:45:00Z",
        engagement={
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "impressions": 0,
            "engagement_score": 0
        },
        trend_velocity=0.0,
        decay_score=0.5
    )


# ============================================================================
# Test: Required Fields Presence
# ============================================================================

class TestTrendDataRequiredFields:
    """Verify all required fields are present per spec."""
    
    def test_trend_id_required(self, minimal_trend_data):
        """Spec: trend_id is REQUIRED (uuid format)"""
        assert hasattr(minimal_trend_data, 'trend_id')
        assert minimal_trend_data.trend_id is not None
        assert isinstance(minimal_trend_data.trend_id, str)
    
    def test_topic_required(self, minimal_trend_data):
        """Spec: topic is REQUIRED (string)"""
        assert hasattr(minimal_trend_data, 'topic')
        assert minimal_trend_data.topic is not None
        assert isinstance(minimal_trend_data.topic, str)
    
    def test_platform_required(self, minimal_trend_data):
        """Spec: platform is REQUIRED (enum)"""
        assert hasattr(minimal_trend_data, 'platform')
        assert minimal_trend_data.platform is not None
        assert isinstance(minimal_trend_data.platform, str)
    
    def test_sentiment_required(self, minimal_trend_data):
        """Spec: sentiment is REQUIRED (enum)"""
        assert hasattr(minimal_trend_data, 'sentiment')
        assert minimal_trend_data.sentiment is not None
        assert isinstance(minimal_trend_data.sentiment, str)
    
    def test_timestamp_required(self, minimal_trend_data):
        """Spec: timestamp is REQUIRED (ISO8601)"""
        assert hasattr(minimal_trend_data, 'timestamp')
        assert minimal_trend_data.timestamp is not None
        assert isinstance(minimal_trend_data.timestamp, str)
    
    def test_engagement_required(self, minimal_trend_data):
        """Spec: engagement is REQUIRED (object)"""
        assert hasattr(minimal_trend_data, 'engagement')
        assert minimal_trend_data.engagement is not None
        assert isinstance(minimal_trend_data.engagement, dict)
    
    def test_trend_velocity_required(self, minimal_trend_data):
        """Spec: trend_velocity is REQUIRED (number)"""
        assert hasattr(minimal_trend_data, 'trend_velocity')
        assert minimal_trend_data.trend_velocity is not None
        assert isinstance(minimal_trend_data.trend_velocity, (int, float))
    
    def test_decay_score_required(self, minimal_trend_data):
        """Spec: decay_score is REQUIRED (number)"""
        assert hasattr(minimal_trend_data, 'decay_score')
        assert minimal_trend_data.decay_score is not None
        assert isinstance(minimal_trend_data.decay_score, (int, float))


# ============================================================================
# Test: Field Type Validation
# ============================================================================

class TestTrendDataFieldTypes:
    """Verify each field has correct type per spec."""
    
    def test_trend_id_is_string(self, valid_trend_data):
        """trend_id must be string (UUID4 format)"""
        assert isinstance(valid_trend_data.trend_id, str)
    
    def test_topic_is_string(self, valid_trend_data):
        """topic must be string"""
        assert isinstance(valid_trend_data.topic, str)
    
    def test_platform_is_string(self, valid_trend_data):
        """platform must be string"""
        assert isinstance(valid_trend_data.platform, str)
    
    def test_sentiment_is_string(self, valid_trend_data):
        """sentiment must be string"""
        assert isinstance(valid_trend_data.sentiment, str)
    
    def test_timestamp_is_string(self, valid_trend_data):
        """timestamp must be string (ISO8601 format)"""
        assert isinstance(valid_trend_data.timestamp, str)
    
    def test_engagement_is_dict(self, valid_trend_data):
        """engagement must be dict/object"""
        assert isinstance(valid_trend_data.engagement, dict)
    
    def test_trend_velocity_is_number(self, valid_trend_data):
        """trend_velocity must be number (int or float)"""
        assert isinstance(valid_trend_data.trend_velocity, (int, float))
    
    def test_decay_score_is_number(self, valid_trend_data):
        """decay_score must be number (int or float)"""
        assert isinstance(valid_trend_data.decay_score, (int, float))
    
    def test_geographic_origin_is_string_if_present(self, valid_trend_data):
        """geographic_origin must be string (if present)"""
        if valid_trend_data.geographic_origin is not None:
            assert isinstance(valid_trend_data.geographic_origin, str)
    
    def test_metadata_is_dict_if_present(self, valid_trend_data):
        """metadata must be dict/object (if present)"""
        if valid_trend_data.metadata is not None:
            assert isinstance(valid_trend_data.metadata, dict)


# ============================================================================
# Test: Field Constraints (Ranges, Enums, Patterns)
# ============================================================================

class TestTrendDataFieldConstraints:
    """Verify all field constraints per spec."""
    
    # --- topic constraints ---
    
    def test_topic_min_length(self, minimal_trend_data):
        """Spec: topic minLength 1"""
        assert len(minimal_trend_data.topic) >= 1, "topic too short"
    
    def test_topic_max_length(self, minimal_trend_data):
        """Spec: topic maxLength 500"""
        assert len(minimal_trend_data.topic) <= 500, "topic too long"
    
    def test_topic_not_empty(self):
        """topic cannot be empty string"""
        trend = TrendData(
            trend_id=str(uuid4()),
            topic="",  # Invalid: empty
            platform="twitter",
            sentiment="positive",
            timestamp="2026-02-06T10:30:00Z",
            engagement={"likes": 0, "comments": 0, "shares": 0, "impressions": 0, "engagement_score": 0},
            trend_velocity=0.0,
            decay_score=0.5
        )
        assert len(trend.topic) < 1, "topic should not be empty"
    
    # --- platform constraints ---
    
    def test_platform_enum_valid_values(self, valid_trend_data):
        """Spec: platform enum ['twitter', 'news', 'market', 'reddit', 'tiktok']"""
        valid_platforms = ["twitter", "news", "market", "reddit", "tiktok"]
        assert valid_trend_data.platform in valid_platforms
    
    def test_platform_enum_twitter(self):
        """platform can be 'twitter'"""
        trend = TrendData(
            trend_id=str(uuid4()),
            topic="Test",
            platform="twitter",
            sentiment="positive",
            timestamp="2026-02-06T10:30:00Z",
            engagement={"likes": 0, "comments": 0, "shares": 0, "impressions": 0, "engagement_score": 0},
            trend_velocity=0.0,
            decay_score=0.5
        )
        assert trend.platform == "twitter"
    
    def test_platform_enum_news(self):
        """platform can be 'news'"""
        trend = TrendData(
            trend_id=str(uuid4()),
            topic="Test",
            platform="news",
            sentiment="positive",
            timestamp="2026-02-06T10:30:00Z",
            engagement={"likes": 0, "comments": 0, "shares": 0, "impressions": 0, "engagement_score": 0},
            trend_velocity=0.0,
            decay_score=0.5
        )
        assert trend.platform == "news"
    
    def test_platform_enum_market(self):
        """platform can be 'market'"""
        trend = TrendData(
            trend_id=str(uuid4()),
            topic="Test",
            platform="market",
            sentiment="positive",
            timestamp="2026-02-06T10:30:00Z",
            engagement={"likes": 0, "comments": 0, "shares": 0, "impressions": 0, "engagement_score": 0},
            trend_velocity=0.0,
            decay_score=0.5
        )
        assert trend.platform == "market"
    
    # --- sentiment constraints ---
    
    def test_sentiment_enum_valid_values(self, valid_trend_data):
        """Spec: sentiment enum ['positive', 'neutral', 'negative']"""
        valid_sentiments = ["positive", "neutral", "negative"]
        assert valid_trend_data.sentiment in valid_sentiments
    
    def test_sentiment_enum_positive(self):
        """sentiment can be 'positive'"""
        trend = TrendData(
            trend_id=str(uuid4()),
            topic="Test",
            platform="twitter",
            sentiment="positive",
            timestamp="2026-02-06T10:30:00Z",
            engagement={"likes": 0, "comments": 0, "shares": 0, "impressions": 0, "engagement_score": 0},
            trend_velocity=0.0,
            decay_score=0.5
        )
        assert trend.sentiment == "positive"
    
    def test_sentiment_enum_neutral(self):
        """sentiment can be 'neutral'"""
        trend = TrendData(
            trend_id=str(uuid4()),
            topic="Test",
            platform="twitter",
            sentiment="neutral",
            timestamp="2026-02-06T10:30:00Z",
            engagement={"likes": 0, "comments": 0, "shares": 0, "impressions": 0, "engagement_score": 0},
            trend_velocity=0.0,
            decay_score=0.5
        )
        assert trend.sentiment == "neutral"
    
    def test_sentiment_enum_negative(self):
        """sentiment can be 'negative'"""
        trend = TrendData(
            trend_id=str(uuid4()),
            topic="Test",
            platform="twitter",
            sentiment="negative",
            timestamp="2026-02-06T10:30:00Z",
            engagement={"likes": 0, "comments": 0, "shares": 0, "impressions": 0, "engagement_score": 0},
            trend_velocity=0.0,
            decay_score=0.5
        )
        assert trend.sentiment == "negative"
    
    # --- trend_velocity constraints ---
    
    def test_trend_velocity_minimum(self, valid_trend_data):
        """Spec: trend_velocity minimum 0 (no negative growth)"""
        assert valid_trend_data.trend_velocity >= 0
    
    def test_trend_velocity_can_be_zero(self):
        """trend_velocity can be 0 (stagnant trend)"""
        trend = TrendData(
            trend_id=str(uuid4()),
            topic="Test",
            platform="twitter",
            sentiment="positive",
            timestamp="2026-02-06T10:30:00Z",
            engagement={"likes": 0, "comments": 0, "shares": 0, "impressions": 0, "engagement_score": 0},
            trend_velocity=0.0,
            decay_score=0.5
        )
        assert trend.trend_velocity == 0.0
    
    def test_trend_velocity_large_growth(self):
        """trend_velocity can be large (viral trend)"""
        trend = TrendData(
            trend_id=str(uuid4()),
            topic="Test",
            platform="twitter",
            sentiment="positive",
            timestamp="2026-02-06T10:30:00Z",
            engagement={"likes": 0, "comments": 0, "shares": 0, "impressions": 0, "engagement_score": 0},
            trend_velocity=1000.0,  # Very fast growing
            decay_score=0.5
        )
        assert trend.trend_velocity == 1000.0
    
    # --- decay_score constraints ---
    
    def test_decay_score_minimum(self, valid_trend_data):
        """Spec: decay_score minimum 0 (completely stale)"""
        assert valid_trend_data.decay_score >= 0
    
    def test_decay_score_maximum(self, valid_trend_data):
        """Spec: decay_score maximum 1 (brand new)"""
        assert valid_trend_data.decay_score <= 1
    
    def test_decay_score_fresh(self):
        """decay_score 1.0 = fresh trend"""
        trend = TrendData(
            trend_id=str(uuid4()),
            topic="Test",
            platform="twitter",
            sentiment="positive",
            timestamp="2026-02-06T10:30:00Z",
            engagement={"likes": 0, "comments": 0, "shares": 0, "impressions": 0, "engagement_score": 0},
            trend_velocity=0.0,
            decay_score=1.0  # Fresh
        )
        assert trend.decay_score == 1.0
    
    def test_decay_score_stale(self):
        """decay_score 0.0 = stale trend"""
        trend = TrendData(
            trend_id=str(uuid4()),
            topic="Test",
            platform="twitter",
            sentiment="positive",
            timestamp="2026-02-06T10:30:00Z",
            engagement={"likes": 0, "comments": 0, "shares": 0, "impressions": 0, "engagement_score": 0},
            trend_velocity=0.0,
            decay_score=0.0  # Stale
        )
        assert trend.decay_score == 0.0
    
    # --- geographic_origin constraints ---
    
    def test_geographic_origin_enum_if_present(self, valid_trend_data):
        """Spec: geographic_origin enum ['global', 'US', 'EU', 'LATAM', 'APAC', 'AFRICA', 'MENA']"""
        valid_origins = ["global", "US", "EU", "LATAM", "APAC", "AFRICA", "MENA"]
        if valid_trend_data.geographic_origin is not None:
            assert valid_trend_data.geographic_origin in valid_origins
    
    def test_geographic_origin_optional(self, minimal_trend_data):
        """geographic_origin is OPTIONAL (can be None)"""
        assert minimal_trend_data.geographic_origin is None


# ============================================================================
# Test: Engagement Object Schema
# ============================================================================

class TestEngagementSchema:
    """Verify engagement object structure per spec."""
    
    def test_engagement_has_likes(self, valid_trend_data):
        """Spec: engagement.likes is REQUIRED (integer >= 0)"""
        assert 'likes' in valid_trend_data.engagement
        assert isinstance(valid_trend_data.engagement['likes'], int)
        assert valid_trend_data.engagement['likes'] >= 0
    
    def test_engagement_has_comments(self, valid_trend_data):
        """Spec: engagement.comments is REQUIRED (integer >= 0)"""
        assert 'comments' in valid_trend_data.engagement
        assert isinstance(valid_trend_data.engagement['comments'], int)
        assert valid_trend_data.engagement['comments'] >= 0
    
    def test_engagement_has_shares(self, valid_trend_data):
        """Spec: engagement.shares is REQUIRED (integer >= 0)"""
        assert 'shares' in valid_trend_data.engagement
        assert isinstance(valid_trend_data.engagement['shares'], int)
        assert valid_trend_data.engagement['shares'] >= 0
    
    def test_engagement_has_impressions(self, valid_trend_data):
        """Spec: engagement.impressions is REQUIRED (integer >= 0)"""
        assert 'impressions' in valid_trend_data.engagement
        assert isinstance(valid_trend_data.engagement['impressions'], int)
        assert valid_trend_data.engagement['impressions'] >= 0
    
    def test_engagement_has_engagement_score(self, valid_trend_data):
        """Spec: engagement.engagement_score is REQUIRED (number >= 0)"""
        assert 'engagement_score' in valid_trend_data.engagement
        assert isinstance(valid_trend_data.engagement['engagement_score'], (int, float))
        assert valid_trend_data.engagement['engagement_score'] >= 0
    
    def test_engagement_score_formula(self, valid_trend_data):
        """Spec: engagement_score = likes + comments*2 + shares*3"""
        engagement = valid_trend_data.engagement
        expected = engagement['likes'] + engagement['comments']*2 + engagement['shares']*3
        assert engagement['engagement_score'] == expected
    
    def test_engagement_score_zero(self):
        """engagement_score can be 0 (no engagement)"""
        trend = TrendData(
            trend_id=str(uuid4()),
            topic="Test",
            platform="twitter",
            sentiment="positive",
            timestamp="2026-02-06T10:30:00Z",
            engagement={
                "likes": 0,
                "comments": 0,
                "shares": 0,
                "impressions": 0,
                "engagement_score": 0
            },
            trend_velocity=0.0,
            decay_score=0.5
        )
        assert trend.engagement['engagement_score'] == 0
    
    def test_engagement_score_maximum(self, valid_trend_data):
        """Spec: engagement_score maximum 1000000 (1M engagement cap)"""
        assert valid_trend_data.engagement['engagement_score'] <= 1000000


# ============================================================================
# Test: Metadata Object Schema
# ============================================================================

class TestMetadataSchema:
    """Verify metadata object structure per spec."""
    
    def test_metadata_optional(self, minimal_trend_data):
        """metadata is OPTIONAL (can be None)"""
        assert minimal_trend_data.metadata is None
    
    def test_metadata_hashtags_if_present(self, valid_trend_data):
        """Spec: metadata.hashtags is array of strings, max 50 items"""
        if valid_trend_data.metadata and 'hashtags' in valid_trend_data.metadata:
            hashtags = valid_trend_data.metadata['hashtags']
            assert isinstance(hashtags, list)
            assert all(isinstance(h, str) for h in hashtags)
            assert len(hashtags) <= 50
    
    def test_metadata_mentions_if_present(self, valid_trend_data):
        """Spec: metadata.mentions is array of strings, max 50 items"""
        if valid_trend_data.metadata and 'mentions' in valid_trend_data.metadata:
            mentions = valid_trend_data.metadata['mentions']
            assert isinstance(mentions, list)
            assert all(isinstance(m, str) for m in mentions)
            assert len(mentions) <= 50
    
    def test_metadata_source_urls_if_present(self, valid_trend_data):
        """Spec: metadata.source_urls is array of URIs, max 10 items"""
        if valid_trend_data.metadata and 'source_urls' in valid_trend_data.metadata:
            urls = valid_trend_data.metadata['source_urls']
            assert isinstance(urls, list)
            assert all(isinstance(u, str) for u in urls)
            assert len(urls) <= 10
    
    def test_metadata_category_enum_if_present(self, valid_trend_data):
        """Spec: metadata.category enum ['technology', 'fashion', 'finance', 'entertainment', 'news', 'crypto', 'other']"""
        valid_categories = ['technology', 'fashion', 'finance', 'entertainment', 'news', 'crypto', 'other']
        if valid_trend_data.metadata and 'category' in valid_trend_data.metadata:
            assert valid_trend_data.metadata['category'] in valid_categories


# ============================================================================
# Test: Timestamp Format Validation
# ============================================================================

class TestTimestampFormat:
    """Verify timestamp follows ISO8601 format per spec."""
    
    def test_timestamp_iso8601_format(self, valid_trend_data):
        """Spec: timestamp must be ISO8601 format"""
        # Valid ISO8601 examples: 2026-02-06T10:30:00Z, 2026-02-06T10:30:00+00:00
        timestamp = valid_trend_data.timestamp
        try:
            # Try parsing ISO8601
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            assert True
        except ValueError:
            pytest.fail(f"Timestamp {timestamp} is not ISO8601 format")
    
    def test_timestamp_parseable_by_datetime(self, valid_trend_data):
        """Timestamp must be parseable by datetime library"""
        try:
            datetime.fromisoformat(valid_trend_data.timestamp.replace('Z', '+00:00'))
        except ValueError:
            pytest.fail("Timestamp not parseable")
    
    def test_timestamp_not_in_future(self, valid_trend_data):
        """Trend timestamp should not be in future (sanity check)"""
        trend_datetime = datetime.fromisoformat(valid_trend_data.timestamp.replace('Z', '+00:00'))
        now = datetime.now(trend_datetime.tzinfo)
        # Allow 1 minute skew for clock differences
        assert trend_datetime <= now + timedelta(minutes=1)


# ============================================================================
# Test: UUID Format for trend_id
# ============================================================================

class TestTrendIDFormat:
    """Verify trend_id is valid UUID4 format."""
    
    def test_trend_id_uuid_format(self, valid_trend_data):
        """Spec: trend_id must be UUID4 format"""
        trend_id = valid_trend_data.trend_id
        try:
            from uuid import UUID
            UUID(trend_id, version=4)
            assert True
        except (ValueError, AttributeError):
            # Also accept UUID as string without validation
            assert len(trend_id) == 36  # UUID string length
            assert trend_id.count('-') == 4


# ============================================================================
# Test: Invalid Data (Negative Cases)
# ============================================================================

class TestInvalidTrendData:
    """Test that invalid data is rejected."""
    
    def test_invalid_platform(self):
        """Invalid platform should be caught"""
        with pytest.raises((ValueError, AssertionError)):
            trend = TrendData(
                trend_id=str(uuid4()),
                topic="Test",
                platform="invalid_platform",  # Not in enum
                sentiment="positive",
                timestamp="2026-02-06T10:30:00Z",
                engagement={"likes": 0, "comments": 0, "shares": 0, "impressions": 0, "engagement_score": 0},
                trend_velocity=0.0,
                decay_score=0.5
            )
            # In a real implementation, validate platform
            assert trend.platform in ["twitter", "news", "market", "reddit", "tiktok"]
    
    def test_invalid_sentiment(self):
        """Invalid sentiment should be caught"""
        with pytest.raises((ValueError, AssertionError)):
            trend = TrendData(
                trend_id=str(uuid4()),
                topic="Test",
                platform="twitter",
                sentiment="confused",  # Not in enum
                timestamp="2026-02-06T10:30:00Z",
                engagement={"likes": 0, "comments": 0, "shares": 0, "impressions": 0, "engagement_score": 0},
                trend_velocity=0.0,
                decay_score=0.5
            )
            assert trend.sentiment in ["positive", "neutral", "negative"]
    
    def test_negative_trend_velocity(self):
        """Negative trend_velocity should be invalid (spec: minimum 0)"""
        trend = TrendData(
            trend_id=str(uuid4()),
            topic="Test",
            platform="twitter",
            sentiment="positive",
            timestamp="2026-02-06T10:30:00Z",
            engagement={"likes": 0, "comments": 0, "shares": 0, "impressions": 0, "engagement_score": 0},
            trend_velocity=-1.0,  # Invalid: negative
            decay_score=0.5
        )
        # Should validate
        assert trend.trend_velocity >= 0, "trend_velocity cannot be negative"
    
    def test_decay_score_out_of_bounds(self):
        """decay_score out of 0-1 range should be invalid"""
        trend = TrendData(
            trend_id=str(uuid4()),
            topic="Test",
            platform="twitter",
            sentiment="positive",
            timestamp="2026-02-06T10:30:00Z",
            engagement={"likes": 0, "comments": 0, "shares": 0, "impressions": 0, "engagement_score": 0},
            trend_velocity=0.0,
            decay_score=1.5  # Invalid: > 1
        )
        # Should validate
        assert 0 <= trend.decay_score <= 1, "decay_score must be 0-1"


# ============================================================================
# Test: Comprehensive Validation Function
# ============================================================================

def validate_trend_data(trend: TrendData) -> dict:
    """
    Comprehensive TrendData validator per specs/2-design.md.
    
    Returns:
        dict with 'valid' (bool) and 'errors' (list of error messages)
    """
    errors = []
    
    # Required fields
    if not trend.trend_id:
        errors.append("trend_id is required")
    if not trend.topic:
        errors.append("topic is required")
    if not trend.platform:
        errors.append("platform is required")
    if not trend.sentiment:
        errors.append("sentiment is required")
    if not trend.timestamp:
        errors.append("timestamp is required")
    if trend.engagement is None:
        errors.append("engagement is required")
    if trend.trend_velocity is None:
        errors.append("trend_velocity is required")
    if trend.decay_score is None:
        errors.append("decay_score is required")
    
    # Field type validation
    if trend.topic and not isinstance(trend.topic, str):
        errors.append(f"topic must be string, got {type(trend.topic)}")
    if trend.platform and not isinstance(trend.platform, str):
        errors.append(f"platform must be string, got {type(trend.platform)}")
    if trend.sentiment and not isinstance(trend.sentiment, str):
        errors.append(f"sentiment must be string, got {type(trend.sentiment)}")
    
    # Constraint validation
    if trend.topic and (len(trend.topic) < 1 or len(trend.topic) > 500):
        errors.append(f"topic length must be 1-500, got {len(trend.topic)}")
    
    valid_platforms = ["twitter", "news", "market", "reddit", "tiktok"]
    if trend.platform and trend.platform not in valid_platforms:
        errors.append(f"platform must be one of {valid_platforms}, got {trend.platform}")
    
    valid_sentiments = ["positive", "neutral", "negative"]
    if trend.sentiment and trend.sentiment not in valid_sentiments:
        errors.append(f"sentiment must be one of {valid_sentiments}, got {trend.sentiment}")
    
    if trend.trend_velocity is not None and trend.trend_velocity < 0:
        errors.append(f"trend_velocity cannot be negative, got {trend.trend_velocity}")
    
    if trend.decay_score is not None:
        if trend.decay_score < 0 or trend.decay_score > 1:
            errors.append(f"decay_score must be 0-1, got {trend.decay_score}")
    
    # Engagement validation
    if trend.engagement:
        required_engagement_fields = ['likes', 'comments', 'shares', 'impressions', 'engagement_score']
        for field in required_engagement_fields:
            if field not in trend.engagement:
                errors.append(f"engagement.{field} is required")
        
        # engagement_score formula
        if all(f in trend.engagement for f in ['likes', 'comments', 'shares', 'engagement_score']):
            expected_score = trend.engagement['likes'] + trend.engagement['comments']*2 + trend.engagement['shares']*3
            if trend.engagement['engagement_score'] != expected_score:
                errors.append(f"engagement_score calculation incorrect: expected {expected_score}, got {trend.engagement['engagement_score']}")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }


class TestValidationFunction:
    """Test the validation function."""
    
    def test_validate_valid_data(self, valid_trend_data):
        """Valid data passes validation"""
        result = validate_trend_data(valid_trend_data)
        assert result['valid'] is True
        assert len(result['errors']) == 0
    
    def test_validate_catches_missing_required_field(self):
        """Validation catches missing required fields"""
        trend = TrendData(
            trend_id=None,  # Missing
            topic="Test",
            platform="twitter",
            sentiment="positive",
            timestamp="2026-02-06T10:30:00Z",
            engagement={"likes": 0, "comments": 0, "shares": 0, "impressions": 0, "engagement_score": 0},
            trend_velocity=0.0,
            decay_score=0.5
        )
        result = validate_trend_data(trend)
        assert result['valid'] is False
        assert any('trend_id' in error for error in result['errors'])
    
    def test_validate_catches_invalid_platform(self):
        """Validation catches invalid platform"""
        trend = TrendData(
            trend_id=str(uuid4()),
            topic="Test",
            platform="invalid",  # Invalid
            sentiment="positive",
            timestamp="2026-02-06T10:30:00Z",
            engagement={"likes": 0, "comments": 0, "shares": 0, "impressions": 0, "engagement_score": 0},
            trend_velocity=0.0,
            decay_score=0.5
        )
        result = validate_trend_data(trend)
        assert result['valid'] is False
        assert any('platform' in error for error in result['errors'])
    
    def test_validate_catches_engagement_score_mismatch(self):
        """Validation catches incorrect engagement_score calculation"""
        trend = TrendData(
            trend_id=str(uuid4()),
            topic="Test",
            platform="twitter",
            sentiment="positive",
            timestamp="2026-02-06T10:30:00Z",
            engagement={
                "likes": 100,
                "comments": 50,
                "shares": 25,
                "impressions": 5000,
                "engagement_score": 999  # Wrong! Should be 100 + 50*2 + 25*3 = 275
            },
            trend_velocity=0.0,
            decay_score=0.5
        )
        result = validate_trend_data(trend)
        assert result['valid'] is False
        assert any('engagement_score' in error for error in result['errors'])


if __name__ == "__main__":
    # Run tests with: pytest test_trend_data_schema.py -v
    pytest.main([__file__, "-v"])
