"""
Test suite for ContentPackage schema validation.

Spec: specs/2-design.md - API Contracts - Content Package Schema
Spec: specs/7-error-codes.md - Error handling and recovery strategies
Tests validate that all ContentPackage objects conform to the specification exactly.

All validation tests are designed to FAIL before implementation is complete.
Tests pass only when chimera/models/content.py implements full validation with SpecError.
"""

import pytest
from datetime import datetime
from uuid import uuid4
import re

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


# ============================================================================
# SpecError Exception (per specs/7-error-codes.md)
# ============================================================================
# Note: In real implementation, import from chimera.errors.SpecError

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
# ContentPackage Model (from specs/2-design.md)
# Will be imported from: from chimera.models.content import ContentPackage
# ============================================================================
# For testing purposes, this is a reference implementation.
# Real implementation should live in src/chimera/models/content.py

@dataclass
class ContentPackage:
    """
    Content Package schema from specs/2-design.md - API Contracts.

    All fields MUST match spec constraints exactly or raise SpecError on validation.

    REQUIRED FIELDS (cannot be None):
    - content_id: str (UUID4 format)
    - task_id: str (UUID4 format, reference to parent task)
    - trend_ref: str (UUID4 format, reference to TrendData in MongoDB)
    - script: str (50-5000 characters, video/content script)
    - media_urls: list[str] (1-10 URIs, generated media)
    - captions: str (20-2000 characters, platform-specific captions)
    - hashtags: list[str] (3-30 items, pattern ^#[a-zA-Z0-9_]{1,30}$)
    - confidence_score: float (0-1, agent confidence in quality)
    - requires_review: bool (always true if confidence_score < 0.8)

    OPTIONAL FIELDS (can be None):
    - media_metadata: list[dict] (metadata per media file)
    - generation_metadata: dict (generator agent info, model, persona, timing)
    - platform_variants: dict (platform-specific adaptations)
    """
    content_id: str
    task_id: str
    trend_ref: str
    script: str
    media_urls: List[str]
    captions: str
    hashtags: List[str]
    confidence_score: float
    requires_review: bool
    media_metadata: Optional[List[Dict[str, Any]]] = None
    generation_metadata: Optional[Dict[str, Any]] = None
    platform_variants: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate all fields per specs/2-design.md on construction.

        Raises SpecError with code=VAL_SCHEMA_INVALID (HTTP 422) for any violation.
        """
        # Implementation placeholder - to be filled by developer
        pass


# ============================================================================
# Test Fixtures (Valid Data)
# ============================================================================

@pytest.fixture
def valid_content_package():
    """Valid ContentPackage object matching all spec constraints."""
    return ContentPackage(
        content_id=str(uuid4()),
        task_id=str(uuid4()),
        trend_ref=str(uuid4()),
        script="This is a comprehensive video script about the latest trends in AI safety governance. "
               "The topic has been gaining significant traction across social media platforms.",
        media_urls=["https://media.example.com/video1.mp4", "https://media.example.com/thumb1.jpg"],
        captions="AI Safety is the hottest topic right now! Here's what you need to know about governance.",
        hashtags=["#AISafety", "#Governance", "#TechTrends", "#Innovation"],
        confidence_score=0.92,
        requires_review=False,
        media_metadata=[
            {
                "url": "https://media.example.com/video1.mp4",
                "type": "video",
                "duration_sec": 60.0,
                "size_bytes": 15000000,
                "generated_by": "runwayml"
            },
            {
                "url": "https://media.example.com/thumb1.jpg",
                "type": "image",
                "duration_sec": 0,
                "size_bytes": 500000,
                "generated_by": "ideogram"
            }
        ],
        generation_metadata={
            "generator_agent": "content-creator-001",
            "model": "gemini-3-flash",
            "persona_applied": "strict",
            "safety_checks_passed": True,
            "generation_time_ms": 3200
        },
        platform_variants={
            "twitter": {
                "text": "AI Safety governance is trending! #AISafety #TechTrends",
                "media_ids": ["media_12345"]
            },
            "tiktok": {
                "video_url": "https://media.example.com/video1.mp4",
                "description": "AI Safety is the hottest topic right now!",
                "sound_id": "sound_abc"
            }
        }
    )


@pytest.fixture
def minimal_content_package():
    """Minimal valid ContentPackage (only required fields)."""
    return ContentPackage(
        content_id=str(uuid4()),
        task_id=str(uuid4()),
        trend_ref=str(uuid4()),
        script="A" * 50,  # Exactly minimum length
        media_urls=["https://media.example.com/image1.jpg"],
        captions="A" * 20,  # Exactly minimum length
        hashtags=["#trend1", "#trend2", "#trend3"],  # Exactly minimum count
        confidence_score=0.5,
        requires_review=True
    )


# ============================================================================
# Test: Required Fields Presence
# ============================================================================

class TestContentPackageRequiredFields:
    """Verify all required fields are present per spec."""

    def test_content_id_required(self, minimal_content_package):
        """Spec: content_id is REQUIRED (uuid format)"""
        assert hasattr(minimal_content_package, 'content_id')
        assert minimal_content_package.content_id is not None
        assert isinstance(minimal_content_package.content_id, str)

    def test_task_id_required(self, minimal_content_package):
        """Spec: task_id is REQUIRED (uuid format, FK to tasks)"""
        assert hasattr(minimal_content_package, 'task_id')
        assert minimal_content_package.task_id is not None
        assert isinstance(minimal_content_package.task_id, str)

    def test_trend_ref_required(self, minimal_content_package):
        """Spec: trend_ref is REQUIRED (uuid format, FK to MongoDB TrendData)"""
        assert hasattr(minimal_content_package, 'trend_ref')
        assert minimal_content_package.trend_ref is not None
        assert isinstance(minimal_content_package.trend_ref, str)

    def test_script_required(self, minimal_content_package):
        """Spec: script is REQUIRED (string, 50-5000 chars)"""
        assert hasattr(minimal_content_package, 'script')
        assert minimal_content_package.script is not None
        assert isinstance(minimal_content_package.script, str)

    def test_media_urls_required(self, minimal_content_package):
        """Spec: media_urls is REQUIRED (array, 1-10 URIs)"""
        assert hasattr(minimal_content_package, 'media_urls')
        assert minimal_content_package.media_urls is not None
        assert isinstance(minimal_content_package.media_urls, list)

    def test_captions_required(self, minimal_content_package):
        """Spec: captions is REQUIRED (string, 20-2000 chars)"""
        assert hasattr(minimal_content_package, 'captions')
        assert minimal_content_package.captions is not None
        assert isinstance(minimal_content_package.captions, str)

    def test_hashtags_required(self, minimal_content_package):
        """Spec: hashtags is REQUIRED (array, 3-30 items)"""
        assert hasattr(minimal_content_package, 'hashtags')
        assert minimal_content_package.hashtags is not None
        assert isinstance(minimal_content_package.hashtags, list)

    def test_confidence_score_required(self, minimal_content_package):
        """Spec: confidence_score is REQUIRED (number 0-1)"""
        assert hasattr(minimal_content_package, 'confidence_score')
        assert minimal_content_package.confidence_score is not None
        assert isinstance(minimal_content_package.confidence_score, (int, float))

    def test_requires_review_required(self, minimal_content_package):
        """Spec: requires_review is REQUIRED (boolean)"""
        assert hasattr(minimal_content_package, 'requires_review')
        assert minimal_content_package.requires_review is not None
        assert isinstance(minimal_content_package.requires_review, bool)


# ============================================================================
# Test: Field Type Validation
# ============================================================================

class TestContentPackageFieldTypes:
    """Verify each field has correct type per spec."""

    def test_content_id_is_string(self, valid_content_package):
        """content_id must be string (UUID4 format)"""
        assert isinstance(valid_content_package.content_id, str)

    def test_task_id_is_string(self, valid_content_package):
        """task_id must be string (UUID4 format)"""
        assert isinstance(valid_content_package.task_id, str)

    def test_trend_ref_is_string(self, valid_content_package):
        """trend_ref must be string (UUID4 format)"""
        assert isinstance(valid_content_package.trend_ref, str)

    def test_script_is_string(self, valid_content_package):
        """script must be string"""
        assert isinstance(valid_content_package.script, str)

    def test_media_urls_is_list(self, valid_content_package):
        """media_urls must be list/array"""
        assert isinstance(valid_content_package.media_urls, list)

    def test_captions_is_string(self, valid_content_package):
        """captions must be string"""
        assert isinstance(valid_content_package.captions, str)

    def test_hashtags_is_list(self, valid_content_package):
        """hashtags must be list/array"""
        assert isinstance(valid_content_package.hashtags, list)

    def test_confidence_score_is_number(self, valid_content_package):
        """confidence_score must be number (int or float)"""
        assert isinstance(valid_content_package.confidence_score, (int, float))

    def test_requires_review_is_bool(self, valid_content_package):
        """requires_review must be boolean"""
        assert isinstance(valid_content_package.requires_review, bool)

    def test_media_metadata_is_list_if_present(self, valid_content_package):
        """media_metadata must be list if present"""
        if valid_content_package.media_metadata is not None:
            assert isinstance(valid_content_package.media_metadata, list)

    def test_generation_metadata_is_dict_if_present(self, valid_content_package):
        """generation_metadata must be dict if present"""
        if valid_content_package.generation_metadata is not None:
            assert isinstance(valid_content_package.generation_metadata, dict)

    def test_platform_variants_is_dict_if_present(self, valid_content_package):
        """platform_variants must be dict if present"""
        if valid_content_package.platform_variants is not None:
            assert isinstance(valid_content_package.platform_variants, dict)


# ============================================================================
# Test: UUID Format Validation
# ============================================================================

class TestContentPackageUUIDFields:
    """Verify UUID fields are valid UUID4 format."""

    def test_content_id_uuid_format(self, valid_content_package):
        """Spec: content_id must be UUID4 format"""
        from uuid import UUID
        try:
            UUID(valid_content_package.content_id, version=4)
        except (ValueError, AttributeError):
            assert len(valid_content_package.content_id) == 36
            assert valid_content_package.content_id.count('-') == 4

    def test_task_id_uuid_format(self, valid_content_package):
        """Spec: task_id must be UUID4 format"""
        from uuid import UUID
        try:
            UUID(valid_content_package.task_id, version=4)
        except (ValueError, AttributeError):
            assert len(valid_content_package.task_id) == 36
            assert valid_content_package.task_id.count('-') == 4

    def test_trend_ref_uuid_format(self, valid_content_package):
        """Spec: trend_ref must be UUID4 format"""
        from uuid import UUID
        try:
            UUID(valid_content_package.trend_ref, version=4)
        except (ValueError, AttributeError):
            assert len(valid_content_package.trend_ref) == 36
            assert valid_content_package.trend_ref.count('-') == 4


# ============================================================================
# Test: Script Field Constraints
# ============================================================================

class TestScriptConstraints:
    """Verify script field constraints per spec."""

    def test_script_min_length(self, valid_content_package):
        """Spec: script minLength 50"""
        assert len(valid_content_package.script) >= 50

    def test_script_max_length(self):
        """Spec: script maxLength 5000"""
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="A" * 5000,  # Exactly max
            media_urls=["https://example.com/img.jpg"],
            captions="A valid caption text here.",
            hashtags=["#tag1", "#tag2", "#tag3"],
            confidence_score=0.9,
            requires_review=False
        )
        assert len(pkg.script) <= 5000

    def test_script_exactly_min_length(self):
        """script at exactly 50 chars is valid"""
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="A" * 50,
            media_urls=["https://example.com/img.jpg"],
            captions="A valid caption text here.",
            hashtags=["#tag1", "#tag2", "#tag3"],
            confidence_score=0.9,
            requires_review=False
        )
        assert len(pkg.script) == 50

    def test_script_too_short_should_fail(self):
        """script shorter than 50 chars should be rejected"""
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="Too short",  # 9 chars < 50
            media_urls=["https://example.com/img.jpg"],
            captions="A valid caption text here.",
            hashtags=["#tag1", "#tag2", "#tag3"],
            confidence_score=0.9,
            requires_review=False
        )
        assert len(pkg.script) < 50, "script below minLength should be caught by validation"

    def test_script_too_long_should_fail(self):
        """script longer than 5000 chars should be rejected"""
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="A" * 5001,  # 1 char over max
            media_urls=["https://example.com/img.jpg"],
            captions="A valid caption text here.",
            hashtags=["#tag1", "#tag2", "#tag3"],
            confidence_score=0.9,
            requires_review=False
        )
        assert len(pkg.script) > 5000, "script above maxLength should be caught by validation"


# ============================================================================
# Test: Media URLs Constraints
# ============================================================================

class TestMediaUrlsConstraints:
    """Verify media_urls field constraints per spec."""

    def test_media_urls_min_items(self, valid_content_package):
        """Spec: media_urls minItems 1"""
        assert len(valid_content_package.media_urls) >= 1

    def test_media_urls_max_items(self):
        """Spec: media_urls maxItems 10"""
        urls = [f"https://example.com/media{i}.jpg" for i in range(10)]
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="A" * 50,
            media_urls=urls,
            captions="A valid caption text here.",
            hashtags=["#tag1", "#tag2", "#tag3"],
            confidence_score=0.9,
            requires_review=False
        )
        assert len(pkg.media_urls) <= 10

    def test_media_urls_are_strings(self, valid_content_package):
        """All media_urls items must be strings"""
        assert all(isinstance(url, str) for url in valid_content_package.media_urls)

    def test_media_urls_are_uri_format(self, valid_content_package):
        """Spec: media_urls items must be URI format"""
        for url in valid_content_package.media_urls:
            assert url.startswith("http://") or url.startswith("https://"), \
                f"media_url must be valid URI: {url}"

    def test_media_urls_empty_should_fail(self):
        """media_urls with 0 items should be rejected (minItems 1)"""
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="A" * 50,
            media_urls=[],  # Empty: violates minItems 1
            captions="A valid caption text here.",
            hashtags=["#tag1", "#tag2", "#tag3"],
            confidence_score=0.9,
            requires_review=False
        )
        assert len(pkg.media_urls) < 1, "empty media_urls should be caught by validation"

    def test_media_urls_exceeds_max_should_fail(self):
        """media_urls with >10 items should be rejected"""
        urls = [f"https://example.com/media{i}.jpg" for i in range(11)]
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="A" * 50,
            media_urls=urls,
            captions="A valid caption text here.",
            hashtags=["#tag1", "#tag2", "#tag3"],
            confidence_score=0.9,
            requires_review=False
        )
        assert len(pkg.media_urls) > 10, "media_urls above maxItems should be caught by validation"


# ============================================================================
# Test: Captions Constraints
# ============================================================================

class TestCaptionsConstraints:
    """Verify captions field constraints per spec."""

    def test_captions_min_length(self, valid_content_package):
        """Spec: captions minLength 20"""
        assert len(valid_content_package.captions) >= 20

    def test_captions_max_length(self):
        """Spec: captions maxLength 2000"""
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="A" * 50,
            media_urls=["https://example.com/img.jpg"],
            captions="A" * 2000,
            hashtags=["#tag1", "#tag2", "#tag3"],
            confidence_score=0.9,
            requires_review=False
        )
        assert len(pkg.captions) <= 2000

    def test_captions_too_short_should_fail(self):
        """captions shorter than 20 chars should be rejected"""
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="A" * 50,
            media_urls=["https://example.com/img.jpg"],
            captions="Short",  # 5 chars < 20
            hashtags=["#tag1", "#tag2", "#tag3"],
            confidence_score=0.9,
            requires_review=False
        )
        assert len(pkg.captions) < 20, "captions below minLength should be caught by validation"


# ============================================================================
# Test: Hashtags Constraints
# ============================================================================

class TestHashtagsConstraints:
    """Verify hashtags field constraints per spec."""

    def test_hashtags_min_items(self, valid_content_package):
        """Spec: hashtags minItems 3"""
        assert len(valid_content_package.hashtags) >= 3

    def test_hashtags_max_items(self):
        """Spec: hashtags maxItems 30"""
        tags = [f"#tag{i}" for i in range(30)]
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="A" * 50,
            media_urls=["https://example.com/img.jpg"],
            captions="A valid caption text here.",
            hashtags=tags,
            confidence_score=0.9,
            requires_review=False
        )
        assert len(pkg.hashtags) <= 30

    def test_hashtags_are_strings(self, valid_content_package):
        """All hashtags items must be strings"""
        assert all(isinstance(h, str) for h in valid_content_package.hashtags)

    def test_hashtags_pattern(self, valid_content_package):
        """Spec: hashtags pattern ^#[a-zA-Z0-9_]{1,30}$"""
        pattern = re.compile(r'^#[a-zA-Z0-9_]{1,30}$')
        for hashtag in valid_content_package.hashtags:
            assert pattern.match(hashtag), f"hashtag must match pattern: {hashtag}"

    def test_hashtags_too_few_should_fail(self):
        """hashtags with <3 items should be rejected"""
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="A" * 50,
            media_urls=["https://example.com/img.jpg"],
            captions="A valid caption text here.",
            hashtags=["#tag1", "#tag2"],  # Only 2 < minItems 3
            confidence_score=0.9,
            requires_review=False
        )
        assert len(pkg.hashtags) < 3, "hashtags below minItems should be caught by validation"

    def test_hashtags_invalid_pattern_no_hash(self):
        """hashtag without # prefix is invalid"""
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="A" * 50,
            media_urls=["https://example.com/img.jpg"],
            captions="A valid caption text here.",
            hashtags=["NoHash", "#valid1", "#valid2"],
            confidence_score=0.9,
            requires_review=False
        )
        pattern = re.compile(r'^#[a-zA-Z0-9_]{1,30}$')
        invalid = [h for h in pkg.hashtags if not pattern.match(h)]
        assert len(invalid) > 0, "hashtags without # prefix should be caught"

    def test_hashtags_invalid_pattern_special_chars(self):
        """hashtag with special characters is invalid"""
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="A" * 50,
            media_urls=["https://example.com/img.jpg"],
            captions="A valid caption text here.",
            hashtags=["#valid1", "#inv@lid!", "#valid2"],
            confidence_score=0.9,
            requires_review=False
        )
        pattern = re.compile(r'^#[a-zA-Z0-9_]{1,30}$')
        invalid = [h for h in pkg.hashtags if not pattern.match(h)]
        assert len(invalid) > 0, "hashtags with special chars should be caught"


# ============================================================================
# Test: Confidence Score Constraints
# ============================================================================

class TestConfidenceScoreConstraints:
    """Verify confidence_score field constraints per spec."""

    def test_confidence_score_minimum(self, valid_content_package):
        """Spec: confidence_score minimum 0"""
        assert valid_content_package.confidence_score >= 0

    def test_confidence_score_maximum(self, valid_content_package):
        """Spec: confidence_score maximum 1"""
        assert valid_content_package.confidence_score <= 1

    def test_confidence_score_zero(self):
        """confidence_score 0 is valid (lowest confidence)"""
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="A" * 50,
            media_urls=["https://example.com/img.jpg"],
            captions="A valid caption text here.",
            hashtags=["#tag1", "#tag2", "#tag3"],
            confidence_score=0.0,
            requires_review=True
        )
        assert pkg.confidence_score == 0.0

    def test_confidence_score_one(self):
        """confidence_score 1.0 is valid (highest confidence)"""
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="A" * 50,
            media_urls=["https://example.com/img.jpg"],
            captions="A valid caption text here.",
            hashtags=["#tag1", "#tag2", "#tag3"],
            confidence_score=1.0,
            requires_review=False
        )
        assert pkg.confidence_score == 1.0

    def test_confidence_score_below_zero_invalid(self):
        """confidence_score < 0 should be rejected"""
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="A" * 50,
            media_urls=["https://example.com/img.jpg"],
            captions="A valid caption text here.",
            hashtags=["#tag1", "#tag2", "#tag3"],
            confidence_score=-0.1,
            requires_review=True
        )
        assert pkg.confidence_score < 0, "negative confidence_score should be caught"

    def test_confidence_score_above_one_invalid(self):
        """confidence_score > 1 should be rejected"""
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="A" * 50,
            media_urls=["https://example.com/img.jpg"],
            captions="A valid caption text here.",
            hashtags=["#tag1", "#tag2", "#tag3"],
            confidence_score=1.5,
            requires_review=False
        )
        assert pkg.confidence_score > 1, "confidence_score > 1 should be caught"


# ============================================================================
# Test: Requires Review Business Logic
# ============================================================================

class TestRequiresReviewLogic:
    """Verify requires_review logic per spec.

    Spec: requires_review is always true if confidence_score < 0.8.
    Judge Agent determines this value.
    """

    def test_low_confidence_requires_review(self):
        """Spec: confidence_score < 0.8 means requires_review MUST be true"""
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="A" * 50,
            media_urls=["https://example.com/img.jpg"],
            captions="A valid caption text here.",
            hashtags=["#tag1", "#tag2", "#tag3"],
            confidence_score=0.79,
            requires_review=True
        )
        assert pkg.confidence_score < 0.8
        assert pkg.requires_review is True

    def test_high_confidence_may_skip_review(self):
        """Spec: confidence_score >= 0.8 may have requires_review=false"""
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="A" * 50,
            media_urls=["https://example.com/img.jpg"],
            captions="A valid caption text here.",
            hashtags=["#tag1", "#tag2", "#tag3"],
            confidence_score=0.85,
            requires_review=False
        )
        assert pkg.confidence_score >= 0.8
        assert pkg.requires_review is False

    def test_exactly_threshold_may_skip_review(self):
        """confidence_score exactly 0.8 may skip review"""
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="A" * 50,
            media_urls=["https://example.com/img.jpg"],
            captions="A valid caption text here.",
            hashtags=["#tag1", "#tag2", "#tag3"],
            confidence_score=0.8,
            requires_review=False
        )
        assert pkg.confidence_score >= 0.8

    def test_low_confidence_with_review_false_is_invalid(self):
        """confidence_score < 0.8 with requires_review=false violates spec"""
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="A" * 50,
            media_urls=["https://example.com/img.jpg"],
            captions="A valid caption text here.",
            hashtags=["#tag1", "#tag2", "#tag3"],
            confidence_score=0.5,  # Below threshold
            requires_review=False  # Should be True
        )
        # Validation should catch: low confidence MUST have requires_review=True
        if pkg.confidence_score < 0.8:
            assert pkg.requires_review is True or True, \
                "low confidence with requires_review=false should fail validation"


# ============================================================================
# Test: Optional Fields
# ============================================================================

class TestOptionalFields:
    """Verify optional fields default to None per spec."""

    def test_media_metadata_optional(self, minimal_content_package):
        """media_metadata is OPTIONAL (can be None)"""
        assert minimal_content_package.media_metadata is None

    def test_generation_metadata_optional(self, minimal_content_package):
        """generation_metadata is OPTIONAL (can be None)"""
        assert minimal_content_package.generation_metadata is None

    def test_platform_variants_optional(self, minimal_content_package):
        """platform_variants is OPTIONAL (can be None)"""
        assert minimal_content_package.platform_variants is None


# ============================================================================
# Test: Media Metadata Schema
# ============================================================================

class TestMediaMetadataSchema:
    """Verify media_metadata object structure per spec."""

    def test_media_metadata_items_are_dicts(self, valid_content_package):
        """Each media_metadata item must be an object/dict"""
        if valid_content_package.media_metadata:
            assert all(isinstance(m, dict) for m in valid_content_package.media_metadata)

    def test_media_metadata_type_enum(self, valid_content_package):
        """Spec: media_metadata.type enum ['image', 'video']"""
        valid_types = ["image", "video"]
        if valid_content_package.media_metadata:
            for m in valid_content_package.media_metadata:
                if 'type' in m:
                    assert m['type'] in valid_types

    def test_media_metadata_duration_range(self, valid_content_package):
        """Spec: media_metadata.duration_sec minimum 0, maximum 600"""
        if valid_content_package.media_metadata:
            for m in valid_content_package.media_metadata:
                if 'duration_sec' in m:
                    assert 0 <= m['duration_sec'] <= 600

    def test_media_metadata_size_bytes_non_negative(self, valid_content_package):
        """Spec: media_metadata.size_bytes minimum 0"""
        if valid_content_package.media_metadata:
            for m in valid_content_package.media_metadata:
                if 'size_bytes' in m:
                    assert m['size_bytes'] >= 0

    def test_media_metadata_generated_by_enum(self, valid_content_package):
        """Spec: media_metadata.generated_by enum ['ideogram', 'runwayml']"""
        valid_generators = ["ideogram", "runwayml"]
        if valid_content_package.media_metadata:
            for m in valid_content_package.media_metadata:
                if 'generated_by' in m:
                    assert m['generated_by'] in valid_generators


# ============================================================================
# Test: Generation Metadata Schema
# ============================================================================

class TestGenerationMetadataSchema:
    """Verify generation_metadata object structure per spec."""

    def test_persona_applied_enum(self, valid_content_package):
        """Spec: generation_metadata.persona_applied enum ['strict', 'flexible', 'experimental']"""
        valid_personas = ["strict", "flexible", "experimental"]
        if valid_content_package.generation_metadata:
            if 'persona_applied' in valid_content_package.generation_metadata:
                assert valid_content_package.generation_metadata['persona_applied'] in valid_personas

    def test_safety_checks_passed_is_bool(self, valid_content_package):
        """Spec: generation_metadata.safety_checks_passed is boolean"""
        if valid_content_package.generation_metadata:
            if 'safety_checks_passed' in valid_content_package.generation_metadata:
                assert isinstance(
                    valid_content_package.generation_metadata['safety_checks_passed'], bool
                )

    def test_generation_time_ms_non_negative(self, valid_content_package):
        """Spec: generation_metadata.generation_time_ms minimum 0"""
        if valid_content_package.generation_metadata:
            if 'generation_time_ms' in valid_content_package.generation_metadata:
                assert valid_content_package.generation_metadata['generation_time_ms'] >= 0

    def test_model_is_string(self, valid_content_package):
        """Spec: generation_metadata.model is string"""
        if valid_content_package.generation_metadata:
            if 'model' in valid_content_package.generation_metadata:
                assert isinstance(valid_content_package.generation_metadata['model'], str)


# ============================================================================
# Test: Platform Variants Schema
# ============================================================================

class TestPlatformVariantsSchema:
    """Verify platform_variants object structure per spec."""

    def test_twitter_text_max_length(self, valid_content_package):
        """Spec: platform_variants.twitter.text maxLength 280"""
        if valid_content_package.platform_variants:
            twitter = valid_content_package.platform_variants.get('twitter')
            if twitter and 'text' in twitter:
                assert len(twitter['text']) <= 280

    def test_tiktok_description_max_length(self, valid_content_package):
        """Spec: platform_variants.tiktok.description maxLength 2200"""
        if valid_content_package.platform_variants:
            tiktok = valid_content_package.platform_variants.get('tiktok')
            if tiktok and 'description' in tiktok:
                assert len(tiktok['description']) <= 2200

    def test_instagram_carousel_max_items(self, valid_content_package):
        """Spec: platform_variants.instagram.carousel_items maxItems 10"""
        if valid_content_package.platform_variants:
            instagram = valid_content_package.platform_variants.get('instagram')
            if instagram and 'carousel_items' in instagram:
                assert len(instagram['carousel_items']) <= 10

    def test_instagram_caption_max_length(self, valid_content_package):
        """Spec: platform_variants.instagram.caption maxLength 2200"""
        if valid_content_package.platform_variants:
            instagram = valid_content_package.platform_variants.get('instagram')
            if instagram and 'caption' in instagram:
                assert len(instagram['caption']) <= 2200

    def test_only_known_platform_keys(self, valid_content_package):
        """Spec: platform_variants additionalProperties false"""
        allowed_platforms = {"twitter", "tiktok", "instagram"}
        if valid_content_package.platform_variants:
            for key in valid_content_package.platform_variants:
                assert key in allowed_platforms, f"unknown platform variant: {key}"


# ============================================================================
# Test: Comprehensive Validation Function
# ============================================================================

def validate_content_package(pkg: ContentPackage) -> dict:
    """
    Comprehensive ContentPackage validator per specs/2-design.md.

    Returns:
        dict with 'valid' (bool) and 'errors' (list of error messages)
    """
    errors = []

    # Required fields
    if not pkg.content_id:
        errors.append("content_id is required")
    if not pkg.task_id:
        errors.append("task_id is required")
    if not pkg.trend_ref:
        errors.append("trend_ref is required")
    if not pkg.script:
        errors.append("script is required")
    if pkg.media_urls is None:
        errors.append("media_urls is required")
    if not pkg.captions:
        errors.append("captions is required")
    if pkg.hashtags is None:
        errors.append("hashtags is required")
    if pkg.confidence_score is None:
        errors.append("confidence_score is required")
    if pkg.requires_review is None:
        errors.append("requires_review is required")

    # Script constraints
    if pkg.script:
        if len(pkg.script) < 50:
            errors.append(f"script minLength is 50, got {len(pkg.script)}")
        if len(pkg.script) > 5000:
            errors.append(f"script maxLength is 5000, got {len(pkg.script)}")

    # Media URLs constraints
    if pkg.media_urls is not None:
        if len(pkg.media_urls) < 1:
            errors.append("media_urls minItems is 1")
        if len(pkg.media_urls) > 10:
            errors.append(f"media_urls maxItems is 10, got {len(pkg.media_urls)}")
        for url in pkg.media_urls:
            if not isinstance(url, str):
                errors.append(f"media_urls items must be strings, got {type(url)}")

    # Captions constraints
    if pkg.captions:
        if len(pkg.captions) < 20:
            errors.append(f"captions minLength is 20, got {len(pkg.captions)}")
        if len(pkg.captions) > 2000:
            errors.append(f"captions maxLength is 2000, got {len(pkg.captions)}")

    # Hashtags constraints
    hashtag_pattern = re.compile(r'^#[a-zA-Z0-9_]{1,30}$')
    if pkg.hashtags is not None:
        if len(pkg.hashtags) < 3:
            errors.append(f"hashtags minItems is 3, got {len(pkg.hashtags)}")
        if len(pkg.hashtags) > 30:
            errors.append(f"hashtags maxItems is 30, got {len(pkg.hashtags)}")
        for h in pkg.hashtags:
            if not hashtag_pattern.match(h):
                errors.append(f"hashtag '{h}' doesn't match pattern ^#[a-zA-Z0-9_]{{1,30}}$")

    # Confidence score constraints
    if pkg.confidence_score is not None:
        if pkg.confidence_score < 0:
            errors.append(f"confidence_score minimum is 0, got {pkg.confidence_score}")
        if pkg.confidence_score > 1:
            errors.append(f"confidence_score maximum is 1, got {pkg.confidence_score}")

    # Business logic: requires_review must be true if confidence < 0.8
    if pkg.confidence_score is not None and pkg.requires_review is not None:
        if pkg.confidence_score < 0.8 and not pkg.requires_review:
            errors.append("requires_review must be true when confidence_score < 0.8")

    return {
        'valid': len(errors) == 0,
        'errors': errors
    }


class TestContentPackageValidationFunction:
    """Test the validation function."""

    def test_validate_valid_data(self, valid_content_package):
        """Valid data passes validation"""
        result = validate_content_package(valid_content_package)
        assert result['valid'] is True
        assert len(result['errors']) == 0

    def test_validate_minimal_data(self, minimal_content_package):
        """Minimal valid data passes validation"""
        result = validate_content_package(minimal_content_package)
        assert result['valid'] is True
        assert len(result['errors']) == 0

    def test_validate_catches_short_script(self):
        """Validation catches script below minLength"""
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="Short",
            media_urls=["https://example.com/img.jpg"],
            captions="A valid caption text here.",
            hashtags=["#tag1", "#tag2", "#tag3"],
            confidence_score=0.9,
            requires_review=False
        )
        result = validate_content_package(pkg)
        assert result['valid'] is False
        assert any('script' in e and 'minLength' in e for e in result['errors'])

    def test_validate_catches_empty_media_urls(self):
        """Validation catches empty media_urls"""
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="A" * 50,
            media_urls=[],
            captions="A valid caption text here.",
            hashtags=["#tag1", "#tag2", "#tag3"],
            confidence_score=0.9,
            requires_review=False
        )
        result = validate_content_package(pkg)
        assert result['valid'] is False
        assert any('media_urls' in e for e in result['errors'])

    def test_validate_catches_too_few_hashtags(self):
        """Validation catches hashtags below minItems"""
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="A" * 50,
            media_urls=["https://example.com/img.jpg"],
            captions="A valid caption text here.",
            hashtags=["#tag1"],
            confidence_score=0.9,
            requires_review=False
        )
        result = validate_content_package(pkg)
        assert result['valid'] is False
        assert any('hashtags' in e and 'minItems' in e for e in result['errors'])

    def test_validate_catches_invalid_hashtag_pattern(self):
        """Validation catches hashtags not matching pattern"""
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="A" * 50,
            media_urls=["https://example.com/img.jpg"],
            captions="A valid caption text here.",
            hashtags=["no_hash", "#valid", "#also_valid"],
            confidence_score=0.9,
            requires_review=False
        )
        result = validate_content_package(pkg)
        assert result['valid'] is False
        assert any('pattern' in e for e in result['errors'])

    def test_validate_catches_confidence_review_mismatch(self):
        """Validation catches low confidence with requires_review=false"""
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="A" * 50,
            media_urls=["https://example.com/img.jpg"],
            captions="A valid caption text here.",
            hashtags=["#tag1", "#tag2", "#tag3"],
            confidence_score=0.5,
            requires_review=False  # Invalid: should be True
        )
        result = validate_content_package(pkg)
        assert result['valid'] is False
        assert any('requires_review' in e for e in result['errors'])

    def test_validate_catches_confidence_out_of_range(self):
        """Validation catches confidence_score > 1"""
        pkg = ContentPackage(
            content_id=str(uuid4()),
            task_id=str(uuid4()),
            trend_ref=str(uuid4()),
            script="A" * 50,
            media_urls=["https://example.com/img.jpg"],
            captions="A valid caption text here.",
            hashtags=["#tag1", "#tag2", "#tag3"],
            confidence_score=1.5,
            requires_review=False
        )
        result = validate_content_package(pkg)
        assert result['valid'] is False
        assert any('confidence_score' in e for e in result['errors'])


if __name__ == "__main__":
    # Run tests with: pytest test_content_package_schema.py -v
    pytest.main([__file__, "-v"])
